# Task 4G Implementation Report

## Preflight Repo Check
- Live repo paths actually inspected before editing:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/REBUILD_DOCS_INDEX.md`
  - `docs/technical/REBUILD_INTENT_AND_SYSTEM_SPEC.md`
  - `docs/technical/v1_canonical_schema.md`
  - `docs/technical/TASK4F_IMPLEMENTATION_REPORT.md`
  - `artifacts/diagnostics/task4g/TASK4G_RECOVERY_REPORT.md`
  - `artifacts/diagnostics/task4g/TASK4G_ACTIVE_DB_DIAGNOSTIC.md`
  - `artifacts/diagnostics/task4g/TASK4G_BLOCKER_REPORT.md`
  - `core/ml_trainer.py`
  - `core/ml_predictor.py`
  - `core/canonical_ml_reader.py`
  - `modules/ml_module.py`
  - `tests/test_ml_trainer.py`
  - `tests/test_ml_module.py`
  - `tests/test_canonical_ml_reader.py`
- Prompt inputs read from the user-provided TextEdit/iCloud files:
  - `Prompt for Task4G(2.0).rtf`
  - `Prompt for Task4G(3.0).rtf`
  - `Prompt for Task4G（Real Rerun Task4G Promotion）.rtf`
- Real runtime paths re-proved from disk before the promotion run:
  - active DB: `manufacturing_data.db`
  - active model: `models/production_efficiency_model.pkl`
  - active preprocessor: `models/production_preprocessor.pkl`

## Exact Baseline Evidence
- Approved baseline in [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md):
  - `- Task 4F passed`
  - no `Task 4G passed` line existed before this run
- Active DB coverage re-proved from disk before the rerun:
  - `fact_machine_hour rows 64725`
  - `nonnull good_qty 22256`
  - `positive good_qty 22172`
  - `nonnull team_leader 29259`
  - `nonnull manpower 26432`
  - `nonnull hours_since_last_maintenance 15556`
- Candidate-first precondition was therefore satisfied on the repaired active DB.

## What Changed
- Updated [core/ml_trainer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py):
  - canonical retraining now seeds adapter defaults from the real active preprocessor path while still writing candidate artifacts first
  - candidate promotion now requires a real predictor smoke on canonical machine-hour inputs
  - successful promotion now writes active provenance manifests and returns the post-promotion candidate status consistently
- Updated [core/ml_predictor.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py):
  - removed the legacy `prediction < 0.3` fallback rule
  - canonical predictor now accepts low positive kWh/unit outputs and only rejects negative values or outputs above the configured upper bound
- Updated [modules/ml_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py):
  - retraining result rendering now shows predictor-smoke status alongside the promotion gate
- Added [tests/test_ml_predictor.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_predictor.py) to prove low-but-valid model outputs stay on the `model` source path
- Updated [tests/test_ml_trainer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_trainer.py) and [tests/test_ml_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_module.py) for the new predictor-smoke gate and result structure

## Exact Task 4G Promotion Rule
- Candidate artifacts are trained into `models/task4g_artifacts/` first.
- Candidate manifests are written before promotion.
- Promotion is blocked unless all of the following are true:
  - candidate model exists and is loadable
  - candidate preprocessor exists and is loadable
  - candidate model manifest is present
  - candidate preprocessor manifest is present
  - candidate preprocessor manifest feature contract matches the live training feature columns
  - at least one canonical prediction produced by the candidate artifacts returns `source == model`
- Only after the gate passes are the active model and preprocessor paths overwritten.

## Exact Failure Found During The Real Rerun
- First real rerun candidate version:
  - `20260330_213125`
- The first rerun trained successfully but promotion was correctly blocked.
- Exact blocker:
  - candidate predictor smoke returned non-model source for every sampled canonical candidate row
- Root cause proved from the live canonical training slice:
  - `rows_after_filtering 3945`
  - `kwh_per_unit p50 0.008240628410465491`
  - `rows below 0.3 = 3916 / 3945`
- That proved the predictor's legacy `0.3` lower guard was incompatible with the real canonical Task 4G target distribution.
- After replacing that guard with a non-negative lower bound, the rerun was repeated.

## Exact Real Rerun Result
- Successful Task 4G artifact version:
  - `20260330_213926`
- Training source:
  - `fact_machine_hour`
- Real training load summary:
  - `rows_loaded 64725`
  - `rows_after_hard_block 3945`
  - `rows_after_filtering 3945`
  - `distinct_machines_after_filtering 24`
  - `month_coverage January 2025`
- Selected model:
  - `xgboost`
- Real evaluation metrics:
  - `r2_score 0.2091456031294202`
  - `mae 0.011774886343415532`
  - `rmse 0.07774618132391221`

## Exact Artifact State After Promotion
- Active model path:
  - `models/production_efficiency_model.pkl`
- Active preprocessor path:
  - `models/production_preprocessor.pkl`
- Active artifact modified timestamps:
  - model `2026-03-30T21:40:37.645287`
  - preprocessor `2026-03-30T21:40:37.650813`
- Active provenance manifests now exist and are valid:
  - `models/production_efficiency_model.provenance.json`
  - `models/production_preprocessor.provenance.json`
- Active manifest summary:
  - `artifact_version_id 20260330_213926`
  - `selected_model xgboost`
  - `promotion_success true`
  - `task_tag Task 4G`
- Candidate artifact set retained:
  - `models/task4g_artifacts/production_efficiency_model.candidate.20260330_213926.pkl`
  - `models/task4g_artifacts/production_preprocessor.candidate.20260330_213926.pkl`
  - matching `.provenance.json` files beside both artifacts
- Backup artifact set created during promotion:
  - `models/task4g_artifacts/production_efficiency_model.backup.20260330_213926.pkl`
  - `models/task4g_artifacts/production_preprocessor.backup.20260330_213926.pkl`
- Backup manifest paths are null because the pre-Task-4G active artifacts were legacy files without existing provenance manifests.

## Exact Predictor Smoke Proof
- Promotion gate result:
  - `passed true`
  - `failures []`
- Predictor smoke result:
  - `passed true`
  - `prediction_source model`
  - `predicted_efficiency 0.008638044819235802`
  - `confidence 0.9028894697049799`
  - `sample_month January 2025`
  - `sample_machine_id 024-135`
  - `sample_hour_ts 2025-01-12T16:00:00`
  - `candidate_rows_considered 1`

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/ml_predictor.py core/ml_trainer.py modules/ml_module.py tests/test_ml_predictor.py tests/test_ml_trainer.py tests/test_ml_module.py`
- Focused ML regressions:
  - `python3 -m unittest tests.test_ml_predictor tests.test_ml_trainer tests.test_ml_module tests.test_canonical_ml_reader`
  - Result: `Ran 20 tests ... OK`
- Post-fix regression:
  - `python3 -m unittest tests.test_ml_trainer tests.test_ml_module tests.test_ml_predictor`
  - Result: `Ran 13 tests ... OK`
- Task 4G repair regression recheck:
  - `python3 -m unittest tests.test_fact_machine_hour_repair`
  - Result: `Ran 1 test ... OK`
- Real promotion run:
  - `python3 - <<'PY' ... run_canonical_retraining() ... PY`
  - Result: active promotion succeeded with artifact version `20260330_213926`

## Remaining Limitations
- Canonical inference and retraining still use documented adapter defaults for features that are not yet first-class Gold columns.
- Retraining remains synchronous and user-triggered.
- The training metadata table records real training attempts on the active DB path; it is not a separate candidate-only metadata store.
- Optimization advanced tabs remain canonical-retarget-pending beyond the Phase 1 summary/ranking path.

## Pass Status
Task 4G should be considered passed.

The real active-path rerun now stages candidate artifacts first, proves a live canonical predictor smoke with `source == model`, promotes the active artifacts only after that gate passes, and records Task 4G provenance on the active model and preprocessor paths.
