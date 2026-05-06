# Post-FYP Stage B9.1 CSI Carry-Forward Preflight Report

## Purpose

Stage B9.1 adds a read-only preflight helper for boundary-month CSI carry-forward planning.
The helper identifies previous-package CSI rows whose timestamp canonical month equals the target month, preserves stable identity and hash evidence, and produces a reconciliation plan before any ETL, backfill, or canonical materialization run.

## Scope

This stage adds `core/csi_carry_forward_preflight.py`, tests it with temp SQLite fixtures, records read-only evidence from existing temp DBs, and updates the rebuild docs index.

It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence basis

Stage B9.1 reads the prior Stage B7/B8 evidence chain:

| Stage | Evidence used |
| --- | --- |
| B7.1 | July-package CSI extracted-versus-canonical audit proved the gap is `235` rows that canonicalize to August. |
| B7.2 | Current first-available timestamp CSI canonical month policy remains accepted for this evidence chain. |
| B7.3 | The `235` July-package spill identities were traceable in August raw and silver scope in the B6.4 temp DB. |
| B8.2 | August-only clean-baseline rehearsal succeeded operationally but matched `0/235` spill identities. |
| B8.3 | Carry-forward or adjacent-package reconciliation was selected as the next design direction before broader rehearsal. |

Read-only DB evidence used in this stage:

| Purpose | DB path | Access |
| --- | --- | --- |
| Previous-package candidate/hash evidence | `/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db` | SQLite read-only URI |
| Current August-only overlap baseline | `/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db` | SQLite read-only URI |

## Carry-forward problem restatement

Source package month and canonical event month can diverge.
For CSI, the accepted canonical month rule uses the first available timestamp from production start, production end, preparation end, or shift date evidence.
That means July-package rows can legitimately belong to August canonical scope.

B8.2 proved that a clean August-only ingestion can produce August raw, silver, and gold output while still omitting the July-package rows that canonicalize to August.
Stage B9.1 therefore treats carry-forward as a reconciliation requirement, not as a runtime implementation change.

## Preflight helper behavior

The helper exposes:

```text
build_csi_carry_forward_preflight(target_month="August 2025", db_path=None, current_package_db_path=None)
```

Behavior:

- supports August 2025 only for Stage B9.1;
- requires an explicit `db_path`;
- refuses DB paths inside the GitHub-safe repo;
- refuses DB paths inside the original runtime repo;
- opens SQLite with `mode=ro`;
- reads candidate rows from `etl_csi_data`;
- optionally compares candidates against current-package `raw_csi_event` and `csi_job_event`;
- returns a structured preflight plan and evidence object;
- writes no files and runs no ETL/backfill/materialization.

Required output fields are present: `target_month`, `previous_package_month`, `canonical_month_key`, `current_policy`, `carry_forward_required`, `candidate_count`, `candidate_identity_fields`, `source_row_hash_available`, `duplicate_risk_summary`, `current_package_overlap_summary`, `reconciliation_strategy`, `planned_inclusion_stage`, `planned_duplicate_prevention`, `planned_post_run_evidence`, `abort_criteria`, and `proof_gaps`.

## August 2025 candidate summary

Command:

```text
python3.11 - <<'PY'
from core.csi_carry_forward_preflight import build_csi_carry_forward_preflight
build_csi_carry_forward_preflight(
    db_path="/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db",
    current_package_db_path="/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db",
)
PY
```

Summary:

| Metric | Result |
| --- | ---: |
| target month | August 2025 |
| previous package month | July 2025 |
| canonical month key | `2025-08` |
| carry-forward required | `true` |
| candidate identities | `235` |
| canonical month distribution | `{"2025-08": 235}` |
| distinct machines | `70` |
| distinct orders | `138` |
| good quantity sum | `739769.0` |
| min start time | `2025-08-01 00:02:01` |
| max end time | `2025-08-11 15:40:37` |
| duplicate candidate identity groups | `0` |

Top machine/order summaries by good quantity were produced by the helper and retained in the structured result.
The largest machine summary row was machine `D-024-147`, `1` row, `1` distinct order, good quantity `46594.0`.
The largest machine/order summary row was machine `D-024-147`, order `J250019578`, `1` row, good quantity `46594.0`.

## Identity/hash strategy

Candidate identity fields:

```text
machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty
```

The strategy remains the B7.3 two-step proof:

1. Match previous-package ETL candidate identities to target-month raw CSI rows by composite identity.
2. Use the matched raw `source_row_hash` values to prove silver traceability where available.

Read-only B6.4 evidence:

