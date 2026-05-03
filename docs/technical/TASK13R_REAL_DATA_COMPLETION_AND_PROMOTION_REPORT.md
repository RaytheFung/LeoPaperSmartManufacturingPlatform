# Task13R Real-Data Completion And Promotion Report

## 1. accepted baseline used

- Accepted runtime baseline:
  - `Task11`
  - `Task12A`
  - `Task12B`
- Shared DB baseline verified before this run:
  - `manufacturing_data.db` SHA1 = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - canonical Gold months available = `January 2025` -> `June 2025`
- Active artifacts remained unchanged throughout Task13R work:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. what actually blocked Task13

- The original Task13 blocker was confirmed on a dedicated July 2025 temp replay against a copy of the accepted shared DB baseline.
- Runtime was **not** being spent in month discovery or mapping:
  - July extraction completed in about `45-52s`
  - July mapping completed in about `0.5-0.6s`
  - July Bronze save completed in about `25-31s`
- The first confirmed blocker was July Silver normalization on real data:
  - original probe on `/tmp/task13r_materialize_probe.db` showed `energy` normalization at about `125.234s`
  - the same probe showed `csi` normalization at about `137.659s`
  - the same probe showed `mes` normalization at about `141.978s`
- After Task13R runtime hardening, Silver stopped being the primary blocker on the same July month slice:
  - `energy` normalization benchmark: about `21.736s`
  - `csi` normalization benchmark: about `0.447s`
  - `mes` normalization benchmark: about `0.270s`
- The remaining blocker is now the July Gold overlay/materialization path:
  - on `/tmp/task13r_v3_temp.db`, July Silver completed and persisted, but `fact_machine_hour` for `2025-07` remained `0` during the Task13R probe window
  - because July Gold still did not close cleanly, the full Jul 2025 -> Feb 2026 temp sweep could not be completed honestly in this run

## 3. exact runtime/checkpoint strategy used

- Shared DB safety:
  - all real-data Task13R execution used temp DB copies only
  - shared `manufacturing_data.db` was kept read-only for verification and fingerprinting
- Temp DB probe paths used:
  - `/tmp/task13r_temp.db`
  - `/tmp/task13r_materialize_probe.db`
  - `/tmp/task13r_v2_temp.db`
  - `/tmp/task13r_v3_temp.db`
- Added narrow runtime hardening only where the July replay proved it necessary:
  - `core/silver_normalizer.py`
    - fast-path real-data energy normalization for month-scoped Bronze frames
    - fast-path CSI/MES normalization when the materializer supplies month-scoped extracted Bronze columns
  - `core/canonical_materializer.py`
    - month-scoped Bronze SELECTs now pull only the columns needed for Silver normalization
    - Gold now scopes CSI/MES overlays to the target month instead of reading all months
    - Gold now narrows cross-month quantity support reads to only the target month’s CSI source hashes
    - Gold temp rows now cache parsed hour timestamps in-memory so the same `hour_ts` string is not reparsed repeatedly during CSI/MES/maintenance overlay
  - `core/gold_fact_builder.py`
    - maintenance overlay now reuses computed maintenance-window stats instead of recomputing 7-day/30-day slices twice per machine-hour
  - `scripts/run_task13r_temp_sweep.py`
    - added a dedicated temp-DB sweep runner with JSONL checkpoints, month-level resumability, and per-stage timing/count logging
- Checkpoint target:
  - `--checkpoint-log /tmp/task13r_checkpoint*.jsonl`
- Promotion rule used in this run:
  - do not touch shared DB unless the full temp sweep closes cleanly

## 4. exact month-by-month temp-DB results

