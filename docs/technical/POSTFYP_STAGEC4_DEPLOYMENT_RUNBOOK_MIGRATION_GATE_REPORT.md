# Post-FYP Stage C4 Deployment Runbook Migration Gate Report

## Purpose

Stage C4 prepares factory deployment pilot operational materials after the Stage C3 app launch and route-smoke evidence.

It adds a deployment runbook, live/shared DB migration gate checklist, operator acceptance checklist, and a read-only deployment readiness preflight script.

## Scope

This is deployment-readiness preparation only.

C4 does not execute live/shared DB migration, run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire carry-forward into active ETL runtime, wire DQ rules into runtime behavior, add Streamlit write controls, create live DB mode, move files, delete files, rename files, archive files, or quarantine files.

Runtime code is unchanged. The only Python addition is a new standard-library read-only preflight script under `scripts/` plus focused tests.

## Factory deployment objective

The project target remains Factory Production Deployment readiness with production-grade safety gates.

C4 makes the next controlled factory deployment pilot handoff operationally safer by defining operator steps, migration approval gates, backup/checksum/rollback expectations, acceptance placeholders, and a machine-readable read-only preflight.

C4 does not claim production deployment is complete.

## Files changed

| File | Change type | Reason |
| --- | --- | --- |
| `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md` | Added | Provides operator startup, stop, boundary, smoke, and escalation guidance for controlled factory deployment pilot readiness. |
| `docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md` | Added | Defines approval evidence required before any future live/shared DB migration or promoted DB write. |
| `docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md` | Added | Provides sign-off placeholders and risk-acceptance checks for pilot readiness. |
| `scripts/check_factory_deployment_readiness.py` | Added | Adds a read-only standard-library JSON preflight for required files, unsafe local artifacts, Git DB tracking, tracked `etl_outputs`, carry-forward default, and runtime modes. |
| `tests/test_factory_deployment_readiness_check.py` | Added | Covers the new preflight helper with temporary fixtures and policy-import checks. |
| `README.md` | Updated | Adds minimal pointer to operations runbooks and the C4 preflight command. |
| `docs/DOCS_GUIDE.md` | Updated | Adds the new operations docs to the active operator navigation set. |
| `docs/technical/REBUILD_DOCS_INDEX.md` | Updated | Adds the C4 report and operations runbook pointers. |
| `docs/technical/POSTFYP_STAGEC4_DEPLOYMENT_RUNBOOK_MIGRATION_GATE_REPORT.md` | Added | Captures scope, summaries, validation, unsafe scans, risks, and C5 recommendation. |

## Deployment runbook summary

`docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md` defines:

- purpose and scope;
- controlled factory deployment pilot readiness objective;
- environment prerequisites;
- reviewed-branch selection rule;
- Python 3.11 / Streamlit launch procedure;
- `standard`, `demo_readonly`, and `pilot_review` runtime mode choices;
- startup and stop procedures;
- DB local-only boundary;
- source-data, generated-output, and model-artifact boundaries;
- carry-forward disabled-by-default boundary;
- live/shared DB migration gate;
- operational owner responsibilities;
- smoke test checklist;
- incident and rollback escalation;
- operator non-goals;
- known limitations before production launch.

The runbook states that the current branch line supports controlled factory deployment pilot readiness only and that production deployment is not complete.

## Migration gate checklist summary

`docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md` defines approval evidence required before any future live/shared DB migration or promoted DB write.

It requires:

- pre-migration backup;
- backup checksum proof;
- dry-run SQL diff;
- row-count baseline;
- duplicate `source_row_hash` baseline;
- carry-forward candidate traceability if carry-forward is involved;
- Gold delta review;
- reviewer acceptance;
- app/runtime smoke;
- rollback/restore plan;
- abort gates;
- no-main/no-force-push branch discipline;
- promotion approval record.

The checklist is approval-only. It does not execute migration.

## Operator acceptance checklist summary

`docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md` provides a sign-off template for controlled pilot readiness.

It includes:

- operator and reviewer role placeholders;
- pre-pilot checks;
- app launch checks;
- route checks;
- DB safety checks;
- source-data checks;
- generated-output checks;
- model-artifact checks;
- carry-forward disabled-state checks;
- evidence reports to review;
- known risks to accept;
- risks not accepted for production deployment;
- sign-off fields.

It explicitly separates pilot-readiness acceptance from production deployment approval.

## Read-only deployment preflight summary

`scripts/check_factory_deployment_readiness.py` is standard-library only.

It does not import Streamlit, connect to SQLite, create files, write files, run ETL, run backfill, run materialization, run migration, or inspect DB contents.

It checks:

