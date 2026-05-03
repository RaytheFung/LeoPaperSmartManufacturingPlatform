# Task 3C1 Implementation Report

## What Was Changed
- Added [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) to create and build the first `fact_machine_hour` Gold table from Silver `energy_meter_hour`.
- Added [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) to lock the Gold energy aggregation rules and deterministic audit behavior.

## Exact Aggregation Rules
- Gold grain is exactly `canonical_machine_id x hour_ts`.
- Only Silver energy rows with non-null `canonical_machine_id` and non-null `hour_ts` are eligible.
- If one or more `aggregate_total` meters exist for a machine-hour, Gold uses only those rows for `energy_total_kwh` and `energy_total_cost`.
- If no `aggregate_total` meter exists, Gold falls back to summing `main`, `uv`, `ir`, and `motor` component rows.
- `aggregate_total` is never added on top of component sums.
- `combo` rows are treated explicitly and are never silently added into totals. They are reflected through `source_flags` and the `energy_total_source_method`.
- Gold preserves deterministic audit fields:
  - `energy_source_row_count`
  - `energy_source_row_hashes_json`
  - `source_flags`
  - `energy_total_source_method`

## Deliberately Out Of Scope
- CSI, MES, and maintenance minute attribution
- `setup_minutes`, `production_minutes`, `planned_stop_minutes`, `unplanned_stop_minutes`, `maintenance_minutes`, and `idle_minutes` derivation
- Streamlit page retargeting
- Legacy unified-view rewrites
- ML changes

## Known Ambiguities Before CSI/MES Attribution
- `combo` meters remain explicit but unresolved for exact sub-component allocation; later attribution logic must decide whether they stay separate evidence or can be apportioned safely.
- When both aggregate and component rows are present, Gold preserves the component subtotals but trusts aggregate rows for total energy. Later attribution rules must decide how to reason about mismatches between those two views.
- `machine_state` and `state_confidence` are placeholders in this task because no four-source attribution has started yet.

## Validation Performed
- Focused Gold unit tests cover:
  - aggregate-total preference
  - component-sum fallback
  - explicit combo handling without double counting
  - null-canonical exclusion
  - one-row-per-machine-hour grain
  - deterministic audit fields
- Broader regression run:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 41 tests ... OK`
- Light real-sample smoke validation:
  - Read the first 40 rows from `data/能耗、費用報表June(1-30).xlsx`
  - Wrote them through Bronze `raw_energy_hourly`
  - Normalized them into Silver `energy_meter_hour`
  - Built Gold `fact_machine_hour`
  - Result: `silver_rows 40`, `gold_rows 40`
  - Sample Gold rows showed `energy_total_source_method = aggregate_total_preferred` on the June labels tested

## Pass Status
Task 3C1 should be considered passed once the current Gold builder and tests are validated in the live repo, because the required energy-only Gold backbone is now isolated, deterministic, and still clearly bounded away from CSI/MES/maintenance attribution.
