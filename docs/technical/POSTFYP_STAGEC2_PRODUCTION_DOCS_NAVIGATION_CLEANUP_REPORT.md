# Post-FYP Stage C2 Production Docs Navigation Cleanup Report

## Purpose

Stage C2 cleans up operator-facing documentation and navigation for factory production deployment readiness.

Stage C1 inventoried active runtime files, deployment-critical docs, technical ledgers, tests, source data, generated outputs, model artifacts, and legacy/dormant/misleading surfaces. C2 turns that inventory into clearer documentation boundaries without moving, deleting, archiving, quarantining, or editing active runtime code.

## Scope

This is a docs/navigation and warning-boundary task.

It updated operator-facing documentation, added a manual-check warning file, added this C2 report, and updated the rebuild docs index. It did not delete, move, rename, archive, or quarantine files. It did not run ETL, historical backfill, canonical materialization, carry-forward reconciliation execution, live DB migration, DB writes, model retraining, model artifact promotion, source-discovery policy changes, runtime canonical predicate changes, Streamlit write-control changes, or active runtime code edits.

## Factory deployment objective

The project target is controlled factory deployment pilot readiness with production-grade safety gates.

The documentation now foregrounds that the repository is being hardened for deployment readiness, not declared fully production-launched. Live/shared DB migration, runtime CSI carry-forward adoption, promoted DB writes, data-quality runtime enforcement, and ML artifact promotion remain gated future work.

## Files changed

| File | Change type | Reason |
| --- | --- | --- |
| `README.md` | Updated | Reframed top-level operator docs around factory deployment pilot readiness, local DB/no-DB-in-Git safety, source/output boundaries, disabled carry-forward, and gated live migration. |
| `docs/DOCS_GUIDE.md` | Updated | Converted the docs guide into a production-readiness navigation guide and separated active operator docs from historical evidence docs. |
| `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` | Updated | Clarified Stage C runtime ownership boundaries, disabled carry-forward scaffolding, local DB boundary, and experimental-lab non-production status. |
| `docs/technical/TECHNICAL_OVERVIEW.md` | Updated | Replaced outdated Stage 3 framing with a concise production-readiness architecture overview. |
| `project_context.md` | Updated | Added a top warning banner marking the file as historical context, not current deployment truth. |
| `tests/manual_checks/README.md` | Added | Warned that manual checks are not production deployment scripts and may query or mutate local DB state. |
| `docs/technical/REBUILD_DOCS_INDEX.md` | Updated | Added the C2 report under the Stage C Production-Readiness section. |
| `docs/technical/POSTFYP_STAGEC2_PRODUCTION_DOCS_NAVIGATION_CLEANUP_REPORT.md` | Added | Captures scope, dependency proof, validation, unsafe scans, and C3 recommendation. |

## README cleanup summary

`README.md` now states that the project is being hardened for controlled factory deployment pilot readiness with production-grade safety gates. It explicitly says production launch is not complete.

The README now clarifies:

- `manufacturing_data.db` is local runtime state and must never be staged, committed, or pushed.
- `source_data/` is source truth for accepted historical packages.
- `etl_outputs/` is generated output, not source truth.
- CSI carry-forward is disabled-by-default and not active runtime behavior.
- live/shared DB migration remains gated, not abandoned.
- active model artifacts must not be retrained or promoted without a separate gate.
- launch instructions remain centered on `scripts/bootstrap_py311_and_run.sh` and port `8502`.
- routine Stage C checks are lightweight compile/unit/source-discovery checks, not ETL or materialization execution.

## Docs navigation cleanup summary

`docs/DOCS_GUIDE.md` now separates:

- active operator/navigation docs;
- Stage B/C technical evidence reports;
- historical or presentation-era evidence docs;
- source-data and generated-output folder intent;
- externalized history.

It points readers to `README.md`, `docs/LAUNCHING_TIPS.md`, `ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md`, `DATA_CONTRACTS_GUIDE.md`, `TECHNICAL_OVERVIEW.md`, and `REBUILD_DOCS_INDEX.md` as the current navigation set.

## Active runtime ownership wording summary

`ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` now clarifies:

- the file is the current routed-runtime ownership map for Stage C production-readiness cleanup;
- local DB state remains local-only and out of Git;
- source-discovery policy and canonical predicates remain unchanged;
- carry-forward scaffolding remains disabled-by-default and is not active ETL, materialization, Streamlit, DQ, ML, or app behavior;
- live/shared DB migration remains gated and requires a later production-grade migration gate;
- the Experimental Intelligence Lab is an internal review lane, not defended production execution.

## Legacy/history warning boundary summary

`project_context.md` now starts with a warning banner that it is historical context only and not current deployment truth.

The C2 report documents, but does not edit, code-module legacy candidates such as `modules/shared_ml_components.py`, `modules/euvg_module.py`, and `modules/dormant_legacy_app_helpers.py`. That preserves the prompt boundary against editing active or legacy Python modules in this stage.

## Manual checks warning summary

