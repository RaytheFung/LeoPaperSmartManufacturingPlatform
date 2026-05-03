# Task 3C8 Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/`
  - `core/gold_fact_builder.py`
  - `tests/test_gold_fact_builder.py`
- `CURRENT_REBUILD_STATUS.md` exists and was used as the live execution ledger.
- Historical handoff path note:
  - the current repo only has the handoff docs under `docs/technical/`
  - old root-level references are not present anymore
  - I continued from `CURRENT_REBUILD_STATUS.md` plus the `docs/technical/` copies as instructed

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) with a re-run-safe `overlay_maintenance_state_review_on_fact_machine_hour()` step.
- The new overlay reviews existing Gold rows and promotes only a very narrow subset to `machine_state = maintenance`.
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with focused maintenance-state promotion, blocking, rerun-safety, preservation, row-grain, and deterministic-flag coverage.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) so the live status ledger reflects Task 3C8 as passed and points the next intended step at app retargeting onto canonical Gold.

## Exact Maintenance-State Eligibility Rule
- Gold only considers a row eligible for maintenance-state promotion when all of these are true:
  - `source_flags.maintenance_txn_in_hour` is true
  - `source_flags.maintenance_distinct_work_order_in_hour_count >= 1`
  - `multiple_csi_overlap_flag = 0`
  - no positive `setup_minutes`
  - no positive `production_minutes`
  - no positive `planned_stop_minutes`
  - no positive `unplanned_stop_minutes`
  - no positive `good_qty`
  - no positive `scrap_qty`
  - current `machine_state` is null or `idle`
  - either:
    - `csi_source_row_hash` is null
    - or `csi_overlap_minutes` is null or `< 1.0`

If a row passes those checks:
- `machine_state = "maintenance"`
- `state_confidence = "low"`
- `maintenance_minutes` stays null
- `attribution_method` is preserved

## Exact Promotion Method Recorded
- When promoted, Gold records:
  - `maintenance_state_promotion_method = "same_hour_maintenance_txn_without_conflicting_operational_evidence"`
  - `maintenance_state_confidence = "low"`
  - `maintenance_state_review_passed = true`

## Exact Skip / Blocked Reasons
- `maintenance_state_no_same_hour_maintenance`
- `maintenance_state_missing_work_order_in_hour`
- `maintenance_state_multiple_csi_overlap`
- `maintenance_state_conflicting_operational_minutes`
- `maintenance_state_conflicting_quantity`
- `maintenance_state_existing_non_idle_state`
- `maintenance_state_existing_csi_overlap`

Blocking precedence used:
1. no same-hour maintenance
2. missing work-order evidence in-hour
3. multiple CSI overlap
4. conflicting operational minutes
5. conflicting quantity
6. existing non-idle state
7. existing meaningful CSI overlap

This keeps the rule deterministic and reviewable.

## Maintenance-State Review Flags
- Gold records these deterministic audit keys in `source_flags`:
  - `maintenance_state_promotion_method`
  - `maintenance_state_confidence`
  - `maintenance_state_review_passed`
  - `maintenance_state_blocked_reason`
  - `maintenance_state_same_hour_work_order_count`
  - `maintenance_state_current_hour_work_order_types`

## Interaction With Idle
- This task is allowed to replace `machine_state = idle` with `machine_state = maintenance` only when:
  - same-hour maintenance eligibility fully passes
  - there are no stronger setup / production / stop minutes
  - the row otherwise only had `idle` or null state
- Unit coverage confirms this replacement path works.
- In the live June validation slice selected for the report, `rows_replacing_idle_with_maintenance = 0`.

## Why `maintenance_minutes` Stayed Out Of Scope
- Same-hour maintenance transactions are still treated as evidence of maintenance activity, not exact downtime duration.
- A transaction log can prove that maintenance touched the hour, but it does not safely prove the maintenance occupied the full hour or a precise subset of minutes.
- Because of that, Task 3C8 promotes state only in narrow cases and leaves `maintenance_minutes` null.

