# Task 1 Repo Audit

Date: 2026-03-20

Scope:
- live repository audit only;
- no business-logic rewrite;
- no UI changes;
- one tiny import fix applied because the ETL page could not import the unified-view module from the live package layout.

## 1. Actual repo structure

```text
LeoPaperSmartManufacturingPlatform/
├── app.py
├── core/
│   ├── enhanced_etl_solution_CURRENT.py
│   ├── data_utils.py
│   ├── maintenance_integration.py
│   ├── ml_predictor.py
│   ├── ml_trainer.py
│   ├── ui_utils.py
│   ├── utils.py
│   └── etl/
│       ├── __init__.py
│       ├── extractor.py
│       ├── mapper.py
│       └── reporter.py
├── modules/
│   ├── etl_module.py
│   ├── euvg_module.py
│   ├── maintenance_module.py
│   ├── ml_module.py
│   ├── optimization_module.py
│   ├── shared_ml_components.py
│   └── unified_view_module.py
├── scripts/
│   ├── auto_ingest.py
│   ├── bootstrap_py311_and_run.sh
│   └── process_jan_to_june_2025.py
├── data/
├── 2025 DataSet(JAN to JUN)/
├── etl_outputs/
├── models/
├── docs/
├── tests/
├── manufacturing_data.db
├── requirements.txt
└── run_app.sh
```

## 2. Runtime entry points

Primary app runtime:
- `app.py` is the Streamlit shell and page router.
- `scripts/bootstrap_py311_and_run.sh` is the preferred launcher for macOS Python 3.11 on port `8502`.
- `run_app.sh` is a secondary launcher that uses `.venv`.
- `.streamlit/config.toml` pins `port = 8502` and `address = "0.0.0.0"`.

Secondary executable paths:
- `scripts/process_jan_to_june_2025.py`: bulk month-by-month ETL pipeline runner.
- `scripts/auto_ingest.py`: polling watcher that reruns ETL and optionally retrains ML.
- `core/ml_trainer.py`: standalone model trainer.
- `core/ml_predictor.py`: standalone predictor smoke path.
- `modules/unified_view_module.py`: page module can be run directly.
- `modules/ml_module.py`: page module can be run directly.

## 3. Where the real logic currently lives

ETL:
- orchestration façade: `core/enhanced_etl_solution_CURRENT.py`
- raw source loading: `core/etl/extractor.py`
- machine-pattern mapping: `core/etl/mapper.py`
- ETL reporting/export: `core/etl/reporter.py`
- ETL UI, SQLite persistence, upload flow: `modules/etl_module.py`

Unified view:
- in-memory hourly construction logic: `modules/euvg_module.py`
- SQLite-backed unified-view processing and UI: `modules/unified_view_module.py`
- app-level June-only in-memory load path: `app.py`

ML:
- training pipeline: `core/ml_trainer.py`
- prediction and fallback simulation: `core/ml_predictor.py`
- ML UI: `modules/ml_module.py`
- shared prediction/insight widgets: `modules/shared_ml_components.py`
- optimization module also consumes ML prediction: `modules/optimization_module.py`

Maintenance:
- maintenance ingestion/integration logic: `core/maintenance_integration.py`
- maintenance UI and upload flow: `modules/maintenance_module.py`

App orchestration:
- page routing: `app.py`
- startup scripts: `scripts/bootstrap_py311_and_run.sh`, `run_app.sh`

Persistence:
- central live store is `manufacturing_data.db`
- current database contains ETL, unified-view, maintenance, and ML tables already populated

## 4. Duplicate or conflicting code paths

### 4.1 Unified-view truth is split across multiple implementations
- `app.py` builds an in-memory unified dataset from hardcoded June files in `data/`.
- `modules/unified_view_module.py` builds and stores `unified_view` in SQLite.
- `modules/euvg_module.py` contains another unified-hourly implementation and feature-engineering path.

Result:
- there is no single authoritative unified-data path yet.

### 4.2 Formal analytics can fall back to synthetic/demo data
- `modules/unified_view_module.py` generates synthetic records when stored ETL data is unavailable.
- `_process_from_stored_etl_data()` is effectively a stub that reports success with `records_created = 0`.
- `modules/ml_module.py`, `modules/optimization_module.py`, `modules/shared_ml_components.py`, and `core/ml_predictor.py` all contain demo/fallback/simulated paths.

Result:
- current user-facing outputs are not safe to treat as formal canonical analysis.

### 4.3 ETL page had a broken live import path
- `modules/etl_module.py` attempted `from unified_view_module import auto_process_after_etl`.
- In the live repo, the file lives at `modules/unified_view_module.py`, not repo root.

Result:
- ETL could succeed while auto-triggered unified-view creation failed.

Fix applied:
- changed the import to `from modules.unified_view_module import auto_process_after_etl`.

### 4.4 App shell contains dead or legacy paths
- `app.py` routes ETL to `modules.etl_module.render_etl_page`, but also still contains unused local helpers like `show_etl_page()` and `show_overview_page()`.

