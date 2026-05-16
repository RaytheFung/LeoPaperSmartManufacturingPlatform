# Factory Owner Review Capture Template

## Purpose

This template captures factory-side owner and reviewer decisions after a controlled route walkthrough.

It is designed for owner-review evidence capture after the internal Stage D3 rehearsal. It does not approve production deployment, live/shared DB migration, promoted DB writes, runtime carry-forward adoption, ETL execution, historical backfill, canonical materialization, model retraining, or artifact promotion.

## Scope

Use this template when a real operational owner, technical reviewer, DB owner, and rollback owner are available to review the selected branch and route walkthrough evidence.

Leave every sign-off and final decision field as `TBD` until user-provided real sign-off evidence exists.

## Reviewer / owner roles

| Role | Name | Responsibility | Initials | Date |
| --- | --- | --- | --- | --- |
| Operational owner | TBD | Accept or reject controlled pilot-readiness route evidence | TBD | TBD |
| Technical reviewer | TBD | Review validation, route observations, runtime mode, and safety scans | TBD | TBD |
| DB owner | TBD | Confirm local DB boundary and migration gate stance | TBD | TBD |
| Rollback owner | TBD | Confirm rollback ownership before any future promoted DB write | TBD | TBD |

## Selected branch / commit

| Field | Value |
| --- | --- |
| selected branch | TBD |
| selected commit SHA | TBD |
| review date | TBD |
| review environment | TBD |
| Streamlit launch workspace | TBD, must not be GitHub-safe tree or original runtime repo |
| Streamlit port | TBD |
| validation log path | TBD |
| unsafe scan evidence path | TBD |

## Runtime mode

Recommended route review mode: `demo_readonly`.

Use `demo_readonly` for the six defended-core routes. Use `pilot_review` only if the owner explicitly needs to observe Experimental Intelligence Lab visibility. Do not use `standard` unless a later approved operational write-mode review opens that scope.

| Runtime mode reviewed | Value |
| --- | --- |
| defended-core route mode | TBD |
| experimental route mode, if used | TBD |
| reason for `pilot_review`, if used | TBD |

## Pre-review safety checks

- [ ] Selected branch and commit SHA are recorded.
- [ ] Runtime mode is recorded.
- [ ] Streamlit launch workspace is outside the GitHub-safe tree.
- [ ] Streamlit launch workspace is outside the original runtime repo.
- [ ] `python3.11 scripts/check_factory_deployment_readiness.py` passed.
- [ ] Route/runtime tests passed.
- [ ] Source-discovery/carry-forward guardrail tests passed.
- [ ] No DB file exists inside the GitHub-safe tree.
- [ ] `manufacturing_data.db` is not tracked.
- [ ] No DB file is staged.
- [ ] No raw Excel file is staged.
- [ ] No generated `etl_outputs` artifact is staged.
- [ ] No model artifact is staged.
- [ ] No local env or upload folder is staged.
- [ ] Owner/reviewer sign-off is not pre-filled.

## Route-by-route owner observation table

| Route | Runtime mode to observe | Expected owner observation | Forbidden actions | Owner observation notes | Status | Owner/reviewer initials |
| --- | --- | --- | --- | --- | --- | --- |
| ETL Pipeline | `demo_readonly` | Route is visible and read-only; upload/process/backfill/month-write controls are hidden or unavailable. | Do not upload files; do not process ETL; do not run backfill; do not materialize canonical tables. | TBD | TBD | TBD |
| Canonical Operations Overview | `demo_readonly` | Route is visible as a read-only canonical operations surface or reports unavailable data without mutation. | Do not trigger writes; do not alter DB/source/output state. | TBD | TBD | TBD |
| Energy Analysis | `demo_readonly` | Route is visible as a read-only canonical energy surface or reports missing canonical Gold data without fallback mutation. | Do not run ETL; do not materialize; do not alter DB/source/output state. | TBD | TBD | TBD |
| Operational Decision Support | `demo_readonly` | Route is visible as read-only decision support or reports unavailable canonical data without legacy/synthetic fallback mutation. | Do not treat as production solver; do not trigger ETL/materialization; do not alter DB/source/output state. | TBD | TBD | TBD |
| Efficiency Prediction & Governance | `demo_readonly` | Route is visible with reviewer-facing inference/governance surfaces; retraining controls are hidden. | Do not retrain; do not promote artifacts; do not replace model/preprocessor/provenance files. | TBD | TBD | TBD |
| Maintenance | `demo_readonly` | Route is visible with evidence and browse surfaces; upload/integration controls are hidden. | Do not upload maintenance files; do not integrate maintenance into ETL; do not write maintenance DB state. | TBD | TBD | TBD |
| Experimental Intelligence Lab | `demo_readonly`, then `pilot_review` only if approved | Hidden in `demo_readonly`; optionally visible in `pilot_review` as experimental and non-defended for production claims. | Do not upload real-input files; do not export artifacts; do not run manual stress-test controls; do not claim production defense. | TBD | TBD | TBD |

