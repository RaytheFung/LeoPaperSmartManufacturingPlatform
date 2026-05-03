# Task14C Artifact Backup Manifest

## 1. durable candidate staging

- staging root:
  - `models/task14c_artifacts/staged_candidate_20260418_070130/`
- staged files:
  - `production_efficiency_model.candidate.task14c.pkl`
    - SHA-256 `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - `production_preprocessor.candidate.task14c.pkl`
    - SHA-256 `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - `task14b_eval_summary.source.json`
    - SHA-256 `40c501bdfe702fd907894885ff7f40b0e3bbd152aa0b8ec84d6fff13518aec44`

## 2. live backup set

- backup root:
  - `models/task14c_artifacts/live_backup_20260418_070130/`
- backup files:
  - `production_efficiency_model.pkl`
    - SHA-256 `1e72e3d80b54da1e122e729f657e3049b771ca9a21a44dcf620f6c905dee4f25`
  - `production_preprocessor.pkl`
    - SHA-256 `f930ac1e9bc65be797532a99c7a51cdf00097c9e8d8eb016e0ba1f6720d4d3b1`
  - `production_efficiency_model.provenance.json`
    - SHA-256 `afbac9e1fe4838911e1cb2e21fdc51bb0345f4c05fea526af60b385eec437049`
  - `production_preprocessor.provenance.json`
    - SHA-256 `dc740043ee931eca1893e30429df149b13c944a4e238a359468d26549f51842c`

## 3. compact rollback procedure

- If a later live activation is attempted and fails:
  - copy `models/task14c_artifacts/live_backup_20260418_070130/production_efficiency_model.pkl` back to `models/production_efficiency_model.pkl`
  - copy `models/task14c_artifacts/live_backup_20260418_070130/production_preprocessor.pkl` back to `models/production_preprocessor.pkl`
  - copy `models/task14c_artifacts/live_backup_20260418_070130/production_efficiency_model.provenance.json` back to `models/production_efficiency_model.provenance.json`
  - copy `models/task14c_artifacts/live_backup_20260418_070130/production_preprocessor.provenance.json` back to `models/production_preprocessor.provenance.json`

## 4. task14c gate outcome

- Live activation was not performed in Task14C.
- This manifest therefore records durable rollback readiness only; no rollback execution was needed.