| Metric | Result |
| --- | ---: |
| candidate identities | `235` |
| raw identity matched candidates | `235` |
| raw unmatched candidates | `0` |
| raw hash matched candidates | `235` |
| raw matched rows | `470` |
| distinct source row hashes | `470` |
| silver matched candidates | `235` |
| silver unmatched candidates | `0` |
| all candidates have raw source-row-hash evidence | `true` |

The `470` raw matched rows/source hashes reflect two provenance surfaces in the B6.4 temp DB for the same `235` candidate identities: one absolute local source-file path and one repo-relative `source_data/...` source-file path.
This does not create duplicate candidate identities in the preflight result, but B9.2 must explicitly control source-hash duplication before any temp execution evidence is accepted.

## Current-package overlap check

The helper compared the `235` previous-package candidate identities against the B8.2 August-only temp DB.

| Metric | Result |
| --- | ---: |
| current raw August rows | `22399` |
| current silver August rows | `22399` |
| raw overlap candidate count | `0` |
| raw overlap row count | `0` |
| silver overlap candidate count | `0` |
| silver overlap row count | `0` |
| overlap status | `zero_overlap` |

This confirms the B8.2 limitation from another angle: the current August package does not overlap those July-package spill identities.

## Reconciliation strategy

Recommended B9.2 strategy:

1. Carry forward only previous-package CSI identities whose canonical month equals the target month.
2. Prefer `source_row_hash` after raw identity matching.
3. Use the stable composite identity as the fallback where hash evidence is not directly available on the candidate surface.
4. Reject candidate identities already present in current-package raw or silver scope unless an approved tie-breaker exists.
5. Execute only against a temp DB outside Git.
6. Compare carry-forward-enhanced August output with the B8.2 August-only baseline.

## Duplicate-prevention plan

Duplicate prevention must require:

- zero duplicate candidate composite identity groups before inclusion;
- zero current-package raw/silver overlap for automatically includable candidates;
- explicit review if current-package overlap is non-zero;
- zero duplicate `source_row_hash` groups in `raw_csi_event` and `csi_job_event` after any future temp-only carry-forward run;
- separate reporting of source package month, canonical event month, and source-file provenance.

B9.1 result:

| Duplicate risk metric | Result |
| --- | ---: |
| candidate duplicate identity groups | `0` |
| candidate duplicate identity rows | `0` |
| current raw overlap candidates | `0` |
| current silver overlap candidates | `0` |
| duplicate prevention required | `true` |
| risk level | `controlled_zero_overlap_in_current_package` |

## Abort criteria

Abort any future carry-forward execution if:

- DB path is missing, repo-local, original-runtime-local, or not an existing file;
- target month is outside the approved scope;
- required ETL CSI staging evidence is unavailable;
- candidate identity fields are insufficient for duplicate prevention;
- current-package overlap is non-zero and no approved tie-breaker exists;
- duplicate source-row-hash groups would be introduced;
- execution would write a live DB, repo DB, raw workbook, generated `etl_outputs`, or model artifact;
- runtime canonical predicates or source-discovery defaults would be changed without a separate approved stage.

## What remains unproven

Stage B9.1 does not prove:

- carry-forward ETL execution;
- Bronze/Silver/Gold materialization after inclusion;
- `fact_machine_hour` deltas with carry-forward;
- duplicate source-row-hash group counts after an actual temp-only carry-forward run;
- broader month-boundary behavior beyond July to August 2025.

## Runtime behavior impact

No runtime behavior changed.
The helper is read-only planning code.
It does not change source discovery, ETL extraction, canonical predicates, DQ wiring, Streamlit behavior, model artifacts, or `app.py`.

## Tests run

Validation commands run:

```text
python3.11 -m unittest tests.test_csi_carry_forward_preflight
```

Full requested validation was run after the report and docs index update; see the final terminal reply for exact pass/fail status.

## Unsafe file scan

Unsafe file checks were run before commit; see the final terminal reply for exact results.
No DB, SQLite, raw Excel, generated `etl_outputs`, local env folder, or model artifact is intentionally staged by Stage B9.1.

## Recommended B9.2

Recommended B9.2: temp-only CSI carry-forward reconciliation rehearsal.

B9.2 should:

- copy the required runtime DB to a temp path outside Git;
- include the `235` prior-package August-canonical CSI identities in temp-only scope;
- prove raw and silver source-row-hash handling;
- prove duplicate source-row-hash groups remain zero;
- compare August raw/silver/gold output against the B8.2 baseline;
- preserve the original runtime DB unchanged;
- avoid any runtime predicate or source-discovery default change until the temp evidence is accepted.
