# Task11 Post-Presentation Runtime Reconciliation Report

## 1. accepted baseline reconstructed from live ledger + accepted reports

- `CURRENT_REBUILD_STATUS.md` and the accepted Task4T/5/6A/6B/6C/6D/6E/7/8/TaskX-RF/TaskX2 reports agree that the defended shell is now:
  - `🔄 ETL Pipeline`
  - `📊 Canonical Operations Overview`
  - `⚡ Energy Analysis`
  - `🎯 Operational Decision Support`
  - `🤖 Efficiency Prediction & Governance`
  - `🔧 Maintenance`
  - `🧪 Experimental Intelligence Lab`
- Direct source review of `app.py` confirms those exact sidebar labels and dispatch targets are live.
- Direct source review of the routed page modules confirms the defended analytics routes read canonical `fact_machine_hour` through dedicated canonical readers rather than using legacy `unified_view` / EUVG as primary truth.
- Active ML artifacts remain the accepted Task 4L bundle only:
  - `models/production_efficiency_model.pkl`
  - `models/production_preprocessor.pkl`
  - `models/production_efficiency_model.provenance.json`
  - `models/production_preprocessor.provenance.json`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. direct-source-verified contradictions found

- `docs/DOCS_GUIDE.md` previously said to trust `project_context.md` on disagreement. Direct source review showed that was unsafe.
- `project_context.md` still described older routed/runtime truth, including:
  - retired or dormant route framing such as `team performance`
  - a more `unified_view`-centric architecture description
  - older ML quality/status framing
- `CURRENT_REBUILD_STATUS.md` and `docs/technical/REBUILD_DOCS_INDEX.md` still listed `project_context.md` as part of the active navigation set without warning that it was no longer authoritative for current routed-runtime ownership.
- `app.py` still retains dormant legacy helpers and imports:
  - `load_data()`
  - `show_overview_page(...)`
  - `show_team_performance_page(...)`
  - dormant EUVG/unified-view imports
  - these are not current routed truth, but their presence creates path ambiguity
- `modules/unified_view_module.py` remains the live routed file for `📊 Canonical Operations Overview`, but the filename and the retained `UnifiedViewProcessor` / `unified_view` storage logic can be misread as current primary runtime truth even though `render_unified_view_page()` is canonical-only

## 3. evidence-based statements retained but not re-proven

- `docs/technical/FINAL_STAGE_SYNC_STATUS.md` remains useful as a historical sync note for accepted archival decisions and broader-project clutter outside the repo root
- external holding-folder archival decisions from Task5A were retained as accepted history, not re-executed here
- accepted Task7/Task8 documentation outputs were retained as live documentation assets, not re-authored here
- dormant legacy helper code was documented as non-authoritative, but this task did not delete or archive any repo code blindly

## 4. authoritative runtime ownership map

- `🔄 ETL Pipeline`
  - `app.py` -> `modules/etl_module.py`
  - helper ownership: `core/bronze_raw_store.py`, `core/silver_normalizer.py`, `core/canonical_materializer.py`, `core/gold_fact_builder.py`
- `📊 Canonical Operations Overview`
  - `app.py` -> `modules/unified_view_module.py` -> `core/canonical_gold_reader.py`
- `⚡ Energy Analysis`
  - `app.py` -> `core/canonical_energy_reader.py`
- `🎯 Operational Decision Support`
  - `app.py` -> `modules/optimization_module.py` -> `core/canonical_optimization_reader.py`
  - supporting evidence/preview helpers: `core/intervention_preview.py`, `core/maintenance_evidence.py`, `core/canonical_ml_reader.py`
- `🤖 Efficiency Prediction & Governance`
  - `app.py` -> `modules/ml_module.py` -> `core/canonical_ml_reader.py`
  - active-artifact inference only: `core/ml_predictor.py`
  - review/evidence helpers: `core/ml_review_queue.py`, `core/intervention_preview.py`, `core/maintenance_evidence.py`
- `🔧 Maintenance`
  - `app.py` -> `modules/maintenance_module.py`
  - helper ownership: `core/maintenance_evidence.py`, `core/canonical_energy_reader.py`
