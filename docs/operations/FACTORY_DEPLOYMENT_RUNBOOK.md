# Factory Deployment Runbook

## Purpose

This runbook gives operators and reviewers a controlled path for factory deployment pilot readiness checks.

It describes how to select a reviewed branch, launch the Streamlit app safely, preserve local DB and artifact boundaries, run smoke checks, and escalate rollback concerns before any production deployment claim is made.

## Scope

This runbook applies to the LeoPaper Smart Manufacturing Platform repository in a controlled pilot-readiness setting.

It does not approve live/shared DB migration, promoted DB writes, runtime CSI carry-forward adoption, ETL execution, historical backfill, canonical materialization, ML artifact promotion, or production launch completion.

## Deployment objective

The objective is Factory Production Deployment readiness with production-grade safety gates.

The current branch line supports controlled factory deployment pilot readiness only. Production deployment is not complete until live/shared DB migration, backup/restore proof, operational owner acceptance, monitoring, and rollback gates are approved.

## Environment prerequisites

- Use a reviewed branch from the GitHub-safe tree.
- Use Python 3.11 for validation and Streamlit launch.
- Keep local runtime state out of Git.
- Confirm no DB, local environment, upload, raw source, model promotion, or generated-output artifact is staged.
- Use `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` for routed-runtime ownership.
- Use `docs/technical/DATA_CONTRACTS_GUIDE.md` for source, data-quality metadata, local DB, and carry-forward boundaries.

## Branch selection rule

Use only a reviewed branch created for the current stage or a later approved deployment-readiness branch.

Do not run factory pilot checks from `main` unless a separate approval explicitly selects it. Do not force-push, rewrite, or bypass review history.

## Python / Streamlit launch procedure

Recommended launch path on macOS:

```bash
bash scripts/bootstrap_py311_and_run.sh
```

Alternative when the local Python 3.11 environment already exists:

```bash
.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true
```

For isolated app-smoke evidence, copy the required app code to `/tmp` and run Streamlit from the `/tmp` workspace, not from the GitHub-safe tree.

## Runtime mode choices

Supported runtime modes:

- `standard`: normal local runtime shell; operational controls may be visible.
- `demo_readonly`: defended-core read-only shell; write-capable controls are hidden or disabled and the Experimental Intelligence Lab route is hidden.
- `pilot_review`: defended-core write controls stay hidden while pilot-review experimental surfaces remain available.

Use `demo_readonly` for conservative smoke checks unless the pilot-review plan explicitly requires `pilot_review`.

## Startup procedure

1. Confirm the selected branch.
2. Run `python3.11 scripts/check_factory_deployment_readiness.py`.
3. Run the lightweight validation matrix listed in `README.md`.
4. Confirm no DB or local environment artifacts are present in the GitHub-safe tree.
5. Launch Streamlit with the selected runtime mode.
6. Open `http://localhost:8502`.
7. Confirm the visible route set matches the selected runtime mode.
8. Do not click upload, ETL, backfill, materialization, migration, retraining, or write controls during smoke checks.

## Stop procedure

Stop Streamlit with:

```bash
pkill -f "streamlit run app.py"
```

Then confirm the port is closed:

```bash
lsof -n -P -iTCP:8502 -sTCP:LISTEN || true
```

## DB local-only boundary

`manufacturing_data.db` is local runtime state. It must never be staged, committed, pushed, or copied into the GitHub-safe tree.

Any promoted live/shared DB migration requires the separate migration gate checklist. A local DB may support review and rehearsal only; it is not the final factory deployment state.

## Source data boundary

`source_data/` is source truth for accepted historical packages. Raw workbook changes must not be staged unless a future source-data governance task explicitly approves them.

March 2026 remains blocked/out of canonical scope unless a later approved stage reopens that boundary.

## Generated output boundary

`etl_outputs/` is generated output. Keep only `.gitkeep` and `ETL_OUTPUTS_GUIDE.md` under version control.

Generated reports, mappings, cache files, and summaries must be recreated by controlled ETL runs and must not be staged as product state.

## Model artifact boundary

The active model/preprocessor artifacts and provenance files remain guarded runtime artifacts.

Do not retrain, replace, promote, or stage model artifacts without a separate model-promotion gate.

## Carry-forward disabled-by-default boundary

CSI carry-forward remains disabled-by-default. Current carry-forward code is governance/preflight scaffolding, not active ETL, materialization, Streamlit, DQ, ML, or app behavior.

Do not present carry-forward as active runtime behavior unless a later adoption gate approves runtime wiring.

## Live/shared DB migration gate

Live/shared DB migration is gated, not abandoned.

Before any promoted DB write, the migration gate checklist must be completed with backup, checksum, dry-run SQL diff, row-count baseline, duplicate source-hash baseline, traceability, Gold delta review, reviewer acceptance, app/runtime smoke, rollback/restore proof, and abort criteria.

## Operational owner responsibilities

Operational owners must:

- confirm the selected branch and commit;
- confirm the runtime mode;
- review the Stage C3 app-smoke report and latest Stage C report;
- confirm local DB and no-DB-in-Git boundaries;
- approve or reject pilot-readiness risks;
- maintain rollback and escalation contacts;
- keep evidence of validation commands and outcomes.

## Smoke test checklist

- `python3.11 scripts/check_factory_deployment_readiness.py` returns success.
- Compile and unit validation pass.
- No DB files exist in the GitHub-safe tree.
- No local env or upload folders exist in the GitHub-safe tree.
- `manufacturing_data.db` is not tracked.
- Streamlit launches on the selected port.
- HTTP bootstrap returns success.
- Route visibility matches the selected runtime mode.
- Logs show no immediate traceback.
- Process stops cleanly.

## Incident / rollback escalation

Escalate immediately if:

- a DB file appears in the GitHub-safe tree;
- a local runtime DB is modified outside an approved plan;
- source workbooks, model artifacts, or generated outputs are staged unexpectedly;
- Streamlit logs show tracebacks during launch;
- route visibility does not match runtime-mode expectations;
- any migration, ETL, materialization, backfill, retraining, or carry-forward execution is triggered accidentally.

Rollback decisions for DB state must follow the migration gate checklist and require backup/restore evidence.

## What operators must not do

- Do not run ETL during C4 readiness checks.
- Do not run historical backfill.
- Do not run canonical materialization.
- Do not execute carry-forward reconciliation.
- Do not execute live/shared DB migration.
- Do not write the original runtime DB.
- Do not stage DB files, raw Excel files, generated `etl_outputs`, or model artifacts.
- Do not add production claims before migration and owner gates pass.

## Known limitations before production launch

- C3 proved Streamlit bootstrap smoke, not full production route execution.
- Live/shared DB migration has not been executed.
- Live rollback has not been proven.
- Runtime CSI carry-forward adoption remains unapproved.
- Production monitoring, support ownership, access policy, and incident response remain future work.
