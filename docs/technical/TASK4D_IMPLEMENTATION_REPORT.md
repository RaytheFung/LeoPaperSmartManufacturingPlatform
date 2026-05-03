# Task 4D Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/`
  - `core/canonical_materializer.py`
  - `core/canonical_gold_reader.py`
  - `core/ml_predictor.py`
  - `core/ml_trainer.py`
  - `modules/ml_module.py`
  - `modules/shared_ml_components.py`
  - `app.py`
  - `tests/`
- Confirmed the live ML route before editing:
  - `app.py`
  - sidebar route `🤖 Machine Learning`
  - `show_ml_module()`
  - `render_ml_module()`
- Confirmed the old ML page path still depended on:
  - hardcoded `manufacturing_data.db`
  - legacy `unified_view`
  - fallback / simulated prediction behavior
  - legacy training UI assumptions

## What Changed
- Added [core/canonical_ml_reader.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) as the narrow canonical ML helper over `fact_machine_hour` only.
- Rewrote [modules/ml_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) so the live ML page now renders canonical month-scoped inference results, readiness metrics, blocked rows, and an explicit contract note instead of querying legacy tables.
- Added [tests/test_canonical_ml_reader.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_ml_reader.py) for month loading, feature derivation, hard-block behavior, predictor gating, empty-month behavior, and no-legacy-source assertions.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) so the live execution ledger reflects Task 4D.
- Updated [docs/technical/REBUILD_DOCS_INDEX.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md) so Task 4D is indexed with the other rebuild reports.

## Exact ML Page / Module Retargeted
- Retargeted module:
  - `modules/ml_module.py`
- Exact page path:
  - `app.py` sidebar route `🤖 Machine Learning`
  - `show_ml_module()`
  - `render_ml_module()`
- Task 4D scope kept narrow:
  - month selector from canonical Gold availability
  - canonical inference input building for the selected month
  - machine-level latest-row candidate selection
  - saved-model inference only when predictor artifacts are available and return `source == model`
  - explicit blocked-row reporting instead of fallback simulation
- Training tab status:
  - visible for honesty / continuity
  - explicitly marked canonical-retarget-pending
  - does not execute the legacy trainer from this page

## Exact Canonical Read Rule Used
- The helper reads from `fact_machine_hour` only.
- Available months come from distinct `substr(hour_ts, 1, 7)` values in `fact_machine_hour`.
- Selected-month rows are loaded by canonical month bounds:
  - `hour_ts >= month_start`
  - `hour_ts < next_month_start`
- The helper does not:
  - query `unified_view`
  - recreate compatibility tables
  - silently fabricate demo rows
  - accept non-model predictor output as if it were canonical inference
- If `fact_machine_hour` is missing or the selected month has no canonical rows, the page warns explicitly and stops.

## Exact Canonical ML Adapter Contract
- Direct canonical fields used:
  - `canonical_machine_id`
  - `hour_ts`
  - `material_code`
  - `task_name`
  - `good_qty`
  - `team_leader`
  - `team_size`
  - `manpower`
  - `hours_since_last_maintenance`
  - `last_maintenance_work_order_type`
  - `source_flags`
- Derived inference fields:
  - `machine_id = canonical_machine_id`
  - `production_qty = good_qty`
  - `hour_of_day`, `day_of_week`, `month`, `is_weekend` from `hour_ts`
  - `task_difficulty` inferred from `task_name`
- Safe adapter rules:
  - `task_difficulty` maps `光` to `Easy`, `印` to `Medium`, and mixed `印` + `光` or `+` to `Hard`, otherwise documented `Medium`
  - `team_size` uses canonical `team_size`, then rounded `manpower`, then the saved preprocessor default
  - `maintenance_intensity_30d` uses `source_flags.maintenance_distinct_work_order_count_30d`, otherwise `0.0`
  - `cumulative_maintenance_count` uses the saved preprocessor default because Gold does not yet carry a first-class cumulative column
  - `last_maintenance_type` uses canonical `last_maintenance_work_order_type`, then the matching source flag, then `unknown`
  - `team_leader` and `material_code` fall back to `unknown` with adapter notes when missing

## Exact Block / Safety Rule Used
- Rows are blocked before inference when:
  - machine ID is missing
  - timestamp is missing
  - `good_qty <= 0`
  - `hours_since_last_maintenance` is missing
