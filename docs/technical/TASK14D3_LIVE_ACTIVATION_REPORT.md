# Task14D3 Live Activation Report

## 1. accepted baseline used

- Accepted baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
  - `Task14A`
  - `Task14B`
  - `Task14C`
- Shared live artifact baseline before any Task14D3 action remained:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
- Hard boundaries held throughout:
  - no `manufacturing_data.db` write
  - no ETL/materialization change
  - no canonical semantic change
  - no blocked-row-rule change
  - no predictor-contract redesign

## 2. Python 3.11 gate environment result

- Fresh gate environment built at:
  - `/tmp/task14d3_gate_env_20260419`
- Exact interpreter:
  - `/tmp/task14d3_gate_env_20260419/bin/python`
  - `Python 3.11.15 | packaged by conda-forge | (main, Mar 5 2026, 16:59:26) [Clang 19.1.7]`
- Repo-pinned package imports passed:
  - `numpy 1.24.3`
  - `pandas 2.1.4`
  - `scikit-learn 1.3.2`
  - `joblib 1.5.3`
  - `streamlit 1.31.0`
  - `plotly 5.18.0`
- `xgboost` status in this fresh gate:
  - installed = `2.0.3`
  - importable = `true`

## 3. xgboost gate conclusion

- Task14D3 activation does **not** require `xgboost` as a hard gate:
  - live active bundle remains `random_forest`
  - staged Task14C candidate is also `random_forest` on the accepted Task14B summary
- One small repo hardening was applied anyway because prior Task14D/Task14D2 evidence showed native-load failure on `xgboost` can crash `core/ml_trainer.py` at import time even when `xgboost` is not needed for the defended activation path.
- That hardening only broadens the optional import guard so native-load failure is treated as “optional dependency unavailable” rather than a fatal gate crash.

## 4. frozen live / staged artifact verification

- Fresh live SHA-256 checksums still match the frozen Task14C baseline exactly:
  - live model `models/production_efficiency_model.pkl`
    - `1e72e3d80b54da1e122e729f657e3049b771ca9a21a44dcf620f6c905dee4f25`
  - live preprocessor `models/production_preprocessor.pkl`
    - `f930ac1e9bc65be797532a99c7a51cdf00097c9e8d8eb016e0ba1f6720d4d3b1`
  - live model provenance `models/production_efficiency_model.provenance.json`
    - `afbac9e1fe4838911e1cb2e21fdc51bb0345f4c05fea526af60b385eec437049`
  - live preprocessor provenance `models/production_preprocessor.provenance.json`
    - `dc740043ee931eca1893e30429df149b13c944a4e238a359468d26549f51842c`
- Durable staged candidate SHA-256 checksums also still match the Task14C manifest exactly:
  - staged model
    - `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - staged preprocessor
    - `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - staged Task14B summary copy
    - `40c501bdfe702fd907894885ff7f40b0e3bbd152aa0b8ec84d6fff13518aec44`
- Existing Task14C rollback backup remains byte-identical to current live:
  - model `1e72e3d80b54da1e122e729f657e3049b771ca9a21a44dcf620f6c905dee4f25`
  - preprocessor `f930ac1e9bc65be797532a99c7a51cdf00097c9e8d8eb016e0ba1f6720d4d3b1`
  - model provenance `afbac9e1fe4838911e1cb2e21fdc51bb0345f4c05fea526af60b385eec437049`
  - preprocessor provenance `dc740043ee931eca1893e30429df149b13c944a4e238a359468d26549f51842c`

## 5. fresh frozen-protocol revalidation progress

- The repo live DB path hit a fresh read-path blocker in this session:
  - direct sqlite access through the live repo file raised `sqlite3.OperationalError: disk I/O error`
  - creating a brand-new `/tmp` working copy also failed because the local filesystem had only about `116 MiB` free, far below the `6.7 GiB` DB size
- Task14D3 therefore reused the already-existing Task14B/Task13R working DB at:
  - `/tmp/task13r_v3_temp.db`
