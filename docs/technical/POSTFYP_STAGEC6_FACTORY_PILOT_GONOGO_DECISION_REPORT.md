# Post-FYP Stage C6 Factory Pilot Go/No-Go Decision Report

## Purpose

Stage C6 records the go/no-go decision for controlled factory pilot owner review after the Stage C handoff pack.

It decides whether the current Stage C branch line is ready for owner review while preserving the separate block on production deployment and live/shared DB migration.

## Scope

This is a read-only documentation and decision-gate stage.

C6 creates this decision report, creates the Stage C closeout report, adds a minimal C6 status note to the handoff pack, and updates the rebuild docs index. It does not modify active runtime Python files, run ETL, run historical backfill, run canonical materialization, run carry-forward reconciliation execution, write the original runtime `manufacturing_data.db`, create DB files in the GitHub-safe tree, promote a temp DB, execute live/shared DB migration, retrain/promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire DQ rules into runtime behavior, add Streamlit write controls, create live DB mode, or move/delete/rename/archive/quarantine files.

## Evidence basis from C1-C5

| Stage | Evidence basis | C6 interpretation |
| --- | --- | --- |
| C1 | Production-readiness inventory | Active runtime, docs, tests, source, generated output, model, legacy, and safety surfaces are identified. |
| C2 | Production docs navigation cleanup | Operator-facing docs now foreground pilot readiness, local DB safety, gated migration, and disabled carry-forward. |
| C3 | App launch and route smoke | `/tmp`-only Streamlit bootstrap in `demo_readonly` returned HTTP `200 text/html 891` with no immediate traceback/error evidence. |
| C4 | Deployment runbook, migration checklist, operator checklist, readiness preflight | Operational controls and a read-only JSON preflight exist for pilot review. |
| C5 | Factory pilot handoff pack and acceptance report | Owner-review materials, sign-off placeholders, accepted pilot risks, and blocked production risks are consolidated. |

## Readiness preflight result

Command run during C6:

```bash
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_preflight_pycache python3.11 scripts/check_factory_deployment_readiness.py
```

Observed JSON summary:

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

Observed checks passed:

- required files present;
- `manufacturing_data.db` not tracked;
- no repo-local DB files;
- no local environment or upload folders;
- tracked `etl_outputs` limited to `.gitkeep` and `ETL_OUTPUTS_GUIDE.md`;
- carry-forward default disabled;
- supported runtime modes include `standard`, `demo_readonly`, and `pilot_review`.

## App smoke result

C6 did not relaunch Streamlit because the prompt defined C6 as docs/decision-only and said not to launch Streamlit unless a docs path issue required repeating smoke.

The app-smoke evidence basis remains C3:

- Streamlit launched from `/tmp/leopaper_stage_c3_app_smoke/`, not from the GitHub-safe tree.
- Runtime mode was `SMART_MFG_RUNTIME_MODE=demo_readonly`.
- Python was `3.11.15`.
- Streamlit was `1.31.0`.
- Listener was `127.0.0.1:8502`.
- HTTP bootstrap returned `200 text/html 891`.
- Log scan found no `Traceback`, `Exception`, or `Error`.
- The process stopped cleanly.
- No DB file appeared in the GitHub-safe tree or smoke workspace.

## Route contract result

C6 relies on the route-contract evidence from C3 and refreshes the route/runtime tests in the C6 validation matrix.

C3 proved the defended core route labels remained visible in the expected runtime modes, the Experimental Intelligence Lab was hidden in `demo_readonly`, and loader-dependent legacy pages were not visible.

## Operations runbook result

The operations runbook exists at `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md`.

It covers branch selection, Python/Streamlit launch, runtime modes, startup and stop procedure, DB/source/output/model boundaries, carry-forward disabled-by-default boundary, live/shared DB migration gate, owner responsibilities, smoke checks, incident/rollback escalation, and operator non-goals.

## Handoff pack result

The handoff pack exists at `docs/operations/FACTORY_PILOT_HANDOFF_PACK.md`.

C6 adds a minimal status note that the pack is ready for owner review while keeping sign-off placeholders unfilled. Production deployment remains blocked until future gates pass.

## Owner sign-off status

Owner sign-off status: not provided.

C6 does not mark operational owner acceptance, technical reviewer acceptance, DB owner acceptance, rollback owner assignment, or final go/no-go sign-off as complete because no actual owner/reviewer decision evidence was provided by the user.

## Go/no-go decision

