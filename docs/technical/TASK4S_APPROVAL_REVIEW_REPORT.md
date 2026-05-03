# TASK4S Approval Review Report

## Outcome

This separate quantity-only approval-review task passed.

No live DB write was performed.
No live `good_qty` / `scrap_qty` semantics changed in this task.
No dominant-event row identity semantics changed in this task.

Recommendation:

- approve opening a later narrow live replacement execution task
- keep the current live quantity semantics unchanged in this task
- keep anomaly-tainted dominant groups excluded unless a separate anomaly policy is explicitly approved

## Direct-Source-Verified Inputs

The following are direct-source-verified from the current active DB snapshot and current repo code:

- live DB path: `manufacturing_data.db`
- scope table: `fact_machine_hour`
- scope filters:
  - `csi_source_row_hash IS NOT NULL`
  - `hour_ts >= '2025-01-01T00:00:00'`
  - `hour_ts < '2025-07-01T00:00:00'`
  - `multiple_csi_overlap_flag = 1`
  - `(good_qty IS NOT NULL OR scrap_qty IS NOT NULL)`
- shadow comparator implementation:
  - [`core/csi_quantity_shadow.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/csi_quantity_shadow.py)
- current landed quantity metadata / anomaly helper path:
  - [`core/fact_machine_hour_repair.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/fact_machine_hour_repair.py)
- current focused shadow tests:
  - [`tests/test_csi_quantity_shadow.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_csi_quantity_shadow.py)

## Exact Future Write Scope

If a later live execution task is explicitly approved, the exact write scope should be:

- all `31,669` currently eligible rows
- across `29,846` fully eligible dominant-event groups
- within the exact hardened landed scope only:
  - `csi_source_row_hash IS NOT NULL`
  - `hour_ts >= '2025-01-01T00:00:00'`
  - `hour_ts < '2025-07-01T00:00:00'`
  - `multiple_csi_overlap_flag = 1`
  - `(good_qty IS NOT NULL OR scrap_qty IS NOT NULL)`
- plus the group-level eligibility rule:
  - every quantity-bearing row in the same `csi_source_row_hash` group must have positive `csi_qty_row_basis_minutes`
  - every quantity-bearing row in the same `csi_source_row_hash` group must have positive `production_minutes`
  - no quantity-bearing row in the same `csi_source_row_hash` group may have `csi_qty_minute_budget_anomaly_flag = 1`

This future write scope should be defined by full eligible dominant groups, not only by materially changed rows.

Reason:

- group-level conservation is defined at the dominant-group level
- partial material-only updates would create an avoidable risk of breaking group totals or leaving mixed semantics inside one eligible group

Expected materially changed subset on the current snapshot:

- `3,388` eligible rows

## Exact Fields That Would Change

Future live execution should only target these semantic quantity fields on the eligible scope:

- `good_qty`
- `scrap_qty`

Direct-source-verified expectation on the current snapshot:

- `good_qty` would materially change on `3,388` eligible rows
- `scrap_qty` aggregate drift is `0.0`
- all scoped rows currently have `scrap_qty = 0.0`, so `scrap_qty` is expected to remain numerically unchanged on this snapshot even if it is recomputed for symmetry

## Exact Fields That Must Not Change

The following fields must remain unchanged in any later narrow live replacement:

- `csi_source_row_hash`
- `machine_state`
- `setup_minutes`
- `production_minutes`
- `planned_stop_minutes`
- `unplanned_stop_minutes`
- `idle_minutes`
- `order_id`
- `material_code`
- `task_name`
- `csi_qty_basis_method`
- `csi_qty_row_basis_minutes`
- `csi_qty_event_basis_minutes`
- `csi_qty_minutes_vs_production_diff`
- `csi_qty_minutes_vs_production_abs_diff`
- `csi_qty_alignment_status`
- `csi_qty_material_misalignment_flag`
- `csi_qty_minute_budget_anomaly_flag`
- `csi_qty_minute_budget_anomaly_reason`

Interpretation:

- the future task would be quantity-only
- it would not reland metadata
- it would not alter the dominant-event identity contract
- it would not alter the Task 4P blended-minute contract

## Before / After Invariants

Any later live execution task should enforce these invariants before commit and again after commit.

Before-write invariants:

- exact eligible-scope snapshot still equals:
  - eligible rows: `31,669`
  - anomaly-excluded rows: `8`
  - eligible dominant groups: `29,846`
  - ineligible dominant groups: `2`
- remaining non-anomalous null/non-positive basis exclusions: `0`
- remaining non-anomalous missing/non-positive production exclusions: `0`
- dominant-identity conflicts on the candidate scope: `0`

After-write invariants:

- only eligible rows were targeted
- anomaly-excluded rows remain unchanged
- ineligible dominant groups remain unchanged
- dominant-event row identity remains unchanged
- persisted `production_minutes` remains unchanged
- total `good_qty` on the exact hardened scope remains conserved within floating-point tolerance
- total `scrap_qty` on the exact hardened scope remains conserved exactly
- per-dominant-group total quantity remains conserved within floating-point tolerance

## Backup Procedure

The later live execution task should not start until these backup steps complete successfully:

1. Stop any concurrent app/process that might write to `manufacturing_data.db`.
2. Create a timestamped full-file SQLite backup in `backups/`, for example:
   - `backups/manufacturing_data_task4s_live_qty_replace_<timestamp>.db`
3. Materialize a narrow pre-write rollback snapshot for the exact eligible scope with:
   - `canonical_machine_id`
   - `hour_ts`
   - `csi_source_row_hash`
   - pre-write `good_qty`
   - pre-write `scrap_qty`
4. Record the pre-write diagnostic counts and totals in the execution log before any update is attempted.

## Rollback Procedure

The later live execution task should support both immediate rollback and post-commit rollback.

Immediate rollback:

1. Build the eligible staging set in temp or staging tables.
2. Run all invariant checks before update.
3. Apply the update inside a single explicit transaction.
4. Re-run invariants before commit.
5. If any invariant fails, rollback the transaction and stop.

Post-commit rollback:

1. If the issue is isolated to quantity values only, restore `good_qty` / `scrap_qty` for the exact eligible scope from the pre-write rollback snapshot.
2. If any broader corruption or scope leak is detected, restore the full SQLite backup file and stop.
3. Re-run the same read-only approval diagnostics after rollback to confirm the pre-write state is restored.

## Abort Conditions

The later live execution task should abort without writing if any of the following are observed:

- eligible row count is no longer `31,669`
- anomaly-excluded row count is no longer `8`
- eligible dominant-group count is no longer `29,846`
- ineligible dominant-group count is no longer `2`
- any non-anomalous candidate row has null/non-positive `csi_qty_row_basis_minutes`
- any non-anomalous candidate row has null/non-positive `production_minutes`
- any anomaly-tainted dominant group appears in the target update set
- any target row outside the exact hardened landed scope appears in the staging set
- any dominant-group total fails conservation beyond floating-point tolerance in pre-commit validation
- any non-quantity field appears in the update set

## Anomaly Exclusions That Remain Fixed

The future live execution scope must keep these rows excluded unless a separate anomaly policy is approved:

- `8` excluded rows across `2` dominant groups

Direct-source-verified anomaly group breakdown:

- `1` row on `024-146 @ 2025-03-11T10:00:00`
  - reason: `negative_operational_minutes`
- `7` rows in the `166-002 / J250010360 / UV(染)` dominant group
  - `6` rows reason: `production_minutes_gt_60`
  - `1` additional row in the same group is excluded by whole-group policy even though its own row anomaly flag is `0`

## Read-Only Pre-Approval Checks

These values were recomputed read-only from the current active snapshot.

Row-level totals:

- eligible rows: `31,669`
- excluded anomaly rows: `8`
- excluded null/non-positive basis rows on the raw exact scope: `6`
- excluded missing/non-positive production rows on the raw exact scope: `0`
- expected materially changed eligible rows: `3,388`

Dominant-group totals:

- eligible dominant groups: `29,846`
- ineligible dominant groups: `2`

Aggregate drift:

- aggregate absolute drift for `good_qty`: `1,570,672.6960422653`
- aggregate absolute drift for `scrap_qty`: `0.0`

Conservation:

- current `good_qty` total: `76,513,478.70666954`
- shadow `good_qty` total: `76,513,478.7066698`
- `good_qty` delta: `0.0000002682209014892578`
- current `scrap_qty` total: `0.0`
- shadow `scrap_qty` total: `0.0`
- `scrap_qty` delta: `0.0`

Interpretation:

- `good_qty` conservation holds to floating-point noise only
- `scrap_qty` is exactly conserved
- these are read-only diagnostics, not a live replacement result

## Concentration Risk Review

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
- `PG0002500221-05-01: 8`
- `PF0002302506-08-01: 8`
- `PH0002201236-03-01: 6`
- `PB1072100270-02-01: 5`
- `PA1002314265-01-06: 4`

Interpretation:

- risk is concentrated in a relatively small machine/task slice rather than spread uniformly across all overlap rows
- `印色` work dominates the materially changed set and should be sampled explicitly in any future live execution validation

## Coverage / Safety Review

No new test was added in this task.

Reason:

- the current task is approval-review only
- [`tests/test_csi_quantity_shadow.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_csi_quantity_shadow.py) already covers:
  - unchanged single-row eligible anchors
  - anomaly-group exclusion
  - multi-row eligible reallocation
  - null-basis exclusion
