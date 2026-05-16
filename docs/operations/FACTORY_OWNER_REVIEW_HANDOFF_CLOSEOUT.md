# Factory Owner Review Handoff Closeout

## Purpose

This closeout pack prepares the external owner-review handoff gate after the internal Stage D1-D3 route walkthrough sequence.

It tells operational owners, technical reviewers, DB owners, and rollback owners what evidence is ready, what they must verify, what they must not approve yet, and how to return review results for a future owner-acceptance closeout.

## Scope

This is an external owner-review handoff document.

It does not approve production deployment, live/shared DB migration, promoted DB writes, ETL execution, historical backfill, canonical materialization, carry-forward reconciliation, runtime carry-forward adoption, model retraining, artifact promotion, source-discovery policy changes, runtime canonical predicate changes, DQ runtime wiring, or Streamlit write controls.

No sign-off field is filled in this document. All owner/reviewer fields remain placeholders until real owner-review evidence is returned.

## Selected branch / commit placeholder

| Field | Value |
| --- | --- |
| selected branch for owner review | TBD |
| selected commit SHA for owner review | TBD |
| owner-review package prepared by | TBD |
| owner-review package returned by | TBD |
| review date | TBD |
| review environment | TBD |
| runtime mode reviewed | TBD |
| evidence return location | TBD |

## External owner-review objective

The owner-review objective is to decide whether the current branch is acceptable for controlled factory pilot owner review.

This objective is not production deployment approval. It is an external review gate for route visibility, read-only runtime posture, operator evidence capture, DB/artifact safety boundaries, accepted pilot risks, rejected production risks, and escalation readiness.

## Evidence package ready for owner review

Owner/reviewer package:

- `docs/operations/FACTORY_OWNER_REVIEW_EXECUTION_PROTOCOL.md`
- `docs/operations/FACTORY_OWNER_REVIEW_EVIDENCE_INTAKE_CHECKLIST.md`
- `docs/operations/FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md`
- `docs/operations/FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK.md`
- `docs/operations/FACTORY_ROUTE_WORKFLOW_SMOKE_CHECKLIST.md`
- `docs/operations/FACTORY_PILOT_HANDOFF_PACK.md`
- `docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md`
- `docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md`
- `docs/technical/POSTFYP_STAGED3_INTERNAL_ROUTE_WALKTHROUGH_REHEARSAL_REPORT.md`
- `docs/technical/POSTFYP_STAGED2_FACTORY_ROUTE_WALKTHROUGH_EVIDENCE_PACK_REPORT.md`
- `docs/technical/POSTFYP_STAGED1_FACTORY_ROUTE_WORKFLOW_SMOKE_REPORT.md`
- `docs/technical/POSTFYP_STAGEC6_FACTORY_PILOT_GONOGO_DECISION_REPORT.md`

Internal evidence basis:

- D1: route workflow smoke evidence and manual checklist.
- D2: route walkthrough evidence pack with all route statuses pending owner walkthrough.
- D3: internal route rehearsal, `/tmp` Streamlit bootstrap proof, route contract refresh, and owner-review capture template.
- D4: external owner-review pending closeout and handoff gate.
- D5: external owner-review execution protocol and evidence intake checklist.

## Required owner / reviewer roles

| Role | Required responsibility | Assigned person | Initials | Date |
| --- | --- | --- | --- | --- |
| Operational owner | Accept or reject controlled pilot-readiness route evidence | TBD | TBD | TBD |
| Technical reviewer | Review validation, route evidence, runtime mode, and safety scans | TBD | TBD | TBD |
| DB owner | Confirm local DB boundary and live/shared DB migration block | TBD | TBD | TBD |
| Rollback owner | Confirm rollback ownership before any future promoted DB write | TBD | TBD | TBD |

## What the owner should verify

- Selected branch and commit SHA are recorded.
- Runtime mode used for route review is recorded.
- `demo_readonly` is used for defended-core route review unless `pilot_review` is explicitly selected for Experimental Intelligence Lab visibility.
- Route observations are recorded for every required route.
- No buttons were clicked during the walkthrough.
- No files were uploaded.
- No ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, artifact promotion, or DB write occurred.
- Validation results are available.
- Unsafe scan results are available.
- `manufacturing_data.db` remains local-only and untracked.
- No DB, raw Excel, generated `etl_outputs`, or model artifact is staged.
- Accepted pilot risks are explicit.
- Rejected production risks are explicit.

