# Task 3C7 Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - Gold builder: `core/gold_fact_builder.py`
  - Gold tests: `tests/test_gold_fact_builder.py`
  - technical reports: `docs/technical/`
  - live status ledger: `CURRENT_REBUILD_STATUS.md`
- `CURRENT_REBUILD_STATUS.md` exists and was used as the live execution ledger.
- Historical handoff path note:
  - the current repo only has the handoff docs under `docs/technical/`
  - the old root-level copies are no longer present
  - I therefore worked from `CURRENT_REBUILD_STATUS.md` plus the `docs/technical/` copies, and did not treat the missing root handoff paths as current truth

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) with a re-run-safe `overlay_idle_on_fact_machine_hour()` step.
- The new overlay:
  - updates only `idle_minutes`, idle-specific `source_flags`, and `machine_state/state_confidence` when the row is safely attributable as idle
  - leaves all 3C1–3C6 fields and behaviors intact
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with focused idle-eligibility, skip-reason, rerun-safety, state-priority, preservation, row-grain, and deterministic-flag coverage.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) to mark Task 3C7 passed and move the next intended step to maintenance-state promotion review.

## Exact Idle Eligibility Rule
- Gold only considers a row eligible for idle attribution when all of these are true:
  - `csi_source_row_hash` exists
  - `multiple_csi_overlap_flag = 0`
  - `source_flags.maintenance_txn_in_hour` is false
  - `source_flags.csi_minute_attribution_method == "csi_fractional_minute_reconciliation"`
  - `source_flags.csi_totals_exceed_window` is false
  - `csi_overlap_minutes >= 59.5`
- If any of those checks fail, Gold does not assign idle minutes and records a deterministic skip reason in `source_flags`.

## Exact Idle Calculation Rule
- For eligible rows only:
  - `setup_minutes`, `production_minutes`, `planned_stop_minutes`, and `unplanned_stop_minutes` are treated as safe zero when null
  - `assigned_minutes = setup + production + planned_stop + unplanned_stop`
  - `idle_minutes_raw = 60 - assigned_minutes`
- Result handling:
  - if `abs(idle_minutes_raw) < 0.5`, Gold stores `idle_minutes = 0.0`
  - if `idle_minutes_raw < 0` after tolerance, Gold stores `idle_minutes = null` and records a warning
  - if `idle_minutes_raw > 0`, Gold stores that positive value

## Exact Tolerance Rule
- Full-hour CSI coverage threshold:
  - `csi_overlap_minutes >= 59.5`
- Residual clamp:
  - if `abs(60 - assigned_minutes) < 0.5`, Gold treats the residual as zero instead of emitting tiny false idle values
- Negative residual handling:
  - Gold does not force negative idle into the row
  - it leaves `idle_minutes` null and records `idle_negative_residual`

## State Rule Used
- Idle is the lowest priority among the currently implemented states:
  1. `setup_changeover`
  2. `production`
  3. `planned_stop`
  4. `unplanned_stop`
  5. `idle`
- Gold only sets `machine_state = idle` when:
  - idle eligibility passes
  - `idle_minutes > 0`
  - all higher-priority implemented state minutes are absent or zero
- If setup / production / stop minutes are already active, Gold preserves the existing state and adds `idle_minutes` as context only.

## Exact Skip Reasons
- `idle_missing_csi_source`
- `idle_multiple_csi_overlap`
- `idle_same_hour_maintenance`
- `idle_non_fractional_csi_minutes`
- `idle_partial_csi_coverage`
- `idle_negative_residual`

Notes:
- `idle_non_fractional_csi_minutes` is also the effective skip path when `csi_totals_exceed_window` forced the earlier CSI layer onto wall-clock fallback.
- Gold records these idle audit keys in `source_flags`:
  - `idle_attribution_method`
  - `idle_match_confidence`
  - `idle_full_hour_csi_coverage`
  - `idle_assigned_minutes_basis`
  - `idle_attribution_warning`
  - `idle_skipped_reason`

