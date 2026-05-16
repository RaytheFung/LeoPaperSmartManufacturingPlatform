# Post-FYP Stage D1 Factory Route Workflow Smoke Report

## Purpose

Stage D1 extends the Stage C3 app bootstrap smoke into fuller page-by-page factory workflow smoke evidence and operator walkthrough guidance.

D1 verifies that routed app pages can be opened or safely assessed in deployment-pilot-safe runtime modes without executing ETL, historical backfill, canonical materialization, carry-forward reconciliation, live/shared DB migration, model retraining, artifact promotion, or DB writes inside Git.

## Scope

This is a docs/evidence stage.

Changed files are limited to:

- `docs/operations/FACTORY_ROUTE_WORKFLOW_SMOKE_CHECKLIST.md`
- `docs/technical/POSTFYP_STAGED1_FACTORY_ROUTE_WORKFLOW_SMOKE_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

D1 does not modify `app.py`, active runtime Python files, source data, generated outputs, model artifacts, DB files, Streamlit write controls, source-discovery default policy, runtime canonical predicates, carry-forward runtime wiring, or DQ runtime behavior.

## Factory deployment objective

The target remains Factory Production Deployment readiness with production-grade safety gates.

D1 supports that target by adding practical route workflow smoke evidence for controlled factory deployment pilot owner review. It does not claim production deployment completion. Production deployment, live/shared DB migration, promoted DB writes, runtime carry-forward adoption, model promotion, monitoring, and owner acceptance remain gated.

## Readiness preflight refresh

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 scripts/check_factory_deployment_readiness.py
```

Observed result:

- `success: true`
- `check_count: 7`
- `passed_count: 7`
- `critical_failures: []`

Passed checks:

- required files present;
- `manufacturing_data.db` not tracked;
- no repo-local DB files;
- no local environment or upload folders;
- tracked `etl_outputs` limited to `.gitkeep` and `ETL_OUTPUTS_GUIDE.md`;
- carry-forward default disabled;
- supported runtime modes include `demo_readonly`, `pilot_review`, and `standard`.

## Route contract refresh

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 -m unittest tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities tests.test_runtime_paths
```

Observed result:

- `10` tests ran.
- Result was `OK`.

Guardrail command:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
```

Observed result:

- `34` tests ran.
- Result was `OK`.

Source-discovery comparison:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Observed result:

- text diagnostic returned `overall: PASS`;
- JSON diagnostic returned `success: true`, `month_count: 9`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`;
- July 2025 through February 2026 resolved in both legacy and manifest modes;
- March 2026 remained expected-blocked in both modes.

Runtime route visibility probe:

| Runtime mode | Visible routes | Write-control stance | Experimental route |
| --- | --- | --- | --- |
| `standard` | ETL Pipeline; Canonical Operations Overview; Energy Analysis; Operational Decision Support; Efficiency Prediction & Governance; Maintenance; Experimental Intelligence Lab | `suppress_write_controls = false` | exposed |
| `demo_readonly` | ETL Pipeline; Canonical Operations Overview; Energy Analysis; Operational Decision Support; Efficiency Prediction & Governance; Maintenance | `suppress_write_controls = true` | hidden |
| `pilot_review` | ETL Pipeline; Canonical Operations Overview; Energy Analysis; Operational Decision Support; Efficiency Prediction & Governance; Maintenance; Experimental Intelligence Lab | `suppress_write_controls = true` | exposed |

Static route-module import probe from the `/tmp` smoke workspace imported these modules successfully:

- `modules.etl_module`
- `modules.unified_view_module`
- `modules.energy_module`
- `modules.optimization_module`
- `modules.ml_module`
- `modules.maintenance_module`
- `modules.experimental_intelligence_lab_module`

## Smoke workspace boundary

Actual Streamlit process smoke was run only from:

```text
/tmp/leopaper_stage_d1_route_smoke/
```

Logs were written outside Git:

```text
/tmp/leopaper_stage_d1_route_smoke_logs/streamlit_8502.log
```

Copied into the smoke workspace:

- `app.py`
- `core/`
- `modules/`
- `config/`
- `static/`
- `.streamlit/`
- `requirements.txt`

Intentionally not copied:

- `.git`
- `manufacturing_data.db`
- `*.db`, `*.sqlite`, `*.sqlite3`
- `source_data/`
- `data/`
- `models/`
- `etl_outputs/`
- local environment folders;
- `temp_uploads/`

Workspace unsafe scan for DB/source/model/output/env/upload directories returned no matches.

## Streamlit bootstrap evidence

Launch environment:

- launch directory: `/tmp/leopaper_stage_d1_route_smoke/`
- runtime mode: `SMART_MFG_RUNTIME_MODE=demo_readonly`
- pycache prefix: `/tmp/leopaper_stage_d1_pycache`
- address: `127.0.0.1`
- port: `8502`
- headless: `true`
- Streamlit version: `1.31.0`
- Python version: `3.11.15`

HTTP bootstrap result:

```text
200 text/html 891
```

Startup log scan:

- scanned for `Traceback`, `Exception`, and `Error`;
- result was clean;
- expected `Stopping...` appeared after termination.

Process evidence:

- listener was observed on `127.0.0.1:8502`;
- process terminated cleanly;
- follow-up listener check showed the port closed.

No browser clicks, button clicks, uploads, ETL, backfill, materialization, carry-forward scripts, model training, artifact promotion, or DB promotion were performed.

## Route smoke matrix

| Route label | Runtime mode where visible | Classification | Write controls suppressed | Smoke method | Expected risk | Safe to render non-interactively | Full automated body render |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ETL Pipeline | `demo_readonly`, `pilot_review`, `standard` | defended-core | yes in `demo_readonly` and `pilot_review` | route contract, runtime capability probe, module import, app bootstrap | upload/process/backfill/month-write controls must remain hidden in read-only modes | yes in `demo_readonly` if no controls are clicked | skipped; no stable non-click route URL and route contains write controls in non-read-only mode |
| Canonical Operations Overview | `demo_readonly`, `pilot_review`, `standard` | defended-core | yes in `demo_readonly` and `pilot_review` | route contract, runtime capability probe, module import, app bootstrap | canonical read may report missing data but must not mutate state | yes for read-only observation | skipped; no stable non-click route URL |
| Energy Analysis | `demo_readonly`, `pilot_review`, `standard` | defended-core | yes in `demo_readonly` and `pilot_review` | route contract, runtime capability probe, module import, app bootstrap | canonical Gold read may report unavailable data; no fallback mutation allowed | yes for read-only observation | skipped; no stable non-click route URL |
| Operational Decision Support | `demo_readonly`, `pilot_review`, `standard` | defended-core | yes in `demo_readonly` and `pilot_review` | route contract, runtime capability probe, module import, app bootstrap | canonical Gold read may report unavailable data; no legacy/synthetic fallback mutation allowed | yes for read-only observation | skipped; no stable non-click route URL |
| Efficiency Prediction & Governance | `demo_readonly`, `pilot_review`, `standard` | defended-core | yes in `demo_readonly` and `pilot_review` | route contract, runtime capability probe, module import, app bootstrap | retraining controls must remain hidden in read-only modes | yes for read-only observation | skipped; no stable non-click route URL and retraining controls must not be touched |
| Maintenance | `demo_readonly`, `pilot_review`, `standard` | defended-core | yes in `demo_readonly` and `pilot_review` | route contract, runtime capability probe, module import, app bootstrap | upload/integration controls must remain hidden in read-only modes | yes for read-only observation | skipped; no stable non-click route URL and upload/integration controls must not be touched |
| Experimental Intelligence Lab | `pilot_review`, `standard`; hidden in `demo_readonly` | experimental | defended-core write controls suppressed in `pilot_review`; experimental real-input/export/stress-test surfaces may be visible | route contract, runtime capability probe, module import | experimental route has upload/export/manual stress-test surfaces and is not defended for production claims | yes only for explicit manual observation without clicking controls | skipped; hidden in `demo_readonly`, and `pilot_review` exposes controls that must not be clicked during automated smoke |

## Page-by-page smoke result

Automated result:

- app bootstrap smoke passed from `/tmp` in `demo_readonly`;
- route visibility contract passed;
- runtime capability probe passed;
- route-module import/static contract passed;
- no DB files were found in the smoke workspace;
- no startup traceback/error evidence was found.

Full automated page body navigation was skipped by design.

Reason:

- the app uses Streamlit sidebar widget state for route selection;
- no stable non-click route query pattern was identified for selecting each page body;
- browser-clicking through the sidebar would risk interacting with widgets and controls the prompt explicitly forbids;
- D1 therefore uses route contract tests, runtime capability probes, module import/static proof, app bootstrap smoke, and the manual operator walkthrough checklist as the safe evidence set.

Manual operator walkthrough evidence should be captured with `docs/operations/FACTORY_ROUTE_WORKFLOW_SMOKE_CHECKLIST.md`.

## Manual walkthrough checklist

D1 adds:

```text
docs/operations/FACTORY_ROUTE_WORKFLOW_SMOKE_CHECKLIST.md
```

The checklist includes:

- purpose;
- scope;
- runtime mode to use;
- before-starting checks;
- route-by-route checklist;
- controls that must not be clicked;
- evidence to capture;
- expected safe observations;
- failure/escalation criteria;
- DB/artifact safety checks;
- owner/reviewer initials placeholders.

Owner/reviewer placeholders remain unfilled because no actual sign-off evidence was provided.

## DB/artifact safety evidence

D1 did not write the original runtime DB and did not create DB files inside the GitHub-safe tree.

Observed safety evidence:

- GitHub-safe readiness preflight reported no repo-local DB files.
- `manufacturing_data.db` was not tracked.
- smoke workspace DB/source/model/output/env/upload scan returned no matches.
- Streamlit was launched from `/tmp/leopaper_stage_d1_route_smoke/`, not from the GitHub-safe tree and not from the original runtime repo.
- No raw Excel files, generated `etl_outputs`, model artifacts, or DB files were staged during D1.

## Runtime behavior impact

No runtime behavior changed.

D1 does not modify:

- `app.py`;
- active runtime Python files under `core/` or `modules/`;
- Streamlit route wiring;
- runtime modes or runtime capabilities;
- source-discovery default policy;
- runtime canonical predicates;
- DQ runtime behavior;
- carry-forward runtime wiring;
- source data;
- generated outputs;
- model artifacts;
- DB state.

## Validation

Validation commands used for D1:

```bash
git status --short
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 -m compileall core modules scripts tests
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 -m unittest tests.test_factory_deployment_readiness_check
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 scripts/check_factory_deployment_readiness.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d1_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Observed final validation result:

- `git status --short` showed only the intended D1 docs/report/index files before staging.
- `compileall core modules scripts tests` passed.
- `tests.test_factory_deployment_readiness_check` passed with `7` tests.
- `tests.test_runtime_paths`, `tests.test_app_route_contract`, `tests.test_runtime_mode`, and `tests.test_runtime_capabilities` passed with `10` tests.
- `tests.test_source_discovery_default_switch`, `tests.test_csi_carry_forward_config`, and `tests.test_csi_carry_forward_runtime_adapter` passed with `34` tests.
- `scripts/check_factory_deployment_readiness.py` returned `success: true`, `check_count: 7`, `passed_count: 7`, and no critical failures.
- `scripts/compare_source_discovery_modes.py` returned `overall: PASS`.
- `scripts/compare_source_discovery_modes.py --json` returned `success: true`, `month_count: 9`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`.

## Unsafe file scan

Required unsafe scans:

```bash
find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print
find . -maxdepth 5 \( -name ".venv" -o -name ".conda311" -o -name ".miniforge" -o -name "temp_uploads" \) -print
git ls-files manufacturing_data.db || true
git check-ignore --no-index -v manufacturing_data.db || true
git status --ignored --short | head -100
```

Observed unsafe scan result:

- DB scan returned no `*.db`, `*.sqlite`, or `*.sqlite3` files under max depth 5.
- Local environment/upload scan returned no `.venv`, `.conda311`, `.miniforge`, or `temp_uploads` folders under max depth 5.
- `git ls-files manufacturing_data.db || true` returned no tracked file.
- `git check-ignore --no-index -v manufacturing_data.db || true` returned `.gitignore:5:*.db manufacturing_data.db`.
- `git status --ignored --short | head -100` showed only the intended D1 docs/report/index changes plus ignored Python `__pycache__/` folders.

## Skipped/blocked route smoke items

Skipped:

- automated browser-click traversal of every route page body;
- any button click;
- any file upload;
- ETL execution;
- historical backfill;
- canonical materialization;
- carry-forward reconciliation execution;
- live/shared DB migration;
- model retraining;
- artifact promotion.

Blocker rationale for automated route traversal:

- no stable non-click route URL exists for each Streamlit sidebar route;
- clicking through pages is not required to prove route visibility and would increase the chance of touching forbidden controls;
- the safe evidence path is route contract tests, runtime capability probes, static module import proof, bootstrap smoke, and manual checklist capture.

## Remaining risks

- Manual operator route observations still need owner/reviewer capture.
- Actual owner/reviewer sign-off is not provided.
- Live/shared DB migration remains blocked.
- Promoted DB writes remain blocked.
- Runtime carry-forward adoption remains blocked.
- Full production workflow execution remains unproven.
- Production monitoring, access control, support ownership, and incident response remain future work.
- Experimental Intelligence Lab remains non-defended for production claims.

## Recommended D2

Recommended D2: controlled manual operator route walkthrough evidence capture.

D2 should use the D1 checklist to record selected branch, commit SHA, runtime mode, each route observation, screenshots or typed notes, no-click/no-upload confirmation, DB/artifact safety checks, reviewer initials, accepted pilot risks, blocked production risks, and explicit escalation notes. D2 should keep live/shared DB migration, promoted DB writes, runtime carry-forward adoption, and model promotion blocked unless a separate approved stage opens that scope.