- required deployment docs and runtime/config files exist;
- `manufacturing_data.db` is not tracked by Git;
- no `*.db`, `*.sqlite`, or `*.sqlite3` files exist under repo max depth 5;
- no `.venv`, `.conda311`, `.miniforge`, or `temp_uploads` folders exist under repo max depth 5;
- `etl_outputs/` exists and only `.gitkeep` / `ETL_OUTPUTS_GUIDE.md` are tracked;
- carry-forward default mode is `disabled`;
- runtime modes include `standard`, `demo_readonly`, and `pilot_review`.

Observed output summary during C4 validation:

```json
{
  "success": true,
  "summary": {
    "check_count": 7,
    "critical_failures": [],
    "passed_count": 7
  }
}
```

## What C4 proves

C4 proves:

- pilot handoff runbooks/checklists exist in `docs/operations/`;
- the read-only preflight helper can detect missing required docs in temporary fixtures;
- the helper detects repo-local DB files;
- the helper detects local environment folders;
- the helper confirms carry-forward default mode is disabled without importing Streamlit;
- the helper confirms runtime modes include `standard`, `demo_readonly`, and `pilot_review`;
- the helper does not create DB files;
- the GitHub-safe tree remains DB-free during validation;
- existing route/runtime and source-discovery/carry-forward guardrail tests still pass.

## What C4 does not prove

C4 does not prove:

- production deployment is complete;
- live/shared DB migration is safe to execute now;
- live rollback has been tested;
- full page-by-page factory workflow execution has passed;
- runtime carry-forward adoption is approved;
- model artifacts are production-upgraded;
- operational monitoring and incident response are complete.

## Runtime behavior impact

No active runtime behavior changed.

C4 did not modify `app.py`, active runtime Python modules under `core/` or `modules/`, runtime route definitions, runtime modes, runtime capabilities, source-discovery defaults, canonical predicates, data-quality runtime wiring, carry-forward runtime wiring, Streamlit controls, source data, generated outputs, model artifacts, or DB state.

The new preflight script is read-only and is not wired into runtime.

## Validation

Validation result: passed for the C4 docs plus read-only preflight scope.

Commands run:

```bash
git status --short
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_compile_pycache python3.11 -m compileall core modules scripts tests
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_newtest_pycache python3.11 -m unittest tests.test_factory_deployment_readiness_check
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_runtime_tests_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_guardrail_tests_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_script_pycache python3.11 scripts/check_factory_deployment_readiness.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_compare_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c4_compare_json_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Observed results:

- compileall passed;
- `tests.test_factory_deployment_readiness_check` passed with `7` tests;
- runtime route/path/mode/capability tests passed with `10` tests;
- source-discovery/carry-forward guardrail tests passed with `34` tests;
- `scripts/check_factory_deployment_readiness.py` returned `"success": true`;
- `scripts/compare_source_discovery_modes.py` returned `overall: PASS`;
- `scripts/compare_source_discovery_modes.py --json` returned `"success": true`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`.

## Unsafe file scan

Unsafe scan result: passed.

Commands run:

```bash
find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print
find . -maxdepth 5 \( -name ".venv" -o -name ".conda311" -o -name ".miniforge" -o -name "temp_uploads" \) -print
git ls-files manufacturing_data.db || true
git check-ignore --no-index -v manufacturing_data.db || true
git status --ignored --short | head -100
```

Observed results:

- DB scan returned no `*.db`, `*.sqlite`, or `*.sqlite3` files under max depth 5.
- Local environment/upload scan returned no `.venv`, `.conda311`, `.miniforge`, or `temp_uploads` folders under max depth 5.
- `git ls-files manufacturing_data.db || true` returned no tracked file.
- `git check-ignore --no-index -v manufacturing_data.db || true` returned `.gitignore:5:*.db manufacturing_data.db`.
- `git status --ignored --short | head -100` showed intended C4 docs/script/test/report changes plus ignored `__pycache__/` folders only.

## Remaining risks

- C4 is preparation and preflight only; it does not execute live/shared DB migration.
- App bootstrap and route contract evidence remain stronger than full page-by-page factory workflow evidence.
- Live rollback/restore is documented as a gate but not executed.
- Runtime carry-forward adoption remains disabled-by-default and unapproved.
- Production monitoring, access control, owner cadence, and incident response remain future deployment work.

## Recommended C5

Recommended C5 should be a read-only operations handoff review and owner-acceptance pack.

C5 should not execute live/shared DB migration. It should collect selected branch/commit, C3/C4 evidence, runbook review, owner sign-off placeholders, unresolved risks, and a go/no-go recommendation for whether a later live migration rehearsal stage may be planned.
