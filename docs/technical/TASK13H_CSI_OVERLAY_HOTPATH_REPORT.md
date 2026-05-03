# Task13H CSI Overlay Hotpath Report

## 1. accepted baseline used

- Accepted live baseline remained:
  - `Task11`
  - `Task12A`
  - `Task12B`
- Shared DB remained frozen at the accepted Jan-Jun 2025 canonical baseline:
  - `manufacturing_data.db`
  - SHA1 before Task13H = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- Active artifacts remained the accepted Task 4L bundle only:
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
- July temp baseline used:
  - existing Task13R/Task13G temp DB `/tmp/task13r_v3_temp.db`
  - SHA1 before Task13H Gold closure = `52a5545895b28928db6fd7bf9306cca7493e9ced`

## 2. exact July baseline before changes

- Before Task13H logic changes, the same July temp DB already held:
  - `raw_energy_hourly = 99695`
  - `raw_csi_event = 24967`
  - `raw_mes_report = 23151`
  - `raw_maintenance_txn = 593`
  - `energy_meter_hour = 99695`
  - `csi_job_event = 24967`
  - `mes_report_event = 23151`
  - `maintenance_txn_event = 593`
  - `fact_machine_hour = 0`
- Task13G had already proven the July Gold blocker was inside the CSI overlay stage:
  - `energy_backbone_only = 1.367s`
  - `energy_backbone_plus_csi_state_overlay = timeout at 20.003s`
- Baseline reader state before Task13H:
  - `CanonicalGoldReader` exposed only `June 2025` -> `January 2025`
  - `July 2025` page rows = `0`

## 3. CSI overlay internal profiling design added

- Added internal CSI overlay profiling inside:
  - `CanonicalMaterializer._overlay_gold_rows_with_csi(...)`
  - `GoldFactBuilder._overlay_machine_rows_with_csi(...)`
- Added measured substeps for:
  1. per-machine preparation
  2. gold hour-row preparation / sorting
  3. CSI event window preparation / sorting
  4. active-event window maintenance
  5. overlap candidate construction per hour
  6. dominant-event selection / confidence routing
  7. row mutation / CSI field application
  8. source-flag merge work adjacent to overlay
- Added a month-scoped read-only profiler entrypoint:
  - `CanonicalMaterializer.profile_gold_csi_overlay_hot_path(...)`
- Added machine-level distribution output with:
  - `gold_row_count`
  - `csi_event_count`
  - `overlay_seconds`
  - `avg_candidate_overlap_count`
  - per-step seconds

## 4. machine-level runtime distribution

Profiled July result on `/tmp/task13r_v3_temp.db`:

- `total_machine_groups_processed = 87`
- `total_gold_rows_processed = 64727`
- `total_csi_events_processed = 24111`
- `total_overlay_seconds = 1.146`
- `average_candidate_overlap_count = 1.185305`
- `slowest_top_n_share_of_overlay_seconds = 0.20758`
- distribution shape = `globally_expensive_across_most_machines`

Top 10 slowest machine groups:

| Machine | Gold rows | CSI events | Overlay seconds | Avg candidate overlap count |
| --- | ---: | ---: | ---: | ---: |
| `024-107` | 744 | 270 | 0.095061 | 1.180180 |
| `024-071` | 744 | 344 | 0.017390 | 1.190031 |
| `024-065` | 744 | 296 | 0.016846 | 1.166951 |
| `024-058` | 744 | 282 | 0.015869 | 1.178797 |
| `024-059` | 744 | 279 | 0.015624 | 1.170695 |
| `024-081` | 744 | 331 | 0.015605 | 1.167939 |
| `024-099` | 744 | 248 | 0.015596 | 1.116904 |
| `024-063` | 744 | 313 | 0.015546 | 1.116170 |
| `024-095` | 744 | 327 | 0.015334 | 1.190893 |
| `024-068` | 744 | 364 | 0.014993 | 1.272727 |

Interpretation:

- The July CSI overlay is not dominated by one or two pathological machines.
- Even the slowest 10 groups account for only about `20.8%` of overlay runtime.
- The remaining cost is distributed broadly across the month-wide machine set.

## 5. exact internal hotspot found

Global internal CSI-overlay step totals:

