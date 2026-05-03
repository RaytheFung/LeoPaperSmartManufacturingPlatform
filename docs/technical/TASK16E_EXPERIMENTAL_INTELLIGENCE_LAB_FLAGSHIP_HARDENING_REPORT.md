# Task16E Experimental Intelligence Lab Flagship Hardening Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task14F passed`
  - `Task15A passed`
  - `Task15C passed`
  - `Task15E passed`
  - `Task15F passed`
  - `Task15G passed`
  - `Task15H passed`
  - `Task15I closed Task15 and allowed Task16 entry`
  - `Task16A passed`
  - `Task16B passed`
  - `Task16C passed`
  - `Task16D passed`
- Active live bundle remained unchanged:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- Default runtime DB path remained the repo-local:
  - `manufacturing_data.db`

## 2. task boundary kept

- Task16E stayed narrow:
  - no DB writes
  - no ETL/materialization rerun
  - no retraining
  - no artifact promotion
  - no good_qty semantic change
  - no blocked-logic change
  - no defended-core prediction-behavior change
- The task only touched experimental-lane wording/provenance, explicit active-artifact binding on the scheduling prototype, one read-only `.conda311` smoke path, focused tests, and the minimal ledger/manifest/doc anchors.

## 3. experimental route wording hardening landed

- `modules/experimental_intelligence_lab_module.py`
  - replaced the stale route copy `active Task 4L artifacts` with `active saved live artifacts`
  - reframed the lane as an `internal-landing experimental flagship lane`
  - preserved the honesty boundaries:
    - read-only
    - no DB writes
    - no artifact promotion
    - no solver claim
    - no predictive-maintenance production claim
  - added one compact live-bundle caption:
    - `Task 14F / 20260419_181842 / random_forest`
- Direct source check on the live route file now confirms:
  - stale `Task 4L` wording absent
  - internal-landing flagship wording present
  - `active saved live artifacts` wording present

## 4. active artifact / data-path verification landed

- `core/experimental_scheduling.py`
  - added one explicit active-artifact binding helper that resolves:
    - `models/production_efficiency_model.pkl`
    - `models/production_preprocessor.pkl`
    - both live provenance JSONs
  - the default experimental scheduling path now instantiates `MLPredictor` against those explicit repo-local live paths instead of relying on implicit relative defaults
  - the scheduling payload now carries a compact active-binding summary so smoke/tests can prove:
    - `task_tag = Task 14F`
    - `artifact_version_id = 20260419_181842`
    - `selected_model = random_forest`
    - predictor instantiated from the explicit active live paths
    - model and preprocessor both loaded successfully
- Result:
  - the stale Task4L route reference was copy-only
  - the smallest safe live-path hardening still landed because the old default constructor path was implicit rather than explicit
  - defended-core prediction behavior was not touched

## 5. prototype provenance hardening landed

- Scheduling provenance stayed explicit:
  - default queue provenance = `Real-seeded synthetic queue`
  - preferred pilot path = `Real-input pilot queue`
  - manual queue remains stress-test-only
- Maintenance provenance stayed explicit:
  - prototype mode = `Weak-label model` or `Fallback evidence score`
  - `core/experimental_maintenance_prototype.py` now returns and states the stored maintenance-event observation horizon explicitly
  - live smoke on the repo DB confirmed:
    - stored maintenance-event horizon end = `2025-08-14`
- `modules/experimental_intelligence_lab_module.py`
  - now adds one compact late-anchor note when the selected month extends beyond the stored maintenance-event horizon

## 6. new read-only smoke path

- Added:
  - `scripts/run_task16e_experimental_lab_smoke.py`
- The script runs under `.conda311` and proves:
  - `app.py` imports successfully
  - `modules/experimental_intelligence_lab_module.py` imports successfully
  - the experimental route is visible in `standard` and `pilot_review`, hidden in `demo_readonly`
  - repo-local DB resolution still points to `manufacturing_data.db`
  - one real selected-month experimental route snapshot builds successfully
  - one real selected-month scheduling payload builds with explicit `Real-seeded synthetic queue` provenance
  - one real selected-month maintenance payload builds with explicit prototype mode and maintenance-event horizon
  - active model / preprocessor / provenance fingerprints remain unchanged before/after
  - no DB write, ETL/materialization, retraining, or artifact promotion occurred

## 7. validation result

- `py_compile` passed on:
  - `core/experimental_scheduling.py`
  - `core/experimental_maintenance_prototype.py`
  - `modules/experimental_intelligence_lab_module.py`
  - `scripts/run_task16e_experimental_lab_smoke.py`
  - `tests/test_experimental_scheduling.py`
  - `tests/test_experimental_maintenance_prototype.py`
  - `tests/test_experimental_intelligence_lab_route.py`
- Focused unit tests passed:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_experimental_scheduling tests.test_experimental_maintenance_prototype tests.test_experimental_intelligence_lab_route`
  - result:
    - `Ran 14 tests in 0.490s`
    - `OK`
- New smoke passed:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python scripts/run_task16e_experimental_lab_smoke.py`
  - key result highlights:
    - selected month = `February 2026`
    - route exposure = `standard yes / demo_readonly no / pilot_review yes`
    - `fact_machine_hour` rows = `879,978`
    - month coverage = `2025-01` -> `2026-02`
    - route snapshot built successfully
    - scheduling payload = `3` queue rows / `3` assigned rows / provenance `Real-seeded synthetic queue`
    - maintenance payload = `86` risk rows / prototype mode `Weak-label model` / stored future-event observation through `2025-08-14`
    - active scheduling binding = `Task 14F / 20260419_181842 / random_forest`

## 8. live DB / live artifact safety

- Repo-local DB contents remained untouched.
- No write-capable SQL path was executed.
- No ETL/materialization path was executed.
- No retraining or artifact promotion path was executed.
- Before/after fingerprints remained unchanged:
  - DB SHA1:
    - `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - model SHA-256:
    - `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - preprocessor SHA-256:
    - `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - model provenance SHA-256:
    - `d23648bb1fb24b9e830ba6586df5ed4faf02645522b085293e968f3a76774ff5`
  - preprocessor provenance SHA-256:
    - `66cbdb505ef3c577a0523efabf8881d6f6b104470fc17ff203f44f520d3a7611`

## 9. closeout decision

- Result: **Task16E passed**
- Why it passed:
  - the experimental route no longer carries stale Task4L live-bundle wording
  - predictor-backed scheduling now binds explicitly to the repo-local live Task14F artifact paths
  - queue provenance and maintenance prototype provenance remain explicit and honest
  - the runtime ownership manifest and living ledger now describe the lane as an internal-landing experimental flagship while keeping it non-defended for production claims
  - the new `.conda311` read-only experimental-lane smoke passed
  - no DB write, ETL/materialization, retraining, or artifact promotion occurred
