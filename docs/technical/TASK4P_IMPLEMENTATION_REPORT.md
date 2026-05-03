# TASK4P Implementation Report

## Outcome

Task 4P passed.

Phase A stayed complete:

- canonical Gold minute semantics for multi-event CSI rows were already implemented in the live code
- Python builder and SQL repair logic already matched the same minute contract
- quantity semantics remained intentionally unchanged
- focused tests still passed in this run

Phase B is now complete:

- the active Jan-Jun 2025 Gold DB was safely rewritten onto the approved Task 4P minute contract
- the old unsafe whole-table SQL repair path was not used for the final landing
- the active DB now matches the verified Jan-Jun benchmark state for Task 4P minute semantics

## Exact Old Minute Contract

- one dominant CSI overlap candidate owned the row
- only that dominant event contributed `setup_minutes`, `production_minutes`, `planned_stop_minutes`, and `unplanned_stop_minutes`
- `csi_overlap_minutes` effectively reflected only the dominant event overlap
- multi-overlap rows skipped idle entirely via `idle_multiple_csi_overlap`
- quantity followed that same dominant event and its dominant-event production minutes

## Exact New Minute Contract In Code

- dominant-event selection is still used for row identity/context and quantity:
  - `order_id`
  - `order_suffix`
  - `material_code`
  - `task_name`
  - `team_leader`
  - `actual_speed_per_hour`
  - `csi_source_row_hash`
  - `good_qty` / `scrap_qty`
- minute fields now use all overlapping CSI candidates in the machine-hour:
  - `setup_minutes = sum(candidate setup overlap minutes)`
  - `production_minutes = sum(candidate reconciled dominant-event production minutes)`
  - `planned_stop_minutes = sum(candidate reconciled planned-stop minutes)`
  - `unplanned_stop_minutes = sum(candidate reconciled unplanned-stop minutes)`
- the row minute budget is the unioned CSI wall-clock coverage inside the hour:
  - coverage is built from the union of all setup and production intervals
  - coverage is capped at `60.0`
- if summed raw assigned minutes exceed that coverage budget, all four minute categories are scaled by:
  - `coverage_minutes / raw_assigned_minutes`
- if summed raw assigned minutes fit within coverage, no scaling is applied

## Sequential Vs Competing Same-Hour Events

- sequential/non-competing same-hour events are preserved additively when their summed assigned minutes stay within the row’s CSI coverage budget
- genuinely competing/overbooked same-hour events are blended by proportional down-scaling to the CSI coverage budget

## Explicit 60-Minute Budget Rule

- persisted operational minutes never exceed the row’s unioned CSI coverage in the hour
- unioned CSI coverage itself is capped at `60.0`
- therefore persisted operational minutes are always bounded to `<= 60.0`

## Machine State Rule After Minute Blending

- `machine_state` now comes from the final blended minute fields, using the same priority:
  1. `setup_changeover`
  2. `production`
  3. `planned_stop`
  4. `unplanned_stop`

## Idle Rule After Minute Blending

- multi-overlap rows are no longer skipped only because `multiple_csi_overlap_flag = 1`
- idle is now allowed when all of these are true:
  - the row has CSI coverage
  - all contributing CSI candidates used safe fractional minute reconciliation
  - no contributing candidate tripped the totals-exceed-window path
  - unioned CSI coverage for the row is at least `59.5` minutes
  - there is no same-hour maintenance transaction
- when eligible:
  - `idle_minutes = 60 - blended_assigned_minutes`
  - residuals with absolute value `< 0.5` clamp to `0.0`
- partial-coverage rows still keep `idle_minutes = null`

## Quantity Confirmation

- `good_qty` / `scrap_qty` allocation was intentionally left unchanged
- quantity still follows the dominant event only
- quantity basis now explicitly preserves the dominant event’s production minutes even when the row’s persisted `production_minutes` were blended upward or downward by multi-event minute semantics

## Files Changed

- `core/gold_fact_builder.py`
- `core/fact_machine_hour_repair.py`
- `core/canonical_materializer.py`
- `tests/test_gold_fact_builder.py`
- `tests/test_fact_machine_hour_repair.py`
- `tests/test_canonical_materializer.py`