- `🧪 Experimental Intelligence Lab`
  - `app.py` -> `modules/experimental_intelligence_lab_module.py`
  - prototype ownership: `core/experimental_scheduling.py`, `core/experimental_maintenance_prototype.py`
  - status: experimental bonus only, not defended core

The authoritative live ownership map is now frozen in:

- `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`

## 5. exact stale/duplicate/dormant files and why

- `project_context.md`
  - retained for broad historical architecture context
  - not current routed-runtime truth
- dormant legacy helpers in `app.py`
  - still present in-file for continuity, but not used by current sidebar dispatch
- `modules/unified_view_module.py`
  - live routed canonical page remains authoritative
  - retained `UnifiedViewProcessor` / `unified_view` persistence logic is compatibility/history debt, not current page truth
- `modules/shared_ml_components.py`
  - legacy `unified_view` helper module
  - not used by the defended routed ML page
- legacy lookup helpers inside `core/ml_predictor.py`
  - some still query `unified_view`
  - current routed prediction flow depends on canonical candidate building plus active saved artifacts, not those helper lookups
- external standalone code copies and cloned project folders listed in `docs/technical/FINAL_STAGE_SYNC_STATUS.md`
  - confirmed non-authoritative for this repo runtime
  - left untouched because blind archival/deletion was out of scope

## 6. exact changes made (if any)

- added `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` as the authoritative routed-runtime ownership map
- added this closeout report `docs/technical/TASK11_POST_PRESENTATION_RUNTIME_RECONCILIATION_REPORT.md`
- updated `docs/DOCS_GUIDE.md` so it no longer points users to `project_context.md` as the conflict-resolution authority
- updated `project_context.md` with an explicit note that it is historical architecture context, not the live routed-runtime ledger
- updated `CURRENT_REBUILD_STATUS.md` to mark Task11 passed and replace the active navigation set with the new manifest-backed source-of-truth
- updated `docs/technical/REBUILD_DOCS_INDEX.md` to index the new manifest/report and clarify the downgraded role of `project_context.md`
- added one focused AppTest smoke in `tests/test_task11_runtime_reconciliation.py` to prove the defended sidebar labels plus ETL/experimental tab contract from live `app.py`
- no routed logic, data-contract, artifact, or DB changes were made because direct source review showed the live shell already matched the accepted canonical baseline

## 7. validation / smoke summary

- direct-source review covered the required docs and live routed files in the requested order before edits
- active artifact provenance re-check confirmed:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`
- focused AppTest smoke now verifies:
  - exact defended sidebar labels
  - default ETL tabs:
    - `📤 Upload New Data`
    - `🧭 Latest Run Snapshot`
    - `📈 Historical Runs`
  - experimental route tabs:
    - `Constraint-Aware Scheduling Prototype`
    - `Predictive Maintenance Prototype`
  - experimental anchor control label:
    - `Anchor month for current-state view`
- direct source confirmation remains:
  - routed `📊 Canonical Operations Overview` still points to `modules/unified_view_module.py`, but its routed page reads canonical `fact_machine_hour` via `core/canonical_gold_reader.py`
  - no touched routed page depends on `unified_view` as primary truth
  - active artifacts still remain Task4L bundle only

## 8. remaining limitations

- dormant legacy helpers still exist inside the repo and may continue to confuse filename-based reviews until a later explicit cleanup task is approved
- `modules/unified_view_module.py` still carries a legacy filename even though its routed page is canonical
- broader-project external copies and packaged review artifacts outside the repo root still need a separate explicit archival/deletion decision
- this task froze ownership/documentation truth only; it did not delete legacy code, retrain models, or alter the live DB

## 9. recommended next stage after reconciliation

- keep the next follow-up on final presentation assets and rehearsal only
- use:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`
  - `docs/DOCS_GUIDE.md`
  - `docs/technical/REBUILD_DOCS_INDEX.md`
- do not reopen routed logic, artifact promotion, retraining, solver work, or DB-write scope unless a separate explicit task approves it
