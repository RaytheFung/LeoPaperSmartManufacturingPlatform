# Final Stage Sync Status

## A. Current Accepted Baseline

- Task4T is passed.
- Task5 is passed.
- Task5A is passed.
- The app is presentation-ready and potential-demonstration ready for the current scope.
- Active ML artifacts remain unchanged from the accepted Task4L/Task5 state.
- `manufacturing_data.db` was not written in Task5A.
- Routed page logic, predictor contracts, and quantity semantics were not changed in Task5A.
- External holding folder for sidelined repo clutter:
  - `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/`

## B. What Task5A Archived

- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/History/flattened_review_snapshots/docs_technical/`
  - archived the stale advisor/review snapshot bundle:
    - `ADVISOR_REVIEW_PACKET.md`
    - `UNIFIED_VIEW_ADVISOR_WALKTHROUGH.md`
    - `ENERGY_MODULE_PANEL_WALKTHROUGH.md`
    - `MAINTENANCE_MODULE_PANEL_WALKTHROUGH.md`
    - `ML_MODULE_PANEL_WALKTHROUGH.md`
    - `OPTIMIZATION_MODULE_PANEL_WALKTHROUGH.md`
    - `FACT_MACHINE_HOUR_PIPELINE_PANEL_WALKTHROUGH.md`
    - `ML_OPTIMIZATION_REBUILD_INSPECTION_REPORT.md`
    - `ML_OPTIMIZATION_REBUILD_ROADMAP.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/History/legacy_prompts_handover/external_project_folder/`
  - archived clearly stale external prompt/handover drafts:
    - `CHATGPT_POST_TASK4K_HANDOFF.md`
    - `NEW_CHATGPT_WINDOW_AFTER_TASK4K_PROMPT.txt`
    - `Task4S_new_window_handover.md`
    - `claude_code_prompt.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/History/external_project_orphans/project_root_duplicates/`
  - archived exact external duplicates of canonical in-repo docs:
    - `UPDATED_HANDOFF_TASK3B_READY.md`
    - `REAL_DATA_PLUS_SCENARIO_MODE_STRATEGY.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/docs_history/`
  - now holds the former `docs/history/` repo folder:
    - `DATA_INTEGRITY.md`
    - `REFACTORING_LOG.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/docs_project_management/`
  - now holds the former `docs/project_management/` repo folder:
    - `ROADMAP_STAGE3.md`
- `/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform_repo_holding_20260404/History/HISTORY_MANIFEST.md`
  - records the original path, new History path, archive reason, and safe-to-archive evidence for every archived file.

## C. What Was Intentionally Not Archived And Why

- `CURRENT_REBUILD_STATUS.md`, `docs/technical/REBUILD_DOCS_INDEX.md`, and accepted Task reports stayed in place because they remain live truth anchors.
- In-repo `docs/technical/SESSION_HANDOFF_CONTEXT.md` and `docs/technical/UPDATED_HANDOFF_TASK3B_READY.md` stayed in place because they are still indexed historical handoff docs inside the repo.
- Active routed/runtime files under `app.py`, `modules/`, `core/`, `tests/`, and `models/` stayed in place because Task5A is governance-only and those files remain active or validated paths.
- `manufacturing_data.db` and backup DB artifacts stayed in place because DB/data movement was explicitly out of scope.
- External `/Users/rayfung/Documents/VCC/LeoPaper/TASK4K_INTERRUPTED_HANDOFF.md` and `/Users/rayfung/Documents/VCC/LeoPaper/TASK4K_CONTINUATION_PROMPT.txt` stayed in place because `docs/technical/TASK4K_IMPLEMENTATION_REPORT.md` still records those exact paths as Task4K preflight inputs.
- Dormant-but-known code such as `modules/shared_ml_components.py`, `modules/euvg_module.py`, and `core/enhanced_etl_solution_CURRENT.py` stayed in place because they are still referenced by accepted documentation/audit trails and were not re-proven safe to archive in this run.

## D. Remaining Uncertain Files / Unresolved Clutter

- External standalone code copies in `/Users/rayfung/Documents/VCC/LeoPaper/`:
  - `corrected_energy_attribution.py`
  - `etl_auto_trigger.py`
  - `fixed_unified_view.py`
  - `maintenance_integration.py`
  - `smart_manufacturing_etl.py`
  - `unified_view_module.py`
- Broader-project cloned folders / packaged review artifacts:
  - `LeoPaperSmartManufacturingPlatform_upload/`
  - `LeoPaperSmartManufacturingPlatform副本/`
  - `smart_manufacturing_app/`
  - `(6:8)smart_manufacturing_app副本/`
  - `LeoPaperSmartManufacturingPlatform for Review`
  - `LeoPaperSmartManufacturingPlatform for Review.zip`
  - `LeoPaperSmartManufacturingPlatform.zip`
  - `LeoPaperSmartManufacturingPlatform_review.zip`
  - `LeoPaperSmartManufacturingPlatform副本.zip`
- Presentation files, screenshots, PDFs, and unrelated personal/backup files in the broader project folder were left untouched because this run did not establish whether they are still needed outside the repo workflow.
- The external holding folder itself is intentionally temporary; if a later cleanup wants to delete or further consolidate it, that should be a separate explicit decision.

## E. Exact Proposed Prompt For The Next Task (`Task6 UI polish & demo freeze`)

```text
Please execute Task6 only: UI polish & demo freeze.

