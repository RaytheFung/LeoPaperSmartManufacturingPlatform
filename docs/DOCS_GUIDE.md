# Docs Folder Guide

This file is not the main repo README.

Use:
- `README.md` for app/runtime entry information
- `CURRENT_REBUILD_STATUS.md` for the live rebuild ledger
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` for the current authoritative routed-runtime ownership map
- `project_context.md` for older high-level architecture context only

## Best Current Docs

- `docs/LAUNCHING_TIPS.md` - safest app startup path on macOS
- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` - authoritative current routed-runtime ownership map
- `docs/technical/TECHNICAL_OVERVIEW.md` - concise architecture map
- `docs/technical/REBUILD_DOCS_INDEX.md` - full rebuild-doc reading order
- `docs/UI_DESIGN_STANDARDS.md` and `docs/Design_Language_Guidelines.md` - UI conventions

## Folder Intent

- `docs/technical/` stays as the main in-repo technical record.
- Technical reports remain flat there on purpose so older absolute-path links do not break.
- Raw source data is kept under `source_data/`, split into `2025_jan_jun_initial/` and `2025_jul_2026_feb_collected/`.
- `etl_outputs/` is generated output, not source truth; keep only `ETL_OUTPUTS_GUIDE.md` and the placeholder under version control.
- Submitted report and presentation-build workspaces are no longer part of the active product repo.
- Generated report/presentation assets should stay outside this repo unless a future task explicitly promotes them as product documentation.

## Externalized History

Older historical or academic material that was already judged safe to move lives outside the repo:
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/`

If current code and older docs disagree, trust `CURRENT_REBUILD_STATUS.md`, `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`, the live code under `app.py`, `core/`, and `modules/`, and the runtime commands in `README.md`.
