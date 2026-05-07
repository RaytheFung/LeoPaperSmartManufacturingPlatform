# Post-FYP Stage C1 Production-Readiness Inventory Report

## Purpose

Stage C1 inventories the repository surfaces that matter for factory production deployment readiness before any cleanup, quarantine, archive, or wording rewrite is attempted.

This stage is planning-only. It classifies active runtime files, deployment-critical documents, technical ledgers, tests, source data, generated outputs, model artifacts, legacy candidates, quarantine candidates, history-only files, and unclear files requiring review.

## Scope

Stage C1 changed only this report and the rebuild docs index.

It did not delete, move, rename, archive, or quarantine files. It did not run ETL, historical backfill, canonical materialization, carry-forward reconciliation execution, live DB migration, model retraining, artifact promotion, source-discovery policy changes, runtime canonical predicate changes, Streamlit write-control changes, or app route wiring changes.

`app.py` and all runtime code were read only.

## Factory deployment objective

The active objective is controlled factory deployment pilot readiness with production-grade safety gates.

That means the repo needs an operator-readable active surface map, explicit DB and artifact safety boundaries, and a cleanup plan for stale or misleading files. It does not mean the local runtime DB is ready for live/shared deployment, and it does not approve runtime carry-forward adoption.

## Active runtime inventory

| Surface | Classification | Files / folders | C2 action |
| --- | --- | --- | --- |
| Streamlit entry point | `active_runtime` | `app.py` | Leave untouched due runtime dependency. |
| Runtime mode and page visibility | `active_runtime` | `core/runtime_mode.py`, `core/runtime_capabilities.py`, `core/ui_utils.py`, `static/styles.css`, `.streamlit/config.toml` | No action unless Stage C app smoke finds a deployment-mode defect. |
| Routed ETL page | `active_runtime` | `modules/etl_module.py`, `core/enhanced_etl_solution_CURRENT.py`, `core/bronze_raw_store.py`, `core/silver_normalizer.py`, `core/canonical_materializer.py`, `core/gold_fact_builder.py`, `core/etl/` | Leave untouched due runtime dependency; C2 may add warning banners only if approved. |
| Source discovery and contracts | `active_runtime` | `core/source_manifest_discovery.py`, `core/source_family_registry.py`, `core/data_contracts.py`, `config/source_manifest.v1.json`, `config/data_quality_rules.v1.json` | No action; source-discovery default policy must remain unchanged. |
| Canonical operations overview | `active_runtime` | `modules/unified_view_module.py`, `core/canonical_gold_reader.py` | Leave untouched; file name is historical but routed function is active. |
| Energy analysis | `active_runtime` | `modules/energy_module.py`, `core/canonical_energy_reader.py` | No action. |
| Operational decision support | `active_runtime` | `modules/optimization_module.py`, `core/canonical_optimization_reader.py`, `core/intervention_preview.py`, `core/maintenance_evidence.py`, `core/canonical_ml_reader.py`, `core/ml_predictor.py` | No action; do not relabel as solver or execution engine. |
| ML prediction and governance | `active_runtime` | `modules/ml_module.py`, `core/canonical_ml_reader.py`, `core/ml_predictor.py`, `core/ml_review_queue.py`, `core/ml_trainer.py`, `core/intervention_preview.py` | Leave untouched; retraining/artifact promotion remains outside C1/C2 unless reopened. |
| Maintenance evidence | `active_runtime` | `modules/maintenance_module.py`, `core/maintenance_evidence.py`, `core/maintenance_integration.py`, `core/canonical_energy_reader.py` | Leave untouched; upload/write controls must remain governed by runtime mode. |
| Experimental intelligence lab | `active_runtime` | `modules/experimental_intelligence_lab_module.py`, `core/experimental_scheduling.py`, `core/experimental_maintenance_prototype.py` | Keep separate from defended-core production claims; C2 may add warning banners only if needed. |
| Runtime paths | `active_runtime` | `core/runtime_paths.py` | No action; keep repo-local DB path contract explicit and DB local-only. |
| Carry-forward disabled scaffolding | `active_runtime` for guarded helpers, not active ETL behavior | `core/csi_carry_forward_config.py`, `core/csi_carry_forward_runtime_adapter.py`, `core/csi_carry_forward_audit_schema.py`, `core/csi_carry_forward_audit_workflow.py` | Leave disabled-by-default; do not wire into active runtime in C2. |
| Utility and support helpers | `active_runtime` or `unclear_requires_review` by caller | `core/data_utils.py`, `core/machine_alias_registry.py`, `core/csi_quantity_shadow.py`, `core/november_december_*`, `core/csi_boundary_inventory.py`, `core/csi_carry_forward_preflight.py`, `core/backfill_rehearsal_preflight.py`, `core/fact_machine_hour_repair.py`, `core/utils.py` | Keep for now; require Pro review before any cleanup because several scripts/tests import them. |

