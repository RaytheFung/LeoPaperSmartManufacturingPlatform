# Factory Owner Review Execution Protocol

## Purpose

This protocol makes external factory owner/reviewer route review executable and auditable.

It explains who should perform the review, which branch and runtime mode to use, what evidence to capture, what actions are forbidden, how to classify the decision, and how to return the evidence package for a future D6 decision record.

This protocol is for external review execution. It is not proof that review has completed.

## Scope

This protocol applies to controlled factory owner-review of the LeoPaper Smart Manufacturing Platform GitHub-safe branch selected for review.

It does not approve production deployment, live/shared DB migration, promoted DB writes, ETL execution, historical backfill, canonical materialization, carry-forward reconciliation, runtime carry-forward adoption, model retraining, artifact promotion, source-discovery policy changes, runtime canonical predicate changes, DQ runtime wiring, or Streamlit write controls.

## Who should perform the review

| Role | Required responsibility | Name | Initials | Date |
| --- | --- | --- | --- | --- |
| Operational owner | Decide whether route evidence is acceptable for controlled pilot review | TBD | TBD | TBD |
| Technical reviewer | Verify validation, runtime mode, route evidence, and safety scans | TBD | TBD | TBD |
| DB owner | Confirm local DB boundary and live/shared DB migration block | TBD | TBD | TBD |
| Rollback owner | Confirm rollback responsibility before any future promoted DB write | TBD | TBD | TBD |

## Required branch / commit recording

Record these fields before the review begins:

| Field | Value |
| --- | --- |
| selected branch | TBD |
| selected commit SHA | TBD |
| review date | TBD |
| review location / environment | TBD |
| reviewer package version | TBD |
| evidence return location | TBD |

Do not review an unrecorded branch or moving branch tip. If the branch changes during review, restart evidence capture with the new commit SHA.

## Runtime mode to use

Default runtime mode: `demo_readonly`.

Use `demo_readonly` for defended-core route review because it hides write-capable controls and hides the Experimental Intelligence Lab route.

Use `pilot_review` only if the owner explicitly needs to observe Experimental Intelligence Lab visibility. In `pilot_review`, defended-core write controls remain hidden, but experimental real-input, export, and manual stress-test surfaces may be visible and must not be clicked.

Do not use `standard` unless a later approved operational write-mode review opens that scope.

## Pre-review safety checks

- [ ] Selected branch is recorded.
- [ ] Selected commit SHA is recorded.
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
- [ ] No owner/reviewer sign-off is pre-filled.

## App launch instructions

Use a reviewed local launch plan from the deployment runbook.

For owner-review evidence capture, launch from an approved non-Git workspace whenever the stage requires isolated smoke evidence. Do not launch from the GitHub-safe tree or original runtime repo when the active stage requires `/tmp` isolation.

Record:

- launch workspace;
- runtime mode;
- Python version;
- Streamlit version;
- address and port;
- startup log path;
- HTTP bootstrap result;
- process stop result.

Do not click write-capable controls during launch or route review.

## Route walkthrough instructions

Walk through each required route using the selected runtime mode.

Required routes:

- ETL Pipeline
- Canonical Operations Overview
- Energy Analysis
- Operational Decision Support
- Efficiency Prediction & Governance
- Maintenance
- Experimental Intelligence Lab, hidden in `demo_readonly` and visible only if `pilot_review` is explicitly used

Record a typed observation or screenshot for each route. If a route is hidden by runtime mode, record the visibility result instead of changing runtime mode unless the owner explicitly approves `pilot_review`.

## Evidence to capture per route

| Route | Evidence to capture | Expected safety stance |
| --- | --- | --- |
| ETL Pipeline | Route visible in `demo_readonly`; no upload/process/backfill/month-write control used; any read-only banner or warning noted. | No ETL, backfill, materialization, or DB write. |
| Canonical Operations Overview | Route visible; read-only observation or safe unavailable-data message noted. | No DB/source/output mutation. |
| Energy Analysis | Route visible; canonical energy surface or safe missing-Gold warning noted. | No ETL/materialization/fallback mutation. |
| Operational Decision Support | Route visible; decision-support surface or safe unavailable-data message noted. | No production-solver claim or write action. |
| Efficiency Prediction & Governance | Route visible; inference/governance surface noted; retraining controls hidden or untouched. | No retraining or artifact promotion. |
| Maintenance | Route visible; evidence/browse surface noted; upload/integration controls hidden or untouched. | No maintenance upload, integration, or DB write. |
| Experimental Intelligence Lab | Hidden in `demo_readonly`; optional `pilot_review` observation only if explicitly approved. | No upload, export, manual stress test, or production-defense claim. |

