# Post-FYP Stage B6.4 July Baseline Isolation and Idempotence Report

## Purpose

Stage B6.4 isolates the July 2025 baseline in a temporary DB copy, prunes existing July partitions, reruns July once, and records row-count and source-hash evidence.

## Scope

This stage updates the temp-only July rehearsal script, focused safety tests, this report, and the docs index.
It runs one July 2025 rehearsal against `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db` only.
It does not write the original runtime DB, create a DB inside the GitHub-safe tree, promote a temp DB, change Streamlit/manual ETL behavior, retrain models, promote artifacts, run March 2026, or wire data-quality rules into runtime materialization.

## B6.3 limitation being addressed

Stage B6.3 copied a DB that already contained July rows.
That made Bronze/Silver July row counts appear doubled versus extracted rows, so B6.3 proved temp-only execution safety but not clean-baseline Bronze/Silver evidence.
B6.4 addresses that gap by deleting only clearly July-scoped partitions in the temp DB before the single rerun.

## Temp DB boundary

- original runtime DB: `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db`
- original DB size before/after: `7226900480` bytes
- original DB mtime before/after: `1776434362`
- temp DB: `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`
- temp DB size before run: `7226900480` bytes
- temp DB SHA-256 before run: `acf2faffb9ffa3e366b4440a50e62783c9bb22142d0d3ded75c9ea019fc40d26`
- temp DB size after run: `7226900480` bytes
- temp DB SHA-256 after run: `d1ea71372a41d0f751c22e17a10a9c0cb71eecba1dc350848ed2b37591c564c3`

The script refuses DB paths inside the GitHub-safe repo and inside the original runtime repo.
Isolation mode also requires an explicit `--temp-db-path`.

## July partition isolation method

The script adds `--isolate-july-baseline`.
When enabled, it introspects all SQLite tables, records `PRAGMA table_info`, deletes only rows covered by explicit July predicates, and records pre/post row counts.
Tables without a conservative July predicate are skipped with a reason.

## Tables inspected

Inspected tables:
`calculation_audit`, `csi_job_event`, `energy_meter_hour`, `etl_csi_data`, `etl_energy_data`, `etl_mes_data`, `etl_runs`, `fact_machine_hour`, `machine_activity_analysis`, `machine_inventory`, `machine_monthly_presence`, `maintenance_ml_features`, `maintenance_records`, `maintenance_records_backup`, `maintenance_summary`, `maintenance_txn_event`, `mes_report_event`, `ml_models`, `raw_csi_event`, `raw_energy_hourly`, `raw_maintenance_txn`, `raw_mes_report`, `sqlite_sequence`, `three_way_matches`, `unified_view`, `unified_view_runs`.

## Tables pruned

| Table | Predicate summary | Pre-July rows | Post-July rows | Deleted rows |
| --- | --- | ---: | ---: | ---: |
| `etl_runs` | `month_processed = July 2025` | 1 | 0 | 1 |
| `etl_energy_data` | `month_year = July 2025` | 99,695 | 0 | 99,695 |
| `etl_csi_data` | `month_year = July 2025` | 24,952 | 0 | 24,952 |
| `etl_mes_data` | `month_year = July 2025` | 23,151 | 0 | 23,151 |
| `raw_energy_hourly` | `raw_timestamp` month is `2025-07` | 99,695 | 0 | 99,695 |
| `raw_csi_event` | canonical CSI month expression is `2025-07` | 24,967 | 0 | 24,967 |
| `raw_mes_report` | `raw_payload_json` report time month is `2025-07` | 23,151 | 0 | 23,151 |
| `raw_maintenance_txn` | transaction month is `2025-07` | 593 | 0 | 593 |
| `energy_meter_hour` | `hour_ts` month is `2025-07` | 99,695 | 0 | 99,695 |
| `csi_job_event` | canonical CSI month expression is `2025-07` | 24,967 | 0 | 24,967 |
| `mes_report_event` | `report_ts` month is `2025-07` | 23,151 | 0 | 23,151 |
| `maintenance_txn_event` | `txn_ts` month is `2025-07` | 593 | 0 | 593 |
| `fact_machine_hour` | `hour_ts` month is `2025-07` | 64,727 | 0 | 64,727 |
| `machine_monthly_presence` | `month_year = July 2025` | 255 | 0 | 255 |