## Deployment-critical docs inventory

| File / folder | Classification | Reason | C2 action |
| --- | --- | --- | --- |
| `README.md` | `deployment_critical_doc` | Main runtime entry, local DB boundary, launch commands, and current working-set summary. | Update wording in C2 to reduce demo/FYP residue and align test commands with Stage C validation set. |
| `docs/LAUNCHING_TIPS.md` | `deployment_critical_doc` | macOS Python 3.11 and port 8502 runbook. | No action unless app smoke changes the launch path. |
| `docs/DOCS_GUIDE.md` | `deployment_critical_doc` | Short docs navigation map. | Update wording after C2 cleanup decisions if paths change. |
| `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` | `deployment_critical_doc` | Authoritative routed-runtime ownership map. | Update wording in C2 after inventory decisions are accepted. |
| `docs/technical/DATA_CONTRACTS_GUIDE.md` | `deployment_critical_doc` | Source manifest, DQ metadata, carry-forward, and local DB boundaries. | No C1 edit; add Stage C note only if C2 changes docs structure. |
| `docs/technical/REBUILD_DOCS_INDEX.md` | `deployment_critical_doc` | Evidence ledger reading order. | Updated in C1 for this report. |
| `docs/technical/TECHNICAL_OVERVIEW.md` | `deployment_critical_doc` | Concise architecture map. | Pro review before C2 wording updates. |
| `AGENTS.md` | `deployment_critical_doc` | Local agent launch/run instructions and final reply format. | No action. |

## Technical ledger inventory

| File / folder | Classification | Reason | C2 action |
| --- | --- | --- | --- |
| `CURRENT_REBUILD_STATUS.md` | `technical_ledger` | Living execution ledger; not updated in C1 by request boundary. | Do not update unless a future prompt explicitly requires it. |
| `docs/technical/POSTFYP_STAGEA_*` through `POSTFYP_STAGEB13_1_*` | `technical_ledger` | Completed post-FYP governance and factory-deployment alignment evidence. | Keep for history; do not rewrite except index/navigation updates. |
| `docs/technical/TASK*.md`, `TASK*.txt`, `TASK*.diff`, `TASK*.csv` | `technical_ledger` and `keep_for_history` | Historical implementation, audit, presentation, and runtime-hardening evidence. | C2 should add a warning/index boundary before moving any files; require Pro review first. |
| `docs/technical/*_ZH.md` | `keep_for_history` | Chinese operator/presentation support docs; useful history but not the English production deployment operator surface. | Pro review before any archive/quarantine decision. |
| `project_context.md` | `keep_for_history` and `legacy_candidate` | Older architecture/status note with post-presentation wording and legacy unified-view references. | Add warning banner or move to history only after Pro review. |

## Tests inventory

