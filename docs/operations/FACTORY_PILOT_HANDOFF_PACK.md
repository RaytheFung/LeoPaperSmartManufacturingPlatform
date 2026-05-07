# Factory Pilot Handoff Pack

## Purpose

This handoff pack consolidates the Stage C3 app-smoke evidence and Stage C4 operational runbooks/checklists into one controlled factory pilot handoff record.

It is intended for operational owner and technical reviewer acceptance before any factory pilot handoff.

## Scope

This pack is read-only operational documentation.

It does not approve production deployment, live/shared DB migration, promoted DB writes, runtime carry-forward adoption, ETL execution, historical backfill, canonical materialization, ML artifact promotion, source-discovery policy changes, runtime canonical predicate changes, or data-quality runtime wiring.

## Selected branch / commit placeholder

| Field | Value |
| --- | --- |
| selected branch | TBD by reviewer |
| selected commit SHA | TBD by reviewer |
| runtime mode for pilot smoke | TBD, recommended `demo_readonly` unless `pilot_review` is explicitly approved |
| operational owner | TBD |
| technical reviewer | TBD |
| DB owner | TBD |
| rollback owner | TBD |
| acceptance date | TBD |

## Factory deployment pilot objective

The objective is controlled factory deployment pilot readiness with production-grade safety gates.

This means the branch should be ready for operational review, app-shell smoke, route-contract review, and explicit owner acceptance. It does not mean the system is production-launched or that local runtime state is final factory deployment state.

## C6 status note

Stage C6 marks this handoff pack ready for owner review with the decision: provisional GO for factory pilot owner review; NO-GO for production deployment/live DB migration.

Sign-off placeholders remain unfilled because no actual operational owner, technical reviewer, DB owner, or rollback owner decision evidence has been provided. Production deployment remains blocked until future owner-acceptance, migration, backup/checksum/rollback, and operational gates pass.

## What is ready for pilot review

- Stage C1 identified active runtime, source, generated output, model artifact, legacy, and docs surfaces.
- Stage C2 cleaned operator-facing documentation and warning boundaries.
- Stage C3 proved the app shell could launch from a `/tmp` smoke workspace in `demo_readonly` mode and return HTTP `200 text/html` without traceback.
- Stage C3 confirmed route visibility for `standard`, `demo_readonly`, and `pilot_review`.
- Stage C4 added the deployment runbook, migration gate checklist, operator acceptance checklist, and read-only readiness preflight.
- The deployment readiness preflight can confirm required docs/files, no tracked `manufacturing_data.db`, no repo-local DB files, no local env/upload folders, tracked `etl_outputs` control files only, disabled carry-forward default, and expected runtime modes.

## What is not production-complete

- Live/shared DB migration has not been executed.
- Promoted DB writes are not approved.
- Runtime carry-forward adoption is not active.
- Live rollback/restore has not been executed.
- Full route-by-route production workflow execution has not been proven.
- Model artifacts have not been retrained or promoted in Stage C.
- Production monitoring, support ownership, access control, and incident response are not complete.

## Required operator/reviewer roles

| Role | Required responsibility |
| --- | --- |
| Operational owner | Accept or reject pilot-readiness risk and confirm handoff scope. |
| Technical reviewer | Review branch, commit, validation, smoke evidence, and safety scans. |
| DB owner | Confirm local-only DB boundary and migration gate requirements. |
| Rollback owner | Confirm rollback/restore ownership before any later promoted DB write. |

## Pre-handoff checks

- [ ] Selected branch recorded.
- [ ] Selected commit SHA recorded.
- [ ] Latest Stage C report reviewed.
- [ ] `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md` reviewed.
- [ ] `docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md` reviewed.
- [ ] `docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md` reviewed.
- [ ] `python3.11 scripts/check_factory_deployment_readiness.py` returns success.
- [ ] Compile/unit/source-discovery validation passes.
- [ ] Unsafe file scan returns no DB or local env/upload artifacts in the GitHub-safe tree.
- [ ] No raw source, generated output, or model artifact change is staged.

## App launch evidence from C3

Stage C3 launched Streamlit only from `/tmp/leopaper_stage_c3_app_smoke/` in `SMART_MFG_RUNTIME_MODE=demo_readonly`.

Observed C3 evidence:

- Python: `Python 3.11.15`.
- Streamlit: `1.31.0`.
- address: `127.0.0.1`.
- port: `8502`.
- HTTP bootstrap: `200 text/html 891`.
- log evidence had no `Traceback`, `Exception`, or `Error` lines.
- process stopped cleanly.
- no DB files appeared in the GitHub-safe tree or smoke workspace.

## Deployment runbook evidence from C4

Stage C4 added `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md`.

The runbook covers:

- branch selection;
- Python / Streamlit launch;
- runtime mode choices;
- startup and stop procedures;
- DB local-only boundary;
- source data boundary;
- generated output boundary;
- model artifact boundary;
- carry-forward disabled-by-default boundary;
- live/shared DB migration gate;
- owner responsibilities;
- smoke checklist;
- incident and rollback escalation;
- operator non-goals.

## Readiness preflight evidence from C4

Stage C4 added `scripts/check_factory_deployment_readiness.py`.

The helper is standard-library only and read-only. It does not import Streamlit, connect to SQLite, create files, or write files.

Expected success summary:

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

## DB local-only boundary

`manufacturing_data.db` is local runtime state and must not be staged, committed, pushed, copied into the GitHub-safe tree, or treated as final factory deployment state.

Any DB used for smoke or rehearsal must remain local-only or `/tmp`-only unless a later approved migration stage explicitly changes that boundary.

## Source data boundary

`source_data/` is source truth for accepted historical packages.

Raw workbook changes must not be staged during pilot handoff. March 2026 remains blocked/out of canonical scope unless a later approved stage reopens that boundary.

## Generated output boundary

`etl_outputs/` is generated output, not source truth.

Only `.gitkeep` and `ETL_OUTPUTS_GUIDE.md` should be tracked. Generated reports, mappings, summaries, and caches must not be staged as product state.

## Model artifact boundary

Active model and preprocessor artifacts remain guarded runtime artifacts with provenance manifests.

C5 does not retrain, replace, promote, or approve promotion of model artifacts.

## Carry-forward disabled-by-default boundary

CSI carry-forward remains disabled-by-default and is not active ETL, materialization, Streamlit, DQ, ML, or app behavior.

Carry-forward evidence from Stage B remains governance/preflight evidence only until a separate adoption gate approves runtime wiring.

## Live/shared DB migration blocked boundary

Live/shared DB migration remains blocked pending a separate approval stage.

The migration gate must include backup, checksum, dry-run SQL diff, row-count baseline, duplicate source-hash baseline, carry-forward traceability if relevant, Gold delta review, reviewer acceptance, app/runtime smoke, rollback/restore proof, and abort criteria.

## Evidence reports to review

- `docs/technical/POSTFYP_STAGEC5_FACTORY_PILOT_HANDOFF_ACCEPTANCE_REPORT.md`
- `docs/technical/POSTFYP_STAGEC4_DEPLOYMENT_RUNBOOK_MIGRATION_GATE_REPORT.md`
- `docs/technical/POSTFYP_STAGEC3_APP_LAUNCH_ROUTE_SMOKE_REPORT.md`
- `docs/technical/POSTFYP_STAGEC2_PRODUCTION_DOCS_NAVIGATION_CLEANUP_REPORT.md`
- `docs/technical/POSTFYP_STAGEC1_PRODUCTION_READINESS_INVENTORY_REPORT.md`
- `docs/technical/POSTFYP_STAGEB13_1_FACTORY_DEPLOYMENT_ALIGNMENT_REPORT.md`
- `docs/technical/POSTFYP_STAGEB12_CSI_CARRY_FORWARD_AUDIT_SCHEMA_CLOSEOUT_REPORT.md`
- `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md`
- `docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md`
- `docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md`

## Go/no-go checklist

| Check | Status |
| --- | --- |
| selected branch and commit recorded | TBD |
| readiness preflight passes | TBD |
| compile/unit/source-discovery validation passes | TBD |
| unsafe file scan passes | TBD |
| C3 app-smoke evidence reviewed | TBD |
| C4 runbook/checklists reviewed | TBD |
| local DB boundary accepted | TBD |
| live/shared DB migration remains blocked | TBD |
| carry-forward disabled-state accepted | TBD |
| production blockers accepted as blockers | TBD |
| operational owner sign-off captured | TBD |

## Sign-off placeholders

| Field | Value |
| --- | --- |
| go/no-go decision | TBD |
| accepted pilot risks | TBD |
| blocked production risks | TBD |
| operational owner | TBD |
| operational owner decision | TBD |
| technical reviewer | TBD |
| technical reviewer decision | TBD |
| DB owner | TBD |
| rollback owner | TBD |
| date | TBD |

## Escalation / rollback note

If a DB file appears in the GitHub-safe tree, a runtime DB is modified outside an approved plan, validation fails, route visibility differs from the expected runtime mode, or a write-capable action is triggered accidentally, stop the handoff and escalate to the operational owner and technical reviewer.

Rollback for any future DB mutation must follow `docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md`. C5 does not execute rollback because C5 does not execute migration or DB writes.

## Remaining production blockers

- Live/shared DB migration approval and execution remain future work.
- Backup/checksum/rollback/restore evidence for promoted DB writes remains future work.
- Full route-by-route production workflow smoke remains future work.
- Runtime carry-forward adoption remains unapproved.
- Production monitoring, access control, support ownership, and incident response remain future work.
