# Task16A Defended-Core Governance And Smoke Hardening Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task14F passed`
  - `Task15A passed`
  - `Task15C passed`
  - `Task15E passed`
  - `Task15I completed as read-only review`
- Active live bundle remained unchanged:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- Default runtime DB path remained the repo-local:
  - `manufacturing_data.db`

## 2. task boundary kept

- Task16A stayed narrow:
  - no DB writes
  - no ETL/materialization rerun
  - no retraining
  - no artifact promotion
  - no good_qty semantic change
  - no blocked-logic change
  - no Rule-B prototype or remediation work
- The task only touched defended-core governance wording, dormant predictor helper isolation, and one read-only `.conda311` smoke path.

## 3. stale-governance normalization landed

- `core/ml_trainer.py`
  - replaced the stale default retraining provenance tag `Task 4L` with the neutral default `canonical_retraining_candidate`
  - replaced the stale default retraining archive dirname `task4l_artifacts` with `canonical_retraining_artifacts`
  - removed stale `Task 4L` wording from the time-aware reevaluation blocker messages
- `CURRENT_REBUILD_STATUS.md`
  - converted the remaining present-tense `Task 4L` live-bundle statements on the living status ledger into historical-stage wording or live-bundle-neutral boundary wording so the primary re-entry file no longer conflicts with Task14F truth
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`
  - corrected the active-artifact section from the stale Task4L live-bundle claim to the accepted Task14F live bundle

## 4. dormant predictor helper-debt isolation landed

- `core/ml_predictor.py`
  - added one explicit class docstring boundary that separates defended-core saved-model prediction from dormant legacy lookup helpers
  - added `_legacy_lookup_db_path()` and `_open_legacy_unified_view_connection()` so the remaining `unified_view` compatibility helpers use the repo-local DB through `core.runtime_paths.get_database_path()`
  - kept the legacy `unified_view` helper behavior backward-safe and unchanged in purpose
  - did not change `predict_efficiency()` behavior on the defended-core routed path

## 5. new read-only smoke path

- Added:
  - `scripts/run_task16a_defended_core_smoke.py`
- The script runs under `.conda311` and proves:
  - repo-local DB-path resolution through `core/runtime_paths.get_database_path()`
  - canonical Gold month enumeration
  - canonical ML post-June fact slice readability
  - canonical Optimization month enumeration
  - active saved-artifact loadability through `MLPredictor`
  - defended-core import success for:
    - `app.py`
    - `modules/ml_module.py`
    - `modules/optimization_module.py`
    - `modules/maintenance_module.py`
  - unchanged DB/model/preprocessor fingerprints across the smoke itself

## 6. validation result

- `py_compile` passed on:
  - `core/ml_trainer.py`
  - `core/ml_predictor.py`
  - `tests/test_ml_trainer.py`
  - `tests/test_ml_predictor.py`
  - `scripts/run_task16a_defended_core_smoke.py`
- Focused unit tests passed:
  - `tests.test_ml_trainer`
  - `tests.test_ml_predictor`
- Added focused proof points:
  - the default retraining manifests now use the neutral retraining tag/archive defaults
  - legacy predictor lookup helpers resolve the repo-local DB through runtime paths
- New smoke passed:
  - `./.conda311/bin/python scripts/run_task16a_defended_core_smoke.py`
  - resolved DB path matched repo-local `manufacturing_data.db`
  - canonical Gold months = `14`
  - canonical ML post-June fact rows on `February 2026` = `57,792`
  - canonical Optimization months = `14`
  - predictor loaded the active model and preprocessor successfully
  - defended-core imports succeeded for `app.py`, `modules/ml_module.py`, `modules/optimization_module.py`, and `modules/maintenance_module.py`

## 7. live DB / live artifact safety

- Repo-local DB contents remained untouched.
- No write-capable SQL path was executed.
- No ETL/materialization path was executed.
- No retraining or artifact promotion path was executed outside temporary unit-test sandboxes.
- Before/after live fingerprints remained unchanged for:
  - `manufacturing_data.db`
  - `models/production_efficiency_model.pkl`
  - `models/production_preprocessor.pkl`
  - both live provenance JSONs

## 8. closeout decision

- Result: **Task16A passed**
- Why it passed:
  - defended-core stale live-bundle wording was corrected on the material surfaces touched by this task, including the living status ledger
  - dormant `unified_view` helper debt in `core/ml_predictor.py` is now isolated and explicitly marked without changing routed prediction behavior
  - the new `.conda311` read-only smoke path passed against the repo-local DB
  - no DB write, retraining, or artifact promotion occurred
