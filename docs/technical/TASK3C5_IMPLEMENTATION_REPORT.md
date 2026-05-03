# Task 3C5 Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - Gold builder: `core/gold_fact_builder.py`
  - Silver normalizer: `core/silver_normalizer.py`
  - Gold tests: `tests/test_gold_fact_builder.py`
  - technical reports: `docs/technical/`
- `SESSION_HANDOFF_CONTEXT.md` is present in the repo.
- `UPDATED_HANDOFF_TASK3B_READY.md` is also now present in the repo.

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) so the CSI overlay can reconcile productive vs stop minutes conservatively instead of using wall-clock production overlap only.
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with focused reconciliation, fallback, state-priority, summed-minute, and layer-preservation tests.

## Exact CSI Minute-Reconciliation Rule
- Setup inference remains unchanged:
  - `setup_start_ts = prep_end_ts - actual_changeover_minutes`
  - setup window = `[setup_start_ts, prep_end_ts)`
- Post-setup CSI event window is used only when:
  - `prep_end_ts` is valid
  - `prod_end_ts` is valid
  - `prod_end_ts > prep_end_ts`
- For safe reconciliation:
  - `event_window_minutes = minutes(prep_end_ts, prod_end_ts)`
  - `hour_post_setup_overlap_minutes = overlap([prep_end_ts, prod_end_ts), [hour_ts, hour_ts + 1h))`
  - `overlap_fraction = hour_post_setup_overlap_minutes / event_window_minutes`
  - `production_minutes = actual_prod_minutes * overlap_fraction`
  - `planned_stop_minutes = planned_stop_minutes * overlap_fraction`
  - `unplanned_stop_minutes = unplanned_stop_minutes * overlap_fraction`
- This preserves CSI minute totals approximately when summed across the event’s covered hours.

## Exact Tolerance Rule
- Before using the reconciliation path, Gold checks:
  - `actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes`
  - against `event_window_minutes`
- If CSI totals exceed the wall-clock post-setup window by more than:
  - `max(5 minutes, 5% of event_window_minutes)`
  then Gold does not force those totals into hour rows.
- Instead it falls back to wall-clock production overlap only and records deterministic warning flags.

## Blank / Null Stop-Minute Handling Assumption
- Real June CSI inspection showed:
  - `準備結束時間`, `實際生產時間`, `實際計劃停機時間`, `實際無計劃停機時間`, and `心電圖實際轉版時間` all share the same 1,394 null-row pattern
  - explicit zero values are common in the non-null rows
- Conservative assumption used:
  - explicit `0` means true zero
  - blank / null stop-minute fields are treated as missing, not as implied zero
- Because of that, safe reconciliation only runs when the key CSI minute totals are all present.

## Real June CSI Usability Inspection
- On `CSI印刷心電圖報表June.xlsx`:
  - usable post-setup windows: `19,524`
  - safe reconciliation candidates under the chosen tolerance: `17,948`
  - rows with planned stop minutes > 0: `15,251`
  - rows with unplanned stop minutes > 0: `11,620`
  - rows exceeding tolerance: `1,576`
- This supports the chosen conservative split:
  - use fractional reconciliation when safe
  - fall back when totals materially exceed the wall-clock window

## Fallback Rule
- Gold falls back to `csi_wall_clock_overlap_fallback` when:
  - the post-setup window is invalid
  - key CSI minute totals are missing
  - CSI totals exceed the tolerance
- In fallback:
  - `setup_minutes` still uses the existing setup-window logic
  - `production_minutes` uses the simpler wall-clock overlap
  - `planned_stop_minutes` and `unplanned_stop_minutes` remain null
- Gold records these markers in `source_flags`:
  - `csi_minute_attribution_method`
  - `csi_minute_reconciliation_warning`
  - `csi_totals_exceed_window`
  - `csi_used_wall_clock_fallback`

## Machine-State Rule Used
- Within the currently implemented states, Gold now uses:
  1. `setup_changeover`
  2. `production`
  3. `planned_stop`
  4. `unplanned_stop`
- Specifically:
  - if `setup_minutes > 0`, state = `setup_changeover`
  - else if `production_minutes > 0`, state = `production`
  - else if `planned_stop_minutes > 0`, state = `planned_stop`
  - else if `unplanned_stop_minutes > 0`, state = `unplanned_stop`
  - else state remains null

## Preservation Of Other Layers
- Energy fields are unchanged.
- MES overlay behavior and the Task 3C4 MES re-run safety fix are unchanged.
- Maintenance context overlay is unchanged.
- `source_flags` are still merged deterministically, and CSI-specific keys are cleared before a new CSI overlay pass so stale CSI minute markers do not linger.

## Deliberately Out Of Scope
- Maintenance-state labeling
- Final idle attribution
- MES prep-hours fallback for setup inference
- Quantity allocation
- UI or Streamlit retargeting
- ML changes

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py tests/test_gold_fact_builder.py`
- Focused Gold tests:
  - `python3 -m unittest tests/test_gold_fact_builder.py`
  - Result: `Ran 31 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 66 tests ... OK`

## Live June Smoke Validation
- Exact files used:
  - `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
  - `2025 DataSet(JAN to JUN)/CSI Monthly/CSI印刷心電圖報表June.xlsx`
  - `2025 DataSet(JAN to JUN)/MES Monthly/MES生產數據June(Printer).xlsx`
  - `2025 DataSet(JAN to JUN)/(12:3:2026) Maintenance/印刷機維修記錄清單（2025年全年）.xlsx`
- I did not use the deleted working-tree energy copy under `data/能耗、費用報表June(1-30).xlsx`.
- Live slice used:
  - `canonical_machine_id = 024-128`
  - date window `2025-06-25` to `2025-07-01`
- Result:
  - `gold_rows_checked 144`
  - `rows_with_safe_csi_minute_reconciliation 35`
  - `rows_using_wall_clock_fallback 67`
  - `rows_with_planned_stop_minutes_gt_0 33`
  - `rows_with_unplanned_stop_minutes_gt_0 34`
  - `rows_with_csi_totals_exceed_window_warning 3`
  - `invalid_maintenance_txn_rows_excluded 0`
- Concrete example rows:
  - `024-128 / 2025-06-26T00:00:00 / order VP25000589 / suffix 0 / setup 27.0 / production 1.80 / planned_stop 2.47 / unplanned_stop 0.84 / state setup_changeover`
  - `024-128 / 2025-06-26T01:00:00 / order VP25000589 / suffix 0 / production 19.31 / planned_stop 26.50 / unplanned_stop 9.02 / state production`

## Remaining Limitations
- Gold still attributes minutes from one dominant CSI event per machine-hour. Multi-event CSI blending is still out of scope.
- Fallback rows still use wall-clock production overlap rather than a richer stop split.
- This task does not attempt idle attribution or final full state hierarchy beyond the currently implemented states.
- The live validation was a real positive machine-family slice, not a full all-machine month reconciliation run.

## Pass Status
Task 3C5 should be considered passed. Gold now distinguishes productive and stop minutes more realistically when CSI minute totals are safe, falls back conservatively when they are not, preserves the existing energy + MES + maintenance overlays, and passes both focused and broader regression validation.