| Test group | Classification | Files / folders | Deployment value | C2 action |
| --- | --- | --- | --- | --- |
| Runtime path and app shell | `active_test` | `tests/test_runtime_paths.py`, `tests/test_app_route_contract.py`, `tests/test_app_legacy_quarantine.py`, `tests/test_runtime_mode.py`, `tests/test_runtime_capabilities.py` | Protects route visibility, DB path, and read-only runtime profiles. | No action. |
| Source discovery and data contracts | `active_test` | `tests/test_source_*`, `tests/test_data_contracts.py`, `tests/test_task13_source_discovery.py` | Protects manifest-backed source policy and accepted/blocked month boundaries. | No action. |
| ETL and canonical backbone | `active_test` | `tests/test_etl_modules.py`, `tests/test_bronze_raw_store.py`, `tests/test_silver_normalizer.py`, `tests/test_canonical_materializer.py`, `tests/test_gold_fact_builder.py`, `tests/test_fact_machine_hour_repair.py` | Protects the canonical ingestion/materialization backbone. | Keep; do not run heavy ETL in C1/C2 unless approved. |
| Routed analytics | `active_test` | `tests/test_canonical_gold_reader.py`, `tests/test_canonical_energy_reader.py`, `tests/test_canonical_ml_reader.py`, `tests/test_canonical_optimization_reader.py`, `tests/test_energy_route_contract.py`, `tests/test_ml_module.py`, `tests/test_optimization_module.py`, `tests/test_maintenance_evidence.py` | Protects defended-core read surfaces. | No action. |
| ML and artifact governance | `active_test` | `tests/test_ml_predictor.py`, `tests/test_ml_trainer.py`, `tests/test_ml_review_queue.py`, `tests/test_intervention_preview.py` | Protects inference/retraining guardrails. | Do not promote artifacts in C2. |
| Experimental lane | `active_test` | `tests/test_experimental_intelligence_lab_route.py`, `tests/test_experimental_scheduling.py`, `tests/test_experimental_maintenance_prototype.py`, `tests/test_task12b_pilot_review_mode.py` | Protects the non-defended pilot-review lane. | Keep separate from production claims. |
| Carry-forward governance | `active_test` | `tests/test_csi_*`, `tests/test_august_*`, `tests/test_november_december_*`, `tests/test_temp_backfill_rehearsal_safety.py` | Protects disabled-by-default and temp-only safety boundaries. | No runtime adoption in C2. |
| Manual checks | `unclear_requires_review` | `tests/manual_checks/` | Ad hoc diagnostics; some scripts query or mutate `manufacturing_data.db`. | Add warning banner or move to manual-only history after Pro review. |

## Source data / generated output / model artifact inventory

| File / folder | Classification | Count / contents | Stage C interpretation | C2 action |
| --- | --- | --- | --- | --- |
| `source_data/` | `source_data` | 45 files total; 41 raw workbook files; Jan-Jun initial package plus Jul 2025-Feb 2026 accepted extension package; grouped energy files include March 2026 rows but March remains blocked. | Source truth for accepted historical packages. Raw Excel files must never be staged in a cleanup commit unless a future source-data governance prompt explicitly approves it. | Leave untouched. |
| `data/` | `source_data` and `legacy_candidate` | 3 tracked June demo/sample inputs. | Still documented as lightweight June demo path; confusing for factory deployment if treated as production input. | C2 should add warning banner or move behind a sample-data guide after Pro review. |
| `etl_outputs/` | `generated_output` | 2 tracked control files: `.gitkeep`, `ETL_OUTPUTS_GUIDE.md`; generated contents ignored. | Generated ETL reports/cache/mappings should not be staged. | Leave control files only; do not stage generated files. |
| `models/production_efficiency_model.pkl` and `models/production_preprocessor.pkl` | `model_artifact` | Active Task 14F model/preprocessor bundle. | Runtime artifact dependency; must not be retrained or promoted in C1/C2 unless explicitly approved. | Leave untouched. |
| `models/production_*.provenance.json` | `model_artifact` and `deployment_critical_doc` | Active artifact provenance manifests. | Required for artifact accountability. | Leave untouched. |
| `models/task14f_artifacts/` | `model_artifact` and `keep_for_history` | Live backup set from Task 14F. | Rollback/history support. | Keep for now; Pro review before archive. |
| `models/task14c_artifacts/`, `models/task4g_artifacts/`, `models/task4l_artifacts/` | `model_artifact`, `legacy_candidate`, `keep_for_history` | Older staged candidates and backups. | Valuable provenance but can confuse active artifact ownership. | C2 should add warning banner or archive map only after Pro review. |
| `manufacturing_data.db`, `*.db`, `*.sqlite`, `*.sqlite3` | `generated_output` / local runtime artifact | No DB file found in the GitHub-safe tree during C1 scan. | Must remain local-only and untracked. | Must not be staged, committed, or promoted. |
| `.venv/`, `.conda311/`, `.miniforge/`, `temp_uploads/` | `generated_output` / local runtime artifact | None found in the GitHub-safe tree during C1 scan. | Local-only environment/upload artifacts. | Must not be staged. |

