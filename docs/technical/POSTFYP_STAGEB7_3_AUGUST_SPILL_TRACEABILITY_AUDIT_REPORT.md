# Post-FYP Stage B7.3 August Spill Traceability Audit Report

## Purpose

Stage B7.3 audits whether the `235` July-package CSI rows that canonicalize to August remain traceable under August canonical scope.
Stage B7.1 proved the July extracted-versus-canonical row gap was an August spill boundary.
Stage B7.2 accepted the current first-available timestamp CSI canonical month-assignment policy for Stage B7.
This stage verifies traceability for those July-package spill identities before any broader multi-month rehearsal.

## Scope

This is a read-only audit and decision-pack task.
It adds a standalone read-only traceability helper, focused safety tests, this report, a rebuild-docs index entry, and a short data-contract note.
It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence source

The audit used the preferred Stage B6.4 temp-only DB:

- DB path: `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`
- Resolved read-only path: `/private/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`
- Script: `python3.11 scripts/audit_august_csi_spill_traceability.py --db-path /tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db --pretty`

The helper opens SQLite in read-only mode, refuses GitHub-safe repo DB paths, refuses original runtime repo DB paths, requires an explicit `--db-path`, prints structured JSON to stdout, and does not write files.

## Spill-row identity from B7.1

The B7.1 spill identity is unchanged:

| Evidence point | Result |
| --- | ---: |
| July-package spill rows | `235` |
| Spill canonical month | `2025-08` |
| Distinct CSI machine IDs | `70` |
| Distinct order IDs | `138` |
| Good quantity sum | `739,769.0` |
| Min start time | `2025-08-01 00:02:01` |
| Max end time | `2025-08-11 15:40:37` |

The top spill contributors by good quantity remain `D-024-147`, `D-024-143`, `D-024-144`, `D-024-131`, and `D-024-082`.

## August traceability method

The audit:

1. Rebuilds the July-package spill identity from `etl_csi_data` where `month_year = 'July 2025'` and the ETL-available canonical month expression is not `2025-07`.
2. Reads August canonical `raw_csi_event` rows using the current raw CSI canonical month expression for `2025-08`.
3. Reads August canonical `csi_job_event` rows using the current silver CSI canonical month expression for `2025-08`.
4. Matches each spill row to August raw CSI rows by a stable composite identity.
5. Uses the matched raw `source_row_hash` values to prove August silver traceability.
6. Reads August `etl_csi_data` and `fact_machine_hour` only as context, not as required proof.

No ETL, backfill, or materialization was executed.

## Matching key / fingerprint method

`etl_csi_data` spill rows do not carry `source_row_hash` directly.
The audit therefore uses a two-step key:

Primary proof path:

- Match spill identity into August canonical raw rows by composite identity.
- Use matched raw `source_row_hash` values to match August canonical silver rows.

Composite fallback identity:

```text
machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty
```

This key was selected because these fields are available in the July ETL spill rows and in raw/silver CSI event surfaces after normalization.

## Traceability result

| Metric | Result |
| --- | ---: |
| July-package spill identities audited | `235` |
| Spill identities matched in August canonical raw scope | `235` |
| Spill identities unmatched in August canonical raw scope | `0` |
| August raw rows matched to spill identities | `470` |
| Distinct August raw source hashes matched | `470` |
| Spill identities matched in August canonical silver scope | `235` |
| Spill identities unmatched in August canonical silver scope | `0` |
| Distinct August silver source hashes matched through raw | `235` |

The raw matched row count is `470` because the current temp DB contains two raw provenance variants for each of the `235` spill identities:

| Matched raw source file | Matched raw rows |
| --- | ---: |
| `/Users/rayfung/Documents/VCC/LeoPaper/DataSet Package(New Collected)/CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年7月.xls` | `235` |
| `source_data/2025_jul_2026_feb_collected/CSI(July2025 to Feb2026)/CSI印刷心電圖報表2025年7月.xls` | `235` |

The source-row-hash duplicate group count is still `0` for August raw scope and `0` for August silver scope.
The extra raw rows are provenance/path variants, not duplicate source-row-hash groups.

August surface context from the current temp DB:

