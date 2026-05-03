# Task13I Aug 2025 to Feb 2026 Sweep And Promotion Report

## 1. accepted baseline used

- Accepted runtime baseline:
  - `Task11`
  - `Task12A`
  - `Task12B`
- Accepted shared-DB baseline at task start:
  - `manufacturing_data.db`
  - SHA1 before Task13I = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - canonical Gold month coverage before Task13I = `January 2025` -> `June 2025`
- Active artifacts stayed unchanged throughout Task13I:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. starting point inherited from Task13H

- Reused Task13H July-closed temp DB:
  - `/tmp/task13r_v3_temp.db`
  - SHA1 inherited into Task13I sweep base = `93682cf0de72b74defb834b88a1888630f8e3ab7`
- Inherited July 2025 landed month state on that temp DB before resuming:
  - `raw_energy_hourly = 99695`
  - `raw_csi_event = 24967`
  - `raw_mes_report = 23151`
  - `raw_maintenance_txn = 593`
  - `energy_meter_hour = 99695`
  - `csi_job_event = 24967`
  - `mes_report_event = 23151`
  - `maintenance_txn_event = 593`
  - `fact_machine_hour = 64727`
- Inherited July reader state on the temp DB:
  - `CanonicalGoldReader`, `CanonicalMLReader`, and `CanonicalOptimizationReader` already exposed `July 2025`

## 3. exact sweep base chosen and why

- Sweep base chosen:
  - existing landed Task13H temp DB `/tmp/task13r_v3_temp.db`
- Why this base was accepted:
  - it already matched the accepted July Task13H fingerprint and month counts
  - it was already derived from the accepted frozen shared baseline through the earlier Task13R/Task13H temp-only chain
  - it avoided reopening July source onboarding or rerunning July Gold unnecessarily
- Execution environment used for Task13I:
  - a clean `/tmp/task13i_py311_net` Python 3.11 env was created because the repo-local `.conda311` runtime tree was cloud-offloaded and non-executable in this workspace
  - the CLI sweep runner used no-op `streamlit` / `plotly` import stubs only to satisfy ETL module imports; no routed UI logic or app code was changed

## 4. month-by-month results from August 2025 to February 2026

| Month | Bronze rows after run | Silver rows after run | `fact_machine_hour` rows | Gold stage timings | Result |
| --- | --- | --- | ---: | --- | --- |
| August 2025 | `raw_energy_hourly 99695` / `raw_csi_event 22634` / `raw_mes_report 20884` / `raw_maintenance_txn 582` | `energy_meter_hour 99685` / `csi_job_event 22634` / `mes_report_event 20884` / `maintenance_txn_event 582` | `64727` | backbone `1.066s`, CSI `1.349s`, CSI qty `3.755s`, MES `17.946s`, maintenance `3.922s`, commit `2.347s` | landed cleanly with accepted August flag policy |
| September 2025 | `raw_energy_hourly 96480` / `raw_csi_event 20267` / `raw_mes_report 18740` / `raw_maintenance_txn 651` | `energy_meter_hour 96480` / `csi_job_event 20267` / `mes_report_event 18740` / `maintenance_txn_event 651` | `62640` | backbone `1.082s`, CSI `1.281s`, CSI qty `3.671s`, MES `16.307s`, maintenance `3.917s`, commit `2.448s` | landed cleanly |
| October 2025 | `raw_energy_hourly 98534` / `raw_csi_event 19169` / `raw_mes_report 17794` / `raw_maintenance_txn 983` | `energy_meter_hour 98534` / `csi_job_event 19169` / `mes_report_event 17794` / `maintenance_txn_event 983` | `64247` | backbone `1.064s`, CSI `1.319s`, CSI qty `2.437s`, MES `15.319s`, maintenance `3.955s`, commit `2.363s` | landed cleanly with accepted localized partial-energy flag |
| November 2025 | `raw_energy_hourly 93777` / `raw_csi_event 22796` / `raw_mes_report 21308` / `raw_maintenance_txn 681` | `energy_meter_hour 93777` / `csi_job_event 22796` / `mes_report_event 21308` / `maintenance_txn_event 681` | `61199` | backbone `1.031s`, CSI `1.327s`, CSI qty `2.773s`, MES `18.418s`, maintenance `4.033s`, commit `2.354s` | landed cleanly with accepted localized partial-energy flag |
| December 2025 | `raw_energy_hourly 96720` / `raw_csi_event 23182` / `raw_mes_report 21814` / `raw_maintenance_txn 734` | `energy_meter_hour 96720` / `csi_job_event 23182` / `mes_report_event 21814` / `maintenance_txn_event 734` | `63240` | backbone `1.151s`, CSI `1.385s`, CSI qty `4.800s`, MES `18.913s`, maintenance `3.962s`, commit `2.552s` | landed cleanly |
| January 2026 | `raw_energy_hourly 96612` / `raw_csi_event 22963` / `raw_mes_report 21492` / `raw_maintenance_txn 0` | `energy_meter_hour 96612` / `csi_job_event 22963` / `mes_report_event 21492` / `maintenance_txn_event 0` | `63054` | backbone `1.072s`, CSI `1.468s`, CSI qty `5.095s`, MES `18.655s`, maintenance `3.981s`, commit `2.563s` | landed cleanly with accepted localized partial-energy flag |
| February 2026 | `raw_energy_hourly 89343` / `raw_csi_event 12786` / `raw_mes_report 11885` / `raw_maintenance_txn 0` | `energy_meter_hour 89343` / `csi_job_event 12786` / `mes_report_event 11885` / `maintenance_txn_event 0` | `57792` | backbone `1.022s`, CSI `0.896s`, CSI qty `4.631s`, MES `10.344s`, maintenance `3.865s`, commit `2.546s` | landed cleanly with accepted partial/quarantine policy |

