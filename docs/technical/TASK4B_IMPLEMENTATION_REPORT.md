# Task 4B Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/`
  - `core/silver_normalizer.py`
  - `core/gold_fact_builder.py`
  - `core/canonical_gold_reader.py`
  - `modules/etl_module.py`
  - `modules/unified_view_module.py`
  - `tests/`
- Confirmed the live post-ETL hook before editing:
  - `modules.etl_module.process_uploaded_files(...)`
  - `from modules.unified_view_module import auto_process_after_etl`
  - `auto_process_after_etl(month_year)`
- Historical handoff path note:
  - the current repo only has the handoff docs under `docs/technical/`
  - old root-level handoff paths are not present anymore
  - Task 4B continued from `CURRENT_REBUILD_STATUS.md` plus `docs/technical/` as instructed

## What Changed
- Added [core/canonical_materializer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_materializer.py) as the focused month-scoped canonical materialization helper for the shared runtime DB.
- Narrowly refactored [core/silver_normalizer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/silver_normalizer.py) so the new materializer can reuse the existing normalization logic on filtered Bronze month slices without changing normalization rules.
- Repurposed [modules/unified_view_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) `auto_process_after_etl(...)` so it now routes to canonical materialization instead of legacy `UnifiedViewProcessor.process_month(...)`.
- Updated [modules/etl_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/etl_module.py) so the live ETL success path reports canonical materialization honestly and keeps the result in session state for the ETL page.
- Added [tests/test_canonical_materializer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_materializer.py) for month-scoped materialization, rerun safety, preservation of other months, explicit missing-Bronze failure, and wrapper routing.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) so the live execution ledger reflects Task 4B as passed and removes the old Gold-population gap from the Unified View page path.

## Exact Live ETL Hook Retargeted
- Pre-Task 4B live path:
  - `modules.etl_module.process_uploaded_files(...)`
  - `modules.unified_view_module.auto_process_after_etl(month_year)`
  - `UnifiedViewProcessor.process_month(month_year, force_reprocess=True)`
- Post-Task 4B live path:
  - `modules.etl_module.process_uploaded_files(...)`
  - optional maintenance integration writes `raw_maintenance_txn` first when a maintenance file is present
  - `modules.unified_view_module.auto_process_after_etl(month_year, db_path=...)`
  - `core.canonical_materializer.CanonicalMaterializer.materialize_month(month_year)`

## Exact Canonical Materialization Rule
- Reads Bronze from the shared runtime DB only:
  - `raw_energy_hourly`
  - `raw_csi_event`
  - `raw_mes_report`
  - `raw_maintenance_txn`
- Does not reread uploaded Excel files if Bronze rows are already present in DB.
- Uses the existing `SilverNormalizer` logic for Energy / CSI / MES / Maintenance row normalization.
- Rebuilds Gold from the existing `GoldFactBuilder` rules:
  - energy backbone
  - CSI overlay
  - MES overlay
  - maintenance context overlay
  - CSI quantity overlay
  - idle overlay
  - maintenance-state review overlay
- Keeps the Task 4A canonical page helper unchanged.

## Exact Month-Scoped Rebuild Rule
- The target month is parsed from the processed ETL month label such as `June 2025`.
- Bronze month selection is source-specific and timestamp-based:
  - Energy: `raw_timestamp`
  - CSI: `raw_start_time` / `raw_end_time` / `raw_prep_end_time` with payload fallback to `班次內日期`
  - MES: payload timestamps such as `報工時間`, `記錄新增時間`, `狀態變更時間`, with planned-time fallback
  - Maintenance: `raw_transaction_date`
- Silver month rebuild:
  - find existing target-month rows in each Silver table
  - delete only those target-month rows by `source_row_hash`
  - upsert only the newly normalized target-month rows
