# TASK4S Post-Landing Decision Report

## Outcome

This read-only post-landing Task 4S decision task passed.

No live quantity replacement was performed.
No live `good_qty` / `scrap_qty` semantics changed.
No dominant-event row identity semantics changed.
No write was made to `manufacturing_data.db` in this task.

## Exact Candidate Scope

This decision reuses the exact hardened landed scope from Task 4S Phase B:

- `csi_source_row_hash IS NOT NULL`
- `start_ts = '2025-01-01T00:00:00'`
- `end_ts = '2025-07-01T00:00:00'`
- `overlap_only = True`
- `quantity_rows_only = True`

Equivalent SQL scope:

```sql
FROM fact_machine_hour
WHERE csi_source_row_hash IS NOT NULL
  AND hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
```

This is the explicit eligible-candidate-set envelope for any later approval review.

## Shadow Contract Reused

The read-only decision reuses the existing Task 4S shadow contract:

- dominant-event identity remains fixed by `csi_source_row_hash`
- only fully eligible dominant groups are candidates
- eligible rows must have:
  - positive landed `csi_qty_row_basis_minutes`
  - positive persisted `production_minutes`
  - no `csi_qty_minute_budget_anomaly_flag`
- for eligible groups only:
  - shadow event total = current group total quantity
  - row share = `production_minutes / group total production_minutes`
  - shadow quantity is redistributed by that share
- anomaly groups remain excluded and retain current quantity

## Coverage Hardening Review

No new test was required in this task.

Reason:

- `tests/test_csi_quantity_shadow.py` already contains a real non-zero scrap overlap case:
  - `test_shadow_reallocates_fully_eligible_multi_row_group_by_production_share`
  - current scrap `2.0 + 8.0`
  - shadow scrap `7.5 + 2.5`

