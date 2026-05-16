# Factory Route Workflow Smoke Checklist

## Purpose

This checklist guides a controlled operator walkthrough of routed app pages for factory deployment readiness review.

It is evidence capture for route visibility, read-only runtime posture, and safe operator observations. It is not production deployment approval, live/shared DB migration approval, ETL approval, backfill approval, materialization approval, carry-forward runtime adoption, or ML artifact promotion.

## Scope

Use this checklist for Stage D1 route workflow smoke on a reviewed GitHub-safe branch.

The checklist covers these routed pages:

- ETL Pipeline
- Canonical Operations Overview
- Energy Analysis
- Operational Decision Support
- Efficiency Prediction & Governance
- Maintenance
- Experimental Intelligence Lab when `pilot_review` is explicitly selected for experimental visibility review

The walkthrough must stay non-mutating. Operators must not click write controls, upload files, process ETL inputs, run backfill, materialize canonical tables, run carry-forward reconciliation, retrain models, promote artifacts, or execute live/shared DB migration.

## Runtime mode to use

Default runtime mode: `demo_readonly`.

Use `demo_readonly` for defended-core route smoke because it hides write-capable controls and hides the Experimental Intelligence Lab route.

Use `pilot_review` only when the reviewer explicitly needs to confirm Experimental Intelligence Lab visibility. In `pilot_review`, defended-core write controls stay hidden, but experimental real-input review, export, and manual stress-test surfaces may be visible. Reviewers must observe those surfaces without clicking upload, export, or execution controls.

Do not use `standard` for D1 unless a later approved stage opens operational write-mode review.

## Before starting

- [ ] Confirm the selected branch is recorded.
- [ ] Confirm the selected commit SHA is recorded.
- [ ] Confirm Python 3.11 is available.
- [ ] Confirm Streamlit will be launched only from a `/tmp` smoke workspace.
- [ ] Confirm the smoke workspace is outside the GitHub-safe tree.
- [ ] Confirm the smoke workspace is outside the original runtime repo.
- [ ] Confirm `SMART_MFG_RUNTIME_MODE=demo_readonly` unless `pilot_review` is explicitly approved.
- [ ] Confirm `python3.11 scripts/check_factory_deployment_readiness.py` has passed on the GitHub-safe tree.
- [ ] Confirm `tests.test_app_route_contract`, `tests.test_runtime_mode`, `tests.test_runtime_capabilities`, and `tests.test_runtime_paths` have passed.
- [ ] Confirm the GitHub-safe tree contains no `*.db`, `*.sqlite`, or `*.sqlite3` files.
- [ ] Confirm `manufacturing_data.db` is not tracked.
- [ ] Confirm no raw Excel files, generated `etl_outputs`, model artifacts, local env folders, or upload folders are staged.

## Route-by-route checklist

| Route | Runtime mode | Expected visibility | Operator observation | Pass / fail | Notes |
| --- | --- | --- | --- | --- | --- |
| ETL Pipeline | `demo_readonly` | Visible | Page opens without triggering ETL. Upload, processing, backfill, and month-write controls are hidden or unavailable. | TBD | TBD |
| Canonical Operations Overview | `demo_readonly` | Visible | Page opens as a read-only canonical operations surface. No write action is triggered. | TBD | TBD |
| Energy Analysis | `demo_readonly` | Visible | Page opens as a read-only canonical energy surface or reports missing canonical Gold data without fallback mutation. | TBD | TBD |
| Operational Decision Support | `demo_readonly` | Visible | Page opens as a read-only decision-support surface or reports unavailable canonical data without legacy/synthetic fallback mutation. | TBD | TBD |
| Efficiency Prediction & Governance | `demo_readonly` | Visible | Page opens with reviewer-facing inference/governance surfaces. Retraining controls are hidden. | TBD | TBD |
| Maintenance | `demo_readonly` | Visible | Page opens with evidence and browse surfaces. Upload/integration controls are hidden. | TBD | TBD |
| Experimental Intelligence Lab | `demo_readonly` | Hidden | Route is not visible in the sidebar. | TBD | TBD |
| Experimental Intelligence Lab | `pilot_review` only | Visible when explicitly selected | Experimental route opens for observation only. Real-input, export, or stress-test controls must not be clicked. | TBD | TBD |

## Controls that must not be clicked

- Upload controls.
- Process ETL controls.
- Historical backfill controls.
- Canonical materialization controls.
- Month-write controls.
- Maintenance upload/integration controls.
- Model retraining controls.
- Artifact promotion controls.
- Experimental real-input upload controls.
- Experimental export controls.
- Experimental manual stress-test controls.
- Carry-forward reconciliation controls or scripts.
- Live/shared DB migration controls or scripts.

## Evidence to capture

- Selected branch and commit SHA.
- Runtime mode.
- `/tmp` smoke workspace path.
- Streamlit port and address.
- HTTP bootstrap result.
- Startup log scan result for `Traceback`, `Exception`, and `Error`.
- Route visibility matrix for `standard`, `demo_readonly`, and `pilot_review`.
- Screenshot or typed note for each route observed manually.
- Confirmation that no buttons were clicked and no files were uploaded.
- Confirmation that no ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, artifact promotion, or DB write was triggered.
- GitHub-safe tree unsafe file scan result.
- Smoke workspace unsafe file scan result.
- Owner/reviewer initials and date placeholders.

## Expected safe observations

- `demo_readonly` shows the six defended-core routes and hides the Experimental Intelligence Lab route.
- `demo_readonly` suppresses write-capable controls.
- `pilot_review` shows the six defended-core routes plus the Experimental Intelligence Lab route.
- `pilot_review` keeps defended-core write controls hidden.
- Route labels match the route-contract tests.
- Loader-dependent legacy pages are not visible in routed shell modes.
- App bootstrap returns a valid Streamlit HTML response.
- Startup logs show no traceback/error evidence.
- The process stops cleanly.

## Failure/escalation criteria

Stop the walkthrough and escalate if any of these occur:

- A DB file appears inside the GitHub-safe tree.
- A DB file appears inside the smoke workspace.
- `manufacturing_data.db` is tracked or staged.
- Streamlit was launched from the GitHub-safe tree or the original runtime repo.
- A write-capable control is clicked.
- A file is uploaded.
- ETL, backfill, materialization, carry-forward reconciliation, migration, retraining, or artifact promotion is triggered.
- Runtime route visibility does not match the route-contract tests.
- Startup logs contain a traceback/error.
- A route page writes to the DB during smoke.
- Raw Excel files, generated `etl_outputs`, model artifacts, or local env/upload folders are staged.

## DB/artifact safety checks

- [ ] `find . -maxdepth 5 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print` returns no GitHub-safe tree DB files.
- [ ] `git ls-files manufacturing_data.db || true` returns no tracked DB file.
- [ ] `git check-ignore --no-index -v manufacturing_data.db || true` confirms ignore coverage.
- [ ] Smoke workspace DB scan returns no DB or SQLite files.
- [ ] No DB file is staged.
- [ ] No raw Excel file is staged.
- [ ] No generated `etl_outputs` artifact is staged.
- [ ] No model artifact is staged.
- [ ] Original runtime `manufacturing_data.db` is not written.

## Owner/reviewer initials placeholders

| Role | Initials | Date | Decision / note |
| --- | --- | --- | --- |
| Operational owner | TBD | TBD | TBD |
| Technical reviewer | TBD | TBD | TBD |
| DB owner | TBD | TBD | TBD |
| Rollback owner | TBD | TBD | TBD |