Read first in this exact order:
1. CURRENT_REBUILD_STATUS.md
2. docs/technical/FINAL_STAGE_SYNC_STATUS.md
3. docs/technical/TASK4T_PRESENTATION_FINALISATION_REPORT.md
4. docs/technical/TASK5_MODEL_BACKED_INTERVENTION_PREVIEW_REPORT.md
5. app.py
6. modules/unified_view_module.py
7. modules/maintenance_module.py
8. modules/ml_module.py
9. modules/optimization_module.py
10. static/styles.css

Important framing:
- This is a presentation-polish task, not a logic task.
- Keep exactly one writer on shared canonical-path files.
- Do NOT retrain models.
- Do NOT promote artifacts.
- Do NOT write manufacturing_data.db.
- Do NOT change routed data contracts or quantity semantics.
- Do NOT widen into solver work, backend expansion, or new features.

Objective:
- tighten reviewer-facing copy
- improve spacing and section rhythm
- improve chart titles / subtitles / captions
- improve section order where presentation readability benefits
- set better expander defaults
- make the live demo easier to scan on desktop and laptop display sizes

Allowed scope:
- headings, captions, labels, chart titles, help text
- section ordering and container grouping
- expander default open/closed state
- harmless layout/CSS polish
- small presentation-only formatting adjustments

Do NOT:
- change ML/optimization/maintenance business logic
- change predictor feature preparation or model selection
- change ETL/materialization behavior
- add new database reads/writes beyond existing routed behavior
- add new tabs, pages, or claims
- archive more files in this task

Validation:
- py_compile only the touched Python files
- run focused tests only if a touched file already has relevant coverage
- run one lightweight Streamlit smoke on port 8502
- confirm the main routed pages still render without exceptions

Docs update rule:
- update CURRENT_REBUILD_STATUS.md and docs/technical/REBUILD_DOCS_INDEX.md only if Task6 truly closes
- write one Task6 report only if the task actually closes cleanly
```

## F. Future Plan After The Presentation

- Open a post-demo `Task7` branch instead of widening the pre-demo freeze.
- Revisit unresolved broader-project clutter only with a separate explicit archival decision.
- Consider maintenance appendix convergence or dormant helper cleanup only after the demo freeze is complete.
- Keep anomaly-policy work, retraining reconsideration, and any advanced optimization branch clearly separated from demo-scope polish.

## G. Final-Stage Roadmap

- Task5 passed
- Task5A passed
- Task6 UI polish & demo freeze
- user end-to-end self-trial
- post-demo Task7 advanced branch
