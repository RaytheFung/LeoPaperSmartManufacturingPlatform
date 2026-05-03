# Task12A Demo-Safe Read-Only Mode Report

## 1. accepted baseline used

- Task11 was treated as accepted and authoritative for the defended runtime ownership map.
- The approved routed shell remained:
  - `🔄 ETL Pipeline`
  - `📊 Canonical Operations Overview`
  - `⚡ Energy Analysis`
  - `🎯 Operational Decision Support`
  - `🤖 Efficiency Prediction & Governance`
  - `🔧 Maintenance`
  - `🧪 Experimental Intelligence Lab`
- The next-stage direction was taken from `TASK8_FUTURE_UPGRADE_ROADMAP.md` Layer 1, where demo-safe read-only mode is explicitly listed as immediate post-demo hardening/productization.
- Active artifacts remained the accepted Task 4L bundle only:
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. exact risky/write-capable surfaces found

- `🔄 ETL Pipeline`
  - upload file controls in `render_upload_section(...)`
  - month-write trigger `🚀 Process {month_year}`
  - post-run `🔄 Process New Month`
  - historical-run mutation controls in `render_historical_runs(...)`
    - bulk select
    - reset order
    - delete selected
    - per-row up/down/delete
  - ETL page constructor path was also risky because `ETLPipelineModule()` created `BronzeRawStore()` and schema-init paths on page load
- `🤖 Efficiency Prediction & Governance`
  - retraining action `Retrain from canonical Gold`
  - that action can refresh candidate artifacts and potentially active artifact state depending on promotion decision
- `🔧 Maintenance`
  - maintenance upload file control `Choose Maintenance Excel File`
  - write trigger `Process Maintenance Data`
  - replace/append upload modes
  - maintenance write path to `maintenance_records`, `maintenance_summary`, and `maintenance_ml_features`
- inspected but not gated further:
  - `📊 Canonical Operations Overview`: read-only analytics only
  - `⚡ Energy Analysis`: read-only analytics only
  - `🎯 Operational Decision Support`: read-only analytics only
  - `🧪 Experimental Intelligence Lab`: already read-only experimental bonus route; manual queue editing stays in-memory only

## 3. runtime-mode design chosen and why

- added one small central helper: `core/runtime_mode.py`
- supported modes:
  - `standard`
  - `demo_readonly`
- resolution order:
  1. `st.session_state["runtime_mode"]` if present
  2. query param `runtime_mode` / `mode` if present
  3. environment variable `SMART_MFG_RUNTIME_MODE`
  4. fallback `standard`

Why this design was chosen:

- small and explicit
- no auth or deployment system required
- easy to drive in demos and AppTests
- centralizes mode normalization instead of scattering conditionals across pages

## 4. exact gating changes by routed page

### top-level shell

- `app.py` now resolves runtime mode once and renders a visible runtime-mode banner near the top of the shell
- sidebar now also shows the current raw runtime-mode value

### `🔄 ETL Pipeline`

- `render_etl_page(runtime_mode=...)` now detects `demo_readonly`
- in `demo_readonly`:
  - upload/process/backfill section is replaced by a warning/caption gate
  - historical-run mutation controls are hidden
  - latest snapshot and historical provenance remain available
- `ETLPipelineModule` now accepts `initialize_schema=False`
- in `demo_readonly`, the ETL page avoids the operational constructor path that would otherwise instantiate `BronzeRawStore()` and schema-init logic on page load

### `🤖 Efficiency Prediction & Governance`

- `render_ml_module(runtime_mode=...)` now shows an explicit read-only info message in `demo_readonly`
- `_render_training_controls(...)` now keeps artifact status/provenance visible but hides the retraining button entirely in `demo_readonly`
- prediction workflow, review queue, Scenario Lab, and reference/audit surfaces remain unchanged

### `🔧 Maintenance`

- `render_maintenance_page(runtime_mode=...)` now shows an explicit read-only info message in `demo_readonly`
- status banner wording now avoids telling demo users to upload data when no maintenance rows exist
- in `demo_readonly`:
  - `Admin / Details` keeps browse-only behavior
  - upload/integration controls are hidden
  - no maintenance file uploader or `Process Maintenance Data` button is shown
- evidence, machine lookup, supporting visuals, legacy/admin reference view, and browse surface remain available

### untouched routed pages

- `📊 Canonical Operations Overview`: unchanged
- `⚡ Energy Analysis`: unchanged
- `🎯 Operational Decision Support`: unchanged
- `🧪 Experimental Intelligence Lab`: unchanged because it was already read-only by contract

## 5. exact files changed

- `app.py`
- `modules/etl_module.py`
- `modules/ml_module.py`
- `modules/maintenance_module.py`
- `core/ui_utils.py`
- `core/runtime_mode.py`
- `tests/test_runtime_mode.py`
- `tests/test_task12a_demo_readonly_mode.py`
- `CURRENT_REBUILD_STATUS.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`
- `docs/technical/TASK12A_DEMO_SAFE_READ_ONLY_MODE_REPORT.md`

## 6. validation / smoke summary

- compile:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile app.py modules/etl_module.py modules/ml_module.py modules/maintenance_module.py core/ui_utils.py core/runtime_mode.py tests/test_runtime_mode.py tests/test_task12a_demo_readonly_mode.py`
- unit tests:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_runtime_mode`
  - result: `3` tests passed
- AppTest smoke:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_task12a_demo_readonly_mode`
  - result: `2` AppTest smokes passed

AppTest evidence proved:

- read-only mode banner is visible
- ETL write-capable controls are hidden in `demo_readonly`
- ML retraining action is hidden in `demo_readonly`
- Maintenance upload/integration controls are hidden in `demo_readonly`
- read-only analytics route `⚡ Energy Analysis` still loads successfully

DB/artifact validation:

- no DB write path was executed during validation
- DB SHA1 before AppTest: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- DB SHA1 after AppTest: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- active artifacts still remained Task 4L only:
  - `models/production_efficiency_model.provenance.json` -> `Task 4L`, `20260401_000808`, `random_forest`, `active`
  - `models/production_preprocessor.provenance.json` -> `Task 4L`, `20260401_000808`, `random_forest`, `active`

## 7. remaining limitations

- runtime mode currently gates the shell by environment/query/session-state only; there is no auth/role system yet
- ETL, ML, and Maintenance operational code paths still exist in `standard` mode; this task hides them in `demo_readonly`, it does not redesign or remove them
- `app.py` and some legacy helper files still carry dormant historical code that is outside this task’s narrow gating scope
- the optimization and experimental routes remain read-only, but this task does not introduce a broader deployment/pilot governance model

## 8. recommended next follow-up after Task12A

- stay inside Layer 1 immediate post-demo hardening/productization
- strong next candidates:
  - guided-operation defaults / audience mode presets
  - deployment/runtime hardening
  - background job governance planning for ETL/retraining
- do not widen into:
  - DB writes
  - retraining redesign
  - artifact promotion redesign
  - solver claims
  - production predictive-maintenance claims
