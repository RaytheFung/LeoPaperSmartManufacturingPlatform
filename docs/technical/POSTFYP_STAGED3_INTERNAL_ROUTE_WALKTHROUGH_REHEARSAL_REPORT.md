# Post-FYP Stage D3 Internal Route Walkthrough Rehearsal Report

## Purpose

Stage D3 performs an internal controlled route walkthrough rehearsal and creates an owner-review capture template for factory-side assessment.

It refreshes route/readiness evidence, runs a `/tmp`-only Streamlit bootstrap rehearsal in `demo_readonly`, builds an internal route evidence model, and prepares the owner-review capture template without marking any owner sign-off complete.

## Scope

This is an evidence/rehearsal/documentation stage.

Changed files are limited to:

- `docs/operations/FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md`
- `docs/operations/FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK.md`
- `docs/technical/POSTFYP_STAGED3_INTERNAL_ROUTE_WALKTHROUGH_REHEARSAL_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

D3 does not modify `app.py`, active runtime Python files, tests, source data, generated outputs, model artifacts, DB files, Streamlit write controls, source-discovery default policy, runtime canonical predicates, carry-forward runtime wiring, or DQ runtime behavior.

## Factory deployment objective

The target remains Factory Production Deployment readiness with production-grade safety gates.

D3 supports that target by preparing practical factory-side owner-review evidence capture. It does not claim production deployment completion. Production deployment, live/shared DB migration, promoted DB writes, runtime carry-forward adoption, model promotion, monitoring, and actual owner acceptance remain gated.

## Readiness preflight refresh

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 scripts/check_factory_deployment_readiness.py
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

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 -m unittest tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities tests.test_runtime_paths
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Observed result:

- route/runtime tests passed with `10` tests;
- source-discovery/carry-forward guardrail tests passed with `34` tests;
- text source-discovery compare returned `overall: PASS`;
- JSON source-discovery compare returned `success: true`, `month_count: 9`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`;
- March 2026 remained expected-blocked in both legacy and manifest modes.

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

## Internal walkthrough rehearsal method

D3 used the safe internal rehearsal method allowed by the prompt:

- create a `/tmp` smoke workspace;
- copy only app-launch code;
- run Streamlit from `/tmp` in `demo_readonly`;
- validate bootstrap with HTTP GET `/`;
- scan startup logs for `Traceback`, `Exception`, and `Error`;
- stop the process cleanly;
- scan the smoke workspace and GitHub-safe tree for DB files;
- use route contract outputs, runtime capability probes, and import probes for route evidence;
- do not browser-click through routes;
- do not click buttons;
- do not upload files;
- do not execute ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, or artifact promotion.

## Smoke workspace boundary

Actual Streamlit process smoke was run only from:

```text
/tmp/leopaper_stage_d3_route_walkthrough/
```

Logs were written outside Git:

