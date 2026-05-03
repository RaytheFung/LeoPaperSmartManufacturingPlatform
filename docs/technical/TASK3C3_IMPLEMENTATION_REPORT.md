# Task 3C3 Implementation Report

## What Changed
- Extended [core/gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py) so `fact_machine_hour` can carry a conservative MES context overlay on top of the existing Task 3C1 energy backbone and Task 3C2 CSI attribution.
- Extended [tests/test_gold_fact_builder.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_gold_fact_builder.py) with focused MES overlay tests, including the real June suffix-format drift that would otherwise block valid matches.

## Exact MES Overlay Rules
- Base table stays `fact_machine_hour` at grain `canonical_machine_id x hour_ts`.
- Existing energy and CSI fields are preserved; MES only fills MES-specific audit fields and `manpower`.
- MES primary match requires:
  - same `canonical_machine_id`
  - same `order_id`
  - same normalized `order_suffix`
  - `report_ts` on the same calendar date as `hour_ts`
- If more than one MES row matches the same Gold row under that identity key, the chosen row is the one whose `report_ts` is closest to the machine-hour end. Ties are broken deterministically by `source_row_hash`.
- On a successful match, Gold now stores:
  - `mes_source_row_hash`
  - `mes_report_ts`
  - `mes_match_method`
  - `mes_match_confidence`
  - `manpower`
- `source_flags` also records:
  - `has_mes_match`
  - `mes_match_candidate_count`
  - `mes_match_used_order_suffix`
  - `mes_report_type`
  - `mes_csi_upload_status`
  - `mes_resource_id_raw`
  - `mes_prep_hours_candidate`
- `attribution_method` becomes `energy_csi_mes_overlay` only when a MES match is applied.

## Order Suffix Decision
- Real June inspection showed `order_id` alone is unsafe for MES matching. There are thousands of `(canonical_machine_id, order_id)` groups with multiple suffixes in the June MES export.
- Gold therefore now carries `order_suffix`, sourced from the dominant CSI event.
- A narrow Gold-local suffix normalization was also required for live June data:
  - CSI suffixes often arrive as Excel-style strings such as `1.0`
  - MES suffixes for the same job often appear as `1`
  - Task 3C3 normalizes only that representation drift inside Gold matching so valid June matches are not lost

## Deliberately Out Of Scope
- No UI or Streamlit retargeting
- No unified-view rewrite
- No ML changes
- No maintenance final attribution
- No low-confidence MES fallback outside the strong job-identity match

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/gold_fact_builder.py tests/test_gold_fact_builder.py`
- Focused Gold tests:
  - `python3 -m unittest tests/test_gold_fact_builder.py`
  - Result: `Ran 17 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_etl_modules.py`
  - Result: `Ran 52 tests ... OK`

## Live Smoke Validation
- Exact source paths used:
  - `2025 DataSet(JAN to JUN)/Energy Usage 1hr Interval/能耗、費用報表June(1-30).xlsx`
  - `2025 DataSet(JAN to JUN)/CSI Monthly/CSI印刷心電圖報表June.xlsx`
  - `2025 DataSet(JAN to JUN)/MES Monthly/MES生產數據June(Printer).xlsx`
- I did not use the deleted working-tree energy copy under `data/能耗、費用報表June(1-30).xlsx`.
- Positive family slice used for live validation:
  - `canonical_machine_id = 024-149`
  - `order_id = J250021016`
  - `order_suffix = 4`
  - `target_date = 2025-06-20`
- Slice result:
  - `energy_rows_loaded 48`
  - `csi_rows_loaded 10`
  - `mes_rows_loaded 10`
  - `gold_rows 24`
  - `csi_attributed_rows 13`
  - `mes_enriched_rows 13`
  - `high_conf_primary_matches 13`
  - `fallback_rows 0`
- Concrete enriched examples:
  - `024-149 / 2025-06-20T11:00:00 / J250021016 / suffix 4 / manpower 3.0 / mes_report_ts 2025-06-20T20:00:00`
  - `024-149 / 2025-06-20T12:00:00 / J250021016 / suffix 4 / manpower 3.0 / mes_report_ts 2025-06-20T20:00:00`

## Remaining Limitations
- This is still MES context only. MES does not yet assign `machine_state`, `setup_minutes`, or `production_minutes`.
- Low-confidence fallback was intentionally not enabled, because the real June data already required strong suffix disambiguation and a broader fallback would raise false-match risk.
- `team_size` remains untouched; Task 3C3 does not equate `team_size` with MES `manpower`.
- The live validation was a real positive family slice, not a full-month Gold reconciliation run.

## Pass Status
Task 3C3 should be considered passed. MES now enriches `fact_machine_hour` conservatively on top of the existing energy + CSI Gold path, the match logic is reviewable and deterministic, the focused and broader tests pass, and the live June family slice produced believable high-confidence MES enrichments without overwriting CSI-derived fields.
