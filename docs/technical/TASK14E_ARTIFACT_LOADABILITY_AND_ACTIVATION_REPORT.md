# Task14E Artifact Loadability And Activation Report

## 1. accepted baseline used

- Accepted baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
  - `Task14A`
  - `Task14B`
  - `Task14C`
  - `Task14D3`
- Shared live artifact baseline before any Task14E action remained:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
- Hard boundaries held throughout:
  - no `manufacturing_data.db` write
  - no ETL/materialization change
  - no canonical semantic change
  - no blocked-row-rule change
  - no predictor-contract redesign

## 2. fresh Python 3.11 gate environment used

- Task14E used a fresh isolated Python 3.11 environment at:
  - `/private/tmp/task14e_gate_env`
- Environment seed source:
  - repo-local `./.conda311/bin/python`
- Dependencies were installed from repo-pinned `requirements.txt`.
- Task14E helper added for repeatable artifact benchmarking:
  - `scripts/run_task14e_loadability_probe.py`

## 3. frozen artifact verification

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

## 4. exact Task14E loadability benchmark result

- Fresh structured probe command:
  - `'/private/tmp/task14e_gate_env/bin/python' scripts/run_task14e_loadability_probe.py --repo-root /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform --local-root /private/tmp/task14e_probe_artifacts`
- Exact size and timing outcomes are recorded in:
  - `docs/technical/TASK14E_LOADABILITY_BENCHMARK_MATRIX.md`
- Key outcomes:
  - live model size = `19,392,395` bytes
  - staged candidate model size = `34,060,500` bytes
  - live model `pickle.load` from current live path = `1.0728650420005579` seconds
  - staged candidate `pickle.load` from current staged path = `0.7879939160011418` seconds
  - staged candidate `pickle.load` from fresh local copy = `0.8101852919990051` seconds
  - staged candidate `joblib.load` from current staged path = `0.6791852499991364` seconds
  - staged candidate `joblib.load` from fresh local copy = `0.6813109169997915` seconds
- Current-path versus local-copy timings for the staged candidate were effectively identical.
- The staged candidate is therefore operationally practical to load in the fresh Task14E env.

## 5. blocker-class classification required by Task14E

- Exact Task14E artifact-loadability blocker classification:
  - `mixed`
- Why `mixed` is the honest classification:
  - the Task14D3 claim that staged-candidate deserialization itself was the operative blocker did not reproduce in the fresh Task14E env
  - the same staged candidate now loads quickly from both the repo staged path and a fresh local `/private/tmp` copy
  - no repo/iCloud/offloaded-path delta was observed for the candidate
  - no serialization-format penalty was observed for the candidate because both `pickle.load` and `joblib.load` were fast
  - no intrinsic candidate loadability problem remains on the current fresh gate
- Task14E therefore closes the prior candidate-loadability blocker as resolved.

## 6. fresh revalidation attempt after closing loadability

- Task14E then attempted the required fresh frozen-protocol revalidation before any live swap.
- Read-only live-gate attempt using the current live DB path:
  - command:
    - `'/private/tmp/task14e_gate_env/bin/python' scripts/run_task14d3_gate_eval.py --repo-root /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform --verbose`
  - result:
    - progressed to `prepare_load_data_start`
    - failed at live DB open/read with `sqlite3.OperationalError: disk I/O error`
- Fresh working-copy attempt into `/private/tmp`:
  - command:
    - `'/private/tmp/task14e_gate_env/bin/python' scripts/run_task14d3_gate_eval.py --repo-root /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform --temp-db-path /private/tmp/task14e_gate_eval.db --verbose`
  - result:
    - `shutil.copy2(...)` failed with `TimeoutError: [Errno 60] Operation timed out`
    - source path:
      - `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db`
    - target path:
      - `/private/tmp/task14e_gate_eval.db`
  - follow-up validation of the target file showed:
    - `size=0 bytes`
    - `blocks=14115040`
    - `sqlite3 /private/tmp/task14e_gate_eval.db 'select count(*) from fact_machine_hour;'`
      - `Error: in prepare, no such table: fact_machine_hour`
- Additional direct live-file probes also stalled and had to be interrupted:
  - `sqlite3 'file:/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db?mode=ro' '.tables'`
  - `od -An -tx1 -N16 /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db`

## 7. activation decision

- Promotion decision: **not attempted**
- Reason:
  - the staged Task14C candidate is now confirmed loadable and practical
  - but Task14E still could not complete the required fresh frozen-protocol active-vs-candidate rerun because the live DB itself is currently unreadable in a reliable way and fresh local-copy creation timed out
  - without a fresh honest revalidation on the accepted Jan-Feb 2026 slice, activation would not meet the Task14E gate

## 8. live DB and artifact safety state

- Shared repo DB remained untouched by Task14E:
  - no write-capable SQL path was executed
  - no ETL/materialization path was executed
  - repo DB stat remained:
    - `mtime = 1776434362`
    - `size = 7226900480`
- Live artifacts remained untouched:
  - no fresh Task14E backup set was created
  - no live model/preprocessor overwrite was attempted
  - no rollback was needed because no live swap was attempted

## 9. Task14E pass / non-pass conclusion

- Task14E did **not** pass.
- What Task14E did close:
  - the prior staged-candidate loadability blocker is no longer valid
- What still blocks closure:
  - live DB read access now fails independently of the candidate artifact
  - fresh working-DB creation from the live DB times out before a usable SQLite copy is produced

## 10. next required continuation boundary

- Next step class:
  - restore reliable read access to `manufacturing_data.db` or provide a healthy fresh working copy of the same DB
- Only after that should the next activation attempt do this exact sequence:
  1. rerun the frozen Task14 gate comparison on the healthy DB source
  2. verify that staged candidate still beats the active Task 4L bundle on the Jan-Feb 2026 holdout
  3. create a fresh Task14E backup set
  4. promote the candidate
  5. run direct predictor and routed ML/Optimization smokes on post-June months