```text
/tmp/leopaper_stage_d3_route_walkthrough_logs/streamlit_8502.log
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

The smoke workspace was outside the GitHub-safe tree and outside the original runtime repo.

## Streamlit bootstrap evidence

Launch environment:

- launch directory: `/tmp/leopaper_stage_d3_route_walkthrough/`
- runtime mode: `SMART_MFG_RUNTIME_MODE=demo_readonly`
- pycache prefix: `/tmp/leopaper_stage_d3_pycache`
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

DB scan evidence:

- no DB file appeared in `/tmp/leopaper_stage_d3_route_walkthrough/`;
- no DB file appeared in the GitHub-safe tree.

## Internal route evidence model

| Route label | Runtime mode visibility | Expected safe observation | Forbidden controls | Internal rehearsal status | Owner review status |
| --- | --- | --- | --- | --- | --- |
| ETL Pipeline | visible in `demo_readonly`, `pilot_review`, `standard` | Read-only ETL route shell; upload/process/backfill/month-write controls hidden in `demo_readonly`. | upload, ETL process, backfill, materialization, month-write controls | `contract_passed`; `bootstrap_only`; `pending_owner_visual_confirmation`; `skipped_due_write_risk` for automated clicking | pending |
| Canonical Operations Overview | visible in `demo_readonly`, `pilot_review`, `standard` | Read-only canonical operations surface or safe unavailable-data message without mutation. | DB/source/output writes | `contract_passed`; `bootstrap_only`; `pending_owner_visual_confirmation`; route click skipped | pending |
| Energy Analysis | visible in `demo_readonly`, `pilot_review`, `standard` | Read-only canonical energy surface or safe missing-Gold warning without fallback mutation. | ETL, materialization, DB/source/output writes | `contract_passed`; `bootstrap_only`; `pending_owner_visual_confirmation`; route click skipped | pending |
| Operational Decision Support | visible in `demo_readonly`, `pilot_review`, `standard` | Read-only decision-support surface or safe unavailable-data message without legacy/synthetic fallback mutation. | production solver claims, ETL, materialization, DB/source/output writes | `contract_passed`; `bootstrap_only`; `pending_owner_visual_confirmation`; route click skipped | pending |
| Efficiency Prediction & Governance | visible in `demo_readonly`, `pilot_review`, `standard` | Reviewer-facing inference/governance surfaces; retraining controls hidden in read-only modes. | retraining, artifact promotion, model/preprocessor/provenance replacement | `contract_passed`; `bootstrap_only`; `pending_owner_visual_confirmation`; route click skipped | pending |
| Maintenance | visible in `demo_readonly`, `pilot_review`, `standard` | Evidence and browse surfaces; upload/integration controls hidden in read-only modes. | maintenance upload, maintenance integration, maintenance DB writes | `contract_passed`; `bootstrap_only`; `pending_owner_visual_confirmation`; route click skipped | pending |
| Experimental Intelligence Lab | hidden in `demo_readonly`; visible in `pilot_review` and `standard` | Hidden under conservative review mode; optional `pilot_review` observation remains experimental and non-defended. | real-input upload, exports, manual stress-test controls, production-defense claims | `contract_passed`; `bootstrap_only` for app shell; `pending_owner_visual_confirmation`; route click skipped | pending |

## Owner-review capture template summary

D3 adds:

```text
docs/operations/FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md
```

The template includes:

- purpose;
- scope;
- reviewer / owner roles;
- selected branch / commit fields;
- runtime mode fields;
- pre-review safety checks;
- route-by-route owner observation table;
- controls not to click;
- evidence capture fields;
- DB/artifact safety confirmation;
- accepted pilot risks;
- rejected production risks;
- sign-off placeholders;
- escalation / no-go criteria;
- final owner decision placeholder.

Every owner/reviewer/sign-off field remains `TBD`.

## DB/artifact safety evidence

D3 did not write the original runtime DB and did not create DB files inside the GitHub-safe tree.

Observed safety evidence:

- GitHub-safe readiness preflight reported no repo-local DB files.
- `manufacturing_data.db` was not tracked.
- smoke workspace DB scan returned no DB or SQLite files.
- GitHub-safe tree DB scan returned no DB or SQLite files after the app smoke.
- Streamlit launched from `/tmp/leopaper_stage_d3_route_walkthrough/`, not from the GitHub-safe tree and not from the original runtime repo.
- No raw Excel files, generated `etl_outputs`, model artifacts, or DB files were staged during D3.

## Owner sign-off status

Owner sign-off status: pending.

D3 does not mark operational owner acceptance, technical reviewer acceptance, DB owner acceptance, rollback owner assignment, final owner decision, production deployment, live/shared DB migration, or runtime carry-forward adoption as complete.

## Runtime behavior impact

No runtime behavior changed.

D3 does not modify:

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

Validation commands for D3:

```bash
git status --short
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 -m compileall core modules scripts tests
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 -m unittest tests.test_factory_deployment_readiness_check
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 scripts/check_factory_deployment_readiness.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d3_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Observed final validation result:

- `git status --short` showed only the intended D3 docs/report/index/walkthrough-pack files before staging.
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
- `git status --ignored --short | head -100` showed only the intended D3 docs/report/index/walkthrough-pack changes plus ignored Python `__pycache__/` folders.

## Skipped/blocked items

Skipped by design:

- browser route clicking;
- button clicking;
- file uploads;
- ETL execution;
- historical backfill;
- canonical materialization;
- carry-forward reconciliation execution;
- live/shared DB migration;
- model retraining;
- artifact promotion;
- production owner sign-off completion.

Rationale:

- no stable non-writing route-selection pattern was identified;
- Streamlit sidebar clicking could risk interactions with controls the prompt forbids;
- D3 can safely prove internal route evidence through route contracts, runtime capabilities, static imports, and `/tmp` bootstrap smoke;
- owner visual confirmation must remain a controlled human review step.

## Remaining risks

- Actual owner/reviewer route visual confirmation is still pending.
- Owner, technical reviewer, DB owner, and rollback owner sign-off remain unfilled.
- Production deployment remains blocked.
- Live/shared DB migration remains blocked.
- Promoted DB writes remain blocked.
- Runtime carry-forward adoption remains blocked.
- Model retraining and artifact promotion remain blocked.
- Full production workflow execution remains unproven.
- Production monitoring, access control, support ownership, and incident response remain future work.
- Experimental Intelligence Lab remains experimental and non-defended for production claims.

## Recommended D4

Recommended D4: owner-review evidence capture closeout.

D4 should use `docs/operations/FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md` to record real owner/reviewer observations, selected branch, commit SHA, runtime mode, route evidence, no-click/no-upload/no-write confirmations, validation and unsafe scan results, accepted pilot risks, rejected production risks, and explicit owner decisions. D4 should still keep live/shared DB migration, promoted DB writes, runtime carry-forward adoption, and model promotion blocked unless a separate approved stage opens that scope.
