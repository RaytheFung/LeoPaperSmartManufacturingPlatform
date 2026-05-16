# Factory Route Walkthrough Evidence Pack

## Purpose

This evidence pack converts the Stage D1 route workflow smoke checklist into a controlled factory route walkthrough record for operator and reviewer assessment.

It is intended to help factory-side reviewers capture route-level observations, runtime-mode evidence, safety boundaries, and explicit no-click/no-write confirmations before any pilot owner decision.

## Scope

This pack is read-only operational evidence capture.

It does not approve production deployment, live/shared DB migration, promoted DB writes, ETL execution, historical backfill, canonical materialization, carry-forward reconciliation, runtime carry-forward adoption, model retraining, artifact promotion, source-discovery policy changes, runtime canonical predicate changes, or DQ runtime wiring.

No route is marked passed in this pack because no actual owner/reviewer walkthrough evidence has been provided. All observed-status cells remain `pending owner walkthrough`.

## Selected branch / commit placeholder

| Field | Value |
| --- | --- |
| selected branch | TBD by reviewer |
| selected commit SHA | TBD by reviewer |
| evidence pack reviewed by | TBD |
| walkthrough date | TBD |
| walkthrough location / environment | TBD |
| Streamlit launch workspace | TBD, must be `/tmp` or another approved non-Git workspace |
| Streamlit port | TBD |
| log path | TBD |

## Runtime mode used

Recommended defended-core walkthrough mode: `demo_readonly`.

Use `demo_readonly` to observe the six defended-core routes with write-capable controls hidden or disabled. In this mode, the Experimental Intelligence Lab route should be hidden.

Use `pilot_review` only if the reviewer explicitly needs to observe Experimental Intelligence Lab visibility. In `pilot_review`, defended-core write controls remain hidden, but experimental real-input, export, and manual stress-test surfaces may be visible and must not be clicked.

Do not use `standard` for this walkthrough unless a later approved operational write-mode review stage opens that scope.

## Operator/reviewer roles

| Role | Responsibility | Assigned person | Date |
| --- | --- | --- | --- |
| Operational owner | Accept or reject route walkthrough evidence for pilot-readiness review | TBD | TBD |
| Technical reviewer | Confirm runtime mode, validation, route observations, and safety scans | TBD | TBD |
| DB owner | Confirm local DB boundary and live/shared migration block | TBD | TBD |
| Rollback owner | Confirm rollback ownership remains required before any future promoted DB write | TBD | TBD |

## Pre-walkthrough safety checks

- [ ] Selected branch is recorded.
- [ ] Selected commit SHA is recorded.
- [ ] `python3.11 scripts/check_factory_deployment_readiness.py` passed on the GitHub-safe tree.
- [ ] Route contract tests passed.
- [ ] Runtime mode is recorded.
- [ ] Streamlit is not launched from the GitHub-safe tree.
- [ ] Streamlit is not launched from the original runtime repo.
- [ ] No `*.db`, `*.sqlite`, or `*.sqlite3` file exists inside the GitHub-safe tree.
- [ ] `manufacturing_data.db` is not tracked.
- [ ] No DB file is staged.
- [ ] No raw Excel file is staged.
- [ ] No generated `etl_outputs` artifact is staged.
- [ ] No model artifact is staged.
- [ ] No local env or upload folder is staged.
- [ ] No owner/reviewer sign-off is pre-filled.

## Route-by-route walkthrough table

| Route | Runtime mode visible | Classification | Expected observation | Forbidden actions | Evidence to capture | Observed status placeholder | Reviewer initials placeholder | Notes placeholder |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ETL Pipeline | `demo_readonly`, `pilot_review`, `standard` | defended-core | In `demo_readonly`, route opens without triggering ETL; upload, processing, backfill, and month-write controls are hidden or unavailable. | Do not upload files; do not process ETL; do not run historical backfill; do not trigger canonical materialization; do not write month data. | Route screenshot or typed observation; runtime mode banner; confirmation no controls were clicked. | pending owner walkthrough | TBD | TBD |
| Canonical Operations Overview | `demo_readonly`, `pilot_review`, `standard` | defended-core | Route opens as a read-only canonical operations surface or reports unavailable canonical data without mutation. | Do not trigger any write action; do not alter DB/source/output state. | Route screenshot or typed observation; any safe missing-data message; confirmation no writes occurred. | pending owner walkthrough | TBD | TBD |
| Energy Analysis | `demo_readonly`, `pilot_review`, `standard` | defended-core | Route opens as a read-only canonical energy surface or reports missing canonical Gold data without fallback mutation. | Do not run ETL; do not materialize canonical tables; do not alter DB/source/output state. | Route screenshot or typed observation; selected runtime mode; safe warning text if no canonical rows are available. | pending owner walkthrough | TBD | TBD |
| Operational Decision Support | `demo_readonly`, `pilot_review`, `standard` | defended-core | Route opens as read-only decision support or reports unavailable canonical data without legacy/synthetic fallback mutation. | Do not run optimization as production solver; do not trigger ETL/materialization; do not alter DB/source/output state. | Route screenshot or typed observation; no-fallback note if shown; confirmation no controls were clicked. | pending owner walkthrough | TBD | TBD |
| Efficiency Prediction & Governance | `demo_readonly`, `pilot_review`, `standard` | defended-core | Route opens with reviewer-facing inference/governance surfaces; retraining controls are hidden in read-only modes. | Do not retrain; do not promote artifacts; do not replace model/preprocessor/provenance files. | Route screenshot or typed observation; model-governance surface note; confirmation retraining controls were not clicked. | pending owner walkthrough | TBD | TBD |
| Maintenance | `demo_readonly`, `pilot_review`, `standard` | defended-core | Route opens with evidence and browse surfaces; upload/integration controls are hidden in read-only modes. | Do not upload maintenance files; do not integrate maintenance into ETL; do not write maintenance DB state. | Route screenshot or typed observation; browse/evidence note; confirmation upload/integration controls were not clicked. | pending owner walkthrough | TBD | TBD |
| Experimental Intelligence Lab | `pilot_review`, `standard`; hidden in `demo_readonly` | experimental | Hidden in `demo_readonly`; visible only when `pilot_review` or `standard` is selected. If reviewed in `pilot_review`, observe only and keep non-defended production status explicit. | Do not upload real-input files; do not export artifacts; do not run manual stress-test controls; do not claim production defense. | Visibility proof in `demo_readonly`; optional `pilot_review` screenshot or typed observation; confirmation no experimental controls were clicked. | pending owner walkthrough | TBD | TBD |

