# Task 3C6 Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - Gold builder: `core/gold_fact_builder.py`
  - Silver normalizer: `core/silver_normalizer.py`
  - Gold tests: `tests/test_gold_fact_builder.py`
  - technical reports: `docs/technical/`
- `CURRENT_REBUILD_STATUS.md` exists and was used as the live execution-status ledger.
- The historical handoff docs are present under:
  - `docs/technical/SESSION_HANDOFF_CONTEXT.md`
  - `docs/technical/UPDATED_HANDOFF_TASK3B_READY.md`
- Root duplicates of those handoff docs had already been removed during repo cleanup, so I used the `docs/technical/` copies as the historical baseline references.

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) with a re-run-safe `overlay_csi_quantity_on_fact_machine_hour()` step that allocates CSI `good_qty` and `scrap_qty` onto existing Gold rows using the already selected dominant `csi_source_row_hash`.
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with focused quantity-allocation coverage for totals, mixed hours, zero vs null behavior, missing quantities, unsafe-basis handling, re-run safety, layer preservation, row-grain preservation, and deterministic `source_flags`.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) so the live status ledger reflects Task 3C6 as passed and points the next intended step at idle attribution.

## Exact Quantity-Allocation Rule
- Gold remains one row per `canonical_machine_id x hour_ts`.
- Quantity allocation is a focused overlay step applied after the existing 3C1–3C5 Gold layers.
- Gold uses the existing `csi_source_row_hash` already selected by the CSI overlay.
- Gold does not try to blend multiple CSI events in this task.
- Gold does not use MES `reported_qty` fallback in this task.

Per CSI event:
- collect Gold rows with the same `csi_source_row_hash`
- keep only rows where `production_minutes > 0`
- compute:
  - `event_gold_production_basis = sum(production_minutes)`

Per eligible Gold row:
- `good_qty = event_good_qty * (row_production_minutes / event_gold_production_basis)`
- `scrap_qty = event_scrap_qty * (row_production_minutes / event_gold_production_basis)`

This means:
- quantity follows the already-built production-minute meaning from Task 3C5
- rows with `machine_state = setup_changeover` still receive quantity when they have positive `production_minutes`
- event totals are preserved approximately when summed back across the event-covered Gold rows

## Safety Rules
- Quantity is allocated only when all of these are true:
  - `csi_source_row_hash` exists
  - matching CSI event exists
  - row `production_minutes` is positive
  - event production basis is positive
  - the CSI quantity field being allocated is present
- If any of those are not true:
  - the relevant Gold quantity field remains null
  - Gold records a deterministic reason in `source_flags`

Warnings used in `source_flags`:
- `csi_qty_missing_source_row_hash`
- `csi_qty_missing_event`
- `csi_qty_no_positive_production_minutes`
- `csi_qty_non_positive_event_basis`
- `csi_qty_missing_all`
- `csi_qty_missing_good_qty`
- `csi_qty_missing_scrap_qty`

## Zero Vs Null Policy
- Explicit source `0` is treated as true zero.
- Blank / null is treated as missing.
- When the allocation basis is safe:
  - explicit `0` is preserved as `0.0`
  - blank / null stays null
- Task 3C6 does not collapse allocated `0.0` back to null.

## Quantity-Allocation Confidence Rule
- Gold records these quantity-audit markers in `source_flags`:
  - `csi_qty_allocation_method`
  - `csi_qty_allocation_confidence`
  - `csi_qty_source_row_hash`
  - `csi_qty_basis_minutes`
  - `csi_qty_allocation_warning`
- Confidence rule used:
  - `high` when the row’s CSI minute basis came from `csi_fractional_minute_reconciliation`
  - `medium` when the row’s CSI minute basis came from `csi_wall_clock_overlap_fallback`
  - `null` when no quantity was allocated

## Re-Run Safety
- Before quantity allocation:
  - `good_qty` is reset to null
  - `scrap_qty` is reset to null
  - all quantity-specific `source_flags` from this task are cleared
- This prevents stale quantity values or stale quantity audit markers from surviving a re-run when the current Gold row is no longer eligible.

## June CSI Quantity Inspection
- On the live June CSI file `CSI印刷心電圖報表June.xlsx`:
  - `正品數量`: `22,552` non-null, `1,394` null, `2,630` explicit zeros
  - `廢品數量`: `22,552` non-null, `1,394` null, `22,551` explicit zeros
  - `纍計數量`: `22,552` non-null, `1,394` null, `1,633` explicit zeros
  - `實際生產時間`: `22,552` non-null, `1,394` null, `3,115` explicit zeros