## 5. accepted flags and quarantines encountered

- August 2025:
  - accepted sentinel anomaly exclusion remained active
  - Bronze energy rows `99695` became Silver energy rows `99685`, which matches the expected `10` excluded anomaly rows
- October 2025:
  - localized partial-energy flag remained active on `1814` Silver rows
- November 2025:
  - localized partial-energy flag remained active on `178` Silver rows
- January 2026:
  - localized partial-energy flag remained active on `637` Silver rows
- February 2026:
  - localized partial-energy flag remained active on `639` Silver rows
  - raw Bronze null-canonical counts were not used as the final quarantine truth because they overstate unresolved mapping before Silver re-resolution
  - effective canonical unresolved scope after Silver normalization was only:
    - `12` CSI Silver rows
    - `12` MES Silver rows
    - all `24` of those unresolved Silver rows were the accepted `1262-00012` quarantine
  - `024-075` and `024-080` were confirmed landed and joinable in Silver:
    - CSI Silver rows for `024-075 = 65`
    - CSI Silver rows for `024-080 = 53`
    - MES Silver rows for `024-075 = 65`
    - MES Silver rows for `024-080 = 52`

## 6. whether any new runtime blocker appeared

- No new runtime blocker appeared.
- Every month from `August 2025` through `February 2026` completed successfully on the temp DB.
- The slowest landed Gold sub-stage remained MES overlay, but it stayed within a practical landed window on every resumed month:
  - August `17.946s`
  - September `16.307s`
  - October `15.319s`
  - November `18.418s`
  - December `18.913s`
  - January `18.655s`
  - February `10.344s`
- Because no month failed, no extra MES hot-path refactor or new blocker-isolation patch was required in Task13I.

## 7. final temp-DB month coverage

- Final temp DB used for the completed sweep:
  - `/tmp/task13r_v3_temp.db`
  - SHA1 after full Aug 2025 -> Feb 2026 sweep = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
- Final temp-DB canonical month coverage:
  - `January 2025 64725`
  - `February 2025 58461`
  - `March 2025 64725`
  - `April 2025 62637`
  - `May 2025 65165`
  - `June 2025 62639`
  - `July 2025 64727`
  - `August 2025 64727`
  - `September 2025 62640`
  - `October 2025 64247`
  - `November 2025 61199`
  - `December 2025 63240`
  - `January 2026 63054`
  - `February 2026 57792`