- `overlap_candidate_construction_seconds = 0.272`
- `gold_hour_row_prep_sort_seconds = 0.244`
- `dominant_event_selection_seconds = 0.203`
- `source_flag_json_seconds = 0.120`
- `row_mutation_seconds = 0.053`
- `active_event_window_maintenance_seconds = 0.025`
- `csi_event_window_prep_sort_seconds = 0.012`
- `per_machine_preparation_seconds = 0.000`

Exact hotspot conclusion:

- The precise internal hotspot is **overlap candidate construction per hour** inside the CSI overlay loop.
- The next largest contributors are hour-row prep/sort and dominant-event selection.
- CSI event preparation itself is no longer the blocker.

## 6. runtime fixes applied and why

- Reworked the per-machine CSI overlay loop to prepare and sort hour rows once per machine using the cached `_hour_ts_dt` values already built in Gold backbone rows.
- Kept one incremental active-window sweep across the machine timeline instead of falling back to per-hour reparsing/re-preparation behavior.
- Removed the redundant second coarse overlap gate inside candidate construction once the active-window bounds already guaranteed event-window overlap.
- Replaced full-list dominant sorting with a single-pass dominant selection using the same tie-break contract.
- Added explicit machine/substep profiling so future runtime work can target measured costs instead of stage-level guesses.

Why these were safe:

- They do not widen or relax canonical semantics.
- They preserve row grain, dominant-event tie-break logic, minute-contract behavior, and source-flag meaning.
- They only reduce repeated loop overhead in the already-approved CSI overlay path.

## 7. July temp-DB result

- July 2025 Gold now lands successfully on the temp DB.
- Task13H July execution used:

```bash
./.conda311/bin/python scripts/run_task13r_temp_sweep.py \
  --shared-db /tmp/task13r_v3_temp.db \
  --temp-db /tmp/task13r_v3_temp.db \
  --checkpoint-log /tmp/task13h_july_gold_run.jsonl \
  --gold-only \
  --debug-gold-stages \
  --gold-debug-log /tmp/task13h_july_gold_run.stages.jsonl \
  "July 2025"
```

- July after-run counts:
  - `raw_energy_hourly = 99695`
  - `raw_csi_event = 24967`
  - `raw_mes_report = 23151`
  - `raw_maintenance_txn = 593`
  - `energy_meter_hour = 99695`
  - `csi_job_event = 24967`
  - `mes_report_event = 23151`
  - `maintenance_txn_event = 593`
  - `fact_machine_hour = 64727`
- Stage timings on the landed July run:
  - backbone = `1.635s`
  - CSI stage = `1.958s`
  - CSI quantity = `3.969s`
  - MES overlay = `22.203s`
  - maintenance overlay = `4.331s`
  - final replace = `2.414s`
  - total Gold materialization = `37.877s`
- Temp DB SHA1 after the landed July run:
  - `93682cf0de72b74defb834b88a1888630f8e3ab7`

## 8. canonical reader smoke result

- `CanonicalGoldReader` smoke passed:
  - available months now include `July 2025`
  - the July-only Gold run reported `available_months_after_run = July 2025 -> January 2025`
  - `July 2025 fact_machine_hour` rows = `64727`
- `CanonicalMLReader` and `CanonicalOptimizationReader` month exposure was verified against the same landed `fact_machine_hour` month-key set (`2025-07` present), which matches the identical `get_available_months()` month query implemented in those reader modules.

## 9. shared DB / artifact safety

- Shared DB remained untouched throughout Task13H:
  - before SHA1 = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - after SHA1 = `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- No shared-DB promotion was attempted.
- No artifact retraining or promotion was attempted.
- Active artifacts remain Task 4L only:
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 10. remaining limitations

- Task13H closes July Gold on temp DB only. It does **not** complete Aug 2025 -> Feb 2026.
- Shared `manufacturing_data.db` is still frozen at the accepted Jan-Jun 2025 baseline.
- Task13 and Task13R are still not passed for full extension / promotion scope.
- After the CSI overlay fix, the longest landed July Gold stage is now the MES overlay stage (`22.203s`), which is outside the narrow Task13H CSI-hotpath target.

## 11. recommended next step after Task13H

- Stop after July for this task, exactly as scoped.
- Resume the broader temp-only extension sweep from `August 2025` using the now-landed July temp DB state.
- If the next runtime blocker appears, target the now-longest landed stage first:
  - `energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay_plus_mes_overlay`
- Do not attempt shared-DB promotion until the full Jul 2025 -> Feb 2026 temp sweep closes cleanly and routed readers remain stable across the extended month set.
