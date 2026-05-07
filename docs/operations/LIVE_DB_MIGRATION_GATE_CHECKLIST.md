# Live DB Migration Gate Checklist

## Purpose

This checklist defines the approval evidence required before any live/shared DB migration or promoted DB write is considered.

## Scope

This is an approval checklist only. It does not execute migration, write a DB, promote a temp DB, run ETL, run materialization, or approve runtime carry-forward adoption.

## When this checklist is required

Use this checklist before:

- creating audit tables in promoted runtime state;
- replacing or modifying a live/shared runtime DB;
- promoting a temp DB;
- applying carry-forward audit records to a promoted DB;
- changing canonical production storage through a migration.

## Pre-migration backup requirements

- Identify the exact DB path.
- Record file size and modified time.
- Create a backup before any proposed write.
- Store backup outside Git.
- Confirm backup readability before migration.
- Record operator and reviewer names.

## Backup checksum requirements

- Compute SHA-256 for the original DB.
- Compute SHA-256 for the backup copy.
- Verify original and backup checksums match before migration.
- Preserve checksum output with the approval record.

## Dry-run SQL diff requirements

- Prepare migration SQL in reviewable form.
- Run dry-run or temp-only rehearsal first.
- Record the exact DDL and DML categories.
- Record tables created, altered, inserted into, updated, or deleted from.
- Confirm no unintended table scope is touched.

## Row-count baseline requirements

- Capture pre-migration row counts for every table in the proposed write scope.
- Capture relevant post-rehearsal row counts in a temp DB.
- Explain every expected delta.
- Block migration if an unexplained delta exists.

## Duplicate source-hash baseline requirements

- Capture duplicate `source_row_hash` groups for all touched source-derived tables that contain the column.
- Confirm the proposed migration does not create unexpected duplicate groups.
- Preserve before/after duplicate evidence in the approval record.

## Carry-forward candidate traceability requirements

If carry-forward is involved:

- identify source package month and target canonical month;
- prove candidate identities are traceable;
- classify include, skip, and block candidates;
- prove duplicate-prevention behavior;
- prove every included candidate has audit provenance;
- preserve reviewer decision status for each candidate class.

## Gold delta review requirements

- Record expected Gold metric deltas before migration.
- Compare temp-only rehearsal deltas against expected deltas.
- Require reviewer explanation for every material metric movement.
- Block migration if Gold deltas are unexplained or outside approved scope.

## Reviewer acceptance requirements

Reviewer acceptance must include:

- selected branch and commit;
- DB path and backup path;
- checksum proof;
- dry-run evidence;
- row-count baseline;
- duplicate baseline;
- Gold delta review;
- rollback procedure;
- app/runtime smoke plan;
- explicit approval or rejection.

## App/runtime smoke requirements

Before promoted DB write:

- run route/runtime unit tests;
- run source-discovery comparison diagnostics;
- run app bootstrap smoke from a safe workspace;
- confirm visible routes match runtime mode;
- confirm no immediate traceback;
- confirm process can stop cleanly.

After promoted DB write, rerun the same smoke matrix before declaring pilot readiness.

## Rollback / restore requirements

- Restore backup into a separate validation path first.
- Verify restored checksum or expected identity.
- Verify row counts on the restored copy.
- Define the exact restore command before migration.
- Assign a rollback owner.
- Define maximum acceptable restore time.

## Abort gates

Abort immediately if:

- backup is missing or checksum mismatches;
- target DB path is ambiguous;
- migration SQL touches unapproved tables;
- duplicate baseline is unexplained;
- Gold deltas are unexplained;
- app smoke fails;
- reviewer acceptance is missing;
- DB files appear in Git;
- branch is not the approved migration branch;
- rollback cannot be executed.

## No-main / no-force-push branch rule

Do not run migration from `main` unless a separate approval explicitly selects it.

Never force-push migration evidence branches. Never bypass review history.

## Promotion approval record

The approval record must state:

- branch and commit SHA;
- approver names;
- DB path;
- backup path;
- checksum evidence;
- migration SQL reference;
- dry-run evidence;
- row-count and duplicate-hash baselines;
- Gold delta review;
- app/runtime smoke result;
- rollback/restore evidence;
- final decision.

## Explicit non-goals

This checklist does not:

- approve live/shared DB migration by itself;
- execute SQL;
- run ETL;
- run historical backfill;
- run canonical materialization;
- wire carry-forward into runtime;
- change source-discovery policy;
- change canonical predicates;
- promote model artifacts;
- declare production deployment complete.
