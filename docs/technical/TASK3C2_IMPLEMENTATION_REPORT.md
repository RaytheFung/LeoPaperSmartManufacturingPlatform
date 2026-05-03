# Task 3C2 Implementation Report

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) so `fact_machine_hour` can be overlaid with CSI operational meaning on top of the existing Task 3C1 energy backbone.
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with focused CSI overlap attribution tests.

## Exact CSI Overlap Rules
- Base table remains `fact_machine_hour` at grain `canonical_machine_id x hour_ts`.
- CSI candidates must match the same `canonical_machine_id`.
- A CSI event overlaps a machine-hour when either its inferred setup window or its production window intersects the hour window.
- Hour overlap is computed against:
  - machine-hour window: `[hour_ts, hour_ts + 1 hour)`
  - setup window: `[setup_start_ts, prep_end_ts)`
  - production window: `[prep_end_ts, prod_end_ts)` when `prep_end_ts` exists
  - production fallback window: `[prod_start_ts, prod_end_ts)` when `prep_end_ts` is unavailable
- If more than one CSI event overlaps the same machine-hour, the dominant event is the one with the greatest total overlap minutes. Ties are broken deterministically by production overlap minutes and then `source_row_hash`.
- `multiple_csi_overlap_flag` is set when more than one CSI event overlaps the same Gold row.

## Exact Setup Inference Rule Used
- `setup_start_ts = prep_end_ts - actual_changeover_minutes`
- `setup_inference_method = csi_prep_end_minus_actual_changeover_minutes`
- `setup_confidence = high` when both `prep_end_ts` and `actual_changeover_minutes >= 0` are available
- If setup cannot be inferred safely from CSI alone, setup fields remain null in this task

## Deliberately Out Of Scope
- MES enrichment
- Maintenance attribution
- Planned-stop / unplanned-stop / idle state assignment
- Streamlit page retargeting
- ML changes

## Validation Performed
- Focused tests cover:
  - CSI production overlap attribution
  - CSI setup overlap attribution
  - dominant event selection
  - multi-event overlap flagging
  - safe null behavior when no CSI event matches
  - preservation of Task 3C1 energy fields
- Broader regression run:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 47 tests ... OK`
- Live smoke checks:
  - Negative-sample smoke with the first 40 June energy rows and first 40 June CSI rows confirmed that a non-overlapping sample slice safely leaves `csi_source_row_hash` null instead of fabricating attribution.
  - Positive-sample smoke on a real overlapping machine family `1262-10015` used:
    - 40 June energy rows from `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
    - 40 June CSI rows from `data/CSI印刷心電圖報表June.xlsx`
  - Result for the positive slice:
    - `gold_rows 40`
    - `csi_attributed_rows 7`
    - sample attributed rows populated `order_id`, `setup_minutes`, `production_minutes`, and `csi_overlap_minutes`

## Remaining Limitations
- This task uses CSI only. MES prep fallback has not started, so setup remains null when CSI cannot support the inference safely.
- `machine_state` is only set to `setup_changeover` or `production` when CSI evidence is clear. Other states remain out of scope in this task.
- Mixed CSI evidence within a single hour is reduced to one dominant event for attribution. Later stages may need richer multi-event treatment.
- No maintenance or MES context is used to disambiguate CSI overlaps in this task.

## Pass Status
Task 3C2 should be considered passed, because CSI operational meaning is now layered onto the Gold machine-hour backbone without altering the existing Task 3C1 energy aggregation logic, and both the focused tests and live smoke validation succeeded within the approved scope.
