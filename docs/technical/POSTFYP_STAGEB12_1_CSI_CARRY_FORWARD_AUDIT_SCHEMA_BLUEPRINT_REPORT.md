# Post-FYP Stage B12.1 CSI Carry-Forward Audit Schema Blueprint Report

## Purpose

Stage B12.1 designs and validates a permanent CSI carry-forward audit/provenance schema blueprint for future adoption review.

The goal is to define how a future approved carry-forward run can record run-level evidence, candidate-level decisions, and Gold metric deltas without changing active ETL, canonical materialization, source-discovery policy, runtime predicates, Streamlit behavior, or live/shared DB state in this stage.

## Scope

This stage adds schema blueprint code, focused unit tests, this report, and documentation index/contract updates.

It does not run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation execution, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote any temp DB, retrain or promote ML artifacts, change source-discovery default policy, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, modify `app.py`, add Streamlit write controls, or create live DB mode.

## Files changed

- `core/csi_carry_forward_audit_schema.py`
- `tests/test_csi_carry_forward_audit_schema.py`
- `docs/technical/POSTFYP_STAGEB12_1_CSI_CARRY_FORWARD_AUDIT_SCHEMA_BLUEPRINT_REPORT.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Schema blueprint summary

`core/csi_carry_forward_audit_schema.py` defines non-destructive SQLite `CREATE TABLE IF NOT EXISTS` DDL for three audit/provenance tables:

- `csi_carry_forward_audit_runs`
- `csi_carry_forward_candidates`
- `csi_carry_forward_gold_deltas`

The module also provides:

- `get_carry_forward_audit_schema_statements()`
- `validate_carry_forward_audit_schema(conn)`
- `create_carry_forward_audit_schema(conn, dry_run=False)`
- `build_candidate_id(stable_identity_key, source_row_hash=None)`
- `build_audit_run_id(source_package_month, target_canonical_month, suffix=None)`

The module uses only `sqlite3` and the Python standard library. It has no pandas, Streamlit, app, ETL, materialization, or DB path dependency.

## Audit run table design

`csi_carry_forward_audit_runs` is the run-level ledger table.

It records the audit run ID, mode, source package month, target canonical month, source and target month keys, carry-forward reason, status, candidate/include/skip/block counts, raw and silver traceability counts, duplicate hash-group counts, Gold row/quantity deltas, DB scope, reviewer status, and notes.

The table is intended to prove whether a future carry-forward run was scoped, reviewed, traceable, and bounded to the approved DB mode.

## Candidate table design

`csi_carry_forward_candidates` is the candidate-decision table.

It records one row per candidate ID per audit run, including source package month, canonical event month, machine/order/material/quantity/timestamp identity, `source_row_hash`, stable identity key, decision, decision reason, existing target hash or identity evidence, inserted/matched flags, provenance source path, and raw payload reference.

The table is designed to preserve inclusion, skip, and block decisions rather than only recording final inserted rows.

## Gold delta table design

`csi_carry_forward_gold_deltas` is the metric-delta table.

It records one row per metric per audit run, including target canonical month, metric name, baseline value, reconciled value, delta value, and notes.

This keeps Gold aggregate effects explicit, including cases where `fact_machine_hour` row count remains unchanged while quantity overlays change.

## Dry-run / in-memory validation

The schema was validated through in-memory SQLite unit tests only.

`create_carry_forward_audit_schema(conn, dry_run=True)` parses and validates the DDL against an internal in-memory database and leaves the caller-provided connection untouched.

`validate_carry_forward_audit_schema(conn)` checks required tables and required columns through SQLite `PRAGMA table_info`.

## Why live DB migration is not run

Stage B12.1 is a schema blueprint and dry-run validation stage only.

Live/shared DB migration remains unapproved because promoted audit-table creation requires a separate migration plan, backup path, rollback plan, reviewer gate, DB scope declaration, and post-migration validation. No original runtime DB or repo-local DB was opened for mutation in this stage.

## Runtime behavior impact

No runtime behavior changed.

The schema module is not imported by active ETL, historical backfill, canonical materialization, Silver normalization, Streamlit, DQ runtime behavior, source discovery, or ML code paths. It does not change canonical CSI predicates and does not execute carry-forward reconciliation.

## Tests run

Required validation is run after this report and docs update. See the terminal closeout for exact pass/fail status.

## Unsafe file scan

Unsafe file scans are run before commit. See the terminal closeout for exact results.

B12.1 intends to stage only the schema module, schema tests, this report, and documentation updates.

## Out of scope

- Live/shared DB migration.
- Original runtime `manufacturing_data.db` writes.
- DB creation inside the GitHub-safe tree.
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

- The schema is not yet migrated into any live/shared runtime DB.
- Foreign-key behavior, retention policy, and reviewer workflow remain future implementation decisions.
- Future promoted migration still needs backup, rollback, and post-migration validation.
- Additional boundary months may require extra decision metadata if their overlap or hash behavior differs from the two proven cases.

## Recommended B12.2

Recommended B12.2 should be a migration preflight and reviewer workflow design stage.

It should define backup/rollback procedure, live/shared DB migration approval criteria, table-retention policy, reviewer status values, sample audit inserts against a temp DB outside Git, and abort criteria before any promoted DB schema change is attempted.
