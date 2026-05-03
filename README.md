# Smart Manufacturing ETL + ML Platform

Streamlit app for monthly manufacturing ETL, unified-view generation, maintenance analysis, ML-assisted efficiency prediction, and optimization insights.

## Current Working Set

Primary runtime files:
- `app.py` - Streamlit entry point
- `modules/` - page modules used by the app
- `core/` - ETL, ML, maintenance, and UI logic
- `CURRENT_REBUILD_STATUS.md` - current rebuild ledger and recommended next step
- `manufacturing_data.db` - local SQLite data store used by the app; kept out of GitHub because the active DB is too large for normal Git/Git LFS hosting
- `models/` - trained model and preprocessing bundle
- `data/` - current sample input files used by the lightweight June demo path
- `source_data/2025_jan_jun_initial/` - raw historical Jan-Jun 2025 source files used by batch ETL
- `source_data/2025_jul_2026_feb_collected/` - raw Jul 2025-Feb 2026 extension source package, with grouped energy files through Mar 2026
- `etl_outputs/` - generated ETL reports, mappings, summaries, and cache files; ignored except for its guide/placeholder
- `scripts/bootstrap_py311_and_run.sh` - recommended launcher on macOS
- `scripts/process_jan_to_june_2025.py` - batch ETL rebuild for Jan-Jun 2025
- `project_context.md` - current architecture/status note

Generated or local-only files:
- `.conda311/`, `.miniforge/`, `.venv/` - local Python environments
- `.streamlit/server.log`, `.streamlit/server.pid` - runtime files
- `manufacturing_data.db`, `*.db`, `*.sqlite*` - local runtime database artifacts; rebuild or transfer separately when a full runtime snapshot is needed
- generated `etl_outputs/*` files - recreated by ETL scripts when needed
- local diagnostic/output holding folder: `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/local_runtime_clutter/`
  - `artifacts/` - Task-run SQLite backups, working copies, probes, and diagnostics moved outside the repo
  - `backups/` - historical SQLite rollback/backup files moved outside the repo
- `__pycache__/`, `.DS_Store`, `~$*.xlsx` - disposable noise

Historical or project-artifact docs have been moved outside the repo into:
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/`

## Run The App

Recommended on macOS:

```bash
bash scripts/bootstrap_py311_and_run.sh
```

Then open:

```text
http://localhost:8502
```

Alternative if the local Python 3.11 env already exists:

```bash
.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true
```

Stop the app:

```bash
pkill -f "streamlit run app.py"
```

## Verify Core Workflows

Rebuild Jan-Jun ETL artifacts:

```bash
python3 scripts/process_jan_to_june_2025.py
```

Retrain the model:

```bash
python3 core/ml_trainer.py
```

Smoke-test inference:

```bash
python3 core/ml_predictor.py
```

Check unified-view coverage:

```bash
sqlite3 manufacturing_data.db "SELECT month_year, COUNT(*), AVG(kwh_per_unit) FROM unified_view GROUP BY month_year;"
```

## Tests

Automated unit tests currently worth keeping in the main test path:

```bash
python3 -m unittest tests.test_etl_modules tests.test_euvg_stage3
```

Manual verification scripts live under `tests/manual_checks/`.

## Notes

- `project_context.md` is the best high-level description of the current system.
- `docs/DOCS_GUIDE.md` is the docs-folder guide only; use it when you want the shortest path to current documentation.
- `docs/technical/REBUILD_DOCS_INDEX.md` groups rebuild docs into static design docs, task reports, and historical handoff docs.
- Folder-specific guides use explicit names to stay readable in the file explorer:
  - `source_data/SOURCE_DATA_GUIDE.md`
  - `source_data/2025_jan_jun_initial/INITIAL_SOURCE_SCOPE.md`
  - `source_data/2025_jul_2026_feb_collected/EXTENDED_SOURCE_SCOPE.md`
  - `etl_outputs/ETL_OUTPUTS_GUIDE.md`
  - `tests/TESTS_GUIDE.md`
- `run_app.sh` exists, but the Python 3.11 bootstrap path is the safer default on macOS.
