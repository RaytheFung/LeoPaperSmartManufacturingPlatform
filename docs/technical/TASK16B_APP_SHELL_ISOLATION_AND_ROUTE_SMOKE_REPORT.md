# Task16B App Shell Isolation And Route Smoke Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task14F passed`
  - `Task15A passed`
  - `Task15C passed`
  - `Task15E passed`
  - `Task15I completed as read-only review`
  - `Task16A passed`
- Active live bundle remained unchanged:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- Default runtime DB path remained the repo-local:
  - `manufacturing_data.db`

## 2. task boundary kept

- Task16B stayed narrow:
  - no DB writes
  - no ETL/materialization rerun
  - no retraining
  - no artifact promotion
  - no good_qty semantic change
  - no blocked-logic change
  - no predictor-behavior change
- The task only touched the defended-core app-entry shell boundary, one route-contract test, one read-only `.conda311` smoke path, and the minimal truth anchors.

## 3. defended-core app-shell isolation landed

- `app.py`
  - added one explicit helper-based route contract that separates defended-core routes, the experimental bonus route, and dormant legacy helper names
  - kept the current sidebar-routed shell on canonical readers/modules only
  - moved the dormant June ETL/EUVG imports into `load_data()` so app-entry import no longer depends on that legacy loader stack
  - kept the in-file legacy helper functions present, but marked them explicitly as dormant/non-routed helper paths

## 4. new read-only route smoke path

- Added:
  - `scripts/run_task16b_app_shell_smoke.py`
- The script runs under `.conda311` and proves:
  - `app.py` imports successfully while legacy loader imports are blocked during app import
  - visible routed pages remain the expected defended-core + experimental contract by runtime mode
  - defended-core route imports succeed for:
    - `modules/unified_view_module.py`
    - `modules/ml_module.py`
    - `modules/optimization_module.py`
    - `modules/maintenance_module.py`
  - the experimental route import also succeeds while remaining bonus-only
  - `core.runtime_paths.get_database_path()` still resolves to repo-local `manufacturing_data.db`
  - DB/model/preprocessor/live-provenance fingerprints remain unchanged across the smoke itself

## 5. validation result

- `py_compile` passed on:
  - `app.py`
  - `tests/test_app_route_contract.py`
  - `scripts/run_task16b_app_shell_smoke.py`
- Focused unit test passed:
  - `tests.test_app_route_contract`
- Added focused proof points:
  - app import now succeeds even when `core.enhanced_etl_solution_CURRENT` and `modules.euvg_module` imports are blocked during app import
  - visible runtime pages across `standard`, `demo_readonly`, and `pilot_review` have zero loader-dependent routed pages
- New smoke passed:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python scripts/run_task16b_app_shell_smoke.py`
  - defended-core route labels matched the live runtime capability contract
  - experimental route remained present only where the runtime capability contract allows it
  - defended-core and experimental routes did not use the dormant legacy loader path
  - route-module imports succeeded

## 6. live DB / live artifact safety

- Repo-local DB contents remained untouched.
- No write-capable SQL path was executed.
- No ETL/materialization path was executed.
- No retraining or artifact promotion path was executed.
- Before/after live fingerprints remained unchanged for:
  - `manufacturing_data.db`
  - `models/production_efficiency_model.pkl`
  - `models/production_preprocessor.pkl`
  - both live provenance JSONs

## 7. closeout decision

- Result: **Task16B passed**
- Why it passed:
  - defended-core route truth is now explicit at app-entry level
  - dormant legacy loader ambiguity was reduced without changing defended-core behavior
  - the new `.conda311` read-only app-shell smoke passed
  - no DB write, ETL/materialization, retraining, or artifact promotion occurred
