# Task14F Working DB Mirror And Activation Report

## 1. accepted baseline used

- Accepted baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
  - `Task14A`
  - `Task14B`
  - `Task14C`
  - `Task14E`
- Shared canonical DB contents remained unchanged throughout Task14F.
- Live artifacts at task start remained the unchanged Task 4L bundle:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. working-mirror discovery and recovery result

- No healthy prior working DB mirror remained available in `/tmp` or `/private/tmp`.
- The only pre-existing temp DB candidate found was unusable:
  - `/private/tmp/task14e_gate_eval.db`
  - `size=0`
  - no `fact_machine_hour` table
- Task14F therefore recovered a fresh working mirror by APFS clone:
  - command:
    - `cp -c manufacturing_data.db /private/tmp/task14f_working_mirror.db`
- That recovered mirror was then cloned into a more durable local path outside the repo tree:
  - command:
    - `cp -c /private/tmp/task14f_working_mirror.db /Users/rayfung/.codex/memories/task14f_working_mirror_20260419.db`

## 3. exact mirror verification result

- Recovered mirror path used for frozen-gate rerun:
  - `/private/tmp/task14f_working_mirror.db`
- Durable mirror path used for post-activation smokes:
  - `/Users/rayfung/.codex/memories/task14f_working_mirror_20260419.db`
- Verified mirror snapshot:
  - `fact_machine_hour` rows = `879,978`
  - month coverage = `2025-01` -> `2026-02`
  - mirror size = `7,226,900,480` bytes
- DB SHA1 equality across all three paths:
  - repo DB `manufacturing_data.db`
    - `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - recovered temp mirror `/private/tmp/task14f_working_mirror.db`
    - `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - durable mirror `/Users/rayfung/.codex/memories/task14f_working_mirror_20260419.db`
    - `40a3300e3915fd7e9928e8ef18c2f0a423e08943`

## 4. fresh frozen-protocol revalidation on the mirror

- Exact command:
  - `'/private/tmp/task14e_gate_env/bin/python' scripts/run_task14d3_gate_eval.py --repo-root /Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform --working-db-path /private/tmp/task14f_working_mirror.db --verbose`
- Mirror-backed frozen protocol reproduced exactly:
  - rows loaded = `879,978`
  - rows after filtering = `364,399`
  - train months = `January 2025` -> `December 2025`
  - eval months = `January 2026` -> `February 2026`
  - train rows = `313,724`
  - eval rows = `50,675`
- Active Task 4L holdout reproduced exactly:
  - `R² = 0.7605741131053376`
  - `MAE = 0.01499678606743838`
  - `RMSE = 0.1523568146386601`
  - non-model-source rows = `0`
- Staged Task14C candidate also reproduced exactly:
  - `R² = 0.812714004142606`
  - `MAE = 0.012804444950338991`
  - `RMSE = 0.13475006522302904`
  - non-model-source rows = `0`
- Mirror-backed candidate smoke passed:
  - `source == model`
  - sample month = `January 2026`
  - sample machine = `024-063`
  - sample hour = `2026-01-02T08:00:00`

## 5. activation decision

- Promotion decision: **promoted**
- Why promotion was now valid:
  - a verified healthy working DB mirror was available
  - fresh frozen-protocol revalidation completed successfully
  - the staged candidate still beat the active Task 4L bundle on all three holdout metrics
  - no predictor-contract change was required
  - a fresh durable rollback backup was created before the swap
  - no shared-DB write was required

## 6. fresh durable rollback backup and live swap

- Fresh Task14F backup root:
  - `models/task14f_artifacts/live_backup_20260419_181842/`
- Backed up files:
  - `production_efficiency_model.pkl`
  - `production_preprocessor.pkl`
  - `production_efficiency_model.provenance.json`
  - `production_preprocessor.provenance.json`
- Exact live swap performed:
  - copied `models/task14c_artifacts/staged_candidate_20260418_070130/production_efficiency_model.candidate.task14c.pkl` to `models/production_efficiency_model.pkl`
  - copied `models/task14c_artifacts/staged_candidate_20260418_070130/production_preprocessor.candidate.task14c.pkl` to `models/production_preprocessor.pkl`
  - updated both live provenance JSONs to the Task14F active state

## 7. post-activation smokes

- Exact read-only smoke command:
  - `'/private/tmp/task14e_gate_env/bin/python' scripts/run_task14f_db_mirror_probe.py --db-path /Users/rayfung/.codex/memories/task14f_working_mirror_20260419.db --month 'February 2026' --queue-size 3`
- Direct predictor smoke passed:
  - `source == model`
  - sample machine = `024-058`
  - sample hour = `2026-02-01T00:00:00`
  - predicted efficiency = `0.016713657957883175`
  - confidence = `0.7081282609418037`
- `🤖 Efficiency Prediction & Governance` smoke passed on `February 2026`:
  - canonical rows loaded = `57,792`
  - inferable rows = `18,762`
  - candidate rows = `76`
  - prediction rows = `76`
  - blocked prediction rows = `0`
- `🎯 Operational Decision Support` smoke passed on `February 2026`:
  - machine summary rows = `86`
  - preview available = `true`
  - schedule rows = `24`
  - team rows = `234`
  - top machine = `024-003`
- Narrow experimental scheduling smoke passed on `February 2026`:
  - queue rows = `3`
  - optimized schedule rows = `3`
  - naive schedule rows = `3`
  - blocked reasons rows = `1`
- These post-activation smokes were run against the verified durable mirror path.
- Task14F does **not** claim that the repo-local DB path itself was re-proven healthy.

## 8. final live artifact state

- Live bundle after Task14F:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
  - `train_months = January 2025 -> December 2025`
  - `eval_months = January 2026 -> February 2026`
- Final live file SHA-256:
  - model
    - `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - preprocessor
    - `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - model provenance
    - `d23648bb1fb24b9e830ba6586df5ed4faf02645522b085293e968f3a76774ff5`
  - preprocessor provenance
    - `66cbdb505ef3c577a0523efabf8881d6f6b104470fc17ff203f44f520d3a7611`

## 9. rollback result

- Rollback was **not** needed.
- The fresh Task14F backup remains available for later manual rollback if ever required.
- The older Task14C backup remains intact and was not overwritten.

## 10. shared DB / scope safety

- Shared repo DB contents remained untouched:
  - no write-capable SQL path was executed
  - no ETL/materialization path was executed
  - no canonical semantic change was made
  - no blocked-row-rule change was made
- Task14F only changed:
  - live artifact files
  - live provenance JSONs
  - report/script/ledger files