## Legacy/dormant/misleading inventory

| File / folder | Classification | Why it is risky or misleading | Recommended C2 action |
| --- | --- | --- | --- |
| `modules/dormant_legacy_app_helpers.py` | `quarantine_candidate` and `keep_for_history` | Explicit dormant June ETL/EUVG helper quarantine; not current routed truth. | Leave untouched or add stronger warning banner; do not delete before route-smoke proof. |
| `modules/shared_ml_components.py` | `legacy_candidate` | Legacy `unified_view` helper module; not part of current defended routed ML path. | Require Pro review; likely quarantine/archive candidate after dependency scan. |
| `modules/euvg_module.py` | `legacy_candidate` and `keep_for_history` | Retained for ETL/EUVG history and dormant helpers; not primary current analytics truth. | Require Pro review before moving; may need warning banner. |
| `modules/unified_view_module.py` | `active_runtime` and `legacy_candidate` | File name and old `UnifiedViewProcessor` helpers reference legacy `unified_view`, but routed `render_unified_view_page()` is active canonical behavior. | Leave untouched due runtime dependency; do not quarantine as a whole. |
| `core/ml_predictor.py` | `active_runtime` and `legacy_candidate` | Active predictor plus dormant legacy lookup helpers. | Leave untouched; cleanup only with focused tests. |
| `project_context.md` | `legacy_candidate` and `keep_for_history` | Post-presentation and Stage 3 wording conflicts with factory deployment objective. | Add warning banner or move to historical docs after Pro review. |
| `README.md` | `deployment_critical_doc` and `legacy_candidate` | Mentions lightweight June demo path and old minimal test list; still the operator entry point. | Update wording in C2, not archive. |
| `docs/technical/DETAILED_MODULE_WALKTHROUGH_REPORT_ZH.md`, `EXPERIMENTAL_*_ZH.md`, `TASK7_*`, `TASK8_*` | `keep_for_history` and `legacy_candidate` | Presentation/reviewer/demo-language support docs can confuse deployment operators. | Keep for history; C2 should separate production runbooks from presentation docs. |
| `tests/manual_checks/` | `unclear_requires_review` and `legacy_candidate` | Manual scripts include direct `manufacturing_data.db` access and at least one delete path. | Add warning banner or move to manual-only quarantine after Pro review. |
| `scripts/process_jan_to_june_2025.py`, `scripts/run_historical_canonical_backfill.py`, `scripts/run_task13r_temp_sweep.py` | `legacy_candidate` / guarded execution script | Scripts can write DB or generated outputs and are not C1-safe execution surfaces. | Add warning banner and require explicit prompt before execution. |
| `scripts/run_august_2025_temp_backfill_rehearsal.py`, `scripts/run_july_2025_temp_backfill_rehearsal.py`, `scripts/run_august_2025_csi_carry_forward_reconciliation.py`, `scripts/run_november_december_csi_carry_forward_reconciliation.py` | `keep_for_history` and guarded temp execution | Historical/temp-only scripts with DB writes under guardrails. | Keep for evidence; do not execute or promote. |
| Root-level `data/` files | `source_data` and `legacy_candidate` | June demo/sample path can be mistaken for deployment source truth. | Add sample-data note or move under a sample namespace only after Pro review. |

