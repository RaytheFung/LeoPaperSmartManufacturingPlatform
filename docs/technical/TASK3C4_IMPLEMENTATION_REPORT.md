# Task 3C4 Implementation Report

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) so `fact_machine_hour` can carry conservative maintenance context on top of the existing Task 3C1 energy backbone, Task 3C2 CSI overlay, and Task 3C3 MES overlay.
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with the MES re-run safety regression test and focused maintenance overlay tests.

## MES Re-Run Safety Fix
- Before each MES overlay attempt, Gold now explicitly resets:
  - `mes_source_row_hash`
  - `mes_report_ts`
  - `mes_match_method`
  - `mes_match_confidence`
  - `manpower`
- Stale MES-specific `source_flags` keys are also removed before the current run is evaluated.
- If a row had previously been labeled `energy_csi_mes_overlay` but no longer has a valid MES match, its `attribution_method` is downgraded back to the non-MES base state instead of leaving a stale MES label behind.

## Maintenance Overlay Rules
- Base table remains `fact_machine_hour` at grain `canonical_machine_id x hour_ts`.
- Maintenance matching in this task uses machine identity only:
  - same `canonical_machine_id`
- Maintenance does not overwrite energy, CSI, or MES fields.
- Maintenance does not set `machine_state`, does not fill `maintenance_minutes`, and does not change `attribution_method`.

## Added Gold Maintenance Fields
- `last_maintenance_txn_ts`
- `last_maintenance_source_row_hash`
- `last_maintenance_work_order_type`
- Existing Gold recency fields remain in use:
  - `hours_since_last_maintenance`
  - `days_since_last_maintenance`

## Exact Recency Definition
- Recency uses only prior maintenance rows:
  - same `canonical_machine_id`
  - `txn_ts < hour_start`
- Same-hour maintenance rows are deliberately excluded from recency.
- Future maintenance rows are ignored for recency.
- If multiple maintenance rows share the same latest prior `txn_ts`, the winner is chosen deterministically by lexicographic `source_row_hash` ordering.

## Current-Hour Maintenance Context Definition
- Current-hour activity uses:
  - same `canonical_machine_id`
  - `hour_start <= txn_ts < hour_end`
- Current-hour maintenance activity is stored as descriptive context only.
- It does not convert the Gold row to `machine_state = maintenance`.

## Exact Counting Definition
- Distinct work-order counts prefer `work_order_id` when present.
- If a set of rows has no usable `work_order_id`, the count falls back to raw row count.
- Gold now records at minimum in `source_flags`:
  - `has_maintenance_history`
  - `maintenance_txn_in_hour`
  - `maintenance_distinct_work_order_count_30d`
  - `maintenance_distinct_work_order_count_7d`
  - `maintenance_distinct_work_order_in_hour_count`
  - `maintenance_last_work_order_type`
- Gold also records deterministic sorted current-hour context in `source_flags`:
  - `maintenance_current_hour_work_order_types`
  - `maintenance_current_hour_txn_types`

## Deliberately Out Of Scope
- Final maintenance-state labeling
- Final downtime attribution
- Planned-stop / unplanned-stop / idle attribution
- UI or Streamlit retargeting
- ML changes
- Legacy `unified_view` rewrite

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py tests/test_gold_fact_builder.py`
- Focused Gold tests:
  - `python3 -m unittest tests/test_gold_fact_builder.py`
  - Result: `Ran 23 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 58 tests ... OK`

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
  - `rows_with_prior_maintenance_history 133`
  - `rows_with_same_hour_maintenance_activity 4`
  - `rows_with_last_maintenance_filled 133`
  - `invalid_maintenance_txn_rows_excluded 0`
  - `distinct_work_order_counts_sample`
    - `2025-06-25T11:00:00 -> 30d=1, 7d=1, in_hour=0`
    - `2025-06-25T12:00:00 -> 30d=1, 7d=1, in_hour=0`
    - `2025-06-25T13:00:00 -> 30d=1, 7d=1, in_hour=0`
- Concrete layered examples:
  - `024-128 / 2025-06-26T00:00:00 / order VP25000589 / suffix 0 / manpower 4.0 / mes_report_ts 2025-06-26T08:00:00 / last_maintenance_txn_ts 2025-06-25T17:12:04.833000 / last_maintenance_work_order_type AM`
  - `024-128 / 2025-06-26T01:00:00 / order VP25000589 / suffix 0 / manpower 4.0 / mes_report_ts 2025-06-26T08:00:00 / last_maintenance_txn_ts 2025-06-25T17:12:04.833000 / last_maintenance_work_order_type AM`

## Remaining Limitations
- Maintenance is still context only. Task 3C4 does not attempt final state assignment or downtime labeling.
- Work-order counting is intentionally conservative and depends on the presence of `work_order_id`; mixed cases still favor the explicit IDs over row count.
- Current-hour maintenance is surfaced as context and flags only; it is not interpreted semantically beyond that.
- The live validation was a real machine-family slice, not a full-month all-machine Gold reconciliation run.

## Pass Status
Task 3C4 should be considered passed. The Gold table now has leakage-safe maintenance context, the MES overlay is re-run safe, the focused and broader tests pass, and the live June slice shows maintenance history and current-hour activity attaching without disturbing the existing energy + CSI + MES Gold path.