Result:
- there is route drift inside the main shell.

### 4.5 Maintenance schema and runtime dependencies are inconsistent
- `core/maintenance_integration.py` declares one `maintenance_summary` schema.
- `modules/maintenance_module.py` and `modules/etl_module.py` overwrite `maintenance_summary` and `maintenance_ml_features` using `to_sql(..., if_exists='replace')`.
- `modules/maintenance_module.py` queries `machine_maintenance_history`, but no repo code creates that view.
- The live database does contain `machine_maintenance_history`, so part of maintenance behavior depends on pre-existing DB state, not reproducible repo code.

Result:
- maintenance is coupled to schema drift and hidden database bootstrap state.

### 4.6 Script data paths do not match the live dataset folders
- `scripts/process_jan_to_june_2025.py` expects:
  - `Energy Usage 1hr Interval(JAN to JUN)`
  - `CSI Monthly(JAN to JUN)`
  - `MES Monthly(JAN to JUN)`
- the live repo folders are:
  - `Energy Usage 1hr Interval`
  - `CSI Monthly`
  - `MES Monthly`

`scripts/auto_ingest.py` repeats the same stale folder assumptions.

Result:
- bulk ETL/watcher scripts are high-risk and may not work against the live dataset layout without path correction.

### 4.7 Path handling is inconsistent across modules
- many modules hardcode `manufacturing_data.db`;
- several modules mutate `sys.path` at runtime;
- imports mix package-qualified and ad hoc forms.

Result:
- execution behavior depends too much on working directory and import context.

## 5. Minimal path-normalization plan

Do this before any broader rebuild:

1. Standardize imports.
- Use package-qualified imports only: `core.*` and `modules.*`.
- Remove ad hoc `sys.path.append(...)` once imports are stable.
- Keep this scoped to import/path hygiene only.

2. Centralize path constants.
- Create one small runtime-path helper for:
  - repo root
  - database path
  - staged `data/`
  - raw dataset root
  - model directory
  - `etl_outputs/`

3. Normalize dataset root names.
- Add one canonical resolver for the live dataset folders.
- Support current live names first.
- If legacy names must be preserved, resolve both explicitly instead of hardcoding only one variant.

4. Mark data-layer status explicitly.
- Treat `modules/unified_view_module.py` and `modules/euvg_module.py` as `legacy_demo` data paths until Bronze/Silver/Gold replacement is ready.
- Do not delete them yet; isolate them.

5. Stop schema replacement drift.
- Do not keep using `to_sql(..., if_exists='replace')` on shared runtime tables once canonical rebuild starts.
- First define the intended schema contract; then write append/upsert logic to that contract.

## 6. High-risk modules to touch first

Priority 1:
- `modules/unified_view_module.py`
  - synthetic fallback in formal path
  - stubbed real-data path
  - central downstream dependency for ML/optimization/maintenance

- `modules/euvg_module.py`
  - competing unified-view implementation
  - embeds business rules that will conflict with canonical rebuild work

- `core/etl/mapper.py`
  - current machine normalization heuristics live here
  - Phase 1 alias-registry work must either replace or wrap this logic carefully

Priority 2:
- `modules/etl_module.py`
  - ETL UI is the current write path into SQLite
  - owns cross-module auto-trigger behavior

- `core/maintenance_integration.py`
  - current maintenance interpretation and schema definitions
  - mixes asset normalization, metrics, and prediction scaffolding

- `modules/maintenance_module.py`
  - depends on DB objects not created by code
  - overwrites shared tables

Priority 3:
- `app.py`
  - mixes page routing with a hardcoded June-only in-memory path and legacy helpers

- `scripts/process_jan_to_june_2025.py`
- `scripts/auto_ingest.py`
  - currently use stale dataset folder names

- `core/ml_trainer.py`
- `core/ml_predictor.py`
- `modules/ml_module.py`
- `modules/optimization_module.py`
- `modules/shared_ml_components.py`
  - all depend on `unified_view`
  - several still expose demo/fallback behavior

## 7. Live database observations

Current live SQLite objects show this repo is already operating from one shared DB:
- `etl_runs`: 6
- `three_way_matches`: 62
- `etl_energy_data`: 564400
- `etl_csi_data`: 124207
- `etl_mes_data`: 115902
- `unified_view`: 195374
- `maintenance_records`: 14378
- `maintenance_summary`: 990
- `maintenance_ml_features`: 0
- `ml_models`: 13

Observed `unified_view` month coverage:
- January 2025
- February 2025
- March 2025
- April 2025
- May 2025
- June 2025

Observed `maintenance_records` month coverage extends beyond Jan-Jun 2025 and includes 2024 plus Jul/Aug 2025.

## 8. Recommended next step

Proceed to Phase 1 only after treating this audit as the source of truth:
- keep app shell intact;
- do not broaden changes yet;
- start canonical rebuild with machine alias registry and path normalization;
- do not let `unified_view` synthetic/demo paths become the formal backbone.