- Read-only validation on that working DB reproduced the frozen protocol boundary exactly:
  - `fact_machine_hour` rows = `879,978`
  - rows after canonical ML filtering = `364,399`
  - train months = `January 2025` -> `December 2025`
  - eval months = `January 2026` -> `February 2026`
  - train rows = `313,724`
  - eval rows = `50,675`
- Fresh active-bundle holdout reproduced exactly on that same working DB:
  - rows considered = `50,675`
  - rows evaluated = `50,675`
  - non-model-source rows = `0`
  - distinct machines retained = `77`
  - `R² = 0.7605741131053375`
  - `MAE = 0.01499678606743838`
  - `RMSE = 0.15235681463866013`

## 6. exact blocker that stopped activation

- Task14D3 still did **not** close one honest activation outcome.
- Exact blocker:
  - the staged candidate bundle can be verified by checksum, but its model deserialization in the fresh Python 3.11 gate is operationally extreme
- Direct benchmark in the fresh gate env:
  - `pickle.load('models/task14c_artifacts/staged_candidate_20260418_070130/production_efficiency_model.candidate.task14c.pkl')`
  - wall time observed = `1950.69` seconds
- Why that still matters:
  - fresh candidate-side holdout rerun could not be completed within a practical gate window
  - live activation would also depend on that same bundle loading through the routed predictor path before post-activation smokes can pass
  - because the candidate-side rerun plus post-activation route smokes did not finish, the Task14D3 pass criteria were not met

## 7. activation decision

- Promotion decision: **not attempted**
- Reason:
  - the fresh gate environment itself is now valid and version-aligned
  - the frozen active-bundle holdout reproduced cleanly
  - staged candidate and rollback checksums are intact
  - but Task14D3 still could not complete the candidate-side fresh rerun plus post-activation routed-smoke path in a practical runtime window because candidate bundle load/deserialization remained the operative blocker

## 8. shared DB / live artifact safety

- Shared repo DB remained untouched by Task14D3:
  - no write-capable SQL path was executed
  - no ETL/materialization path was executed
  - read-only evaluation was redirected to the existing Task14B/Task13R working DB when the live repo DB path proved unreliable
- Live artifacts remained untouched:
  - no fresh Task14D3 backup set was created
  - no live model/preprocessor overwrite was attempted
  - no rollback was needed because no live swap was attempted

## 9. changed files in this run

- `core/ml_trainer.py`
- `tests/test_ml_trainer.py`
- `scripts/run_task14d3_gate_eval.py`
- `docs/technical/TASK14D3_LIVE_ACTIVATION_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## 10. exact manual-local continuation path

- Minimum reproducible command path from the current healthy gate env:
  1. Verify core imports:
     - `'/tmp/task14d3_gate_env_20260419/bin/python' -c "import numpy,pandas,sklearn,joblib,streamlit,plotly,xgboost; print('imports_ok')"`
  2. Re-run the read-only gate helper on the existing working DB:
     - `'/tmp/task14d3_gate_env_20260419/bin/python' scripts/run_task14d3_gate_eval.py --repo-root /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform --working-db-path /tmp/task13r_v3_temp.db --verbose`
  3. Separately benchmark the staged candidate load if the helper still stalls on the candidate pass:
     - `'/tmp/task14d3_gate_env_20260419/bin/python' -c "import pickle,time; t=time.time(); pickle.load(open('models/task14c_artifacts/staged_candidate_20260418_070130/production_efficiency_model.candidate.task14c.pkl','rb')); print(round(time.time()-t,2))"`
- Exact files/paths to verify next:
  - `models/task14c_artifacts/staged_candidate_20260418_070130/production_efficiency_model.candidate.task14c.pkl`
  - `models/task14c_artifacts/staged_candidate_20260418_070130/production_preprocessor.candidate.task14c.pkl`
  - `models/task14c_artifacts/staged_candidate_20260418_070130/task14b_eval_summary.source.json`
  - `/tmp/task13r_v3_temp.db`
  - `scripts/run_task14d3_gate_eval.py`
