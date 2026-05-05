# Post-FYP Stage B8.1 August Temp Rehearsal Preflight Report

## Purpose

Stage B8.1 prepares the read-only evidence contract for a future August 2025 temp-only historical backfill rehearsal.
It defines the August source-discovery preflight, temp DB boundary, isolation surfaces, spill-row traceability requirement, abort criteria, and required post-run evidence before any August execution.

## Scope

This is a read-only preflight and planning task.
It extends the existing historical backfill preflight helper and tests, adds this technical report, and updates the rebuild docs index.

It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence basis from B6/B7

Stage B6 proved the July temp-only clean-baseline rehearsal path and its safety boundary.
Stage B6.4 isolated and pruned July partitions in a temp-only DB before rerun, resolving the earlier doubled-output limitation for July Bronze/Silver evidence.

Stage B7.1 proved the July CSI extracted-versus-canonical row gap was caused by `235` legitimate August-resolving spill rows outside canonical July scope.
Stage B7.2 accepted the current first-available timestamp CSI canonical month-assignment policy for Stage B7 evidence and required future multi-month reports to show extracted rows, canonical rows, and spill deltas explicitly.
Stage B7.3 proved that all `235` July-package CSI spill identities are traceable in August canonical raw and silver surfaces in the current temp DB.

## August source-discovery preflight

The August preflight plan is built through `build_historical_backfill_preflight_plan("August 2025", ...)`.
The helper remains read-only: it performs source-discovery checks only and does not load raw Excel content, run ETL, instantiate canonical materialization, connect to SQLite, copy a database, or write files.

Preflight result with placeholder sources:

| Field | Result |
| --- | --- |
| target month | `August 2025` |
| target month key | `2025-08` |
| default resolver mode | `auto` |
| source-discovery default policy | `auto / manifest-backed` |
| compare diagnostic status | `match` |
| legacy status | `resolved` |
| manifest status | `resolved` |
| difference count | `0` |
| backfill readiness | `ready_with_flags` |

## Expected source files and missing-file status

The August source files remain manifest-backed relative paths under the extension source scope:

| Family | Expected file |
| --- | --- |
| Energy | `Energy(July2025-March2026)/能耗、費用報表_2025.8-10.xlsx` |
| CSI | `CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年8月.xls` |
| MES | `印刷機MES生產數據-2025年3月1日至2026年2月28日.xlsx` |

Expected source families:

| Family | Status |
| --- | --- |
| Energy | `partial` |
| CSI | `complete` |
| MES | `complete` |

The August preflight test creates placeholder source files and reports `missing_source_files = []`.
With a real source-data root, any missing Energy, CSI, or MES path must be listed in `missing_source_files` and must block B8.2 execution until resolved.

The known August readiness flag remains the Energy sentinel exclusion note: Energy is usable but excludes the `2025-08-17 08:00-17:00` sentinel anomaly rows for `1024-10032/024-147` under the current source contract.

## Spill-row traceability requirement

B8.2 must rerun the B7.3 spill identity traceability check after a future August temp-only rehearsal.

Required proof path:

- rebuild the July-package spill identity count of `235`;
- match the identities into August canonical raw CSI rows;
- use matched raw `source_row_hash` values to prove August canonical silver traceability;
- require raw unmatched spill identities = `0`;
- require silver unmatched spill identities = `0`;
- report duplicate `source_row_hash` groups for August raw and silver CSI surfaces.

The stable identity key remains:

```text
machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty
```

## Planned August temp DB boundary

Recommended future temp DB path:

```text
/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db
```

The path is only a recommendation for B8.2.
B8.1 does not create it.
Future execution must prove the temp DB is outside the GitHub-safe tree and outside the original runtime repo.
The original runtime `manufacturing_data.db` must remain untouched.

## Planned isolation/prune surfaces

Future B8.2 isolation should prune only clearly August-scoped temp DB rows before rerun.
The planned surfaces are:

