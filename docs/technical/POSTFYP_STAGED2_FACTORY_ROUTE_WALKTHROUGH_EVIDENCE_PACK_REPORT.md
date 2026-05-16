# Post-FYP Stage D2 Factory Route Walkthrough Evidence Pack Report

## Purpose

Stage D2 creates a controlled factory route walkthrough evidence pack for operator and reviewer assessment.

It converts the Stage D1 route workflow smoke checklist into a practical evidence-capture document with route-level observation fields, forbidden-action boundaries, pass/skip/block criteria, safety checks, and owner/reviewer placeholders.

## Scope

This is a read-only documentation and evidence-pack stage.

Changed files are limited to:

- `docs/operations/FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK.md`
- `docs/technical/POSTFYP_STAGED2_FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK_REPORT.md`
- `docs/operations/FACTORY_PILOT_HANDOFF_PACK.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

D2 does not modify `app.py`, active runtime Python files, tests, source data, generated outputs, model artifacts, DB files, Streamlit write controls, source-discovery default policy, runtime canonical predicates, carry-forward runtime wiring, or DQ runtime behavior.

## Factory deployment objective

The target remains Factory Production Deployment readiness with production-grade safety gates.

D2 supports that target by preparing practical route-level operator review evidence. It does not claim production deployment completion. Production deployment, live/shared DB migration, promoted DB writes, runtime carry-forward adoption, model promotion, monitoring, and owner acceptance remain gated.

## Evidence basis from D1

D1 provided the basis for D2:

- readiness preflight passed with `success: true`, `7` checks, and no critical failures;
- route/runtime tests passed with `10` tests;
- source-discovery and carry-forward guardrail tests passed with `34` tests;
- source-discovery compare diagnostics passed with March 2026 expected-blocked;
- Streamlit bootstrap smoke ran only from `/tmp/leopaper_stage_d1_route_smoke/`;
- runtime mode was `demo_readonly`;
- HTTP bootstrap returned `200 text/html 891`;
- startup log scan was clean for `Traceback`, `Exception`, and `Error`;
- process stopped cleanly;
- no DB files appeared in the GitHub-safe tree or smoke workspace;
- automated route clicking was safely skipped because there was no stable non-click Streamlit route URL and clicking could risk forbidden controls;
- manual route walkthrough capture was deferred to an operator checklist.

## Walkthrough pack summary

D2 adds:

```text
docs/operations/FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK.md
```

The pack includes:

- purpose and scope;
- selected branch / commit placeholders;
- runtime mode guidance;
- operator/reviewer role placeholders;
- pre-walkthrough safety checks;
- route-by-route evidence table;
- evidence capture instructions;
- controls that must not be clicked;
- pass/skip/block criteria;
- DB/artifact safety checks;
- failure escalation rules;
- owner/reviewer initials placeholders;
- final provisional conclusion.

The pack is designed for factory-side operator/reviewer assessment, not FYP demo polish.

## Route-level evidence model

The route-level model covers:

| Route | Classification | Default status |
| --- | --- | --- |
| ETL Pipeline | defended-core | pending owner walkthrough |
| Canonical Operations Overview | defended-core | pending owner walkthrough |
| Energy Analysis | defended-core | pending owner walkthrough |
| Operational Decision Support | defended-core | pending owner walkthrough |
| Efficiency Prediction & Governance | defended-core | pending owner walkthrough |
| Maintenance | defended-core | pending owner walkthrough |
| Experimental Intelligence Lab | experimental | pending owner walkthrough |

Each route records:

- runtime mode where visible;
- defended-core or experimental classification;
- expected observation;
- forbidden actions;
- evidence to capture;
- observed status placeholder;
- reviewer initials placeholder;
- notes placeholder.

No route is marked as passed because no actual manual walkthrough evidence was supplied.

## Pending owner walkthrough status

Owner walkthrough status: pending.

D2 does not fill owner, reviewer, DB owner, or rollback owner sign-off placeholders. It does not mark route observations as passed. It does not convert Stage D1 bootstrap evidence into owner acceptance.

The correct next evidence step is a real owner/reviewer route walkthrough using the D2 evidence pack.

## DB/artifact safety boundary

The DB/artifact boundary remains unchanged:

- `manufacturing_data.db` is local runtime state and must not be staged, committed, pushed, copied into the GitHub-safe tree, or treated as final factory deployment state;
- no DB file may be created inside the GitHub-safe tree;
- no `*.db`, `*.sqlite`, or `*.sqlite3` file may be staged;
- raw Excel files must not be staged in D2;
- generated `etl_outputs` artifacts must not be staged in D2;
- model artifacts must not be retrained, promoted, or staged in D2;
- any future DB rehearsal must remain temp-only unless a later approved migration stage changes that boundary.

## Live DB migration stance

Live/shared DB migration remains blocked.

D2 does not execute migration, approve migration, rehearse migration, promote a temp DB, or provide backup/checksum/rollback/restore evidence for promoted DB writes. Any future live/shared migration must follow the migration gate checklist and separate approval.

## Runtime carry-forward stance

Runtime carry-forward remains disabled-by-default and not active runtime behavior.

D2 does not execute carry-forward reconciliation, wire carry-forward into ETL, change carry-forward defaults, change canonical predicates, or claim carry-forward is production-ready runtime behavior.

## Runtime behavior impact

No runtime behavior changed.

D2 does not modify:

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

Validation commands for D2:

```bash
git status --short
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 -m compileall core modules scripts tests
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 -m unittest tests.test_factory_deployment_readiness_check
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 scripts/check_factory_deployment_readiness.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_d2_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Readiness refresh result recorded before edits:

- `scripts/check_factory_deployment_readiness.py` returned `success: true`;
- `check_count: 7`;
- `passed_count: 7`;
- `critical_failures: []`.

Observed final validation result:

- `git status --short` showed only the intended D2 docs/report/index/handoff-pack files before staging.
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
- `git status --ignored --short | head -100` showed only the intended D2 docs/report/index/handoff-pack changes plus ignored Python `__pycache__/` folders.

## Remaining risks

- Actual owner/reviewer walkthrough evidence is still pending.
- Owner, technical reviewer, DB owner, and rollback owner sign-off remain unfilled.
- Production deployment remains blocked.
- Live/shared DB migration remains blocked.
- Promoted DB writes remain blocked.
- Runtime carry-forward adoption remains blocked.
- Model retraining and artifact promotion remain blocked.
- Full production workflow execution remains unproven.
- Production monitoring, access control, support ownership, and incident response remain future work.
- Experimental Intelligence Lab remains experimental and non-defended for production claims.

## Recommended D3

Recommended D3: controlled owner/reviewer route walkthrough execution and evidence capture.

D3 should use `docs/operations/FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK.md` to record the selected branch, commit SHA, runtime mode, route observations, screenshots or typed notes, no-click/no-upload confirmations, validation and unsafe scan results, reviewer initials, accepted pilot risks, blocked production risks, and explicit escalation notes. D3 should keep live/shared DB migration, promoted DB writes, runtime carry-forward adoption, and model promotion blocked unless a separate approved stage opens that scope.