## What the owner must not approve yet

Owners must not approve:

- production deployment completion;
- live/shared DB migration;
- promoted DB writes;
- runtime carry-forward adoption;
- model retraining or artifact promotion;
- source-discovery policy expansion;
- runtime canonical predicate changes;
- DQ runtime enforcement;
- production monitoring/support/access completion claims;
- any route status as passed without actual route observation evidence.

## Required route walkthrough evidence

| Route | Required owner evidence | Current D4 status |
| --- | --- | --- |
| ETL Pipeline | Owner observation in `demo_readonly`; no upload/process/backfill/materialization action clicked. | pending owner review |
| Canonical Operations Overview | Owner observation in `demo_readonly`; no DB/source/output mutation. | pending owner review |
| Energy Analysis | Owner observation in `demo_readonly`; no ETL/materialization/fallback mutation. | pending owner review |
| Operational Decision Support | Owner observation in `demo_readonly`; no production-solver claim or write action. | pending owner review |
| Efficiency Prediction & Governance | Owner observation in `demo_readonly`; no retraining or artifact promotion. | pending owner review |
| Maintenance | Owner observation in `demo_readonly`; no upload/integration/write action. | pending owner review |
| Experimental Intelligence Lab | Confirm hidden in `demo_readonly`; optional `pilot_review` observation only if explicitly approved, with no upload/export/stress-test action. | pending owner review |

## Required DB/artifact safety confirmation

Owners/reviewers must confirm:

- GitHub-safe tree has no DB files.
- Walkthrough/smoke workspace has no DB files.
- `manufacturing_data.db` is not tracked.
- `manufacturing_data.db` remains local-only in the original runtime repo.
- No DB file is staged.
- No raw Excel file is staged.
- No generated `etl_outputs` artifact is staged.
- No model artifact is staged.
- No temp DB is promoted.
- No live/shared DB migration was executed.

## Required accepted risks

Owners/reviewers must explicitly accept or reject these controlled-pilot risks:

- route walkthrough is controlled owner-review evidence, not production launch;
- local runtime DB remains a review/rehearsal boundary;
- Experimental Intelligence Lab remains non-defended for production claims;
- live/shared DB migration is still future gated work;
- production monitoring, access control, support ownership, and incident response remain future work.

## Required rejected production risks

Owners/reviewers must explicitly reject these risks for production deployment unless a future approved gate changes them:

- live/shared DB migration without migration gate;
- promoted DB writes without backup/checksum/rollback evidence;
- runtime carry-forward adoption without adoption gate;
- model artifact promotion without model-promotion gate;
- production launch completion without owner approval;
- production launch completion without monitoring/support/access readiness.

## Sign-off fields still pending

| Field | Value |
| --- | --- |
| operational owner sign-off | TBD |
| technical reviewer sign-off | TBD |
| DB owner sign-off | TBD |
| rollback owner sign-off | TBD |
| accepted pilot risks | TBD |
| rejected production risks | TBD |
| route walkthrough result | TBD |
| final owner decision | TBD |
| decision date | TBD |

## How to return review results

Return review results by providing:

- selected branch and commit SHA;
- completed `FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md` fields or equivalent typed evidence;
- route-by-route observations;
- screenshots or typed notes, if captured;
- no-click/no-upload/no-write confirmations;
- validation and unsafe scan results reviewed by the owner/reviewer;
- accepted pilot risks;
- rejected production risks;
- operational owner, technical reviewer, DB owner, and rollback owner initials or explicit deferrals;
- final owner decision text.

D5 may record owner acceptance only after real review evidence is returned.

D6 should only record owner acceptance if the returned evidence is complete under `docs/operations/FACTORY_OWNER_REVIEW_EVIDENCE_INTAKE_CHECKLIST.md`.

## No-go escalation conditions

Declare no-go and escalate if:

- owner/reviewer evidence is missing;
- route observations are missing;
- a DB file appears inside the GitHub-safe tree;
- a DB file is staged;
- `manufacturing_data.db` becomes tracked;
- a forbidden control is clicked;
- a file is uploaded;
- ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, or artifact promotion is triggered;
- route visibility differs from the runtime-mode contract;
- startup logs show traceback/error evidence;
- production deployment is requested before migration and owner gates pass;
- live/shared DB migration is requested without migration gate approval;
- runtime carry-forward adoption is requested without an adoption gate.