## Re-Run Safety
- Before applying idle logic:
  - `idle_minutes` is reset to null
  - idle-specific `source_flags` are cleared
  - if the prior row state was `idle`, Gold clears `machine_state` and `state_confidence` so stale idle state can disappear cleanly on rerun
- Gold does not clear non-idle states such as:
  - `setup_changeover`
  - `production`
  - `planned_stop`
  - `unplanned_stop`

## Preservation Of Existing Layers
- Energy aggregation from Task 3C1 is unchanged.
- CSI overlay from Task 3C2 is unchanged.
- MES context overlay from Task 3C3 is unchanged.
- Maintenance context overlay from Task 3C4 is unchanged.
- CSI minute reconciliation from Task 3C5 is unchanged.
- CSI quantity allocation from Task 3C6 is unchanged.
- Gold row grain remains exactly one row per `canonical_machine_id x hour_ts`.
- `attribution_method` is preserved.

## Deliberately Out Of Scope
- Maintenance-state labeling
- Multi-event CSI blending
- MES quantity fallback
- UI or Streamlit retargeting
- ML changes
- KPI/dashboard changes
- changes to `maintenance_minutes`

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py tests/test_gold_fact_builder.py`
- Focused Gold tests:
  - `python3 -m unittest tests/test_gold_fact_builder.py`
  - Result: `Ran 52 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 87 tests ... OK`

## Live June Smoke Validation
- Exact files used:
  - `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
  - `2025 DataSet(JAN to JUN)/CSI Monthly/CSI印刷心電圖報表June.xlsx`
  - `2025 DataSet(JAN to JUN)/MES Monthly/MES生產數據June(Printer).xlsx`
  - `2025 DataSet(JAN to JUN)/(12:3:2026) Maintenance/印刷機維修記錄清單（2025年全年）.xlsx`
- I did not use the deleted working-tree energy copy under `data/能耗、費用報表June(1-30).xlsx`.
- Selected real June slice:
  - `canonical_machine_id = 024-128`
  - focus day `2025-06-26`
- Slice load counts:
  - `energy_rows_loaded 72`
  - `csi_rows_loaded 4`
  - `mes_rows_loaded 0`
  - `maintenance_rows_loaded 58`
- Idle-overlay results:
  - `gold_rows_checked 24`
  - `rows_with_full_hour_csi_coverage 18`
  - `rows_eligible_for_idle 7`
  - `rows_with_idle_minutes_gt_0 7`
  - `rows_with_machine_state_idle 0`
  - `rows_skipped_for_partial_csi_coverage 2`
  - `rows_skipped_for_wall_clock_fallback 13`
  - `rows_skipped_for_same_hour_maintenance 0`
  - `rows_with_idle_negative_residual_warning 0`
- Concrete example rows:
  - `024-128 / 2025-06-26T01:00:00 / state production / production 19.3139 / planned_stop 26.5038 / unplanned_stop 9.0226 / idle 5.1598 / order VP25000589 / good_qty 3142.6692 / scrap_qty 0.0`
  - `024-128 / 2025-06-26T02:00:00 / state production / production 19.3139 / planned_stop 26.5038 / unplanned_stop 9.0226 / idle 5.1598 / order VP25000589 / good_qty 3142.6692 / scrap_qty 0.0`

## Remaining Limitations
- Idle remains conservative and only appears on full-hour fractional CSI rows.
- Partial CSI coverage is still treated as unknown rather than idle.
- Wall-clock fallback rows still do not receive idle because their stop-minute detail is not trusted enough.
- Same-hour maintenance still blocks idle entirely; maintenance-state promotion is still a later task.
- The live slice had no same-day MES rows for the selected family, so live MES preservation remained regression-test-covered rather than live-slice-covered.
- This task does not attempt maintenance-driven state takeover, multi-event CSI blending, or MES quantity fallback.

## Pass Status
Task 3C7 should be considered passed. Gold now adds conservative `idle_minutes` attribution on top of the current 3C1–3C6 layers, keeps reruns safe, preserves existing state and quantity logic, records deterministic idle audit flags, and passes both focused and broader regression validation.