## Tables skipped

Skipped tables were not deleted because they were global, ambiguous, generated legacy surfaces, model metadata, or had no conservative July-specific predicate:
`calculation_audit`, `machine_activity_analysis`, `machine_inventory`, `maintenance_ml_features`, `maintenance_records`, `maintenance_records_backup`, `maintenance_summary`, `ml_models`, `sqlite_sequence`, `three_way_matches`, `unified_view`, `unified_view_runs`.

Key skipped row counts stayed unchanged: `three_way_matches` `89 -> 89`, `machine_inventory` `268 -> 268`, `ml_models` `18 -> 18`, `unified_view` `195374 -> 195374`.

## Source-discovery evidence

Preflight compare diagnostics passed:

- human compare: `overall: PASS`
- JSON compare: `success: true`
- accepted month count: `8`
- expected blocked month count: `1`
- March 2026 remained expected blocked

Execution-time July source evidence:

- default resolver mode: `auto_manifest`
- default backfill readiness: `ready`
- explicit legacy readiness: `ready`
- July compare diagnostic: `success=true`, `matches=true`, `differences=[]`
- missing source files: `[]`

## Execution evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_pycache_stage_b6_4 python3.11 scripts/run_july_2025_temp_backfill_rehearsal.py --isolate-july-baseline --temp-db-path /tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db --data-root source_data/2025_jul_2026_feb_collected
```

Runtime evidence:

- status: `success`
- requested months: `["July 2025"]`
- successful months: `["July 2025"]`
- failed months: `[]`
- duration: `203.497` seconds
- start: `2026-05-05T21:33:30.636558+00:00`
- end: `2026-05-05T21:36:54.132290+00:00`

Extracted scoped rows:

| Family | Rows | Min timestamp | Max timestamp |
| --- | ---: | --- | --- |
| Energy | 99,695 | `2025-07-01 00:00:00` | `2025-07-31 23:00:00` |
| CSI | 24,952 | `2025-07-01 08:00:00` | `2025-08-11 15:40:37` |
| MES | 23,151 | `2025-07-01 00:00:35.457` | `2025-07-31 23:26:10.330` |

Mapping evidence:

- three-way matches: `85`
- Energy original rows: `99,695`
- Energy unique machines: `86`
- CSI machines: `96`
- MES machines: `96`
- MES coverage: `88.5%`
- Energy-to-CSI matches: `85`
- Energy-to-MES matches: `85`
- CSI-to-MES matches: `96`
- partial matches: `csi_mes_only=11`, `energy_csi_only=0`, `energy_mes_only=0`

## Post-run row-count evidence

The read-only post-run summary below uses the same canonical July predicates as the isolation and materialization path.
No second July ETL run was performed.

| Surface | July rows | Range / aggregate evidence |
| --- | ---: | --- |
| `etl_runs` | 1 | one July run after pruning |
| `etl_energy_data` | 99,695 | `2025-07-01 00:00:00` to `2025-07-31 23:00:00`, kWh `1460053.9551` |
| `etl_csi_data` | 24,952 | `2025-07-01 08:00:00` to `2025-08-11 15:40:37`, good qty `131049760.0` |
| `etl_mes_data` | 23,151 | planned date fields unavailable, planned qty `0.0` |
| `raw_energy_hourly` | 99,695 | `2025-07-01T00:00:00` to `2025-07-31T23:00:00`, kWh `1460053.9551` |
| `raw_csi_event` | 24,717 | `2025-07-01 08:00:00` to `2025-08-01 08:00:00`, good qty `130309991.0` |
| `raw_mes_report` | 23,151 | `2025-07-01T00:00:35.457000` to `2025-07-31T23:26:10.330000` |
| `raw_maintenance_txn` | 0 | no July rows after run |
| `energy_meter_hour` | 99,695 | `2025-07-01T00:00:00` to `2025-07-31T23:00:00`, kWh `1460053.9551`, flagged rows `0` |
| `csi_job_event` | 24,717 | `2025-07-01 08:04:53` to `2025-08-01T08:00:00`, good qty `130309991.0` |
| `mes_report_event` | 23,151 | `2025-07-01T00:00:35.457000` to `2025-07-31T23:26:10.330000`, required qty `149269843.0`, reported qty `131319675.0` |
| `maintenance_txn_event` | 0 | no July rows after run |
| `fact_machine_hour` | 64,727 | `2025-07-01T00:00:00` to `2025-07-31T23:00:00`, energy `1262410.8108`, good qty `120767865.0`, scrap qty `0.0`, rows with source flags `64727` |

Canonical materialization reported:

- Bronze used: Energy `99,695`, CSI `24,717`, MES `23,151`, maintenance `0`
- Silver materialized: Energy `99,695`, CSI `24,717`, MES `23,151`, maintenance `0`
- Gold `fact_machine_hour` rows created: `64,727`

## Duplicate/source_row_hash/idempotence evidence

The run did not execute July twice.
Instead, it inspected duplicate `source_row_hash` groups after the single clean-baseline run.

Duplicate July source-hash group counts were `0` for every table with `source_row_hash`:
`raw_energy_hourly`, `raw_csi_event`, `raw_mes_report`, `raw_maintenance_txn`, `energy_meter_hour`, `csi_job_event`, `mes_report_event`, and `maintenance_txn_event`.

`etl_*`, `etl_runs`, `machine_monthly_presence`, and `fact_machine_hour` do not have `source_row_hash`, so duplicate-hash evidence is not applicable there.

The clean-baseline run solved the B6.3 Bronze/Silver doubling issue for the canonical July predicates:
Energy Bronze/Silver equals extracted Energy, MES Bronze/Silver equals extracted MES, CSI canonical Bronze/Silver is lower than extracted CSI because canonical month selection excludes some scoped ETL spill rows.

## Safety evidence

- The original runtime DB size and mtime were unchanged after the run.
- The temp DB path was outside the GitHub-safe tree and outside the original runtime repo.
- The GitHub-safe tree contained no `*.db`, `*.sqlite`, or `*.sqlite3` files after execution.
- No DB file was staged.
- No raw Excel source file was staged.
- No generated `etl_outputs` file was staged.
- No model artifact was staged or modified by this run.
- `app.py` was not modified.
- March 2026 was not run.

## Result verdict

Stage B6.4 is a **temp-only clean-baseline execution pass**.
The July baseline was isolated, existing July partitions were pruned in the temp DB only, the single July run completed successfully, and canonical Bronze/Silver/Gold counts no longer show the B6.3 doubling pattern.

## What passed

- July source-discovery default remained `auto_manifest`.
- Explicit legacy source discovery remained ready.
- Compare diagnostics passed and March 2026 remained blocked.
- Existing July rows were pruned to zero in every explicitly month-scoped table.
- One July temp-only rehearsal completed successfully.
- Bronze/Silver Energy and MES row counts matched extracted rows.
- Canonical Bronze/Silver CSI row counts matched each other under the canonical July predicate.
- Gold `fact_machine_hour` produced `64,727` July rows.
- Duplicate `source_row_hash` groups were zero after the run.
- The original runtime DB was unchanged by size and mtime.

## What failed or remains limited

- CSI extracted rows include spill rows through `2025-08-11`, while canonical July Bronze/Silver uses the canonical July predicate and materialized `24,717` CSI rows.
- Global/ambiguous surfaces such as `three_way_matches`, `machine_inventory`, `unified_view`, and `ml_models` were intentionally not pruned.
- No second-run idempotence execution was performed; evidence is source-hash duplicate inspection after one clean-baseline run.
- No shared/live DB promotion was attempted.

## Rollback / cleanup note

No live DB rollback is required because all DB writes were confined to `/tmp`.
The temp evidence and DB can be removed after review:

```bash
rm -rf /tmp/leopaper_stage_b6_4_july_isolation
```

Do not copy the temp DB back to the original runtime repo or into the GitHub-safe tree.

## Recommended Stage B6 closeout or B7

Recommended next step: close Stage B6 with a concise decision report that confirms July temp-only source-discovery, clean-baseline execution, duplicate-hash, and safety evidence.
Do not proceed to shared/live DB promotion, multi-month rehearsal, or B7 adoption until the CSI spill-row interpretation is accepted as the canonical July policy.
