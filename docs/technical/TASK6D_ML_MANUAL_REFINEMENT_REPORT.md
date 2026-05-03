# Task6D ML Manual Refinement Report

## Verdict

Task6D is passed.

This run stayed inside the approved manual-review refinement boundary for the routed `🤖 Efficiency Prediction & Governance` page. It did not retrain models, promote artifacts, overwrite active model/preprocessor paths, write `manufacturing_data.db`, reopen Task4S quantity work, or broaden into solver-style behavior.

## Evidence Boundary

- Direct-source-verified:
  - [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py)
  - [`core/ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_review_queue.py)
  - [`core/intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/intervention_preview.py)
  - [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
  - [`tests/test_ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_review_queue.py)
- Evidence-based only:
  - `py_compile`
  - focused `unittest`
  - read-only routed render smoke through the live ML entrypoint
  - read-only June 2025 ML smoke on the active canonical month data
- Explicitly out of scope:
  - retraining or artifact promotion
  - active DB writes
  - broader predictor-contract expansion
  - realized-savings or executed-intervention claims
  - Optimization redesign beyond ML-page wording split

## Manual-Review Packet Note

- The prompt referenced `1st Manual Operating on 'Efficiency Prediction & Model Governance' Module.rtfd.zip`.
- On disk, the reviewer packet was present as three live `.rtfd` bundles under [`/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents):
  - [`1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Prediction Workflow).rtfd`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents/1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Prediction Workflow).rtfd)
  - [`1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Model Governance).rtfd`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents/1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Model Governance).rtfd)
  - [`1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Appendix).rtfd`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents/1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Appendix).rtfd)
- Reviewer prose was extracted from each `TXT.rtf`.
- Screenshot attachments were mapped from those `.rtfd` bundles before implementation, while the live routed repo files remained the primary source of truth.

## Routed Path Clarification

- The live routed ML page is still the sidebar item `🤖 Efficiency Prediction & Governance` in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py).
- That route still renders [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py).
- The routed page still reads canonical month-scoped ML input from [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) and active-artifact predictions from [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py).
- No archived `History/` files or stale duplicate ML routes were edited.

## Exact File List Touched

- [`core/ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_review_queue.py)
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
- [`tests/test_ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_review_queue.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`docs/technical/TASK6D_ML_MANUAL_REFINEMENT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK6D_ML_MANUAL_REFINEMENT_REPORT.md)

## Exact Reason For Each Change

- [`core/ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_review_queue.py)
  - added the one approved narrow backend helper for deterministic current-month ML review ranking
  - added reusable current-month inference coverage and blocked-summary helpers so the UI can stop presenting row composition as trend-like signals
  - kept the helper read-only and bounded to current routed canonical ML inputs plus the active saved predictor
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - reframed top-of-page readiness into explicit selected-month inference readiness instead of retraining status
  - replaced the dense raw prediction chart with a primary `Model Review Queue`
  - renamed `Intervention Preview` into `Scenario Lab` and clarified the role split versus Optimization
  - moved blocked raw detail into `Reference & Audit` while keeping compact blocker visibility on the main story
  - reduced governance clutter by hiding audience-facing task-tag noise and moving detailed training-footprint evidence into on-demand disclosure
- [`tests/test_ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_review_queue.py)
  - added focused coverage for support-path coverage summaries, peer-baseline selection, support-weight scoring, and blocked-summary deduplication
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - marked Task6D passed and recorded the direct-source and smoke-evidence closeout
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this closeout report for future recovery
- [`docs/technical/TASK6D_ML_MANUAL_REFINEMENT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK6D_ML_MANUAL_REFINEMENT_REPORT.md)
  - recorded the exact Task6D scope, ranking logic, baseline logic, validation, and pass decision

## New ML Review-Queue Helper

Yes.

