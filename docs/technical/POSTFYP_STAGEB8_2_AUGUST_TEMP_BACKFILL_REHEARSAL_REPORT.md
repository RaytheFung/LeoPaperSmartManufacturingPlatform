# Post-FYP Stage B8.2 August Temp Backfill Rehearsal Report

## Purpose

Stage B8.2 executes one August 2025 clean-baseline historical backfill rehearsal against a temp DB outside Git.
The goal is to capture August source-discovery, isolation, ETL, Bronze/Silver/Gold, spill traceability, duplicate, runtime, and safety evidence before any shared/live DB promotion or runtime behavior change.

## Scope

This stage added a narrow August-only temp rehearsal runner, safety tests, this report, and a rebuild-docs index entry.
It ran one August 2025 rehearsal against `/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db`.

It did not write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, modify active model/preprocessor artifacts, retrain ML models, change source-discovery defaults, change runtime canonical predicates, change Streamlit upload/manual ETL behavior, add write-capable Streamlit controls, modify `app.py`, run March 2026, stage raw Excel files, or stage generated `etl_outputs`.

## Temp DB boundary

Original runtime DB source:

```text
/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db
```

Temp DB copy:

```text
/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db
```

Pre-run DB evidence:

| DB | Size bytes | mtime UTC / epoch | SHA-256 |
| --- | ---: | --- | --- |
| original runtime DB | `7226900480` | `2026-04-17T13:59:22.177873+00:00` / `1776434362` | not rehashed |
| temp DB before mutation | `7226900480` | `2026-05-05T23:04:20.363386+00:00` | `acf2faffb9ffa3e366b4440a50e62783c9bb22142d0d3ded75c9ea019fc40d26` |

Post-run temp DB evidence:

| DB | Size bytes | mtime UTC | SHA-256 |
| --- | ---: | --- | --- |
| temp DB after run | `7226900480` | `2026-05-05T23:06:46.158098+00:00` | `b96dda6d063ad15a1bd0ff7a5d95a7f7a1bdca22781486a1cf889c684ee527fc` |

The original runtime DB size and mtime were unchanged after the run.

## August partition isolation method

The runner inspected SQLite schema only on the temp DB, then deleted rows only when a conservative August predicate was available.
Rules were column-gated: if a table lacked the required columns, the table was skipped rather than pruned.

Canonical August predicates used:

- ETL staging: `month_year = 'August 2025'`
- ETL run ledger: `month_processed = 'August 2025'`
- Energy Bronze/Silver/Gold: `substr(timestamp, 1, 7) = '2025-08'`
- CSI Bronze/Silver: current first-available timestamp canonical month expression equals `2025-08`
- MES Bronze/Silver: report timestamp month equals `2025-08`
- Maintenance Bronze/Silver: transaction timestamp month equals `2025-08`
- Machine monthly presence: `month_year = 'August 2025'`

## Tables inspected

The temp DB inspection saw `26` tables.
Every present table was either pruned with an August predicate or skipped with a reason.

## Tables pruned

| Table | Pre-prune August rows | Post-prune August rows | Deleted rows |
| --- | ---: | ---: | ---: |
| `csi_job_event` | `22634` | `0` | `22634` |
| `energy_meter_hour` | `99685` | `0` | `99685` |
| `etl_csi_data` | `22572` | `0` | `22572` |
| `etl_energy_data` | `99695` | `0` | `99695` |
| `etl_mes_data` | `20884` | `0` | `20884` |
| `etl_runs` | `1` | `0` | `1` |
| `fact_machine_hour` | `64727` | `0` | `64727` |
| `machine_monthly_presence` | `255` | `0` | `255` |
| `maintenance_txn_event` | `582` | `0` | `582` |
| `mes_report_event` | `20884` | `0` | `20884` |
| `raw_csi_event` | `22634` | `0` | `22634` |
| `raw_energy_hourly` | `99695` | `0` | `99695` |
| `raw_maintenance_txn` | `582` | `0` | `582` |
| `raw_mes_report` | `20884` | `0` | `20884` |

## Tables skipped