## Evidence capture instructions

For each route, capture a screenshot or typed note that includes:

- selected branch;
- selected commit SHA;
- runtime mode;
- route label;
- route visibility state;
- expected safe observation;
- whether any missing-data warning is shown;
- confirmation that no buttons were clicked;
- confirmation that no files were uploaded;
- confirmation that no ETL, backfill, materialization, migration, carry-forward reconciliation, retraining, artifact promotion, or DB write was triggered;
- reviewer initials placeholder.

Store evidence outside Git unless a later approved documentation stage explicitly asks for curated screenshots or typed notes to be committed.

## Controls that must not be clicked

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

## Route pass/skip/block criteria

| Status | Criteria |
| --- | --- |
| `pass` | A real owner/reviewer walkthrough observed the route in the approved runtime mode, captured evidence, confirmed no forbidden action was clicked, and confirmed no DB/source/output/model artifact changed. |
| `skip` | The route is intentionally not visible in the selected runtime mode or the reviewer explicitly deferred it with a documented reason. |
| `block` | Route visibility differs from the runtime contract, logs show traceback/error, a forbidden control was clicked, a file was uploaded, a DB/source/output/model artifact changed, or safety evidence is missing. |
| `pending owner walkthrough` | Default D2 status when no actual human walkthrough evidence has been provided. |

## DB/artifact safety checks

- [ ] GitHub-safe tree DB scan returns no files.
- [ ] Smoke/walkthrough workspace DB scan returns no files.
- [ ] `manufacturing_data.db` is not tracked.
- [ ] `manufacturing_data.db` remains local-only in the original runtime repo.
- [ ] No DB file is staged.
- [ ] No raw Excel file is staged.
- [ ] No generated `etl_outputs` artifact is staged.
- [ ] No model artifact is staged.
- [ ] No local env or upload folder is staged.
- [ ] No temp DB is promoted.

## Failure escalation rules

Stop the walkthrough and escalate to the operational owner, technical reviewer, and DB owner if:

- any DB file appears inside the GitHub-safe tree;
- any DB file is staged;
- `manufacturing_data.db` becomes tracked;
- Streamlit is launched from the GitHub-safe tree or the original runtime repo during a stage that requires `/tmp` launch;
- any forbidden control is clicked;
- any file is uploaded;
- ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, or artifact promotion is triggered;
- route visibility differs from the runtime-mode contract;
- logs show traceback/error evidence;
- docs or reviewers attempt to mark production deployment complete without migration and owner gates.

## Owner/reviewer initials placeholders

| Role | Initials | Date | Decision / note |
| --- | --- | --- | --- |
| Operational owner | TBD | TBD | TBD |
| Technical reviewer | TBD | TBD | TBD |
| DB owner | TBD | TBD | TBD |
| Rollback owner | TBD | TBD | TBD |

## Final provisional conclusion

Current D2 conclusion: route walkthrough evidence pack prepared; owner walkthrough pending.

This pack is ready for controlled operator/reviewer use, but it does not prove the routes have been manually accepted. Production deployment remains blocked. Live/shared DB migration remains blocked. Runtime carry-forward adoption remains blocked. Model retraining and artifact promotion remain blocked.

## D3 internal rehearsal note

Stage D3 adds `docs/operations/FACTORY_OWNER_REVIEW_CAPTURE_TEMPLATE.md` for owner/reviewer decision capture after an internal route walkthrough rehearsal.

D3 internal rehearsal status exists for readiness, route contracts, `/tmp` Streamlit bootstrap, runtime visibility probes, and static route-module import checks. Route observed statuses remain `pending owner walkthrough` until real owner/reviewer visual confirmation and initials are provided.
