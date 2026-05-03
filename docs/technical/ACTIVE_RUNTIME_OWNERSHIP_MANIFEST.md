# Active Runtime Ownership Manifest

## Purpose

This file is the authoritative current-source map for the defended runtime after Task11 reconciliation.

Use trust order:

1. `CURRENT_REBUILD_STATUS.md`
2. `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`
3. live code under `app.py`, `modules/`, and `core/`
4. `docs/technical/REBUILD_DOCS_INDEX.md`
5. `README.md` for launch/runtime commands

`project_context.md` is retained as broad historical architecture context only. It is not the live routed-runtime ledger.

## Defended Core Runtime Ownership

- `🔄 ETL Pipeline`
  - route shell: `app.py` -> `modules/etl_module.py`
  - authoritative helpers: `core/bronze_raw_store.py`, `core/silver_normalizer.py`, `core/canonical_materializer.py`, `core/gold_fact_builder.py`
  - runtime truth: defended core
- `📊 Canonical Operations Overview`
  - route shell: `app.py` -> `modules/unified_view_module.py` -> `core/canonical_gold_reader.py`
  - primary data source: canonical `fact_machine_hour`
  - runtime truth: defended core
- `⚡ Energy Analysis`
  - route shell: `app.py` -> `modules/energy_module.py` -> `core/canonical_energy_reader.py`
  - primary data source: canonical `fact_machine_hour`
  - runtime truth: defended core
- `🎯 Operational Decision Support`
  - route shell: `app.py` -> `modules/optimization_module.py` -> `core/canonical_optimization_reader.py`
  - supporting preview/evidence helpers: `core/intervention_preview.py`, `core/maintenance_evidence.py`, `core/canonical_ml_reader.py`
  - primary data source: canonical `fact_machine_hour`
  - runtime truth: defended core
- `🤖 Efficiency Prediction & Governance`
  - route shell: `app.py` -> `modules/ml_module.py` -> `core/canonical_ml_reader.py`
  - active-artifact inference only: `core/ml_predictor.py`
  - review/evidence helpers: `core/ml_review_queue.py`, `core/intervention_preview.py`, `core/maintenance_evidence.py`
  - primary data source: canonical `fact_machine_hour`
  - runtime truth: defended core
- `🔧 Maintenance`
  - route shell: `app.py` -> `modules/maintenance_module.py`
  - authoritative helpers: `core/maintenance_evidence.py`, `core/canonical_energy_reader.py`
  - primary data sources: `maintenance_records` family plus canonical `fact_machine_hour` for supporting observed energy context
  - runtime truth: defended core

## Experimental Runtime Ownership

- `🧪 Experimental Intelligence Lab`
  - route shell: `app.py` -> `modules/experimental_intelligence_lab_module.py`
  - prototypes: `core/experimental_scheduling.py`, `core/experimental_maintenance_prototype.py`
  - runtime truth: internal-landing experimental flagship lane, read-only, non-defended for production claims, separate from defended core
  - scheduling provenance: default queue is real-seeded synthetic unless a narrow real-input pilot queue upload is supplied
  - maintenance provenance: weak-label model or fallback evidence score only; late-anchor future-event observation remains bounded by stored maintenance history

## Active Artifact Ownership

- active model: `models/production_efficiency_model.pkl`
- active preprocessor: `models/production_preprocessor.pkl`
- active manifests:
  - `models/production_efficiency_model.provenance.json`
  - `models/production_preprocessor.provenance.json`
- authoritative live bundle:
  - `task_tag = Task 14F`
  - `artifact_version_id = 20260419_181842`
  - `selected_model = random_forest`
- experimental predictor-backed prototype binding:
  - `core/experimental_scheduling.py` now resolves the same repo-local live model/preprocessor/provenance paths explicitly when no override predictor is passed

Archive folders under `models/task4g_artifacts/` and `models/task4l_artifacts/` are history/provenance support only. They are not the live runtime attachment set for the current defended bundle.

## Dormant / Legacy / Non-Authoritative Files Inside The Repo

- `app.py`
  - current routed shell truth is explicit through helper-based defended-core / experimental route classification
  - the routed `⚡ Energy Analysis` page body now delegates into `modules/energy_module.py`
  - dormant June ETL/EUVG loader imports are not required at app-entry import time for the current routed shell
  - the remaining dormant helper bodies are now quarantined in `modules/dormant_legacy_app_helpers.py`, with `app.py` retaining only tiny compatibility wrappers
  - dormant legacy helpers remain in-file:
    - `load_data()`
    - `show_overview_page(...)`
    - `show_etl_page(...)`
    - `show_team_performance_page(...)`
    - `show_optimization_page(...)`
  - these are not current routed truth
- `modules/dormant_legacy_app_helpers.py`
  - dormant, non-routed, historical compatibility only
  - explicit quarantine module for the extracted June ETL/EUVG loader and old helper-page implementations
  - not part of the current defended routed shell
- `modules/energy_module.py`
  - defended-core routed Energy page module
  - owns the extracted canonical `⚡ Energy Analysis` route body
  - remains canonical-reader-backed through `core/canonical_energy_reader.py`
- `modules/unified_view_module.py`
  - file name is historical
  - routed function `render_unified_view_page()` is canonical and defended
  - legacy `UnifiedViewProcessor` / `unified_view` storage helpers remain for compatibility/history, not for current routed analytics truth
- `modules/shared_ml_components.py`
  - legacy `unified_view` helper module
  - not part of the current defended routed ML path
- `modules/euvg_module.py`
  - retained for ETL/EUVG history and dormant helpers
  - not the primary data truth for current defended analytics routes
- `core/ml_predictor.py`
  - routed prediction path is still active
  - legacy lookup helpers that query `unified_view` are dormant helper debt, not current routed page truth
  - those legacy helpers now resolve the repo-local DB through `core.runtime_paths.get_database_path()` rather than a hard-coded path
- `project_context.md`
  - broad historical architecture context only
  - not authoritative for current routed-runtime ownership

## Confirmed External / Duplicate / Non-Authoritative Copies

Confirmed by `docs/technical/FINAL_STAGE_SYNC_STATUS.md`:

- external standalone code copies under `/Users/rayfung/Documents/VCC/LeoPaper/`
  - `corrected_energy_attribution.py`
  - `etl_auto_trigger.py`
  - `fixed_unified_view.py`
  - `maintenance_integration.py`
  - `smart_manufacturing_etl.py`
  - `unified_view_module.py`
- broader project clones / packaged review artifacts outside the repo root
  - `LeoPaperSmartManufacturingPlatform_upload/`
  - `LeoPaperSmartManufacturingPlatform副本/`
  - `smart_manufacturing_app/`
  - `(6:8)smart_manufacturing_app副本/`
  - `LeoPaperSmartManufacturingPlatform for Review`
  - related `.zip` review/archive packages

These are not part of the authoritative live runtime tree for the defended repo.