## Re-Run Safety
- Before applying maintenance-state review:
  - maintenance-review-specific `source_flags` are cleared
  - if a prior run had set `machine_state = maintenance` through this task, rerun can clear that stale state safely
- Gold does not clear non-maintenance states like:
  - `setup_changeover`
  - `production`
  - `planned_stop`
  - `unplanned_stop`
  - `idle`
- The only state this task may replace directly is:
  - a stale prior `maintenance` state from this same review layer
  - or an otherwise-eligible `idle` row under the narrow promotion rule above

## Preservation Of Existing Layers
- Energy aggregation from Task 3C1 is unchanged.
- CSI overlay from Task 3C2 is unchanged.
- MES context overlay from Task 3C3 is unchanged.
- Maintenance context overlay from Task 3C4 is unchanged.
- CSI minute reconciliation from Task 3C5 is unchanged.
- CSI quantity allocation from Task 3C6 is unchanged.
- Idle attribution from Task 3C7 is unchanged.
- Gold row grain remains exactly one row per `canonical_machine_id x hour_ts`.

## Deliberately Out Of Scope
- exact downtime attribution
- `maintenance_minutes` duration inference
- multi-event CSI blending
- MES quantity fallback
- UI or Streamlit retargeting
- ML changes
- KPI/dashboard work

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py tests/test_gold_fact_builder.py`
- Focused Gold tests:
  - `python3 -m unittest tests/test_gold_fact_builder.py`
  - Result: `Ran 60 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 95 tests ... OK`

## Live June Smoke Validation
- Exact files used:
  - `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
  - `2025 DataSet(JAN to JUN)/CSI Monthly/CSI印刷心電圖報表June.xlsx`
  - `2025 DataSet(JAN to JUN)/MES Monthly/MES生產數據June(Printer).xlsx`
  - `2025 DataSet(JAN to JUN)/(12:3:2026) Maintenance/印刷機維修記錄清單（2025年全年）.xlsx`
- I did not use the deleted working-tree energy copy under `data/能耗、費用報表June(1-30).xlsx`.
- Live search note:
  - I widened the maintenance-hour search across the top 100 real same-hour maintenance candidates
  - the selected positive slice was the first one that actually produced a live Gold maintenance-state promotion
- Selected real June slice:
  - `canonical_machine_id = 024-072`
  - focus day `2025-06-04`
- Slice load counts:
  - `energy_rows_loaded 24`
  - `csi_rows_loaded 10`
  - `mes_rows_loaded 0`
  - `maintenance_rows_loaded 5`
- Maintenance-state review results:
  - `gold_rows_checked 24`
  - `rows_with_same_hour_maintenance_activity 1`
  - `rows_promoted_to_maintenance_state 1`
  - `rows_blocked_by_operational_minutes 0`
  - `rows_blocked_by_quantity 0`
  - `rows_blocked_by_existing_csi_overlap 0`
  - `rows_replacing_idle_with_maintenance 0`
  - `rows_with_maintenance_minutes_still_null 24`
- Concrete example row:
  - `024-072 / 2025-06-04T11:00:00 / state maintenance / confidence low / maintenance_minutes null / same_hour_work_order_count 2 / current_hour_work_order_types ['CM', 'OP'] / no production / no planned_stop / no quantity / no meaningful CSI overlap`

## Remaining Limitations
- This is still a review-style maintenance promotion, not a duration model.
- `maintenance_minutes` remains intentionally null.
- Live June promotions appear sparse under the conservative rule, which is expected.
- The rule still will not promote any row with operational minutes, quantity evidence, or meaningful CSI overlap.
- Multi-event CSI blending and MES quantity fallback remain out of scope.
- ML is still not retargeted to the final Gold state mix.

## Pass Status
Task 3C8 should be considered passed. Gold now has a narrow, rerun-safe maintenance-state promotion review that only upgrades rows with same-hour maintenance evidence and no conflicting operational activity, while preserving all current 3C1–3C7 behavior and leaving `maintenance_minutes` intentionally unclaimed.