## Risk classification

| Risk | Classification | Current C1 decision |
| --- | --- | --- |
| Live/shared DB mutation risk | High | No DB writes were run. Future C2 must keep DB execution out of cleanup unless explicitly approved. |
| DB or SQLite artifact staging risk | High | Scan found no DB files in the GitHub-safe tree. Pre-commit checks must keep blocking DB staging. |
| Raw Excel staging risk | High | Existing source workbooks are already tracked; C1 staged no raw Excel files. Future cleanup commits must not stage raw Excel changes. |
| Generated `etl_outputs` staging risk | High | Only `.gitkeep` and guide are tracked; C1 staged no generated outputs. |
| Model artifact promotion risk | High | Model artifacts were not modified. |
| Active runtime regression risk | High | Runtime files were read only. C2 cleanup must not move active modules without route smoke and tests. |
| Misleading deployment wording risk | Medium | Several docs still carry demo, presentation, FYP, trial, or historical context. C2 should update wording in operator-facing docs first. |
| Legacy-code confusion risk | Medium | Dormant helper modules and legacy unified-view helpers remain. C2 should add banners or quarantine only after dependency proof. |
| Technical-ledger sprawl risk | Medium | Many historical reports remain flat under `docs/technical/`. C2 should improve navigation before moving evidence. |

## Recommended C2 cleanup actions

| C2 action | Targets | Gate before action |
| --- | --- | --- |
| No action | `app.py`, active routed modules, active canonical readers/builders, runtime mode/capability helpers, source manifest/config files, active tests | Keep unchanged unless app smoke reveals a deployment issue. |
| Update wording | `README.md`, `docs/DOCS_GUIDE.md`, `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`, selected operator-facing docs | Docs-only diff, no runtime files, validation matrix passes. |
| Add warning banner | `project_context.md`, `modules/dormant_legacy_app_helpers.py`, `modules/shared_ml_components.py`, `modules/euvg_module.py`, `tests/manual_checks/`, risky scripts | Pro review for modules/scripts; route/dependency smoke before code-file banners if imports are affected. |
| Quarantine/archive | Presentation-support docs, older model artifact folders, legacy helper modules, manual checks | Pro review required; no move/delete in C1; C2 must preserve evidence links or provide redirects/index map. |
| Move to legacy folder | Only files proven non-routed and non-imported | Full import/dependency scan, compileall, unit tests, route smoke, and explicit user approval. |
| Leave untouched due runtime dependency | `app.py`, `modules/etl_module.py`, `modules/unified_view_module.py`, `modules/energy_module.py`, `modules/ml_module.py`, `modules/optimization_module.py`, `modules/maintenance_module.py`, `modules/experimental_intelligence_lab_module.py`, active `core/` readers/builders | Required for C2 unless a later prompt opens implementation scope. |
| Require Pro review before action | `models/task*_artifacts/`, source workbooks, historical technical reports, legacy modules, write-capable scripts | Required before any archive, move, delete, or artifact policy change. |

## Files that must not be touched

- `manufacturing_data.db` and any `*.db`, `*.sqlite`, or `*.sqlite3` file.
- Raw Excel source files under `source_data/` and `data/`.
- Generated `etl_outputs/` contents beyond `.gitkeep` and `ETL_OUTPUTS_GUIDE.md`.
- Active model artifacts under `models/production_efficiency_model.pkl`, `models/production_preprocessor.pkl`, and their provenance manifests.
- Runtime entry and active routed files unless a later prompt explicitly opens runtime cleanup: `app.py`, `modules/etl_module.py`, `modules/unified_view_module.py`, `modules/energy_module.py`, `modules/ml_module.py`, `modules/optimization_module.py`, `modules/maintenance_module.py`, `modules/experimental_intelligence_lab_module.py`.
- Source-discovery and carry-forward policy files: `config/source_manifest.v1.json`, `config/data_quality_rules.v1.json`, `core/source_manifest_discovery.py`, `core/csi_carry_forward_config.py`, `core/csi_carry_forward_runtime_adapter.py`.
- `CURRENT_REBUILD_STATUS.md` unless a future prompt explicitly requires a ledger update.