## 8. shared DB promotion decision

- Promotion decision: **promote**
- Why promotion was justified:
  - shared DB fingerprint at task start matched the accepted frozen baseline `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - the sweep reused the accepted Task13H temp baseline that had already been derived from that frozen shared baseline
  - all months from `July 2025` through `February 2026` landed cleanly on the temp DB
  - temp-DB reader smoke matched the landed month set on Gold / ML / Optimization readers
  - accepted flags and the February `1262-00012` quarantine were documented honestly
- Backup taken before replacement:
  - `/tmp/task13i_shared_db_backup_pre_promotion_20260417.db`
  - backup SHA1 = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- Shared DB replacement:
  - source temp DB = `/tmp/task13r_v3_temp.db`
  - promoted shared DB = `manufacturing_data.db`
- Shared DB fingerprints:
  - before promotion = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - after promotion = `40a3300e3915fd7e9928e8ef18c2f0a423e08943`
  - promoted shared fingerprint now matches the final temp DB exactly

## 9. validation / smoke summary

- Syntax validation passed:
  - `PYTHONPYCACHEPREFIX=/tmp/task13i_pycache /tmp/task13i_py311_net/bin/python -m py_compile core/runtime_paths.py core/silver_normalizer.py core/canonical_materializer.py core/gold_fact_builder.py core/canonical_gold_reader.py core/canonical_ml_reader.py core/canonical_optimization_reader.py modules/etl_module.py scripts/run_task13r_temp_sweep.py tests/test_canonical_materializer.py tests/test_silver_normalizer.py tests/test_task13_source_discovery.py tests/test_etl_extractor.py`
- Focused test validation passed:
  - `tests.test_task13_source_discovery`
  - `tests.test_etl_extractor`
  - `tests.test_silver_normalizer`
  - `tests.test_canonical_materializer`
  - total = `36` tests passed
- Temp-DB reader smoke passed:
  - `CanonicalGoldReader('/tmp/task13r_v3_temp.db').get_available_months()` = `January 2025` -> `February 2026`
  - `CanonicalMLReader('/tmp/task13r_v3_temp.db').get_available_months()` = `January 2025` -> `February 2026`
  - `CanonicalOptimizationReader('/tmp/task13r_v3_temp.db').get_available_months()` = `January 2025` -> `February 2026`
- Post-promotion shared-DB reader smoke passed:
  - `CanonicalGoldReader('manufacturing_data.db').get_available_months()` = `January 2025` -> `February 2026`
  - `CanonicalMLReader('manufacturing_data.db').get_available_months()` = `January 2025` -> `February 2026`
  - `CanonicalOptimizationReader('manufacturing_data.db').get_available_months()` = `January 2025` -> `February 2026`
- Active artifact confirmation after promotion:
  - `models/production_efficiency_model.provenance.json` still reports `Task 4L`, `artifact_version_id 20260401_000808`, `selected_model random_forest`
  - `models/production_preprocessor.provenance.json` still reports `Task 4L`, `artifact_version_id 20260401_000808`, `selected_model random_forest`

## 10. remaining limitations

- Task13I closes the accepted Jul 2025 -> Feb 2026 shared-DB extension scope only.
- March 2026 remains explicitly out of scope even though grouped energy files and adjacent MES timestamps extend beyond February.
- February 2026 remains accepted with flags, not “perfectly complete”:
  - localized partial-energy flags remain active
  - `1262-00012` remains quarantined
- The shared DB is now promoted, but no retraining, artifact refresh, or solver-scope expansion was attempted in Task13I.
- The raw Bronze February null-canonical counts are not a reliable final quarantine metric for this extension window; later audits should use Silver/Gold unresolved diagnostics.

## 11. recommended next step after Task13I

- No further Jul 2025 -> Feb 2026 sweep or shared-DB promotion work is needed for this scope.
- If a follow-up is desired, keep it separate from Task13I:
  - the next honest candidate is a read-only post-landing ML/artifact audit on the expanded Jul 2025 -> Feb 2026 canonical base
  - active Task 4L artifacts should remain unchanged unless a separate later task explicitly approves retraining/promotion
