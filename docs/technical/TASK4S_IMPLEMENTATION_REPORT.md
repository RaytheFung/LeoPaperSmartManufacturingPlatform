# TASK4S Implementation Report

## Outcome

Task 4S passed.

This task stayed decision/shadow-only:

- no active DB write was performed
- no active `good_qty` / `scrap_qty` semantics changed
- no ML logic or artifacts changed
- no UI work was started
- no Task 4T work was started

## Reconstruction Summary

- Task 4R is closed.
- Task 4R added first-class `csi_qty_*` observability but intentionally left active quantity semantics unchanged.
- The smallest safe Task 4S question was whether a future replacement contract could be defined narrowly enough to evaluate read-only and honestly, without touching active quantity.
- The chosen shadow comparator keeps dominant-event row identity fixed and evaluates a future production-share quantity contract only on fully eligible dominant-event groups.

## Exact Current Quantity Contract

The current live contract remains:

- dominant-event row identity via `csi_source_row_hash`
- persisted row `production_minutes` from the Task 4P blended minute contract
- `good_qty` / `scrap_qty` still allocated from dominant-event production basis minutes

In code:

- `core/gold_fact_builder.py`
  - `_overlay_fact_row_with_csi(...)` fixes dominant-event identity
  - `_csi_quantity_basis_minutes_from_row(...)` prefers dominant-event production basis over persisted row `production_minutes`
  - `_build_csi_quantity_updates(...)` allocates quantity by dominant-event basis share
- `core/fact_machine_hour_repair.py`
  - `temp_task4g_csi_dominant` fixes dominant-event quantity identity
  - `temp_task4g_csi_basis` sums dominant-event basis minutes by `source_row_hash`
  - the final quantity update uses `dominant_production_minutes / basis_minutes`
- `core/canonical_materializer.py`
  - `_apply_csi_quantity(...)` reuses the same builder contract rather than defining a new one

## Exact Shadow / Proposed Replacement Contract

Task 4S defines a read-only shadow comparator only:

- contract name:
  - `shadow_production_minutes_share_on_fully_eligible_dominant_groups`
- dominant-event identity stays fixed by `csi_source_row_hash`
- a dominant-event group is eligible only when every quantity-bearing row in that group has:
  - non-null positive landed `csi_qty_row_basis_minutes`
  - positive persisted `production_minutes`
  - no landed minute-budget anomaly flag
- for eligible groups only:
  - shadow event total = current group total quantity
  - shadow row share = row `production_minutes` / group total `production_minutes`
  - shadow quantity is allocated by that production share
- for ineligible groups:
  - shadow quantity falls back to current quantity
  - rows are explicitly marked retained-current and not treated as live-replacement candidates

This is the narrowest safe replacement contract because it:

- does not invent new row identity
- does not force quantity onto null-basis rows
- excludes anomaly rows from replacement candidacy
- conserves totals for eligible groups and therefore for the whole Jan-Jun snapshot when ineligible groups retain current quantity

## Eligibility Rule For Shadow Comparison

Eligible for replacement:

- quantity-bearing overlap row
- same `csi_source_row_hash` group is fully eligible
- row has positive landed `csi_qty_row_basis_minutes`
- row has positive persisted `production_minutes`
- row is not anomaly-flagged

Ineligible:

- landed quantity basis is null or non-positive
- minute-budget anomaly flag is set
- source hash missing
- persisted `production_minutes` is missing or non-positive

## Treatment Of Null-Basis Rows

- null landed basis rows are not forced into the replacement candidate set
- they retain current quantity in the shadow output
- they are counted explicitly as ineligible
- they are the main reason a full live replacement is not yet safe

## Treatment Of Anomaly Rows

- anomaly rows are excluded from replacement candidacy
- they retain current quantity in the shadow output
- they are still visible in diagnostics

On the current live snapshot, anomaly distortion is small:

- `1` quantity-bearing overlap row is excluded for anomaly

## Code Changes

- `core/csi_quantity_shadow.py`
  - new pure read-only shadow comparator helper
- `tests/test_csi_quantity_shadow.py`
  - focused helper tests, including the required anchor rows:
    - `035-017 @ 2025-06-03T05:00:00`
    - `035-018 @ 2025-02-17T15:00:00`
    - `166-002 @ 2025-04-17T14:00:00`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/csi_quantity_shadow.py tests/test_csi_quantity_shadow.py
