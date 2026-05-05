# Post-FYP Stage B6.3 July Temp Backfill Rehearsal Report

## Purpose

Stage B6.3 executes the first July 2025 historical backfill rehearsal against a temporary DB outside Git.
It follows the Stage B6.1 output-equivalence audit and the Stage B6.2 read-only preflight plan.

## Scope

This stage adds a narrow temp-only rehearsal script, safety tests, and this evidence report.
It runs July 2025 ETL/backfill/materialization only against `/tmp/leopaper_stage_b6_3_july_rehearsal/july_rehearsal.db`.
It does not write the original runtime DB, write a DB inside the GitHub-safe tree, promote the temp DB, change Streamlit behavior, retrain models, promote artifacts, or wire data-quality rules into runtime materialization.

## Temp DB boundary

The GitHub-safe repo remained the code/docs working tree.
The temp DB was outside Git:

- temp DB path: `/private/tmp/leopaper_stage_b6_3_july_rehearsal/july_rehearsal.db`
- temp DB inside GitHub-safe repo: `false`
- live DB writes allowed: `false`
- repo DB writes allowed: `false`

The rehearsal script refuses DB paths inside the repo and refuses any target month other than `July 2025`.

## Source DB / temp DB setup

The original runtime DB existed at:

- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/manufacturing_data.db`
- size before/after: `7226900480` bytes
- mtime before/after: `1776434362`

The DB was copied to the temp path before execution:

- temp size before run: `7226900480` bytes
- temp SHA-256 before run: `acf2faffb9ffa3e366b4440a50e62783c9bb22142d0d3ded75c9ea019fc40d26`
- temp size after run: `7491379200` bytes
- temp SHA-256 after run: `dafdce9252816cb734a433ef078f4cf40c20d928d8a8828153451cfad68987ac`

A first script attempt failed before DB mutation because the evidence-capture wrapper compared mixed datetime/string values while summarizing extracted DataFrames.
The temp DB SHA and mtime remained unchanged after that failed attempt.
The wrapper was fixed, the temp DB was refreshed from the original DB, and the recorded rehearsal below is from the corrected run.

## Source-discovery evidence

Preflight compare diagnostics passed before execution:

- accepted month count: `8`
- expected blocked month count: `1`
- March 2026 remained expected blocked
- overall: `PASS`

For the executed July run:

- default resolver mode: `auto_manifest`
- default backfill readiness: `ready`
- explicit legacy readiness: `ready`
- compare diagnostic for July: `success=true`, `matches=true`, `differences=[]`
- missing source files: `[]`

Expected source files:

- Energy: `source_data/2025_jul_2026_feb_collected/Energy(July2025-March2026)/能耗、費用報表__2025.7.xlsx`
- CSI: `source_data/2025_jul_2026_feb_collected/CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年7月.xls`
- MES: `source_data/2025_jul_2026_feb_collected/印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx`

## ETL extraction evidence

The corrected rehearsal captured the scoped ETL state immediately before temp-DB persistence:

| Family | Scoped row count | Min timestamp | Max timestamp |
| --- | ---: | --- | --- |
| Energy | `99695` | `2025-07-01 00:00:00` | `2025-07-31 23:00:00` |
| CSI | `24952` | `2025-07-01 08:00:00` | `2025-08-11 15:40:37` |
| MES | `23151` | `2025-07-01 00:00:35.457` | `2025-07-31 23:26:10.330` |

The raw loader log also reported unscoped workbook load counts:

- Energy loaded: `99695`
- CSI loaded: `24958`
- MES loaded: `242862`

The CSI scoped max end time extends beyond July because the month scoping admits CSI rows whose start or end intersects the target month.

## Mapping evidence

Mapping evidence from the corrected run:

- Energy original rows: `99695`
- Energy unique machines: `86`
- CSI machines: `96`
- MES machines: `96`
- Three-way matches: `85`
- MES coverage: `88.5%`
- Energy-to-CSI matches: `85`
- Energy-to-MES matches: `85`
- CSI-to-MES matches: `96`
- Partial-match console count: `11`

The script now captures partial-match categories from the ETL instance for future runs, but the corrected recorded run was already complete before that summarizer improvement was applied.

## Temp DB staging/materialization evidence

`run_historical_canonical_backfill(["July 2025"])` returned `status: success`.
Canonical materialization returned:

| Surface | July rows |
| --- | ---: |
| Bronze `raw_energy_hourly` used | `199390` |
| Bronze `raw_csi_event` used | `49684` |
| Bronze `raw_mes_report` used | `46302` |
| Bronze `raw_maintenance_txn` used | `593` |
| Silver `energy_meter_hour` materialized | `199390` |
| Silver `csi_job_event` materialized | `49684` |
| Silver `mes_report_event` materialized | `46302` |
| Silver `maintenance_txn_event` materialized | `593` |
| Gold `fact_machine_hour` created | `64727` |

Read-only post-run temp DB summary:

| Table | July row count | Range / aggregate evidence |
| --- | ---: | --- |
| `etl_runs` | `2` | copied DB already had a July run; rehearsal added another run record |
| `etl_energy_data` | `99695` | `2025-07-01 00:00:00` to `2025-07-31 23:00:00`, kWh `1460053.9551` |
| `etl_csi_data` | `24952` | `2025-07-01 08:00:00` to `2025-08-11 15:40:37`, good qty `131049760.0` |
| `etl_mes_data` | `23151` | planned date fields unavailable in this staging table; planned qty `0.0` |
| `raw_energy_hourly` | `199390` | kWh `2920107.9102` |
| `raw_csi_event` | `49739` | good qty `262353570.0` |
| `raw_mes_report` | `46302` | report timestamp `2025-07-01T00:00:35.457000` to `2025-07-31T23:26:10.330000` |
| `raw_maintenance_txn` | `593` | quantity `-9228.0474` |
| `energy_meter_hour` | `199390` | kWh `2920107.9102`, flagged rows `0` |
| `csi_job_event` | `49739` | good qty `262353570.0` |
| `mes_report_event` | `46302` | required qty `298539686.0`, reported qty `262639350.0` |
| `maintenance_txn_event` | `593` | quantity `-9228.0474` |
| `fact_machine_hour` | `64727` | `2025-07-01T00:00:00` to `2025-07-31T23:00:00`, energy `2524821.6216`, good qty `121883699.0`, scrap qty `0.0`, rows with source flags `64727` |

Important interpretation:
the source DB copy already contained July canonical data before the rehearsal.
The rehearsal replaced ETL staging and Gold month partitions, but Bronze/Silver counts doubled because the copied DB was not a blank or July-pruned baseline.
Therefore this run proves temp-only execution safety and successful completion, but it does not prove clean output equivalence from an empty July landing state.

## Runtime evidence

Corrected run:

- start: `2026-05-05T20:47:34.179508+00:00`
- end: `2026-05-05T20:50:57.856879+00:00`
- duration: `203.679` seconds
- status: `success`
- successful months: `["July 2025"]`
- failed months: `[]`
- exception: `null`

## Safety evidence

- Execution used only `/private/tmp/leopaper_stage_b6_3_july_rehearsal/july_rehearsal.db`.
- Original runtime DB size and mtime were unchanged after the run.
- No DB file appeared inside the GitHub-safe working tree.
- No DB, raw Excel, generated `etl_outputs`, local environment, or model artifact was staged.
- The script prints evidence to stdout and does not write report artifacts by default.
- The branch did not modify `app.py`, source-discovery defaults, materializer logic, Silver/Gold logic, model code, or Streamlit controls.

## Result verdict

Stage B6.3 is a **temp-only execution pass with output-equivalence limitations**.

The July 2025 rehearsal completed successfully against the temp DB and did not write the original runtime DB or any DB inside Git.
However, because the copied source DB already had July rows, Bronze/Silver counts are not clean single-pass equivalence evidence.
The Gold `fact_machine_hour` partition ended at the expected `64727` July rows, but a future task should use a blank/pruned temp baseline before claiming full output equivalence.

## What passed

- Source-discovery default July policy remained `auto_manifest`.
- Explicit legacy resolver remained available.
- Compare diagnostics passed.
- March 2026 remained blocked in preflight diagnostics.
- July ETL extraction and mapping completed.
- July temp-only historical backfill returned success.
- Canonical Silver/Gold materialization returned success.
- Temp DB changed; original runtime DB did not.
- No DB or generated runtime artifact entered the GitHub-safe tree.

## What failed or was skipped

- The first script attempt failed before DB mutation because of mixed datetime/string evidence summarization.
- Partial-match category counts were not captured in the corrected run's structured JSON, although the console reported `11` partial matches.
- Clean Bronze/Silver output equivalence was not proven because the copied DB already contained July rows.
- No shared/live DB promotion was attempted.
- No model retraining or artifact promotion was attempted.

## What remains unproven

- Clean single-pass Bronze/Silver equivalence from a July-pruned or blank temp baseline.
- Idempotence behavior for repeated July Bronze/Silver landing.
- Whether the doubled Bronze/Silver rows are expected for the current copied DB state or require a future upsert/hash investigation.
- Full month-by-month behavior beyond July 2025.
- Any shared/live DB promotion safety.

## Rollback / cleanup note

No repo rollback or live DB rollback is required because all DB writes were confined to `/tmp`.
The temp DB can be deleted after review:

`rm -f /tmp/leopaper_stage_b6_3_july_rehearsal/july_rehearsal.db`

Do not copy this temp DB back to the original runtime repo or into the GitHub-safe tree.

## Recommended B6.4

B6.4 should be a July baseline-isolation follow-up.
Recommended scope: create a temp DB copy, remove or isolate existing July Bronze/Silver/Gold partitions in the temp DB only, rerun July once, and compare clean single-pass counts against the Stage B6.3 evidence.
It should also inspect Bronze `source_row_hash` idempotence before any broader month rehearsal or shared DB promotion is considered.
