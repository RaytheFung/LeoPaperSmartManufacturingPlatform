# Task5 Model-Backed Intervention Preview Report

## Verdict
Task5 is passed.

The routed `🤖 Efficiency Prediction & Governance` and `🎯 Operational Decision Support` pages now show a safe, honest, model-backed intervention preview layer on top of the existing canonical routed surfaces without retraining artifacts, without changing predictor contracts broadly, without writing `manufacturing_data.db`, and without implying a solver or realized-savings engine.

## Evidence Boundary
- Direct-source-verified:
  - [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - [`core/intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/intervention_preview.py)
  - [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py)
  - [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py)
  - [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
- Evidence-based only:
  - `py_compile`
  - focused/unit tests
  - AppTest routed-page smoke
  - read-only June 2025 intervention-preview smoke
- Explicitly out of scope:
  - model retraining or artifact promotion
  - active DB writes
  - predictor feature-contract broadening
  - monthly/aggregate savings claims
  - constraint-aware scheduling / solver work
  - quantity/anomaly policy changes

## Exact File List Touched
- [`core/intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/intervention_preview.py)
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
- [`tests/test_intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_intervention_preview.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`docs/technical/TASK5_MODEL_BACKED_INTERVENTION_PREVIEW_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK5_MODEL_BACKED_INTERVENTION_PREVIEW_REPORT.md)

## Exact Reason For Each Change
- [`core/intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/intervention_preview.py)
  - added one narrow deterministic helper shared by ML and Operational Decision Support
  - defined the supported scenario templates and guardrails
  - enforced the `source == model` rule for baseline/scenario preview
  - kept unsupported template and no-seed paths explicit instead of faking results
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - replaced the prior manual single-control What-if demo with a structured intervention-preview panel
  - surfaced baseline, supported-template rows, confidence, delta, comparable-volume kWh change, and honest blocked rows
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - reused the same saved-model preview layer inside the selected-machine drill-down
  - defaulted the drill-down toward a machine with preview coverage when available
  - kept the page explicitly in rule-based decision-support language rather than solver language
- [`tests/test_intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_intervention_preview.py)
  - added focused coverage for supported templates, honest unsupported templates, blocked no-seed behavior, and non-model baseline blocking
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - marked Task 5 passed and recorded the new routed coverage plus evidence
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this closeout report for future recovery
- [`docs/technical/TASK5_MODEL_BACKED_INTERVENTION_PREVIEW_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK5_MODEL_BACKED_INTERVENTION_PREVIEW_REPORT.md)
  - recorded exact scope, guardrails, evidence, and remaining limitations

## Scenario Templates Added
- `Maintenance Refresh`
  - lowers `hours_since_last_maintenance` toward the current what-if lower bound only
- `Crew Support +1`
  - increases `team_size` by exactly `1`
- `Combined Support`
  - applies both only when both individual templates are already valid

## Guardrails
- every preview is seeded from one real eligible canonical machine-hour row
- only the current saved predictor is used
- if baseline or scenario preview returns anything other than `source == model`, the preview blocks honestly
- no synthetic default rows are fabricated
- no aggregate/monthly savings claims are made
- comparable-volume kWh change is limited to the seed row's current machine-hour production volume
- Operational Decision Support still remains prioritization support, not a solver

## Seed-Row Contract
Yes.

All Task5 previews are seeded from real canonical rows returned by [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) and then passed through the shared helper in [`core/intervention_preview.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/intervention_preview.py). No synthetic rows or retrained artifacts were introduced.

## Direct-Source-Verified vs Evidence-Based
- Direct-source-verified:
  - routed page path for ML remains `app.py -> modules/ml_module.py -> core/canonical_ml_reader.py -> core/ml_predictor.py`
  - routed page path for Operational Decision Support remains `app.py -> modules/optimization_module.py -> core/canonical_optimization_reader.py`, with the drill-down now additionally reading canonical ML preview context through the shared helper
  - the new helper only touches the already-supported fields `hours_since_last_maintenance` and `team_size`
- Evidence-based:
  - AppTest confirmed both routed pages render without exceptions after the Task5 change
  - June 2025 read-only smoke confirmed model-backed preview rows still render on live canonical data
  - June 2025 read-only smoke confirmed honest blocked no-preview behavior on machines without an eligible saved-model seed

## Tests Run
- `py_compile`
  - `app.py`
  - `core/intervention_preview.py`
  - `modules/ml_module.py`
  - `modules/optimization_module.py`
  - `tests/test_intervention_preview.py`
  - `tests/test_ml_predictor.py`
  - `tests/test_canonical_ml_reader.py`
  - `tests/test_canonical_optimization_reader.py`
  - `tests/test_ml_module.py`
  - `tests/test_optimization_module.py`
- `unittest`
  - `tests.test_intervention_preview`
  - `tests.test_ml_predictor`
  - `tests.test_canonical_ml_reader`
  - `tests.test_canonical_optimization_reader`
  - `tests.test_ml_module`
  - `tests.test_optimization_module`
  - result: `36` tests passed

## Routed Demo Smoke Summary
- AppTest routed render:
  - ML route rendered with `0` exceptions
  - Operational Decision Support route rendered with `0` exceptions
- AppTest widget evidence:
  - ML route exposed `Select month` and `Scenario seed machine`
  - Operational Decision Support route exposed `Select month`, `Machine family`, and `Inspect machine`
- non-fatal runtime note:
  - Streamlit still emits the existing invalid config-option warnings for `client.model_context_window` and `client.model_auto_compact_token_limit`

## Real-Month Intervention Preview Smoke Summary
- month used: `June 2025`
- ML:
  - canonical input rows: `62,639`
  - latest eligible machine candidates: `76`
  - saved-model preview rows: `76`
  - predictor-gate blocked rows: `0`
  - one live supported preview confirmed on machine `024-039`
  - supported templates on that machine: `Maintenance Refresh`, `Crew Support +1`, `Combined Support`
  - best supported preview on that machine: `Maintenance Refresh`
- Operational Decision Support:
  - machine summaries rendered for `87` machines
  - model-backed preview was available for machine `024-039`
  - honest blocked no-preview path was confirmed for machine `024-105`
  - blocked reason: no eligible canonical saved-model seed row for that machine in the current month

## Remaining Limitations
- intervention preview remains intentionally narrow and template-based
- preview can still show no improvement or a worse predicted result; it is not an optimizer
- some optimization machines still have no saved-model preview because they lack an eligible canonical ML seed row
- Operational Decision Support remains prioritization support rather than a constraint-aware scheduling engine
- Historical Hour Signals remain descriptive only
- no monthly savings roll-up or executed-plan claim is made

## Readiness Decision
Yes.

For the current presentation scope, the app should now be considered both presentation-ready and potential-demonstration ready, with the explicit caveat that Task5 adds a safe comparable-row preview layer rather than a solver or realized-savings engine.