That already exercises the non-zero scrap path honestly and deterministically.

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/csi_quantity_shadow.py tests/test_csi_quantity_shadow.py
./.conda311/bin/python -m unittest tests.test_csi_quantity_shadow
```

Result:

- `Ran 4 tests`
- `OK`

## Read-Only Diagnostics Summary

All diagnostics below are evidence-based from the current live post-Phase-B snapshot.

### Row-level scope totals

- total quantity-bearing overlap rows in exact scope: `31,677`
- rows now eligible for a future production-share replacement: `31,669`
- rows excluded for anomaly: `8`
- rows excluded for any remaining null/non-positive basis: `0`
- rows excluded for any remaining missing/non-positive production: `0`

### Dominant-group totals

- dominant-event groups eligible: `29,846`
- dominant-event groups ineligible: `2`

Interpretation:

- the remaining blocker is no longer missing landed basis
- the remaining blocker is anomaly-tainted dominant groups only

### Ineligible reason breakdown

- `minute_budget_anomaly`: `8`

Anomaly rows by reason in the exact scope:

- `production_minutes_gt_60`: `6`
- `negative_operational_minutes`: `1`

Why anomaly-excluded rows are `8` while anomaly-flagged rows are `7`:

- one anomaly-tainted dominant group contains more than one quantity-bearing row
- the shadow contract excludes the whole dominant group when any quantity-bearing row in it is anomaly-flagged

### Quantity drift

- aggregate absolute quantity drift for `good_qty`: `1,570,672.6960422702`
- aggregate absolute quantity drift for `scrap_qty`: `0.0`
- materially changed eligible rows: `3,388`

### Conservation

- current `good_qty` total: `76,513,478.70666972`
- shadow `good_qty` total: `76,513,478.70666958`
- current `scrap_qty` total: `0.0`
- shadow `scrap_qty` total: `0.0`

Interpretation:

- `scrap_qty` is exactly conserved
- `good_qty` conservation difference is only floating-point noise at the machine precision level
- this is evidence-based conservation, not a live replacement

## Top Affected Buckets

Top affected machines by materially changed eligible rows:

- `035-017: 192`
- `024-147: 184`
- `035-018: 144`
- `024-144: 140`
- `166-002: 134`
- `024-143: 124`
- `024-141: 110`
- `024-140: 108`
- `024-110: 88`
- `024-048: 86`

Top affected task names:

- `印色: 2,218`
- `UV(染): 408`
- `印色+光水油(局部): 121`
- `印色+光水油(染): 120`
- `UV(局部): 106`
- `印色+啞水油(染): 100`
- `印色+啞水油(局部): 72`
- `印色+半光啞水油(染): 53`
- `光水油(染): 28`
- `印刷啤: 26`

Top affected material codes:

- `PA0002500072-01-90: 12`
- `PF0002403237-02-01: 12`
- `PA3002500066-03-01: 11`
- `PA0002417944-01-90: 10`
- `PA0002501038-01-09: 9`
- `PF0002302506-08-01: 8`
- `PG0002500221-05-01: 8`
- `PH0002201236-03-01: 6`
- `PB1072100270-02-01: 5`
- `PA2002500150-01-01: 4`

## Representative Rows

### Representative unchanged anchors

- `035-017 @ 2025-06-03T05:00:00`
  - current `good_qty = 1550.0`
  - current `scrap_qty = 0.0`
  - landed basis `18.0`
  - anomaly flag `0`
  - shadow group eligible: yes
  - shadow `good_qty = 1550.0`
  - shadow `scrap_qty = 0.0`
  - material change: no

- `035-018 @ 2025-02-17T15:00:00`
  - current `good_qty = 1607.0`
  - current `scrap_qty = 0.0`
  - landed basis `16.890202582335295`
  - anomaly flag `0`
  - shadow group eligible: yes
  - shadow `good_qty = 1607.0`
  - shadow `scrap_qty = 0.0`
  - material change: no

### Representative excluded anomaly anchor

- `166-002 @ 2025-04-17T14:00:00`
  - current `good_qty = 130.73394495412845`
  - current `scrap_qty = 0.0`
  - landed basis: null
  - anomaly reason: `production_minutes_gt_60`
  - shadow group eligible: no
  - ineligible reason: `minute_budget_anomaly`
  - shadow quantity falls back to current

### Representative materially changed rows

- `024-143 @ 2025-06-30T11:00:00`
  - `order_id = J250019544`
  - `task_name = 印色`
  - `material_code = PA0002101408-01-08`
  - current `good_qty = 1937.7357679914066`
  - shadow `good_qty = 6366.080155746509`
  - total absolute drift `4428.344387755103`

- `024-148 @ 2025-06-11T11:00:00`
  - `order_id = J250018734`
  - `task_name = 印色`
  - `material_code = PA0002501541-01-01`
  - current `good_qty = 923.8366181091117`
  - shadow `good_qty = 4932.951627785926`
  - total absolute drift `4009.115009676814`

## Decision

Recommendation:

- a later narrow live replacement on non-anomalous eligible groups is now technically justified for approval review

Why this recommendation is now different from the original pre-Phase-B Task 4S decision:

- the null/non-positive landed basis blocker is gone on the hardened scope
- there are now `0` remaining null-basis exclusions on non-anomalous rows
- dominant-identity conflicts remain `0`
- only `2` dominant groups remain ineligible, and only because of anomaly
- the read-only shadow still conserves totals while showing a large enough drift to matter operationally

What this does not mean:

- it is not live approval yet
- it is not a live replacement now
- it does not authorize anomaly handling changes

## Remaining Blockers

- the `8` anomaly-excluded rows across `2` dominant groups still need to remain excluded unless a separate anomaly policy is explicitly approved
- the current live snapshot still differs from older official pre-Phase-B Task 4S counts, so this recommendation is evidence-based on the landed snapshot, not a retroactive rewrite of the older baseline
- any actual live quantity replacement remains a separate explicitly approved task