## Forbidden actions

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

## DB/artifact safety confirmation

Confirm:

- GitHub-safe tree has no DB files.
- Review/smoke workspace has no DB files.
- `manufacturing_data.db` remains local-only and untracked.
- No DB file is staged.
- No raw Excel file is staged.
- No generated `etl_outputs` artifact is staged.
- No model artifact is staged.
- No temp DB is promoted.
- No live/shared DB migration was executed.

## Accepted pilot risks section

Owners/reviewers must mark each item accepted, rejected, or deferred:

| Pilot risk | Decision | Notes |
| --- | --- | --- |
| Route walkthrough is controlled owner-review evidence, not production launch | TBD | TBD |
| Local runtime DB remains a review/rehearsal boundary | TBD | TBD |
| Experimental Intelligence Lab remains non-defended for production claims | TBD | TBD |
| Live/shared DB migration is still future gated work | TBD | TBD |
| Monitoring, access control, support ownership, and incident response remain future work | TBD | TBD |

## Rejected production risks section

Owners/reviewers must explicitly reject or defer these production risks:

| Production risk | Rejected / deferred | Notes |
| --- | --- | --- |
| Live/shared DB migration without migration gate | TBD | TBD |
| Promoted DB writes without backup/checksum/rollback evidence | TBD | TBD |
| Runtime carry-forward adoption without adoption gate | TBD | TBD |
| Model artifact promotion without model-promotion gate | TBD | TBD |
| Production launch completion without owner approval | TBD | TBD |
| Production launch completion without monitoring/support/access readiness | TBD | TBD |

## Required returned evidence package

Return a complete package containing:

- selected branch and commit SHA;
- runtime mode used;
- reviewer names or initials;
- review date;
- route-by-route observations;
- screenshots or typed notes, if captured;
- no-click confirmation;
- no-upload confirmation;
- no ETL/backfill/materialization confirmation;
- no carry-forward reconciliation confirmation;
- no live/shared DB migration confirmation;
- no retraining/promotion confirmation;
- DB/artifact safety confirmation;
- accepted pilot risks;
- rejected production risks;
- decision category;
- final owner/reviewer notes.

## How to submit review results

Submit results by returning a completed `docs/operations/FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md` or equivalent typed evidence.

D6 should only record owner acceptance if the returned evidence is complete and includes real owner/reviewer decisions. If evidence is missing or ambiguous, D6 should keep owner acceptance pending.

## No-go escalation conditions

Declare no-go and escalate if:

- evidence package is incomplete;
- route observations are missing;
- owner/reviewer identity is missing;
- branch or commit SHA is missing;
- a DB file appears inside the GitHub-safe tree;
- a DB file is staged;
- `manufacturing_data.db` becomes tracked;
- a forbidden control is clicked;
- a file is uploaded;
- ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, or artifact promotion is triggered;
- route visibility differs from the runtime-mode contract;
- logs show traceback/error evidence;
- production deployment is requested before migration and owner gates pass;
- live/shared DB migration is requested without migration gate approval;
- runtime carry-forward adoption is requested without an adoption gate.

## Decision categories

| Decision category | Meaning |
| --- | --- |
| `accepted_for_controlled_pilot_review` | Owner accepts the reviewed branch for controlled pilot review only; production deployment remains blocked. |
| `accepted_with_conditions` | Owner accepts review evidence only with listed conditions or required follow-up. |
| `rejected_pending_fixes` | Owner rejects current evidence until listed fixes or evidence gaps are addressed. |
| `blocked_due_safety_risk` | Owner/reviewer blocks the review due to DB/artifact/runtime safety risk. |

## Sign-off fields

| Field | Value |
| --- | --- |
| operational owner sign-off | TBD |
| technical reviewer sign-off | TBD |
| DB owner sign-off | TBD |
| rollback owner sign-off | TBD |
| accepted pilot risks | TBD |
| rejected production risks | TBD |
| decision category | TBD |
| final owner decision | TBD |
| decision date | TBD |

