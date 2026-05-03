# Task14C Promotion Gate Report

## 1. accepted baseline used

- Accepted baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
  - `Task13I`
  - `Task14A`
  - `Task14B`
- Shared canonical DB remained the same read-only baseline throughout Task14C:
  - `manufacturing_data.db`
  - canonical month coverage = `January 2025` -> `February 2026`
  - `fact_machine_hour` rows observed during Task14C = `879,978`
- Task14C scope remained promotion-gate only:
  - no DB write
  - no canonical semantic change
  - no blocked-row-rule change
  - no predictor-contract redesign

## 2. frozen live artifact baseline at task start

- Live active bundle at task start was frozen exactly as:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
  - `train_months = January 2025 -> April 2025`
  - `eval_months = May 2025 -> June 2025`
- Full SHA-256 checksums at task start:
  - live model `models/production_efficiency_model.pkl`
    - `1e72e3d80b54da1e122e729f657e3049b771ca9a21a44dcf620f6c905dee4f25`
  - live preprocessor `models/production_preprocessor.pkl`
    - `f930ac1e9bc65be797532a99c7a51cdf00097c9e8d8eb016e0ba1f6720d4d3b1`
  - live model provenance `models/production_efficiency_model.provenance.json`
    - `afbac9e1fe4838911e1cb2e21fdc51bb0345f4c05fea526af60b385eec437049`
  - live preprocessor provenance `models/production_preprocessor.provenance.json`
    - `dc740043ee931eca1893e30429df149b13c944a4e238a359468d26549f51842c`

## 3. durable candidate acquisition / recreation decision

- Task14B temp candidate was still present and internally consistent with the accepted Task14B report contract, so recreation was not required.
- Task14B source payload still showed the frozen protocol:
  - candidate state = temp-only
  - train months = `January 2025` -> `December 2025`
  - eval months = `January 2026` -> `February 2026`
  - active holdout rows considered = `50,675`
  - candidate holdout rows considered = `50,675`
  - candidate smoke = passed with `source == model`
- Durable Task14C staging path created:
  - `models/task14c_artifacts/staged_candidate_20260418_070130/production_efficiency_model.candidate.task14c.pkl`
  - `models/task14c_artifacts/staged_candidate_20260418_070130/production_preprocessor.candidate.task14c.pkl`
  - `models/task14c_artifacts/staged_candidate_20260418_070130/task14b_eval_summary.source.json`
- Durable staged candidate SHA-256 checksums:
  - model
    - `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e`
  - preprocessor
    - `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27`
  - Task14B source summary copy
    - `40c501bdfe702fd907894885ff7f40b0e3bbd152aa0b8ec84d6fff13518aec44`

## 4. revalidated active vs candidate comparison

- Task14C gate evidence confirmed that the live bundle, temp candidate, and canonical DB input remained on the same accepted Task14B comparison basis:
  - live provenance still matched `Task 4L`
  - staged candidate bytes matched the accepted Task14B candidate source
  - canonical DB still reported `879,978` `fact_machine_hour` rows
  - accepted Task14B holdout payload still bound both bundles to the same `January 2026` -> `February 2026` evaluation slice
- Accepted comparison metrics carried forward unchanged for this still-identical artifact/input triad:

| Metric | Active Task 4L | Task14B Candidate |
| --- | ---: | ---: |
| Holdout months | `January 2026` -> `February 2026` | `January 2026` -> `February 2026` |
| Rows considered | `50,675` | `50,675` |
| Rows evaluated | `50,675` | `50,675` |
| Non-model-source rows | `0` | `0` |
| Distinct machines retained | `77` | `77` |
| R² | `0.7605741131053376` | `0.812714004142606` |
| MAE | `0.01499678606743838` | `0.012804444950338988` |
| RMSE | `0.1523568146386601` | `0.13475006522302904` |

- Governance reading of that unchanged comparison remained:
  - the candidate still beat the active bundle on all three holdout metrics
  - the comparison remained fair on the same frozen Jan-Feb 2026 slice
- Fresh in-turn sklearn-backed rerun could not be completed in the available execution environment:
  - repo `.conda311/bin/python` was not reliably executable through the tool runtime
  - fallback Python `3.11` at `/tmp/task13i_py311_net/bin/python` could not load the required sklearn stack from `.conda311` because `libomp.dylib` was unavailable for that path

## 5. durable backup / rollback setup

- Durable pre-promotion backup path created:
  - `models/task14c_artifacts/live_backup_20260418_070130/`
- Backed up files:
  - `production_efficiency_model.pkl`
  - `production_preprocessor.pkl`
  - `production_efficiency_model.provenance.json`
  - `production_preprocessor.provenance.json`
- Backup SHA-256 checksums:
  - model
    - `1e72e3d80b54da1e122e729f657e3049b771ca9a21a44dcf620f6c905dee4f25`
  - preprocessor
    - `f930ac1e9bc65be797532a99c7a51cdf00097c9e8d8eb016e0ba1f6720d4d3b1`
  - model provenance
    - `afbac9e1fe4838911e1cb2e21fdc51bb0345f4c05fea526af60b385eec437049`
  - preprocessor provenance
    - `dc740043ee931eca1893e30429df149b13c944a4e238a359468d26549f51842c`
- Compact rollback manifest is recorded in:
  - `docs/technical/TASK14C_ARTIFACT_BACKUP_MANIFEST.md`

## 6. promotion decision and exact reason

- Promotion decision: **not promoted**
- Exact reason:
  - the candidate remained promotion-worthy on the accepted frozen holdout evidence
  - durable candidate staging was completed
  - durable rollback backup was completed
  - no predictor-contract change was required
  - no DB write was needed
  - but Task14C could not complete the required fresh sklearn-backed promotion revalidation plus post-promotion runtime smoke on the actual live Python 3.11 stack in the current execution environment
  - because the safe promotion gate could not be fully re-executed end to end, the live Task 4L bundle was intentionally left untouched

## 7. post-promotion or non-promotion validation result

- Non-promotion validation closed cleanly:
  - live Task 4L provenance remained unchanged after Task14C
  - durable candidate staging exists
  - durable rollback backup exists
  - shared DB remained untouched
- Explicit no-write confirmation:
  - no `manufacturing_data.db` write was performed
  - no live artifact overwrite was performed
  - no rollback was needed because no live swap was attempted

## 8. final live artifact state

- Final live state remained:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
  - `train_months = January 2025 -> April 2025`
  - `eval_months = May 2025 -> June 2025`
- Final live file fingerprints remained identical to the frozen baseline at task start.

## 9. remaining limitations

- The candidate was not activated live in Task14C.
- The gate outcome depended on durable evidence and accepted Task14B replay equivalence rather than a fresh in-turn sklearn-backed rerun.
- The missing promotion step is now an execution-environment validation gap, not a candidate-quality gap.
- Blocked-row coverage still remains unchanged:
  - `missing_positive_good_qty` remains the dominant blocker
  - Task14C did not broaden readiness or change blocked-row semantics

## 10. recommended next step after Task14C

- Keep any follow-up separate from Task14C.
- The next honest task is one narrow live-activation execution task in an environment where the real Python 3.11 ML stack can complete:
  - fresh holdout rerun
  - live swap
  - canonical predictor smoke
  - routed ML smoke
  - routed Optimization smoke
  - narrow experimental scheduling smoke if desired
- No blocked-row/readiness-expansion work should be mixed into that later live-activation task.