| Table | Rows | Reason |
| --- | ---: | --- |
| `calculation_audit` | `70` | No conservative August-specific delete predicate is defined. |
| `machine_activity_analysis` | `0` | No conservative August-specific delete predicate is defined. |
| `machine_inventory` | `268` | Global inventory state; `last_seen_date` is not safe enough for August partition deletion. |
| `maintenance_ml_features` | `0` | No conservative August-specific delete predicate is defined. |
| `maintenance_records` | `14378` | No conservative August-specific delete predicate is defined. |
| `maintenance_records_backup` | `71890` | No conservative August-specific delete predicate is defined. |
| `maintenance_summary` | `990` | No conservative August-specific delete predicate is defined. |
| `ml_models` | `18` | Model metadata/artifact table; model artifacts must not be modified. |
| `sqlite_sequence` | `13` | SQLite internal sequence table. |
| `three_way_matches` | `89` | Global mapping state; first/last matched dates do not make row deletion safely month-scoped. |
| `unified_view` | `195374` | Derived/global legacy surface; no conservative August delete predicate is defined. |
| `unified_view_runs` | `19` | No conservative August-specific delete predicate is defined. |

## Source-discovery evidence

| Evidence point | Result |
| --- | --- |
| Default source-discovery mode | `auto_manifest` |
| Default readiness | `ready_with_flags` |
| Explicit legacy readiness | `ready_with_flags` |
| Compare diagnostic | pass |
| Missing source files | `[]` |
| March 2026 | not run; remains blocked in compare diagnostic |

Expected August sources:

- Energy: `source_data/2025_jul_2026_feb_collected/Energy(July2025-March2026)/能耗、費用報表_2025.8-10.xlsx`
- CSI: `source_data/2025_jul_2026_feb_collected/CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年8月.xls`
- MES: `source_data/2025_jul_2026_feb_collected/印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx`

The readiness flag remains the known August Energy sentinel exclusion note.

## Execution evidence

Command:

```text
python3.11 scripts/run_august_2025_temp_backfill_rehearsal.py --temp-db-path /tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db --data-root source_data/2025_jul_2026_feb_collected
```

Runtime:

| Field | Result |
| --- | --- |
| Started UTC | `2026-05-05T23:04:41.552811+00:00` |
| Ended UTC | `2026-05-05T23:06:48.795469+00:00` |
| Duration seconds | `127.243` |
| Runner status | `partial_error` |
| Backfill result status | `success` |
| Successful months | `['August 2025']` |
| Failed months | `[]` |

Canonical materialization for August succeeded:

| Evidence point | Result |
| --- | ---: |
| Bronze `raw_energy_hourly` rows used | `99695` |
| Bronze `raw_csi_event` rows used | `22399` |
| Bronze `raw_mes_report` rows used | `20884` |
| Bronze `raw_maintenance_txn` rows used | `0` |
| Silver `energy_meter_hour` rows materialized | `99685` |
| Silver `csi_job_event` rows materialized | `22399` |
| Silver `mes_report_event` rows materialized | `20884` |
| Silver `maintenance_txn_event` rows materialized | `0` |
| Gold `fact_machine_hour` rows created | `64727` |

## Post-run row-count evidence

| Surface | August rows | Range / aggregate |
| --- | ---: | --- |
| `etl_runs` | `1` | one August run ledger row |
| `etl_energy_data` | `99695` | `2025-08-01 00:00:00` to `2025-08-31 23:00:00`, kWh sum `1001306814.0603` |
| `etl_csi_data` | `22572` | `2025-08-01 08:00:00` to `2025-09-01 08:00:04`, good qty `108162946.0` |
| `etl_mes_data` | `20884` | planned qty `0.0` |
| `raw_energy_hourly` | `99695` | `2025-08-01T00:00:00` to `2025-08-31T23:00:00`, raw kWh `1001306814.0603` |
| `raw_csi_event` | `22399` | `2025-08-01 08:00:00` to `2025-09-01 08:00:00`, raw good qty `107563972.0` |
| `raw_mes_report` | `20884` | `2025-08-01T00:02:33.457000` to `2025-08-31T23:19:53.310000` |
| `raw_maintenance_txn` | `0` | no August maintenance rows |
| `energy_meter_hour` | `99685` | `2025-08-01T00:00:00` to `2025-08-31T23:00:00`, kWh `1306814.0613` |
| `csi_job_event` | `22399` | `2025-08-01 09:07:13` to `2025-09-01T08:00:00`, good qty `107563972.0` |
| `mes_report_event` | `20884` | reported qty `108629979.0`, required qty `124701816.0` |
| `maintenance_txn_event` | `0` | no August maintenance rows |
| `fact_machine_hour` | `64727` | `2025-08-01T00:00:00` to `2025-08-31T23:00:00`, energy `1120241.8068`, good qty `98382657.0`, scrap qty `0.0` |
| `machine_monthly_presence` | `255` | August machine-month rows |

