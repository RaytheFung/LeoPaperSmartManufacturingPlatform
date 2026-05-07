# Docs Folder Guide

This is the production-readiness navigation guide for the documentation folder. Use `README.md` for launch and top-level runtime boundaries.

## Best Current Operator Docs

- `README.md` - app launch, local DB boundary, source/output folders, and deployment-readiness checks.
- `docs/LAUNCHING_TIPS.md` - safest macOS startup path for Streamlit on port `8502`.
- `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md` - controlled factory deployment pilot runbook.
- `docs/operations/FACTORY_PILOT_HANDOFF_PACK.md` - owner/reviewer handoff pack for controlled factory pilot readiness.
- `docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md` - approval checklist for future live/shared DB migration.
- `docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md` - operator/reviewer pilot-readiness sign-off template.
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` - authoritative current routed-runtime ownership map.
- `docs/technical/DATA_CONTRACTS_GUIDE.md` - source manifest, data-quality metadata, local DB, carry-forward, and claim boundaries.
- `docs/technical/TECHNICAL_OVERVIEW.md` - concise production-readiness architecture overview.
- `docs/technical/REBUILD_DOCS_INDEX.md` - full evidence ledger and Stage A/B/C report index.

## Stage B/C Technical Ledger

- Stage B reports document source-discovery governance, temp-only rehearsal evidence, carry-forward disabled scaffolding, audit workflow design, and the factory deployment migration decision gate.
- Stage C reports document production-readiness inventory, docs/navigation cleanup, and later deployment-hygiene evidence.
- Read technical reports as evidence records. They explain what changed and how it was validated; they are not operator runbooks unless explicitly labeled that way.

## Active Docs Versus Historical Evidence

Active operator/navigation docs:
- `README.md`
- `docs/DOCS_GUIDE.md`
- `docs/LAUNCHING_TIPS.md`
- `docs/operations/`
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/TECHNICAL_OVERVIEW.md`
- latest Stage C report under `docs/technical/`

Historical or evidence docs:
- `project_context.md` - historical architecture context only, not current deployment truth.
- `docs/technical/TASK*.md`, `TASK*.txt`, `TASK*.diff`, and `TASK*.csv` - task evidence, implementation history, and audit support.
- Presentation/reviewer support docs remain history unless a later stage promotes them into an operator runbook.

## Folder Intent

- `docs/technical/` remains the main in-repo technical record.
- Technical reports remain flat there on purpose so older absolute-path links inside reports do not break.
- Raw source data is kept under `source_data/`, split into `2025_jan_jun_initial/` and `2025_jul_2026_feb_collected/`.
- `etl_outputs/` is generated output, not source truth; keep only `ETL_OUTPUTS_GUIDE.md` and the placeholder under version control.
- Generated report/presentation assets should stay outside this repo unless a future task explicitly promotes them as product documentation.

## Externalized History

Older historical or academic material that was already judged safe to move lives outside the repo:
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/`

If current code and older docs disagree, trust the latest Stage C report, `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`, `docs/technical/DATA_CONTRACTS_GUIDE.md`, the live code under `app.py`, `core/`, and `modules/`, and the runtime commands in `README.md`.
