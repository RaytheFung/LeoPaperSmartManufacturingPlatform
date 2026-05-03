# Task12B Pilot-Ready Experimental Hardening Report

## 1. accepted baseline used

- Task11 remained accepted as the authoritative routed-runtime ownership baseline.
- Task12A remained accepted as the first completed Layer 1 hardening step with explicit `standard` and `demo_readonly` runtime behavior.
- The defended routed shell remained:
  - `🔄 ETL Pipeline`
  - `📊 Canonical Operations Overview`
  - `⚡ Energy Analysis`
  - `🎯 Operational Decision Support`
  - `🤖 Efficiency Prediction & Governance`
  - `🔧 Maintenance`
  - `🧪 Experimental Intelligence Lab`
- `🧪 Experimental Intelligence Lab` remained experimental bonus scope only and was not relabeled as defended production truth.
- Active artifacts remained the accepted Task 4L bundle only:
  - `task_tag = Task 4L`
  - `artifact_version_id = 20260401_000808`
  - `selected_model = random_forest`

## 2. why Task12A was not enough for pilot-ready use

- Task12A made the defended shell safer for demos, but it did not introduce a governed pilot-review profile.
- The experimental lane was still effectively demo-like because it lacked:
  - a runtime profile dedicated to pilot evaluation
  - a central capability registry for experimental exposure vs defended-core suppression
  - a preferred real-input path for scheduling review
  - exportable handoff outputs for scheduling and predictive-maintenance review
  - explicit route-level provenance around runtime mode, input source, and export scope
- As a result, the repo had a safer reviewer shell, but not yet a clearer separation between defended-core usage and pilot-evaluable experimental review.

## 3. exact experimental/demo-only weaknesses found

- The runtime helper only distinguished `standard` vs `demo_readonly`; there was no profile for pilot review.
- Experimental route exposure was not centrally governed by runtime mode.
- The scheduling prototype still defaulted to:
  - `real-seeded synthetic queue`
  - optional in-memory manual editing
  - no preferred real-input upload contract
- The manual queue path used demo-centric wording and could be mistaken for the primary pilot path.
- The predictive-maintenance prototype had clear weak-label/fallback wording, but its outputs were still mostly UI-bound rather than export-ready.
- Neither experimental prototype exposed a compact manifest that made runtime mode, input provenance, and export provenance explicit for handoff.

## 4. runtime-profile and capability-registry design chosen

- Extended `core/runtime_mode.py` with:
  - `standard`
  - `demo_readonly`
  - `pilot_review`
- Resolution order stayed unchanged:
  1. `st.session_state["runtime_mode"]`
  2. query param `runtime_mode` / `mode`
  3. environment variable `SMART_MFG_RUNTIME_MODE`
  4. fallback `standard`
- Added one narrow central capability helper:
  - `core/runtime_capabilities.py`
- The helper now governs:
  - visible routes by runtime mode
  - defended-core write-capable control suppression
  - experimental route exposure
  - experimental real-input upload availability
  - experimental export availability
  - experimental manual stress-test availability

Chosen profile behavior:

- `standard`
  - defended-core operational controls available
  - experimental route exposed
  - experimental real-input/export surfaces available
- `demo_readonly`
  - defended-core write controls suppressed
  - experimental route hidden
  - experimental real-input/export surfaces hidden
- `pilot_review`
  - defended-core write controls suppressed
  - experimental route exposed
  - experimental real-input/export surfaces enabled for pilot evaluation

## 5. exact route-level changes

### top-level shell

- `app.py` now builds sidebar route visibility from `core/runtime_capabilities.py`.
- `demo_readonly` hides `🧪 Experimental Intelligence Lab`.
- `pilot_review` keeps defended core visible while exposing the experimental lane.

### `🔄 ETL Pipeline`

- ETL now uses the central capability helper rather than a hardcoded `demo_readonly` check.
- `pilot_review` suppresses ETL upload/process/history-mutation controls the same way `demo_readonly` does.

### `🤖 Efficiency Prediction & Governance`

- ML retraining suppression is now driven by the central capability helper.
- `pilot_review` keeps inference/review surfaces visible while hiding retraining.

### `🔧 Maintenance`

- Maintenance upload/integration suppression is now driven by the central capability helper.
- `pilot_review` keeps evidence and browse surfaces visible while hiding upload/integration controls.

### `🧪 Experimental Intelligence Lab`

- Route now accepts runtime mode explicitly.
- `demo_readonly` blocks the route entirely through sidebar visibility plus a guard.
- `pilot_review` adds an explicit info banner that the lane is pilot-evaluable but still non-defended.
- Added a runtime-profile card so route-level governance is visible in the UI.
- Scheduling tab now prefers a real-input pending-queue upload path before the manual stress-test path.
- Manual queue remains available only as an explicit stress-test override.
- Both experimental tabs now expose pilot-review provenance/export sections.