## Spill traceability evidence

B7.3 traceability was rerun against the post-run temp DB.
It failed for the clean August-only rehearsal result.

| Metric | Result |
| --- | ---: |
| July-package spill identities audited | `235` |
| Raw August matched spill identities | `0` |
| Raw August unmatched spill identities | `235` |
| Raw August matched row count | `0` |
| Silver August matched spill identities | `0` |
| Silver August unmatched spill identities | `235` |

Interpretation:

- The August-only source file begins canonical raw CSI at `2025-08-01 08:00:00` after the clean rerun.
- The B7.3 July-package spill identities include rows from `2025-08-01 00:02:01` onward.
- Those spill identities were traceable in the prior B6.4 temp DB because July-package provenance was still present.
- After a clean August-only prune and rerun, those July-package spill rows are not reintroduced by the August CSI source file.

This is the main B8.2 limitation and should be treated as a B8.3 decision point, not as a silent success.

## Duplicate/source_row_hash evidence

Duplicate `source_row_hash` group counts after the single clean-baseline run:

| Surface | Duplicate August source-row-hash groups |
| --- | ---: |
| `raw_energy_hourly` | `0` |
| `raw_csi_event` | `0` |
| `raw_mes_report` | `0` |
| `raw_maintenance_txn` | `0` |
| `energy_meter_hour` | `0` |
| `csi_job_event` | `0` |
| `mes_report_event` | `0` |
| `maintenance_txn_event` | `0` |

No second August run was performed.

## Safety evidence

- Temp DB path was outside the GitHub-safe repo.
- Temp DB path was outside the original runtime repo.
- Original runtime DB size and mtime were unchanged.
- Live DB writes were not allowed.
- Repo DB writes were not allowed.
- March 2026 was not run.
- `ml_models` was inspected and skipped.
- `app.py` was not modified.
- No DB file was created inside the GitHub-safe tree.
- No DB, raw Excel, generated `etl_outputs`, or model artifact is part of the intended staged set.

## Result verdict

Partial pass.

The August temp-only backfill and canonical materialization succeeded against the temp DB.
The safety boundary held.
The B7.3 spill traceability requirement failed after a clean August-only rerun because the July-package spill identities were not present in the August-only source ingestion result.

## What passed

- Temp DB copy and mutation stayed outside Git.
- August partition isolation was conservative and auditable.
- August source discovery resolved with `auto_manifest` and no missing files.
- August ETL/backfill/materialization returned `success`.
- Gold `fact_machine_hour` August rows were created.
- Duplicate `source_row_hash` groups were `0` for the inspected source-hash surfaces.
- Original runtime DB remained unchanged by size and mtime.
- March 2026 was not run.

## What failed or remains limited

- B7.3 spill traceability did not hold after clean August-only isolation and rerun.
- The post-run August raw/silver CSI surfaces did not contain the `235` July-package spill identities.
- The result suggests the July package is required to preserve those spill identities under August canonical scope, or a future policy must explicitly decide how cross-package spill rows should be carried forward.
- The runner output from this run includes upstream ETL print lines before JSON because the capture hardening was added after the run; future runs capture those lines inside structured evidence.

## Rollback / cleanup note

No live rollback is required because only the temp DB was mutated.
Cleanup is to discard `/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db` and its temporary evidence file when no longer needed.
No temp DB should be promoted to shared/live use.

## Recommended B8.3

B8.3 should decide the policy for July-package rows that canonicalize to August.
The decision should choose one of these paths before any live adoption:

- include July-package CSI spill evidence when proving August canonical completeness;
- define an explicit cross-package carry-forward process for spill rows;
- accept that August-only source ingestion excludes those identities and document the resulting canonical limitation;
- or revise source package boundaries only under a separate approved runtime-predicate/source-policy task.