| Month | Temp DB state reached | Bronze rows after run | Silver rows after run | `fact_machine_hour` rows after run | Quarantines in month | Quality flags in month | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| July 2025 | Bronze + Silver completed on temp DB | `raw_energy_hourly 99,695` / `raw_csi_event 24,967` / `raw_mes_report 23,151` / `raw_maintenance_txn 593` | `energy_meter_hour 99,695` / `csi_job_event 24,967` / `mes_report_event 23,151` / `maintenance_txn_event 593` | `0` | none | `quality_status = ok` on all `99,695` July energy Silver rows | blocked at Gold |
| August 2025 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |
| September 2025 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |
| October 2025 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |
| November 2025 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |
| December 2025 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |
| January 2026 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |
| February 2026 | not started | none | none | none | none captured in Task13R run | none captured in Task13R run | not attempted because July Gold blocker remained open |

## 5. unresolved identifiers / quarantines

- July 2025 temp replay:
  - `raw_csi_event` unresolved identifiers in the persisted July Bronze month slice: none
  - `raw_mes_report` unresolved identifiers in the persisted July Bronze month slice: none
- Accepted unresolved identifier still relevant to the broader Task13 extension window:
  - `1262-00012` remains unresolved and quarantined safely for the later February 2026 source family
- Because the Task13R sweep did not move past the July Gold blocker, no new Aug 2025 -> Feb 2026 quarantine capture was completed in this run

## 6. shared DB promotion decision

- Promotion decision: **do not promote**
- Reason:
  - July 2025 Gold did not finish cleanly on the temp DB
  - the full Jul 2025 -> Feb 2026 temp sweep was therefore not completed
  - routed canonical readers on the temp DB still could not see post-June canonical months because July `fact_machine_hour` rows were not landed
- Shared DB after this run:
  - untouched
  - SHA1 remained `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - canonical Gold months remained `January 2025` -> `June 2025`

## 7. validation / smoke summary

- Syntax validation:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/silver_normalizer.py core/canonical_materializer.py core/gold_fact_builder.py scripts/run_task13r_temp_sweep.py` passed
- Focused test validation:
  - `tests.test_task13_source_discovery` passed
  - `tests.test_etl_extractor` passed
  - total passed in that focused subset: `7` tests
- Additional test note:
  - `tests.test_machine_alias_registry` is currently failing in this worktree because the registry loader is returning zero loaded records in that suite; that issue was not reopened in Task13R, and it is separate from the real-data July runtime blocker documented here
- Real-data temp-DB validation completed:
  - shared DB baseline fingerprint verified
  - July extraction/mapping/Bronze write verified on temp DB
  - July Silver completion verified on temp DB with the counts listed above
  - July Gold remained blocked with `fact_machine_hour` July rows still `0`
- Temp DB fingerprint captured after the July Bronze+Silver Task13R probe state:
  - `/tmp/task13r_v3_temp.db` SHA1 = `52a5545895b28928db6fd7bf9306cca7493e9ced`

## 8. remaining limitations

- Task13R is **not passed** in this run.
- The full Jul 2025 -> Feb 2026 real-data temp sweep was not completed.
- The remaining blocker is still the July Gold overlay/materialization path on real data.
- No shared-DB promotion was applied.
- No routed-reader smoke could honestly show post-June canonical months because July Gold did not land.
- `CURRENT_REBUILD_STATUS.md` was intentionally left unchanged.
- Active artifacts remain Task 4L only; no retraining or artifact promotion occurred.

## 9. recommended next step after Task13R

- Continue from the July Gold blocker rather than forcing a partial promotion.
- Use `scripts/run_task13r_temp_sweep.py` against a pre-copied temp DB and checkpoint log once the July Gold path is brought into a practical runtime window.
- The next technical target should be a narrower Gold-phase runtime audit on:
  - CSI/MES/maintenance overlay across the July machine-hour rows
  - quantity allocation on the July row set
  - maintenance-context derivation on the July row set
- Only after July Gold closes cleanly should the temp sweep resume for:
  - `August 2025`
  - `September 2025`
  - `October 2025`
  - `November 2025`
  - `December 2025`
  - `January 2026`
  - `February 2026`
- Shared DB promotion should still remain blocked until the full temp sweep completes and routed canonical readers can see the extended month set cleanly.