- The shared `1,394` null-row pattern lines up with the broader CSI missing-data pattern from earlier tasks.
- Conservative interpretation used:
  - explicit zero is real zero
  - blank / null appears to mean missing rather than implied zero
- `cumulative_qty` was inspected for understanding only and is still deliberately not written into Gold hour rows in this task.

## Preservation Of Existing Layers
- Energy aggregation from Task 3C1 is unchanged.
- CSI setup / production / stop logic from Tasks 3C2 and 3C5 is unchanged.
- MES context overlay from Task 3C3 is unchanged.
- Maintenance context overlay from Task 3C4 is unchanged.
- Gold row grain is unchanged.
- `machine_state`, `state_confidence`, `setup_minutes`, `production_minutes`, `planned_stop_minutes`, `unplanned_stop_minutes`, MES fields, maintenance fields, and `attribution_method` are preserved.

## Deliberately Out Of Scope
- Idle attribution
- Maintenance-state labeling
- MES quantity fallback
- Multi-event CSI quantity blending
- UI or Streamlit retargeting
- ML logic changes
- KPI/dashboard work

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py tests/test_gold_fact_builder.py`
- Focused Gold tests:
  - `python3 -m unittest tests/test_gold_fact_builder.py`
  - Result: `Ran 41 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 76 tests ... OK`

## Live June Smoke Validation
- Exact files used:
  - `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
  - `2025 DataSet(JAN to JUN)/CSI Monthly/CSI印刷心電圖報表June.xlsx`
  - `2025 DataSet(JAN to JUN)/MES Monthly/MES生產數據June(Printer).xlsx`
  - `2025 DataSet(JAN to JUN)/(12:3:2026) Maintenance/印刷機維修記錄清單（2025年全年）.xlsx`
- I did not use the deleted working-tree copy under `data/能耗、費用報表June(1-30).xlsx`.
- Live slice chosen from real June data:
  - `canonical_machine_id = 024-043`
  - focus day `2025-06-25`
- Live slice load counts:
  - `energy_rows_loaded 24`
  - `csi_rows_loaded 5`
  - `mes_rows_loaded 0`
  - `maintenance_rows_loaded 55`
- Current Gold build coverage on that slice:
  - `gold_csi_source_row_hash_coverage 24 of 24`
- Quantity-allocation results:
  - `gold_rows_checked 24`
  - `rows_with_good_qty_allocated 21`
  - `rows_with_scrap_qty_allocated 21`
  - `rows_with_zero_good_qty_preserved 0`
  - `rows_with_zero_scrap_qty_preserved 14`
  - `rows_with_qty_allocation_using_fractional_minute_basis 14`
  - `rows_with_qty_allocation_using_wall_clock_based_production_basis 7`
  - `rows_with_no_safe_qty_allocation 3`
- Concrete example rows:
  - `024-043 / 2025-06-25T00:00:00 / order J250019366 / suffix 1 / production 21.3043 / good_qty 5502.4508 / scrap_qty 0.0 / qty_method csi_production_minutes_share_by_dominant_event`
  - `024-043 / 2025-06-25T13:00:00 / order J250019366 / suffix 16 / production 24.6333 / good_qty 1705.9314 / scrap_qty 0.0640 / qty_method csi_production_minutes_share_by_dominant_event / quantity_confidence medium`

## Remaining Limitations
- Gold still uses one dominant CSI event per machine-hour. Multi-event CSI quantity blending is still out of scope.
- Quantity still follows `production_minutes`; if the current minute attribution falls back to wall-clock overlap, quantity confidence is reduced to `medium`.
- This task still does not allocate `cumulative_qty`.
- This task still does not use MES quantity fallback.
- The live smoke slice did not have same-day MES rows for the chosen family, so live MES preservation remained unit-test-covered rather than live-slice-covered.
- Idle attribution and maintenance-state promotion remain open follow-up tasks.

## Pass Status
Task 3C6 should be considered passed. Gold now allocates CSI `good_qty` and `scrap_qty` onto existing machine-hour rows conservatively, preserves current 3C1–3C5 behavior, keeps re-runs safe, records deterministic quantity-audit metadata, and passes both focused and broader regression validation.