./.conda311/bin/python -m unittest tests.test_csi_quantity_shadow
```

Result:

- `Ran 4 tests`
- `OK`

## Exact Read-Only DB Diagnostics

All active diagnostics were read-only and used the live runtime DB path from `core/runtime_paths.py`.

Scope:

- `fact_machine_hour`
- `hour_ts >= '2025-01-01T00:00:00'`
- `hour_ts < '2025-07-01T00:00:00'`
- `multiple_csi_overlap_flag = 1`

Current live read-only snapshot:

- overlap rows: `43,444`
- quantity-bearing overlap rows: `31,681`
- eligible-for-shadow-replacement rows: `19,253`
- ineligible quantity-bearing rows because landed basis is null/non-positive: `12,427`
- ineligible quantity-bearing rows because anomaly flag is set: `1`
- materially changed eligible rows under the shadow contract: `1,959`

Monthly materially changed rows:

- `2025-01: 367`
- `2025-02: 361`
- `2025-03: 531`
- `2025-06: 700`

Top affected machines:

- `035-017: 126`
- `024-147: 124`
- `166-002: 98`
- `024-144: 86`
- `035-018: 78`
- `024-142: 74`
- `024-143: 72`

Top affected task names:

- `印色: 1,298`
- `UV(染): 252`
- `印色+啞水油(染): 62`
- `印色+光水油(染): 60`
- `印色+光水油(局部): 58`
- `UV(局部): 58`

Top affected material codes:

- `PF0002403237-02-01: 12`
- `PA0002500072-01-90: 12`
- `PF0002302506-08-01: 8`
- `PG0002500221-05-01: 8`

Aggregate absolute quantity drift:

- `909,342.7378543428`

Total conservation check:

- current Jan-Jun `good_qty` total on quantity-bearing overlap rows: `76,519,314.26870583`
- shadow Jan-Jun `good_qty` total: `76,519,314.26870583`
- current Jan-Jun `scrap_qty` total: `0.0`
- shadow Jan-Jun `scrap_qty` total: `0.0`
- conclusion: totals remain conserved under the proposed hybrid replacement scope

## Representative Row Evidence

- `035-017 @ 2025-06-03T05:00:00`
  - current `good_qty = 1550.0`
  - landed basis minutes `18.0`
  - event basis minutes `18.0`
  - eligible for shadow replacement: yes
  - shadow `good_qty = 1550.0`
  - material change: no
- `035-018 @ 2025-02-17T15:00:00`
  - current `good_qty = 1607.0`
  - landed basis minutes `16.890202582335295`
  - event basis minutes `16.890202582335295`
  - eligible for shadow replacement: yes
  - shadow `good_qty = 1607.0`
  - material change: no
- `166-002 @ 2025-04-17T14:00:00`
  - current `good_qty = 130.73394495412845`
  - landed basis minutes: null in the current live snapshot
  - eligible for shadow replacement: no
  - ineligible reason: `missing_positive_quantity_basis_minutes`
  - shadow `good_qty` falls back to current quantity

## Decision Recommendation

Retain current dominant-event live quantity semantics for now.

Reason:

- a future replacement contract is definable and testable
- it conserves totals when scoped narrowly
- but `12,427 / 31,681` quantity-bearing overlap rows in the current live snapshot are still ineligible because landed basis minutes are null/non-positive
- that ineligible slice is too large for an honest wholesale live replacement recommendation
- only `1,959` eligible rows materially change under the shadow comparator, so the near-term decision problem is narrower than the raw Task 4Q drift counts suggested

## Remaining Limitations

- The active DB snapshot used by Task 4S differs from the Task 4R report counts; Task 4S did not write the DB and therefore treats the current live read-only snapshot as the source of truth.
- The shadow comparator uses landed row identity and current group totals; it does not reconstruct a brand-new event identity model.
- Null-basis rows remain the main blocker for a broad live quantity replacement.

## Recommended Next Task Boundary

If future quantity work is explicitly approved, keep it quantity-only and choose one of these first:

- reconstruct missing landed positive quantity basis minutes so the ineligible slice shrinks materially
- or scope a later live replacement only to fully eligible dominant-event groups while retaining current quantity on ineligible groups

Do not widen that next task into ML, UI, or Task 4T until the live quantity scope itself is explicitly approved.