`tests/manual_checks/README.md` was added.

It says manual checks are ad hoc investigation helpers, not production deployment scripts. It warns that some may query or mutate `manufacturing_data.db`, alter legacy `unified_view` tables, or depend on historical assumptions, and it requires explicit approval plus DB backup/rollback review before execution.

## Dependency proof summary

Read-only search commands were used to classify legacy/quarantine candidates before any future quarantine move.

Findings:

- `modules/dormant_legacy_app_helpers.py` is imported by `app.py` for dormant compatibility wrappers, so it must not be moved in C2.
- `modules/euvg_module.py` is imported by `modules/unified_view_module.py`, `modules/dormant_legacy_app_helpers.py`, tests, and smoke scripts, so it must not be moved in C2.
- `modules/shared_ml_components.py` appears in docs and contains legacy `unified_view` DB access, but it is not imported by the current routed app path in the dependency proof. It remains a Pro-review quarantine candidate, not a C2 move target.
- `project_context.md` is referenced by docs/navigation only and is now explicitly marked historical.
- `tests/manual_checks/` contains scripts that query or mutate local `manufacturing_data.db` / `unified_view` state, so they are write-capable/manual-only and require explicit approval before execution.
- `manufacturing_data.db` references remain in runtime path helpers, guarded rehearsal tests, historical reports, manual checks, and write-capable scripts. DB files must stay unstaged and outside Git.

Commands run:

- `rg "shared_ml_components|euvg_module|dormant_legacy_app_helpers" app.py modules core scripts tests docs -n || true`
- `rg "project_context|manual_checks|unified_view" README.md docs modules core scripts tests -n || true`
- `rg "manufacturing_data.db" scripts tests modules core docs -n || true`

## Files intentionally not moved or deleted

No files were moved, deleted, renamed, archived, or quarantined.

Intentionally left in place:

- `app.py`;
- all `modules/*.py`;
- all `core/*.py`;
- all `scripts/*.py`;
- all `tests/*.py`;
- `source_data/`;
- `data/`;
- `etl_outputs/`;
- `models/`;
- historical `docs/technical/TASK*` reports;
- `CURRENT_REBUILD_STATUS.md`.

## Runtime behavior impact

No runtime behavior changed.

C2 did not modify `app.py` or active runtime Python files. It did not change source-discovery defaults, canonical predicates, carry-forward mode, data-quality runtime wiring, model artifacts, DB state, or Streamlit controls.

## Validation

Validation result: passed for the C2 docs/navigation scope.

Observed validation evidence:

- `git status --short` showed only intended docs/report/manual-warning files before staging.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c2_pycache python3.11 -m compileall core modules scripts tests` passed.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c2_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities` passed with `10` tests.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c2_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter` passed with `34` tests.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c2_pycache python3.11 scripts/compare_source_discovery_modes.py` passed with `overall: PASS`.
- `PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c2_pycache python3.11 scripts/compare_source_discovery_modes.py --json` returned `"success": true`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`.

Required validation commands for C2:

- `git status --short`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities`
- `python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Unsafe file scan

Unsafe scan result: passed.

Observed unsafe-scan evidence:

- DB scan returned no `*.db`, `*.sqlite`, or `*.sqlite3` files under max depth 5.
- Local environment/upload scan returned no `.venv`, `.conda311`, `.miniforge`, or `temp_uploads` folders under max depth 5.
- `git ls-files manufacturing_data.db || true` returned no tracked file.
- `git check-ignore --no-index -v manufacturing_data.db || true` returned `.gitignore:5:*.db manufacturing_data.db`.
- `git status --ignored --short | head -100` showed only intended C2 docs changes plus ignored `__pycache__/` folders; no DB, raw Excel, model artifact, generated `etl_outputs`, or local env/upload artifact was staged.

Required unsafe scans:

- `find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print`
- `find . -maxdepth 5 \( -name ".venv" -o -name ".conda311" -o -name ".miniforge" -o -name "temp_uploads" \) -print`
- `git ls-files manufacturing_data.db || true`
- `git check-ignore --no-index -v manufacturing_data.db || true`
- `git status --ignored --short | head -100`

## Remaining risks

- Active app launch and route smoke remain future Stage C work.
- Legacy Python modules remain in place until a later dependency-proof and quarantine stage.
- Historical reports still contain older demo/presentation/FYP language because they are evidence records, not current operator docs.
- Manual checks remain potentially write-capable if executed incorrectly; C2 adds a warning boundary but does not refactor those scripts.
- Live/shared DB migration, rollback, runtime carry-forward adoption, and operational owner acceptance remain unproven.

## Recommended C3

Recommended C3 should be a lightweight app launch and routed smoke stage on the selected branch.

C3 should keep DB writes and runtime behavior unchanged unless explicitly reopened. It should prove the app launches on port `8502`, exercise the defended routed pages in read-only/pilot-safe mode where possible, record route-smoke evidence, and preserve the no-DB-in-Git and no-artifact-promotion safety gates.
