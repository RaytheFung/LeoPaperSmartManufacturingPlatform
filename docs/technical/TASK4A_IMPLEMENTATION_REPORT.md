# Task 4A Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/`
  - `core/gold_fact_builder.py`
  - `modules/unified_view_module.py`
  - `app.py`
  - `tests/`
- Confirmed the live route for the current Unified View / Monthly Insights page is:
  - `app.py`
  - `show_unified_view_page()`
  - `modules.unified_view_module.render_unified_view_page()`
- Historical handoff path note:
  - the current repo only has the handoff docs under `docs/technical/`
  - old root-level handoff paths are not present anymore
  - Task 4A continued from `CURRENT_REBUILD_STATUS.md` plus `docs/technical/` as instructed

## What Changed
- Added [core/canonical_gold_reader.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py) as the focused canonical Gold read/helper layer for the page.
- Retargeted [modules/unified_view_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) so `render_unified_view_page()` now reads `fact_machine_hour` only.
- Added [tests/test_canonical_gold_reader.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_gold_reader.py) with pure helper coverage instead of brittle Streamlit snapshot tests.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) so the live execution ledger reflects Task 4A and the next remaining integration gap.

## Exact Page / Module Retargeted
- Retargeted module:
  - `modules/unified_view_module.py`
- Exact page path:
  - `app.py` sidebar route `📊 Unified View`
  - `show_unified_view_page()`
  - `render_unified_view_page()`

## Exact Canonical Read Rule Used
- The new page helper reads from `fact_machine_hour` only.
- Available months are derived from distinct `substr(hour_ts, 1, 7)` values in `fact_machine_hour`.
- Selected-month rows are loaded by canonical hour range:
  - `hour_ts >= month_start`
  - `hour_ts < next_month_start`
- The helper does not:
  - query legacy `unified_view`
  - recreate `unified_view`
  - persist a compatibility table
  - silently fabricate synthetic/demo rows
- If `fact_machine_hour` is missing or the selected month has no canonical Gold rows, the page now warns explicitly and stops.

## Canonical Page Contract Added
- Raw/canonical fields exposed for the page:
  - `canonical_machine_id`
  - `hour_ts`
  - `machine_state`
  - `state_confidence`
  - `energy_total_kwh`
  - `order_id`
  - `material_code`
  - `task_name`
  - `setup_minutes`
  - `production_minutes`
  - `planned_stop_minutes`
  - `unplanned_stop_minutes`
  - `maintenance_minutes`
  - `idle_minutes`
  - `good_qty`
  - `scrap_qty`
  - `team_leader`
  - `manpower`
  - `hours_since_last_maintenance`
  - `days_since_last_maintenance`
  - `attribution_method`
- Derived display fields added:
  - `month_year`
  - `datetime`
  - `machine_id` as the display alias for `canonical_machine_id`
  - `production_qty = good_qty`
  - `kwh_per_good_unit` with safe divide only when `good_qty > 0`
  - `maintenance_in_hour` derived conservatively from `source_flags.maintenance_txn_in_hour` or `machine_state = maintenance`
  - `state_bucket`
  - `state_label`

## UI Scope Kept Narrow
- The page shell remains month-scoped and analytics-oriented.
- The page still shows:
  - header
  - month selector
  - key metrics
  - state summary
  - sample table
  - export buttons
- Wording was changed so it no longer claims to generate the old unified view.
- No broad app routing change was made.

## Tiny Gold Bug Fixes
- None.
- Task 4A did not change Gold-building logic from Tasks 3C1 to 3C8.

## What Stayed Deliberately Out Of Scope
- ETL page rewrite
- maintenance page rewrite
- optimization page rewrite
- ML page rewrite
- legacy `unified_view` table cleanup
- automatic app-side Gold materialization
- any change to Gold attribution rules from Tasks 3C1 to 3C8

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/canonical_gold_reader.py modules/unified_view_module.py tests/test_canonical_gold_reader.py`
- Focused canonical reader tests:
  - `python3 -m unittest tests/test_canonical_gold_reader.py`
  - Result: `Ran 5 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_canonical_gold_reader.py`
  - Result: `Ran 96 tests ... OK`
- Additional focused page-adjacent regression:
  - `python3 -m unittest tests/test_canonical_gold_reader.py tests/test_gold_fact_builder.py`
  - Result: `Ran 65 tests ... OK`

## Live June Page-Data Smoke Validation
- Validation method:
  - sample-limited temp-db smoke run using real June source files
  - Bronze -> Silver -> Gold built into a temp DB
  - the retargeted page helper then read `June 2025` from that temp `fact_machine_hour`
- Exact files used:
  - `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
  - `2025 DataSet(JAN to JUN)/CSI Monthly/CSI印刷心電圖報表June.xlsx`
  - `2025 DataSet(JAN to JUN)/MES Monthly/MES生產數據June(Printer).xlsx`
  - `2025 DataSet(JAN to JUN)/(12:3:2026) Maintenance/印刷機維修記錄清單（2025年全年）.xlsx`
- Sample limit used for smoke speed:
  - first 120 raw rows per source file
- Selected month:
  - `June 2025`
- Page smoke results:
  - `gold_rows_loaded_for_page 120`
  - `distinct_machines 1`
  - `rows_with_null_machine_state 120`
  - `total_good_qty None`
  - `total_scrap_qty None`
  - `page_export_worked True`
- Example canonical page rows:
  - `2025-06-01 01:00:00 / 024-108 / machine_state null / energy_total_kwh 16.5 / good_qty null / scrap_qty null / team_leader null / material_code null / order_id null`
  - `2025-06-01 02:00:00 / 024-108 / machine_state null / energy_total_kwh 54.0 / good_qty null / scrap_qty null / team_leader null / material_code null / order_id null`

## Important Limitation Discovered During 4A
- The live repo database currently still has legacy `unified_view`, but it does not yet have a populated `fact_machine_hour`.
- This means the retargeted page behavior in the main app is currently:
  - explicit canonical-only warning if Gold has not been materialized
  - no legacy fallback
- That is the intended Task 4A behavior.
- Formal Gold population inside the live app/ETL flow should be the next task, not an implicit fallback inside this page.

## Remaining Limitations
- The sample-limited June smoke run was intentionally small and landed on an energy-only slice, so the page smoke does not prove rich CSI/MES/maintenance overlays on that slice.
- `maintenance_minutes` remains intentionally null in the current Gold model.
- Some canonical page rows can still have null `machine_state`, and the page now warns honestly about that.
- The live repo DB still needs a formal canonical Gold materialization step before this page shows data in-place without a warning.
- Other app pages still remain unretargeted.

## Pass Status
Task 4A should be considered passed.

The Unified View / Monthly Insights style page now reads canonical Gold `fact_machine_hour` only, exposes the required month-scoped analytics contract, stops with an explicit warning when canonical Gold is missing, and no longer silently falls back to legacy `unified_view` or synthetic/demo paths. The remaining gap is canonical Gold population in the live app flow, which is a follow-on integration task rather than a page-read failure.