Provisional GO for factory pilot owner review; NO-GO for production deployment/live DB migration.

This decision means the current Stage C materials are suitable for owner/reviewer assessment of controlled pilot readiness. It does not approve production launch, promoted DB writes, live/shared DB migration, or runtime carry-forward adoption.

## Go conditions

The provisional controlled-pilot owner-review GO is based on:

- C1-C5 evidence exists and is indexed;
- C3 app-shell smoke evidence passed;
- C4 runbook/checklists and readiness preflight exist;
- C6 readiness preflight returned `"success": true`;
- owner sign-off placeholders remain explicit and unfilled;
- live/shared DB migration remains blocked;
- carry-forward remains disabled-by-default;
- no active runtime behavior is changed by C6.

## No-go / blocked conditions

NO-GO conditions for production deployment and live/shared DB migration:

- no actual owner/reviewer sign-off has been provided;
- live/shared DB migration gate has not been completed;
- backup/checksum/rollback/restore evidence for promoted DB writes has not been executed;
- full route-by-route production workflow execution has not been proven;
- runtime carry-forward adoption has not been approved;
- production monitoring, access policy, support ownership, and incident response remain incomplete.

## Accepted controlled-pilot risks

These risks may be accepted only for controlled pilot owner review, not production deployment:

- app bootstrap smoke is not full production workflow execution;
- local runtime DB state is a review/rehearsal boundary;
- owner acceptance is pending;
- future migration planning may require temp-only rehearsal evidence before any promoted DB write;
- production operations ownership is still not complete.

## Blocked production-deployment risks

These risks are blocked for production deployment:

- live/shared DB migration;
- promoted DB writes;
- runtime carry-forward adoption;
- model artifact retraining or promotion;
- source-discovery policy expansion;
- runtime canonical predicate changes;
- data-quality runtime enforcement;
- production launch completion without owner acceptance and migration gates.

## Recommended next stage

Recommended next stage: controlled factory pilot owner-review evidence capture.

That stage should record actual owner/reviewer decisions, selected branch and commit, accepted pilot risks, rejected risks, runtime mode, smoke evidence review, readiness preflight result, unsafe scan result, DB owner boundary acceptance, and rollback owner assignment. It should still keep live/shared DB migration blocked unless a separate approved migration-planning stage opens that scope.

## Runtime behavior impact

No runtime behavior changed.

C6 does not modify `app.py`, active runtime Python files, runtime routes, runtime modes, runtime capabilities, source-discovery defaults, runtime canonical predicates, DQ runtime behavior, carry-forward runtime wiring, Streamlit controls, source data, generated outputs, model artifacts, or DB state.

## Validation

Validation result: passed for the C6 documentation and decision-gate scope.

Commands run:

```bash
git status --short
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_compile_pycache python3.11 -m compileall core modules scripts tests
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_readiness_tests_pycache python3.11 -m unittest tests.test_factory_deployment_readiness_check
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_runtime_tests_pycache python3.11 -m unittest tests.test_runtime_paths tests.test_app_route_contract tests.test_runtime_mode tests.test_runtime_capabilities
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_guardrail_tests_pycache python3.11 -m unittest tests.test_source_discovery_default_switch tests.test_csi_carry_forward_config tests.test_csi_carry_forward_runtime_adapter
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_readiness_pycache python3.11 scripts/check_factory_deployment_readiness.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_compare_pycache python3.11 scripts/compare_source_discovery_modes.py
PYTHONPYCACHEPREFIX=/tmp/leopaper_stage_c6_compare_json_pycache python3.11 scripts/compare_source_discovery_modes.py --json
```

Observed results:

- compileall passed;
- `tests.test_factory_deployment_readiness_check` passed with `7` tests;
- runtime route/path/mode/capability tests passed with `10` tests;
- source-discovery/carry-forward guardrail tests passed with `34` tests;
- `scripts/check_factory_deployment_readiness.py` returned `"success": true`, `check_count: 7`, `passed_count: 7`, and no critical failures;
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
- `git status --ignored --short | head -100` showed the intended C6 docs/report/index changes plus ignored `__pycache__/` folders only.

## Remaining risks

- Actual owner/reviewer decisions are still missing.
- App smoke evidence remains bootstrap-level, not full production route execution.
- Live/shared DB migration remains unexecuted.
- Live rollback/restore remains unexecuted.
- Runtime carry-forward adoption remains unapproved.
- Production monitoring, access control, support ownership, and incident response remain future work.