| Surface | August rows | Good qty sum | Min timestamp | Max timestamp |
| --- | ---: | ---: | --- | --- |
| `raw_csi_event` canonical August | `22,869` | `109,043,510.0` | `2025-08-01 00:02:01` | `2025-09-01 08:00:00` |
| `csi_job_event` canonical August | `22,634` | `108,303,741.0` | `2025-08-01 01:04:59` | `2025-09-01T08:00:00` |
| `etl_csi_data` August staging | `22,572` | `108,162,946.0` | `2025-08-01 08:00:00` | `2025-09-01 08:00:04` |
| `fact_machine_hour` August context | `64,727` | `99,105,840.0` | `2025-08-01T00:00:00` | `2025-08-31T23:00:00` |

## Unmatched rows if any

None.

The read-only helper reported:

- `raw_august_unmatched_spill_row_count = 0`
- `silver_august_unmatched_spill_row_count = 0`

## Interpretation

August traceability for the B7.1 July-package CSI spill identities is proven in the current Stage B6.4 temp DB.
All `235` July-package spill identities are present under August canonical raw scope.
All `235` spill identities are also traceable into August canonical silver scope through matched raw `source_row_hash` values.

This supports the B7.2 policy decision:

- the July extracted-versus-canonical gap is not data loss;
- the spill rows are traceable under August canonical semantics;
- the current first-available timestamp month-assignment rule remains acceptable for Stage B7 evidence.

## Whether August capture is proven

Yes, for traceability in the current temp DB.

The audit proves that the `235` July-package / August-canonical CSI spill identities are present in August canonical raw scope and traceable to August canonical silver scope.
It does not prove a fresh August ETL/backfill/materialization run, because no August execution was in scope.

## Whether future August temp rehearsal is required

A future August temp-only rehearsal is still required for clean August execution and output-equivalence evidence if the next stage needs to prove August backfill behavior.
It is not required merely to prove that the B7.1 `235` spill identities are traceable in the current temp DB.

Future August rehearsal should still record extracted rows, canonical raw rows, canonical silver rows, spill deltas, duplicate/hash evidence, Gold effects, runtime duration, and DB safety.

## Safety evidence

- The audit used `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db`.
- SQLite was opened read-only with `mode=ro`.
- The helper refuses DB paths inside the GitHub-safe repo.
- The helper refuses DB paths inside the original runtime repo.
- The helper fails clearly for missing DB paths.
- The helper does not run ETL, historical backfill, canonical materialization, or ML training.
- The helper does not write files by default.
- No temp DB was promoted.
- No runtime DB was written.
- `app.py` was not modified.

## Runtime behavior impact

No runtime behavior changed.
The new helper is a standalone read-only diagnostic.
No source-discovery default, ETL scope, Bronze/Silver/Gold predicate, DQ runtime wiring, Streamlit route, ML artifact, or optimization behavior changed.

## Tests run

- `python3.11 -m unittest tests.test_august_csi_spill_traceability_safety`
- `python3.11 scripts/audit_august_csi_spill_traceability.py --db-path /tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db --pretty`

The full required regression and safety-validation set for Stage B7.3 was run before commit and is recorded in the terminal handoff for this branch.

## Unsafe file scan

The required unsafe-file scans were run before commit.
The intended staged set is limited to:

- `scripts/audit_august_csi_spill_traceability.py`
- `tests/test_august_csi_spill_traceability_safety.py`
- `docs/technical/POSTFYP_STAGEB7_3_AUGUST_SPILL_TRACEABILITY_AUDIT_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`

No DB file, raw Excel file, generated `etl_outputs` file, local environment folder, model artifact, or `app.py` change is part of Stage B7.3.

## Remaining risks

- The current temp DB proves traceability, not a fresh August clean-baseline execution.
- Raw August scope contains two provenance/path variants for each of the `235` matched spill identities, so future reporting must distinguish identity-level traceability from raw-row provenance counts.
- The audit does not decide whether the first-available timestamp policy is the permanent best business rule.
- Future multi-month rehearsal can still misread extracted package rows as canonical month rows unless extracted-versus-canonical deltas remain explicit.

## Recommended next stage

Recommended next stage: a temp-only August rehearsal plan or execution gate.
It should prove clean August source-discovery, ETL extraction, canonical raw/silver counts, Gold effects, duplicate/hash status, extracted-versus-canonical deltas, and safety boundaries without changing runtime predicates or promoting a temp DB.