| Surface | Scope |
| --- | --- |
| `etl_runs` | `month_processed = 'August 2025'` |
| `etl_energy_data` | `month_year = 'August 2025'` |
| `etl_csi_data` | `month_year = 'August 2025'` |
| `etl_mes_data` | `month_year = 'August 2025'` |
| `raw_energy_hourly` | `substr(raw_timestamp, 1, 7) = '2025-08'` |
| `raw_csi_event` | current raw CSI canonical month expression = `2025-08` |
| `raw_mes_report` | `substr(json_extract(raw_payload_json, '$."報工時間"'), 1, 7) = '2025-08'` |
| `energy_meter_hour` | `substr(hour_ts, 1, 7) = '2025-08'` |
| `csi_job_event` | current silver CSI canonical month expression = `2025-08` |
| `mes_report_event` | `substr(report_ts, 1, 7) = '2025-08'` |
| `fact_machine_hour` | `substr(hour_ts, 1, 7) = '2025-08'` |
| `machine_monthly_presence` | `month_year = 'August 2025'` |

Global or ambiguous tables such as inventory, matching state, SQLite internals, and ML artifacts are not planned prune surfaces.

## Required post-run evidence

Future B8.2 must capture:

- source payload summary and compare diagnostic result;
- extracted Energy/CSI/MES row counts after August month scoping;
- machine mapping counts and partial-match counts;
- ETL staging row counts for August 2025;
- Bronze/Silver row counts for August Energy, CSI, and MES surfaces;
- Gold `fact_machine_hour` August row count;
- duplicate `source_row_hash` group counts for August raw CSI and silver CSI;
- B7.3 spill identity capture under August raw and silver scope;
- aggregate kWh, good quantity, scrap quantity, and quantity-basis checks;
- runtime duration and stage timing;
- temp DB path proof plus live/repo DB non-write proof;
- post-run regression tests and unsafe-file scans.

## Abort criteria

Abort B8.2 before or during execution if:

- the DB path is not temp-only or is inside either repo;
- repo-local `manufacturing_data.db` or another live/shared DB would be written;
- any source file is missing or source payload comparison mismatches;
- March 2026 becomes accepted or appears in target-month output;
- extracted, mapping, ETL staging, Bronze, Silver, or Gold counts materially diverge without explanation;
- canonical materialization writes outside the temp DB;
- B7.3 spill identities are unmatched in August raw or silver scope;
- duplicate source-row-hash groups appear unexpectedly;
- runtime exceeds the declared safe threshold;
- downstream regression tests fail;
- DB files, raw Excel files, generated `etl_outputs`, model artifacts, local env folders, or `app.py` changes would be staged.

## Out of scope

B8.1 does not execute August ETL, backfill, materialization, DB copy, temp DB promotion, source-discovery default changes, canonical predicate changes, DQ runtime wiring, ML retraining, Streamlit UI work, or runtime app changes.

## Validation

Focused validation for the helper:

```text
python3.11 -m unittest tests.test_backfill_rehearsal_preflight
```

The focused test proves:

- August preflight builds with placeholder sources;
- August preflight reports `auto / manifest-backed` source discovery;
- August preflight includes the B7.3 spill-row traceability requirement;
- August preflight does not create DB files;
- March 2026 remains blocked;
- unknown month labels fail clearly.

The full Stage B8.1 validation set is recorded in the terminal handoff for this branch.

## Remaining risks

- B8.1 proves only the preflight contract, not a fresh August execution.
- August Energy remains `ready_with_flags` because of the known sentinel exclusion note.
- The B7.3 spill traceability proof came from the current Stage B6.4 temp DB; B8.2 must prove the same requirement after a fresh August temp-only run.
- Future reports must distinguish source-package extraction rows, canonical month rows, spill identities, and raw provenance variants.

## Recommended B8.2

Execute a temp-only August 2025 rehearsal using the B8.1 preflight contract.
Use the recommended temp DB boundary, apply only the planned August isolation surfaces, run no live DB promotion, and capture the required source-discovery, ETL, Bronze/Silver/Gold, spill traceability, aggregate, runtime, and safety evidence before any further adoption decision.
