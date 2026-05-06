# Post-FYP Stage B12.2 CSI Carry-Forward Audit Workflow Preflight Report

## Purpose

Stage B12.2 designs and validates the CSI carry-forward audit workflow around the B12.1 audit/provenance schema blueprint.

The goal is to define reviewer statuses, retention policy, sample audit inserts, migration preflight checklist, abort gates, and backup/rollback requirements before any live/shared DB migration is considered.

## Scope

This stage adds workflow helper code, focused unit tests, this technical report, and documentation index/contract updates.

It does not run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation execution, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, execute live DB migration, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, modify `app.py`, add Streamlit write controls, or create live DB mode.

## Files changed

- `core/csi_carry_forward_audit_workflow.py`
- `tests/test_csi_carry_forward_audit_workflow.py`
- `docs/technical/POSTFYP_STAGEB12_2_CSI_CARRY_FORWARD_AUDIT_WORKFLOW_PREFLIGHT_REPORT.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Audit workflow helper summary

`core/csi_carry_forward_audit_workflow.py` provides pure helper functions for the B12.1 schema:

- reviewer status values and validation;
- audit retention policy;
- sample audit run, candidate, and Gold delta payload builders;
- insert helpers for caller-supplied SQLite connections;
- workflow count validation;
- migration preflight checklist;
- live migration abort gates;
- backup and rollback requirements.

The module uses only `sqlite3`, JSON, regex, and the Python standard library. It has no pandas, Streamlit, app, ETL, materialization, file-write, or live DB path dependency.

## Reviewer status model

Allowed reviewer statuses are:

| Status | Meaning |
| --- | --- |
| `draft` | Audit evidence is still being prepared. |
| `pending_review` | Audit evidence is ready for reviewer inspection. |
| `accepted` | Reviewer accepted the audit evidence for the scoped decision. |
| `rejected` | Reviewer rejected the audit evidence. |
| `superseded` | A later reviewed audit record replaces this record. |
| `rollback_required` | Reviewer requires rollback or restoration action before further promotion. |

Unknown statuses are rejected by `validate_reviewer_status()`.

## Retention policy

The helper returns a documentation-level policy:

- keep audit run records permanently unless explicitly archived through a reviewed governance step;
- do not delete candidate-level provenance while related canonical rows exist;
- supersede rather than mutate accepted records;
- do not perform automatic cleanup of audit evidence.

This policy is not wired into runtime cleanup behavior.

## Sample audit insert validation

The B12.2 test creates the B12.1 schema in an in-memory SQLite database, inserts one sample audit run, two sample candidate rows, and one sample Gold delta row.

`validate_audit_workflow_counts()` confirms the run-level candidate/include/skip/block counts match the candidate table and that the Gold delta is linked to the same audit run.

No DB file is created in the GitHub-safe tree.

## Migration preflight checklist

The migration checklist requires:

- DB backup path;
- backup checksum;
- dry-run SQL diff;
- row-count baseline;
- duplicate hash baseline;
- rollback script or procedure;
- reviewer approval;
- app/runtime smoke;
- no-main/no-force-push branch rule.

The checklist is structured output only. It does not execute migration SQL.

## Abort gates

The live migration abort gates include:

- missing backup;
- failed checksum;
- duplicate source hash groups;
- unresolved candidate decisions;
- unexpected Gold deltas;
- app smoke failure;
- unsafe DB path;
- reviewer status not accepted;
- migration touches tables outside the reviewed plan.

These gates remain preflight policy helpers only.

## Backup / rollback requirements

The backup and rollback requirements state that future promoted migration work must:

- copy the DB before migration and keep the backup outside Git;
- record and verify a checksum for the pre-migration backup;
- document the restore procedure before applying migration SQL;
- define row-count and schema validation after rollback;
- avoid temp DB promotion without a separate approval gate.

## Why live DB migration is not run

Stage B12.2 is an audit workflow and migration preflight design stage only.

Live/shared DB migration remains unapproved because it requires a separate prompt and approval gate after backup path, checksum, dry-run SQL diff, reviewer acceptance, rollback procedure, and runtime smoke criteria are accepted. No original runtime DB or repo-local DB was opened for mutation in this stage.

## Runtime behavior impact

No runtime behavior changed.

The workflow module is not imported by active ETL, historical backfill, canonical materialization, Silver normalization, Streamlit, source discovery, DQ runtime behavior, or ML code paths. It does not change CSI canonical predicates and does not execute carry-forward reconciliation.

## Tests run

Required validation is run after this report and docs update. See the terminal closeout for exact pass/fail status.

## Unsafe file scan

Unsafe file scans are run before commit. See the terminal closeout for exact results.

B12.2 intends to stage only the workflow module, workflow tests, this report, and documentation updates.

## Out of scope

- Live/shared DB migration.
- Live migration SQL execution.
- Original runtime `manufacturing_data.db` writes.
- DB creation inside the GitHub-safe tree.
- Temp DB promotion.
- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Carry-forward reconciliation execution.
- Runtime carry-forward wiring.
- DQ runtime wiring.
- Streamlit write controls.
- `app.py` changes.
- Source-discovery default changes.
- Runtime canonical predicate changes.
- ML retraining or artifact promotion.
- Raw Excel staging.
- Generated `etl_outputs` staging.

## Remaining risks

- The audit workflow helper is not active runtime behavior.
- Sample inserts are in-memory only and do not prove live/shared DB migration safety.
- Backup, restore, checksum, and app smoke commands are still future implementation details.
- Reviewer workflow ownership and retention/archive operations remain future governance decisions.

## Recommended B12.3

Recommended B12.3 should be a temp-only audit workflow rehearsal.

It should create a temp DB outside Git, apply the B12.1 schema to that temp DB, insert representative audit records for a proven carry-forward case, validate backup/checksum/rollback rehearsal evidence, and still stop before any live/shared DB migration.