## 6. real-input contract introduced

- Added a narrow pending-queue file contract in `core/experimental_scheduling.py`.
- Supported input formats:
  - `.csv`
  - `.xlsx`
  - `.xls`
- Required columns:
  - `preferred_machine_family`
  - `material_code`
  - `task_name`
  - `quantity`
- Optional columns:
  - `job_id`
  - `task_difficulty`
  - `urgency_label`
  - `team_leader`
  - `team_size`
  - `hour_of_day`
  - `last_maintenance_type`
- Validation behavior:
  - unsupported file type blocks clearly
  - parse failure blocks clearly
  - missing required columns block clearly
  - invalid rows are skipped only after schema-level acceptance, using the same queue normalization rules as the manual path
- Accepted uploaded rows are normalized into the shared read-only queue schema with explicit provenance:
  - `provenance_label = Real-input pilot queue`
  - `source_mode = real_input_queue_upload`

## 7. export/provenance outputs introduced

### scheduling prototype

- Added exportable CSV outputs for:
  - queue input
  - optimized schedule
  - candidate scores
  - baseline comparison
  - score breakdown
  - constraint summary
  - blocked reasons
- Added JSON provenance manifest with:
  - runtime mode
  - anchor month
  - queue provenance
  - queue generation rule
  - seed summary when applicable
  - row counts
  - explicit non-defended notice

### predictive-maintenance prototype

- Added exportable CSV outputs for:
  - maintenance risk table
  - evidence factors
  - recent work-order context
  - latest scored snapshots
- Added JSON provenance manifest with:
  - runtime mode
  - anchor month
  - prototype mode
  - horizon days
  - label counts
  - selected machine summary
  - explicit non-defended notice

### route-level provenance

- Both prototype tabs now expose a visible `Pilot Provenance & Export` section.
- Runtime mode, input/current-state provenance, and export availability are shown before download actions.

## 8. validation / smoke summary

- Compile:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile app.py core/runtime_mode.py core/runtime_capabilities.py core/ui_utils.py core/experimental_scheduling.py core/experimental_maintenance_prototype.py modules/etl_module.py modules/ml_module.py modules/maintenance_module.py modules/experimental_intelligence_lab_module.py tests/test_runtime_mode.py tests/test_runtime_capabilities.py tests/test_experimental_scheduling.py tests/test_experimental_maintenance_prototype.py tests/test_experimental_intelligence_lab_route.py tests/test_task12b_pilot_review_mode.py`
- Unit tests:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_runtime_mode tests.test_runtime_capabilities`
  - result: `6` tests passed
- Experimental helper tests:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_experimental_scheduling tests.test_experimental_maintenance_prototype`
  - result: `10` tests passed
- AppTest smokes:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_experimental_intelligence_lab_route tests.test_task12b_pilot_review_mode`
  - result: `2` AppTest smokes passed

Validation proved:

- `pilot_review` runtime mode is visible in the shell
- defended-core routes still load
- defended-core ETL write-capable controls remain suppressed in `pilot_review`
- the experimental lane remains explicitly non-defended
- the preferred real-input contract text is visible on the scheduling prototype
- pilot provenance/export surfaces are reachable on the experimental route

DB/artifact verification:

- no DB write path was executed during validation
- DB SHA1 before AppTest: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- DB SHA1 after AppTest: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- active artifacts still remained Task 4L only:
  - `models/production_efficiency_model.provenance.json` -> `Task 4L`, `20260401_000808`, `random_forest`, `active`
  - `models/production_preprocessor.provenance.json` -> `Task 4L`, `20260401_000808`, `random_forest`, `active`

## 9. remaining limitations

- `pilot_review` is still a runtime-profile convention, not an auth/SSO system.
- The experimental scheduling path still lacks a true live ERP/MES pending-order feed.
- The predictive-maintenance prototype still relies on weak labels or transparent fallback scoring rather than a defended predictive-maintenance production model.
- Exports are flat file handoff outputs only; this task does not add workflow orchestration, shared deployment governance, or DB-backed action tracking.
- July-to-recent backfill remains a separate future task and was not reopened here.

## 10. recommended next step after Task12B

- Keep the next task separate and explicit: July-to-recent backfill should be the recommended follow-up after Task12B.
- Keep that backfill task honest about:
  - month/window scope
  - provenance and refresh boundaries
  - any downstream effect on the experimental lane vs defended core
- Do not bundle that next step with:
  - solver promotion
  - production predictive-maintenance promotion
  - artifact promotion
  - retraining redesign
  - auth/SSO
  - deployment packaging