## Validation Run

- `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py core/fact_machine_hour_repair.py core/canonical_materializer.py tests/test_gold_fact_builder.py tests/test_fact_machine_hour_repair.py tests/test_canonical_materializer.py`
- `python3 -m unittest tests.test_gold_fact_builder tests.test_fact_machine_hour_repair tests.test_canonical_materializer`
- result: `Ran 84 tests ... OK`

## Live DB Diagnostics And Landing In This Run

- active DB path: `manufacturing_data.db`
- prior preserved backup from the failed earlier attempt:
  - `backups/manufacturing_data_task4p_backup_20260401_200450.db`
- fresh backup created before the final DB write in this run:
  - `backups/manufacturing_data_task4p_phaseb_backup_20260401_220924.db`
- pre-write Jan-Jun overlap diagnostics matched the Task 4O audit baseline:
  - overlap rows: `43,453`
  - monthly overlap rows: `4,894 / 4,862 / 7,863 / 8,254 / 8,816 / 8,764`
  - overlap rows with non-null `planned_stop_minutes`: `20,860`
  - overlap rows with non-null `unplanned_stop_minutes`: `19,023`
  - overlap rows with non-null `idle_minutes`: `0`
- representative pre-write active rows captured:
  - `024-147 @ 2025-05-29T21:00:00`
  - `035-017 @ 2025-06-15T20:00:00`
  - `024-143 @ 2025-05-29T21:00:00`
- attempted direct live Jan-Jun month-loop outcome:
  - the month-scoped backfill/materialization path remained safe but did not commit within a practical first-pass runtime window on the active DB
  - the active DB was confirmed unchanged after that stalled attempt was stopped
- final landing route used in this run:
  - promoted the already-verified Jan-Jun Task 4P benchmark DB onto `manufacturing_data.db` after taking the fresh backup above
- post-write Jan-Jun diagnostics:
  - overlap rows: `43,453`
  - monthly overlap rows: `4,894 / 4,862 / 7,863 / 8,254 / 8,816 / 8,764`
  - overlap-row machine-state distribution: `39,179 setup_changeover / 4,274 production`
  - overlap rows with non-null `planned_stop_minutes`: `28,977`
  - overlap rows with non-null `unplanned_stop_minutes`: `25,519`
  - overlap rows with non-null `idle_minutes`: `722`
  - overlap-row quantity totals stayed unchanged: `total_good_qty = 76,519,869.5179145`, `total_scrap_qty = 0.0`, `rows_with_any_qty = 31,681`
- representative post-write active rows:
  - `024-147 @ 2025-05-29T21:00:00`
    - before: `setup 31.8 / production 12.501124 / planned_stop 15.762287 / unplanned_stop 0 / idle 0 / good_qty 6544`
    - after: `setup 35.849755 / production 14.201757 / planned_stop 9.948488 / unplanned_stop 0 / idle 0 / good_qty 6544`
  - `035-017 @ 2025-06-15T20:00:00`
    - before: `production 46.0 / planned_stop 0 / unplanned_stop 13.0 / idle 0 / good_qty 4918`
    - after: `production 46.300181 / planned_stop 0.120878 / unplanned_stop 13.078571 / idle 0.500369 / good_qty 4918`
  - `024-143 @ 2025-05-29T21:00:00`
    - before: `production 60.0 / good_qty 11772.151857`
    - after: `production 60.0 / good_qty 11772.151857`

## Remaining Limitations

- quantity semantics are still the old dominant-event-only contract by design and remain the correct next follow-up boundary only if a future explicit approval is given
- the final live landing in this run used benchmark-copy promotion after verifying the direct active-DB month loop was not practical as a first-pass execution path
- no ML artifacts or non-DB artifacts were changed by Task 4P Phase B

## Next Intended Step

- keep Task 4P closed
- if later approved, scope any multi-event CSI follow-up narrowly to quantity semantics only, with fresh before/after DB diagnostics and without widening into unrelated rebuild work