## Controls not to click

- Upload controls.
- ETL process controls.
- Historical backfill controls.
- Canonical materialization controls.
- Month-write controls.
- Maintenance upload controls.
- Maintenance integration controls.
- Model retraining controls.
- Model or artifact promotion controls.
- Experimental real-input upload controls.
- Experimental export controls.
- Experimental manual stress-test controls.
- Carry-forward reconciliation controls or scripts.
- Live/shared DB migration controls or scripts.

## Evidence capture fields

| Evidence item | Value |
| --- | --- |
| route screenshots or typed notes captured | TBD |
| validation command results captured | TBD |
| unsafe scan results captured | TBD |
| no-click confirmation | TBD |
| no-upload confirmation | TBD |
| no ETL/backfill/materialization confirmation | TBD |
| no carry-forward reconciliation confirmation | TBD |
| no live/shared DB migration confirmation | TBD |
| no model retraining/promotion confirmation | TBD |
| no DB/source/output/model artifact mutation confirmation | TBD |

## DB/artifact safety confirmation

| Safety check | Owner/reviewer confirmation |
| --- | --- |
| GitHub-safe tree has no DB files | TBD |
| smoke/walkthrough workspace has no DB files | TBD |
| `manufacturing_data.db` remains local-only and untracked | TBD |
| no DB files staged | TBD |
| no raw Excel files staged | TBD |
| no generated `etl_outputs` artifacts staged | TBD |
| no model artifacts staged | TBD |
| no temp DB promoted | TBD |

## Accepted pilot risks

| Risk | Accepted? | Notes |
| --- | --- | --- |
| Route walkthrough is controlled owner-review evidence, not production launch | TBD | TBD |
| Local runtime DB remains a review/rehearsal boundary | TBD | TBD |
| Experimental Intelligence Lab remains non-defended for production claims | TBD | TBD |
| Live/shared DB migration is still future gated work | TBD | TBD |
| Monitoring, access control, support ownership, and incident response remain future work | TBD | TBD |

## Rejected production risks

| Risk | Rejected for production deployment? | Notes |
| --- | --- | --- |
| Live/shared DB migration without migration gate | TBD | TBD |
| Promoted DB writes without backup/checksum/rollback evidence | TBD | TBD |
| Runtime carry-forward adoption without adoption gate | TBD | TBD |
| Model artifact promotion without model-promotion gate | TBD | TBD |
| Production launch completion without owner approval | TBD | TBD |

## Sign-off placeholders

| Field | Value |
| --- | --- |
| operational owner sign-off | TBD |
| technical reviewer sign-off | TBD |
| DB owner sign-off | TBD |
| rollback owner sign-off | TBD |
| accepted pilot risks | TBD |
| rejected production risks | TBD |
| final go/no-go decision | TBD |
| decision date | TBD |

## Escalation / no-go criteria

Declare no-go and escalate if:

- a DB file appears inside the GitHub-safe tree;
- a DB file is staged;
- `manufacturing_data.db` becomes tracked;
- a forbidden control is clicked;
- a file is uploaded;
- ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, or artifact promotion is triggered;
- route visibility differs from the runtime-mode contract;
- startup logs show traceback/error evidence;
- owner/reviewer cannot confirm the no-click/no-upload/no-write boundary;
- documentation attempts to mark production deployment complete before migration and owner gates.

## Final owner decision placeholder

| Decision field | Value |
| --- | --- |
| controlled factory pilot owner-review decision | TBD |
| production deployment decision | NO-GO until future migration, owner, rollback, monitoring, and support gates pass |
| live/shared DB migration decision | NO-GO until separate migration gate approval |
| runtime carry-forward adoption decision | NO-GO until separate adoption gate approval |
| final notes | TBD |

## D4 external owner-review handoff note

Stage D4 identifies this file as the live capture template for external owner review.

Results must be returned through this template or equivalent typed owner/reviewer evidence before D5 can record owner acceptance. All actual review, sign-off, risk acceptance, rejected-risk, and final decision fields remain `TBD` until real owner/reviewer evidence is provided.

## D5 evidence intake note

Stage D5 adds `docs/operations/FACTORY_OWNER_REVIEW_EXECUTION_PROTOCOL.md` and `docs/operations/FACTORY_OWNER_REVIEW_EVIDENCE_INTAKE_CHECKLIST.md`.

Use those documents to execute the external review and check returned evidence completeness. D6 should only record owner acceptance if actual evidence is returned and passes the intake checklist. All sign-off fields in this template remain `TBD` until then.
