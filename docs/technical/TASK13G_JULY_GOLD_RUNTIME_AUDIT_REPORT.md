# Task13G July Gold Runtime Audit Report

## 1. accepted baseline used

- Shared promoted baseline remained `manufacturing_data.db` with SHA1 `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`.
- Temp audit DB reused the existing Task13R probe database `/tmp/task13r_v3_temp.db` with SHA1 `52a5545895b28928db6fd7bf9306cca7493e9ced`.
- The accepted July 2025 real-data scope remained the already-landed Task13R Bronze+Silver slice:
  - `raw_energy_hourly = 99695`
  - `raw_csi_event = 24967`
  - `raw_mes_report = 23151`
  - `raw_maintenance_txn = 593`
  - `energy_meter_hour = 99695`
  - `csi_job_event = 24967`
  - `mes_report_event = 23151`
  - `maintenance_txn_event = 593`
  - `fact_machine_hour = 0`

## 2. exact July blocker before changes

- Task13R had already proved that July 2025 real data could be extracted, mapped, and landed through Bronze+Silver on a temp DB.
- The remaining Gold blocker before Task13G was still an opaque multi-minute July Gold run with no clean stage boundary and no safe basis for shared-DB promotion.
- Task13G was scoped to close July Gold on temp DB if possible, or else isolate the exact failing runtime stage without ambiguity.

## 3. debug ladder / instrumentation design added

- Added a six-stage July Gold debug ladder to `CanonicalMaterializer.materialize_gold_month_debug(...)`:
  1. `energy_backbone_only`
  2. `energy_backbone_plus_csi_state_overlay`
  3. `energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay`
  4. `energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay_plus_mes_overlay`
  5. `energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay_plus_mes_overlay_plus_maintenance_overlay`
  6. `final_replace_commit_index_phase`
- Added per-stage `stage_start` / `stage_result` JSONL emission so a stalled stage becomes visible immediately instead of only at month end.
- Added optional hard per-stage timeout support so a non-returning stage resolves to a concrete timeout record.
- Moved Gold-only Task13G runs onto a light startup path by delaying ETL imports in `scripts/run_task13r_temp_sweep.py` until they are actually needed.

## 4. exact per-stage July timings and row counts

Task13G audit command used:

```bash
./.conda311/bin/python scripts/run_task13r_temp_sweep.py \
  --shared-db /tmp/task13r_v3_temp.db \
  --temp-db /tmp/task13r_v3_temp.db \
  --checkpoint-log /tmp/task13g_july_gold_audit_direct2.jsonl \
  --gold-only \
  --debug-gold-stages \
  --gold-stage-timeout-seconds 20 \
  --gold-debug-log /tmp/task13g_july_gold_audit_direct2.stages.jsonl \
  "July 2025"
```

Stage-ladder outcome on the real July temp DB:

| Stage | Status | Duration | Rows loaded/read | Rows output / write | Notes |
| --- | --- | ---: | --- | --- | --- |
| `energy_backbone_only` | success | `1.367s` | `energy_meter_hour = 99695` | `64727` Gold backbone rows, `87` machines, `744` hours | zero CSI/MES/quantity/maintenance fields as expected |
| `energy_backbone_plus_csi_state_overlay` | timeout | `20.003s` | month scope remained `csi_job_event = 24967` | no July Gold commit | first non-success stage; month still had `fact_machine_hour = 0` for `2025-07` |

Supplementary hot-function probe after the ladder run:

```json
{
  "base_rows": 64727,
  "base_seconds": 0.874,
  "csi_job_event_rows": 24967,
  "csi_machine_group_count": 96,
  "csi_group_seconds": 0.371,
  "csi_overlay_status": "TimeoutError",
  "csi_overlay_seconds": 20.001,
  "csi_overlay_error": "overlay_gold_rows_with_csi_timeout"
}
```

This isolates the real July blocker to the CSI state overlay path itself, specifically `CanonicalMaterializer._overlay_gold_rows_with_csi(...)`, not to Bronze/Silver reads, not to base-row construction, and not to CSI event grouping.

## 5. runtime fixes applied and why

- Replaced per-row Gold backbone hour parsing with a unique-hour lookup so July backbone parsing no longer burns runtime on repeated scalar `pd.to_datetime(...)` calls.
- Added vectorized CSI timestamp preparation plus `pd.Timestamp` short-circuit handling in `GoldFactBuilder` so CSI event preparation no longer spends the stage budget reparsing already-normalized timestamps.
- Moved CSI team-size lookup out of the CSI stage and into the MES stage, because it is only consumed by MES overlay and should not pollute the CSI runtime audit boundary.
- Added stage-start/result JSONL emission and hard timeout control so July Gold now resolves to an explicit stage record instead of an opaque long-running process.
- Delayed ETL imports for `--gold-only` runs so Task13G audits reach Gold logic immediately instead of paying unrelated ETL startup cost.

## 6. July temp-DB result

- July 2025 Gold did not land on the temp DB in this run.
- The first stage now completes quickly and deterministically, proving the previous backbone bottleneck has been cut down materially.
- The remaining blocker is the CSI state overlay stage, which times out cleanly at `20.003s` in the formal stage ladder and at `20.001s` in the focused hot-function probe.
- No July `fact_machine_hour` rows were written; `/tmp/task13r_v3_temp.db` remained at SHA1 `52a5545895b28928db6fd7bf9306cca7493e9ced`.

## 7. canonical reader smoke result

- `CanonicalGoldReader('/tmp/task13r_v3_temp.db').get_available_months()` remained `June 2025` -> `January 2025`.
- `CanonicalMLReader('/tmp/task13r_v3_temp.db').get_available_months()` remained `June 2025` -> `January 2025`.
- `CanonicalOptimizationReader('/tmp/task13r_v3_temp.db').get_available_months()` remained `June 2025` -> `January 2025`.
- `CanonicalGoldReader('/tmp/task13r_v3_temp.db').read_month_page_dataframe('July 2025')` returned `0` rows.

## 8. shared DB / artifact safety

- Shared `manufacturing_data.db` was not modified during Task13G; SHA1 remained `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`.
- No shared-DB promotion was attempted.
- No artifact retraining or artifact promotion was attempted.
- The active artifact bundle remains the accepted Task 4L bundle: `artifact_version_id = 20260401_000808`, `selected_model = random_forest`.

## 9. remaining limitations

- July Gold still does not complete on real data.
- The formal ladder now isolates the blocker to the CSI state overlay stage, but the CSI overlay implementation itself still needs further runtime reduction before July can land.
- August 2025 -> February 2026 were intentionally not attempted in Task13G because the July blocker remains open.
- `CURRENT_REBUILD_STATUS.md` was intentionally left unchanged because July did not close cleanly on temp DB.

## 10. recommended next step after Task13G

- Focus only on the CSI overlay hot path, starting with `CanonicalMaterializer._overlay_gold_rows_with_csi(...)` and the machine-level loop inside `GoldFactBuilder._overlay_machine_rows_with_csi(...)`.
- Add one more narrow audit pass that times:
  - active-event window maintenance
  - per-hour overlap construction
  - per-hour dominant-event selection
- Only resume Task13R month sweep or consider any shared-DB promotion after July Gold lands cleanly on temp DB and the canonical readers expose `July 2025`.