- Gold month rebuild:
  - build new `fact_machine_hour` rows only from target-month `energy_meter_hour`
  - apply CSI / MES / maintenance overlays using current Silver context from the shared DB
  - delete only target-month `fact_machine_hour` rows by `hour_ts`
  - insert only the rebuilt target-month rows
- Rerun for the same month is idempotent because the same target partition is deleted and rebuilt rather than appended blindly.
- Other months are preserved.

## Missing-Bronze Safety Rule
- Task 4B fails explicitly when required target-month Bronze rows are missing for:
  - `raw_energy_hourly`
  - `raw_csi_event`
  - `raw_mes_report`
- The error is returned through the ETL wrapper and shown honestly in the ETL page.
- Maintenance Bronze is treated as contextual and may legitimately materialize as zero rows for the month when no maintenance file was loaded.

## Whether Legacy `auto_process_after_etl` Was Repurposed Or Bypassed
- Repurposed.
- The function name stays as the compatibility hook, but its formal behavior is now canonical materialization.
- It no longer points to legacy `UnifiedViewProcessor.process_month(...)`.
- Legacy `unified_view` tables remain in the repo and DB, but the Task 4B hook bypasses them.

## Minimal ETL Page Feedback Added
- After ETL success, the page now reports:
  - target month
  - canonical Silver materialized yes/no
  - canonical Gold materialized yes/no
  - `fact_machine_hour` rows created
  - Silver row counts by table
- The processing-results page also surfaces the canonical materialization result from session state after rerun.

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/canonical_materializer.py core/silver_normalizer.py modules/unified_view_module.py modules/etl_module.py tests/test_canonical_materializer.py`
- Focused Task 4B tests:
  - `python3 -m unittest tests/test_canonical_materializer.py`
  - Result: `Ran 4 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_machine_alias_registry.py tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_canonical_gold_reader.py tests/test_canonical_materializer.py tests/test_etl_modules.py`
  - Result: `Ran 104 tests ... OK`

## Live Smoke Validation
- Validation method:
  - temp DB using the same shared-DB post-trigger shape as the app
  - Bronze rows seeded into the temp DB
  - `modules.unified_view_module.auto_process_after_etl("June 2025", db_path=temp_db)` executed directly
  - [core/canonical_gold_reader.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py) read the month immediately afterward from the same DB
- Target month:
  - `June 2025`
- Smoke source counts used:
  - `raw_energy_hourly 2`
  - `raw_csi_event 1`
  - `raw_mes_report 1`
  - `raw_maintenance_txn 1`
- Materialization result:
  - `silver_rows_materialized_by_table {'energy_meter_hour': 2, 'csi_job_event': 1, 'mes_report_event': 1, 'maintenance_txn_event': 1}`
  - `gold_fact_machine_hour_rows_created 2`
- Immediate same-DB readback:
  - canonical reader month list: `['June 2025']`
  - canonical reader rows for month: `2`
- Legacy bypass check:
  - wrapper reported `legacy_unified_view_bypassed = True`
  - temp DB had no `unified_view` table at all
- Example Gold rows:
  - `024-128 / 2025-06-26T00:00:00 / setup_changeover / 16.5 kWh / VP25000589 / manpower 4.0`
  - `024-128 / 2025-06-26T01:00:00 / production / 9.5 kWh / VP25000589 / manpower 4.0`

## Remaining Limitations
- The canonical live flow is month-upload scoped; it does not backfill all historical months automatically.
- `maintenance_minutes` remains intentionally null in Gold.
- Optimization and ML pages still depend on legacy `unified_view`.
- Month-boundary CSI events that share one `csi_source_row_hash` across adjacent months still depend on previously materialized neighboring-month Gold rows for perfect quantity-basis continuity.

## Pass Status
Task 4B should be considered passed.

The live ETL success path now materializes month-scoped canonical Silver + Gold into the shared runtime DB, the Task 4A Unified View page can read real `fact_machine_hour` rows without a manual temp-db step, and the legacy post-ETL unified-view trigger has been formally replaced by a canonical materialization wrapper.