[`core/ml_review_queue.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_review_queue.py) was added as the one narrow backend helper for this task.

Its scope is limited to:

- current-month inference coverage summarization
- blocked-row collection and blocker summarization
- deterministic machine-level review-queue construction from current-month eligible canonical candidates plus active saved-model predictions

It does not retrain artifacts, query legacy `unified_view`, or write the DB.

## Exact Review-Priority Logic Chosen

The helper computes:

- `severity_gap = max(predicted_efficiency - comparable_baseline, 0)`
- `estimated_excess_kwh = severity_gap * production_qty`
- `support_weight` by support path:
  - direct canonical row = `1.0`
  - adapted row = `0.85`
  - defaulted row = `0.65`
- `review_priority_score = estimated_excess_kwh * confidence * support_weight`

Additional deterministic review context included in the queue:

- support path
- top driver
- Scenario Lab availability
- best supported scenario name when one exists
- deterministic recommended review note from driver + support path + Scenario Lab availability

## Exact Comparable-Baseline Logic Chosen

Preferred comparison order implemented on the current-month machine-level candidate slice:

1. same machine family + same task difficulty peer median, when at least `3` peer rows exist
2. same task difficulty peer median, when at least `5` peer rows exist
3. otherwise selected-month median fallback across all machine-level candidates

Design choice:

- median was used rather than a more aggressive low-percentile target because this task needed a safe, presentation-rigorous, explainable review baseline rather than an implied savings frontier
- the fallback is disclosed on-screen as `Selected-month median fallback` rather than being hidden

## Inference-Coverage Redesign

The old direct/adapted/defaulted/blocked cards were no longer presented as delta-like metric cards.

They were replaced with:

- explicit `Selected-Month Inference Readiness` wording
- a current-month stacked support-path coverage bar
- compact count/share cards for:
  - direct canonical
  - adapted
  - defaulted
  - blocked

Main wording fix:

- readiness is now explicitly framed as current-month inference eligibility / coverage
- it is explicitly not the retraining status for the selected month

## Main Prediction-Surface Redesign

The old dense `Predicted Efficiency by Machine` bar chart was removed as the primary story.

It was replaced by:

- one primary `Model Review Queue`
- one compact `Top Review Priority Score` chart for the top queue slice only
- one machine-level review table with:
  - `Machine`
  - `Support Path`
  - `Predicted kWh / Unit`
  - `Comparable Baseline`
  - `Excess @ Seed Volume`
  - `Confidence`
  - `Review Priority Score`
  - `Top Driver`
  - `Preview Available`
  - `Recommended Review Note`

The full machine-level prediction evidence table remains available only under `Reference & Audit`.

## ML vs Optimization Role Split

The overlap risk was resolved by wording and hierarchy rather than backend broadening.

- ML page role:
  - current-month inference coverage
  - model-backed review queue
  - `Scenario Lab` for one review candidate
  - model evidence and supported template comparison
- Optimization role:
  - operational worklist
  - selected-machine operational review
  - still deterministic decision support, not a solver

Task6D did not redesign Optimization logic.

## Scenario Lab Change

`Intervention Preview` was renamed and reframed as `Scenario Lab`.

The section now:

- states clearly that it is model evidence on one current-month review candidate
- states clearly that execution still belongs on `🎯 Operational Decision Support`
- keeps only the current safe templates:
  - `Maintenance Refresh`
  - `Crew Support +1`
  - `Combined Support`
- keeps baseline, confidence, supported-template count, best supported scenario, and seed-row provenance
- keeps unsupported scenarios visible and honest
- repeats explicitly that this is a preview from the active saved model, not an executed intervention or realized-savings engine

## Blocked-Row Demotion

Blocked rows were not hidden.

They were demoted from the main page story into `Reference & Audit`:

- compact blocker visibility remains above the fold as a top blocker snapshot
- full blocked-reason chart remains visible in the reference section
- raw blocked-row detail now lives inside a collapsed disclosure

## Governance Tab Refinement

The governance tab stayed within presentation scope only.

Changes:

- active task-tag noise was removed from audience-facing provenance tables
- training-footprint detail was moved into `Reference & Audit: Training footprint and provenance`
- top governance status stays visible, but detailed trainer-path evidence is now on demand

## Tests Run

- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile core/ml_review_queue.py modules/ml_module.py tests/test_ml_review_queue.py tests/test_ml_module.py tests/test_intervention_preview.py tests/test_canonical_ml_reader.py`
- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_ml_review_queue tests.test_ml_module tests.test_intervention_preview tests.test_canonical_ml_reader`
  - result: `24` tests passed

## Routed Smoke Summary

- direct routed-file verification:
  - ML route still resolves through `app.py -> modules/ml_module.py`
- read-only routed render smoke:
  - command: `PYTHONPATH=. PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python tests/manual_checks/check_ui_fixes.py`
  - result: `✅ ML module rendered without errors`
- non-fatal runtime note:
  - Streamlit still emits the existing invalid config-option warnings for `client.model_context_window` and `client.model_auto_compact_token_limit`
- AppTest note:
  - a full real-data AppTest against the routed ML surface timed out because the governance path still inspects the real training footprint on the active Jan-Jun canonical dataset
  - Task6D validation therefore used the live routed entrypoint render smoke plus the real-month read-only data smoke below

## Real-Month ML Smoke Summary

- month used: `June 2025`
- selected-month readiness:
  - canonical rows loaded: `62,639`
  - inferable rows: `33,798`
  - blocked rows: `28,841`
- machine-level prediction path:
  - machine-level predictions returned: `76`
  - predictor-gate blocked rows: `0`
- review queue:
  - review-queue rows: `76`
  - top review candidate: `166-002`
  - top review score: `27.738066`
  - top review excess at seed volume: `33.516366`
- Scenario Lab:
  - supported Scenario Lab confirmed on `166-002`
  - supported templates on that machine: `3`
  - best supported scenario on that machine: `Crew Support +1`
- honest blocked no-preview path:
  - machine checked: `024-105`
  - blocked remained honest because the current month has no eligible canonical machine-hour seed row for that machine

## Remaining Limitations

- the review queue is still based on one current-month candidate row per machine; it is a ranking surface, not a root-cause engine
- the comparable baseline is deliberately median-based and safe rather than an aggressive optimized target
- Scenario Lab remains intentionally narrow and template-based
- some machines still have no supported Scenario Lab path because the month has no eligible canonical seed row for them
- retraining still runs synchronously on user action and the governance tab still inspects the real training footprint, which makes full real-data AppTest slower than other pages
- this run did not change active artifacts, predictor feature contracts, or Optimization logic

## Should Task6D Be Considered Passed

Yes.

For the accepted presentation scope, the routed ML page should now be considered closed through Task6D.