- Candidate selection:
  - keep only inference-eligible rows
  - choose the latest eligible row per machine for prediction display
- Predictor gate:
  - if saved artifacts are unavailable, candidates are blocked with `predictor_artifacts_unavailable`
  - if `predict_efficiency(...)` returns anything except `source == model`, that row is blocked with `predictor_returned_non_model_source`
  - the page never surfaces simulated fallback output as canonical inference

## What Stayed Deliberately Out Of Scope
- model retraining or trainer rewrite
- `core/ml_trainer.py` retargeting
- `modules/shared_ml_components.py` cleanup
- new Gold feature engineering columns beyond the documented adapter layer
- maintenance page rewrite
- optimization advanced-tab rewrite
- broad app redesign
- historical backfill automation

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/canonical_ml_reader.py modules/ml_module.py tests/test_canonical_ml_reader.py`
- Focused Task 4D tests:
  - `python3 -m unittest tests/test_canonical_ml_reader.py`
  - Result: `Ran 7 tests ... OK`
- Cross-task canonical regression:
  - `python3 -m unittest tests/test_canonical_ml_reader.py tests/test_canonical_gold_reader.py tests/test_canonical_optimization_reader.py tests/test_canonical_materializer.py`
  - Result: `Ran 22 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_canonical_gold_reader.py tests/test_canonical_materializer.py tests/test_canonical_optimization_reader.py tests/test_canonical_ml_reader.py`
  - Result: `Ran 100 tests ... OK`

## Live Smoke Validation
- Shared DB note:
  - the current repo `manufacturing_data.db` still does not provide the canonical Gold month needed for an honest ML smoke
  - validation therefore used a temp DB that mirrors the canonical Bronze -> Silver/Gold -> ML page flow
- Selected month:
  - `June 2025`
- Smoke steps:
  - created a temp DB with canonical Bronze support tables
  - seeded June Bronze energy, CSI, MES, and maintenance rows using the repo’s real raw-column contracts
  - ran `CanonicalMaterializer.materialize_month("June 2025")`
  - dropped the temp `unified_view` table before ML readback
  - loaded the saved `MLPredictor()` artifacts from `models/`
  - ran `CanonicalMLReader` month loading, candidate selection, and prediction building
- Smoke results:
  - `silver_rows_materialized_by_table {'energy_meter_hour': 3, 'csi_job_event': 3, 'mes_report_event': 3, 'maintenance_txn_event': 2}`
  - `fact_machine_hour_rows_created 3`
  - `canonical_rows_loaded_for_ml 3`
  - `distinct_machines 2`
  - `rows_eligible_for_inference 3`
  - `machines_eligible_for_inference 2`
  - `machines_blocked_after_predictor_gate 0`
  - `predictor_artifacts_found {'model_artifact_present': True, 'predictor_bundle_present': True, 'canonical_inference_enabled': True}`
  - `canonical_inference_worked_without_unified_view True`
- Example canonical fact rows:
  - `024-001 / 2025-06-02T00:00:00 / good_qty 12.0 / hours_since_last_maintenance 4.0 / last_maintenance_work_order_type PM`
  - `024-002 / 2025-06-02T00:00:00 / good_qty 28.0 / hours_since_last_maintenance 5.0 / last_maintenance_work_order_type Corrective`
- Example prediction rows:
  - `024-002 / predicted_efficiency 0.8795 / confidence 0.8574 / top_driver production_qty: Current load 28 units vs typical 1,307`
  - `024-001 / predicted_efficiency 4.4536 / confidence 0.7574 / top_driver production_qty: Current load 8 units vs typical 1,307`

## Remaining Limitations
- Task 4D only retargets the live ML inference page path.
- The current trainer still reads legacy `unified_view`, so retraining is not yet canonical.
- The canonical ML page still uses a documented adapter layer for features that are not yet first-class Gold columns.
- The page shows latest eligible row per machine for prediction display; it is not yet a full historical scoring workbench.
- `maintenance_minutes` remains intentionally null in Gold.

## Pass Status
Task 4D should be considered passed.

The live ML page now reads canonical Gold `fact_machine_hour` only for its active inference path, blocks unsupported rows honestly instead of falling back to simulated output, and continues to expose the legacy training tab only as an explicit canonical-retarget-pending stub.