- the existing multi-row test already exercises non-zero scrap reallocation deterministically

Evidence-based conclusion:

- current tests are sufficient for this read-only approval-review task
- a future live execution task should still include write-path-specific preflight/rollback validation before any commit, but adding that now would widen scope beyond this approval review

## Decision

Approve opening a later live replacement execution task.

Boundary of that approval:

- it is approval to open the later narrow execution task
- it is not approval to write in this task
- it is not approval to include anomaly-tainted dominant groups
- it is not approval to change dominant-event identity semantics
- it is not approval to reland quantity metadata

## Exact SQL / Data-Scope Diagnostics Run

Exact row-scope SQL:

```sql
SELECT
    canonical_machine_id,
    hour_ts,
    order_id,
    task_name,
    material_code,
    csi_source_row_hash,
    production_minutes,
    good_qty,
    scrap_qty,
    csi_qty_row_basis_minutes,
    csi_qty_event_basis_minutes,
    csi_qty_minute_budget_anomaly_flag,
    csi_qty_minute_budget_anomaly_reason
FROM fact_machine_hour
WHERE csi_source_row_hash IS NOT NULL
  AND hour_ts >= '2025-01-01T00:00:00'
  AND hour_ts < '2025-07-01T00:00:00'
  AND multiple_csi_overlap_flag = 1
  AND (good_qty IS NOT NULL OR scrap_qty IS NOT NULL)
ORDER BY csi_source_row_hash, hour_ts, canonical_machine_id;
```

Read-only evaluation method:

- load the exact scope above from `manufacturing_data.db`
- evaluate with `evaluate_shadow_quantity(...)`
- aggregate eligibility, drift, conservation, anomaly-group, and concentration diagnostics from the evaluated rows

## Validation

Commands run in this task:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/csi_quantity_shadow.py tests/test_csi_quantity_shadow.py
./.conda311/bin/python -m unittest tests.test_csi_quantity_shadow
```

Result:

- `Ran 4 tests`
- `OK`