## Files requiring Pro review

- `modules/shared_ml_components.py`.
- `modules/euvg_module.py`.
- `modules/dormant_legacy_app_helpers.py`.
- Legacy helpers inside `modules/unified_view_module.py` and `core/ml_predictor.py`.
- `tests/manual_checks/`.
- Write-capable scripts under `scripts/`, especially historical backfill, canonical materialization, carry-forward reconciliation, Task13/Task14 probes, and January-June processing scripts.
- `models/task4g_artifacts/`, `models/task4l_artifacts/`, `models/task14c_artifacts/`, `models/task14f_artifacts/`.
- Historical/presentation-heavy docs under `docs/technical/TASK7_*`, `TASK8_*`, `EXPERIMENTAL_*_ZH.md`, `DETAILED_MODULE_WALKTHROUGH_REPORT_ZH.md`, and older `TASK*` implementation reports.
- `project_context.md`.

## Runtime behavior impact

No runtime behavior changed.

C1 did not modify `app.py`, modules, core runtime helpers, config manifests, source data, DB files, model artifacts, ETL outputs, tests, scripts, or Streamlit settings.

## Validation

Result: passed for the C1 docs-only scope.

Observed validation evidence:

- Git status before staging showed only `docs/technical/REBUILD_DOCS_INDEX.md` modified and `docs/technical/POSTFYP_STAGEC1_PRODUCTION_READINESS_INVENTORY_REPORT.md` untracked.
- DB scan returned no `*.db`, `*.sqlite`, or `*.sqlite3` files under max depth 5.
- Local environment/upload scan returned no `.venv`, `.conda311`, `.miniforge`, or `temp_uploads` folders under max depth 5.
- `git ls-files manufacturing_data.db || true` returned no tracked file.
- `git check-ignore --no-index -v manufacturing_data.db || true` returned `.gitignore:5:*.db manufacturing_data.db`.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c1_pycache python3.11 -m compileall core modules scripts tests` passed.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c1_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter` passed with `36` tests.

Validation commands requested for C1 were run after the docs-only edits:

- `git status --short`
- `find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print`
- `find . -maxdepth 5 \( -name ".venv" -o -name ".conda311" -o -name ".miniforge" -o -name "temp_uploads" \) -print`
- `git ls-files manufacturing_data.db || true`
- `git check-ignore --no-index -v manufacturing_data.db || true`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter`

Pre-commit safety checks were also run:

- `git status --short`
- `git diff --stat`
- `git diff --cached --stat`
- `find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print`
- `find . -maxdepth 5 \( -name ".venv" -o -name ".conda311" -o -name ".miniforge" -o -name "temp_uploads" \) -print`
- `git status --ignored --short | head -100`

## Remaining risks

- This is an inventory and plan only; no legacy file has been quarantined yet.
- Active app launch and route smoke remain future Stage C work.
- Historical docs still contain demo, presentation, FYP, trial, and local-only context that can confuse production operators.
- Some files are both active and legacy-looking; C2 must not classify whole files as removable when only subcomponents are dormant.
- Model artifact history is useful but visually noisy; cleanup needs a provenance-preserving archive decision.
- Raw source workbooks are already tracked in this safe clone; C2 must not create new raw-source churn.

## Recommended C2

Recommended C2 should be a docs/navigation cleanup stage, not runtime cleanup.

Suggested C2 scope:

1. Update `README.md`, `docs/DOCS_GUIDE.md`, and `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` to foreground factory deployment readiness and demote demo/presentation-era wording.
2. Add clear warning banners to history-only docs and manual-check folders before moving anything.
3. Produce a dependency proof for legacy candidates before any quarantine/archive move.
4. Keep runtime behavior, source-discovery policy, carry-forward disabled state, DB state, model artifacts, raw source workbooks, and generated outputs unchanged.
