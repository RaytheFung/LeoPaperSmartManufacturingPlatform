# Post-FYP Stage B0 Database Boundary and Safe Worktree Report

## Purpose

Stage B0 closed the immediate Git/database boundary risk discovered in Stage A and established a GitHub-safe working tree for post-FYP product hardening.

## Scope

Stage B0 covered local database untracking and safe worktree setup only.
It did not run SQL diagnostics, ETL, canonical materialization, model retraining, artifact promotion, or runtime behavior changes.

## Stage B0 summary

Stage B0 applied `git rm --cached manufacturing_data.db` in the original runtime repo only.
The database remained on disk for local runtime use.
No SQL, ETL, materialization, retraining, or artifact promotion was performed.
The result was staged database untracking only.

## Stage B0.1 summary

Stage B0.1 created local commit `829da16 Stop tracking local runtime database in original runtime repo`.
`manufacturing_data.db` remained on disk at about `6.7 GB`.
`git ls-files manufacturing_data.db` returned no output after untracking.
The `.gitignore` `*.db` rule applied to the database file.
No push was performed because the original runtime repo had no remote configured and local history still contained historical DB objects.

## Stage B0.2 summary

Stage B0.2 created the GitHub-safe working tree:

`/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_github_safe`

The safe tree remote is:

`https://github.com/RaytheFung/LeoPaperSmartManufacturingPlatform.git`

The safe tree baseline HEAD was `8878485`.
The safe tree had no `manufacturing_data.db` and no DB history for that file.
Branch `postfyp/stage-b0-safe-worktree` was pushed.
No commit was created because no file changes were needed in the safe tree.

## Why original runtime repo must not be pushed

The original runtime repo remains a local runtime and DB-backed workspace.
It must not be pushed as-is because historical database objects and local runtime state were not cleaned from its history.
Stage B0.1 only stopped tracking the current database file; it did not rewrite history or remove old database blobs.

## Safe GitHub working tree contract

All post-FYP GitHub work after Stage B0.2 must use:

`/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_github_safe`

The original runtime repo remains available for local app/runtime use, but it is not the GitHub publication surface.

## DB boundary

`manufacturing_data.db` is local-only runtime state.
It must not be staged, committed, copied into the safe tree, or pushed.
The safe tree should also avoid `*.sqlite` and `*.sqlite3` files.

## Validation evidence

- `git ls-files manufacturing_data.db` returned no output after Stage B0.1.
- `.gitignore` covered `manufacturing_data.db` through the `*.db` rule.
- The Stage B0.2 safe tree had no `manufacturing_data.db`.
- The safe tree had no DB history for that file.

## Remaining risks

- The original runtime repo still must not be pushed as-is.
- The safe tree contract depends on continuing to run future GitHub work from the safe tree.
- Historical DB cleanup was not attempted and should not be implied.

## Future workflow rule

Use the GitHub-safe tree for branches, commits, and pushes.
Use the original runtime repo only for local runtime operations that require the local database, unless a later task explicitly changes that boundary.
