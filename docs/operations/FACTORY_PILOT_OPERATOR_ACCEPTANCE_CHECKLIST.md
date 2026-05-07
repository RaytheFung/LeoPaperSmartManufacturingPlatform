# Factory Pilot Operator Acceptance Checklist

## Purpose

This checklist gives operators and reviewers a sign-off template for controlled factory deployment pilot readiness.

It is not production deployment approval. It records whether the pilot-readiness evidence is acceptable for the selected branch.

## Operator / reviewer roles

| Role | Name | Responsibility | Date |
| --- | --- | --- | --- |
| Operational owner | TBD | Accept or reject pilot-readiness risk | TBD |
| Technical reviewer | TBD | Review validation, safety scans, and route evidence | TBD |
| DB owner | TBD | Confirm local DB and migration gate boundaries | TBD |
| Rollback owner | TBD | Own restore plan if a future migration is approved | TBD |

## Pre-pilot checks

- [ ] Selected branch and commit recorded.
- [ ] Latest Stage C report reviewed.
- [ ] `README.md` and `docs/LAUNCHING_TIPS.md` reviewed.
- [ ] `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` reviewed.
- [ ] `docs/technical/DATA_CONTRACTS_GUIDE.md` reviewed.
- [ ] `python3.11 scripts/check_factory_deployment_readiness.py` passed.
- [ ] No unresolved validation failure is accepted silently.

## App launch checks

- [ ] Python 3.11 launch path confirmed.
- [ ] Runtime mode selected.
- [ ] Streamlit starts on expected port.
- [ ] HTTP bootstrap succeeds.
- [ ] Logs show no immediate traceback.
- [ ] Process stops cleanly.

## Route checks

- [ ] ETL Pipeline route label present where expected.
- [ ] Canonical Operations Overview route label present.
- [ ] Energy Analysis route label present.
- [ ] Operational Decision Support route label present.
- [ ] Efficiency Prediction & Governance route label present.
- [ ] Maintenance route label present.
- [ ] Experimental Intelligence Lab visibility matches runtime mode.
- [ ] Loader-dependent legacy pages are not visible.

## DB safety checks

- [ ] No DB files exist inside the GitHub-safe tree.
- [ ] `manufacturing_data.db` is not tracked by Git.
- [ ] No live/shared DB migration has been executed.
- [ ] Any DB used for smoke or rehearsal is local-only or `/tmp`-only.
- [ ] Backup/checksum/rollback checklist is ready before any future promoted write.

## Source data checks

- [ ] `source_data/` is treated as source truth for accepted historical packages.
- [ ] Raw workbook changes are not staged.
- [ ] March 2026 remains blocked unless a later stage approves it.

## Generated output checks

- [ ] Generated `etl_outputs` files are not staged.
- [ ] Only `.gitkeep` and `ETL_OUTPUTS_GUIDE.md` are tracked under `etl_outputs/`.

## Model artifact checks

- [ ] Active model and preprocessor artifacts are unchanged.
- [ ] Provenance manifests are unchanged.
- [ ] No retraining or promotion occurred.

## Carry-forward disabled-state checks

- [ ] Default carry-forward mode is `disabled`.
- [ ] Carry-forward is not active ETL runtime behavior.
- [ ] No carry-forward reconciliation execution occurred.
- [ ] Any future carry-forward adoption requires a separate approval gate.

## Evidence reports to review

- [ ] `docs/technical/POSTFYP_STAGEC4_DEPLOYMENT_RUNBOOK_MIGRATION_GATE_REPORT.md`
- [ ] `docs/technical/POSTFYP_STAGEC3_APP_LAUNCH_ROUTE_SMOKE_REPORT.md`
- [ ] `docs/technical/POSTFYP_STAGEC2_PRODUCTION_DOCS_NAVIGATION_CLEANUP_REPORT.md`
- [ ] `docs/technical/POSTFYP_STAGEC1_PRODUCTION_READINESS_INVENTORY_REPORT.md`
- [ ] `docs/technical/POSTFYP_STAGEB13_1_FACTORY_DEPLOYMENT_ALIGNMENT_REPORT.md`
- [ ] `docs/technical/POSTFYP_STAGEB12_CSI_CARRY_FORWARD_AUDIT_SCHEMA_CLOSEOUT_REPORT.md`

## Known risks to accept

- [ ] App bootstrap smoke is not full route-by-route production execution.
- [ ] Local runtime DB is a rehearsal/review boundary.
- [ ] Operational owner acceptance is required before real pilot handoff.
- [ ] Production monitoring and incident response remain future work.

## Risks not accepted for production deployment

- [ ] Live/shared DB migration is not accepted by this checklist.
- [ ] Runtime carry-forward adoption is not accepted by this checklist.
- [ ] Model artifact promotion is not accepted by this checklist.
- [ ] Source-discovery expansion is not accepted by this checklist.
- [ ] Production launch completion is not accepted by this checklist.

## Sign-off fields / placeholders

| Field | Value |
| --- | --- |
| selected branch | TBD |
| selected commit SHA | TBD |
| runtime mode | TBD |
| app smoke result | TBD |
| route contract result | TBD |
| DB safety scan result | TBD |
| accepted pilot-readiness risks | TBD |
| rejected risks | TBD |
| operational owner sign-off | TBD |
| technical reviewer sign-off | TBD |
| date | TBD |
