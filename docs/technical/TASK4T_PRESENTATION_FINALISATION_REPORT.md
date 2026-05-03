# Task4T Presentation Finalisation Report

## Verdict
Task4T is passed.

The routed `🤖 Efficiency Prediction & Governance` and `🎯 Operational Decision Support` pages now close the remaining presentation-critical gaps without changing the active DB, without retraining or promoting ML artifacts, and without introducing solver-style claims.

## Evidence Boundary
- Direct-source-verified:
  - [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py)
  - [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py)
- Evidence-based only:
  - AppTest routed-page render smoke
  - read-only June 2025 demo smoke
  - Streamlit boot on port `8502` with `HTTP/1.1 200 OK`
- Explicitly out of scope:
  - ML retraining or artifact promotion
  - active DB writes
  - predictor-contract broadening
  - constraint-aware scheduling / solver work
  - maintenance appendix redesign

## Exact File List Touched
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
- [`tests/test_ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_module.py)
- [`tests/test_optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_optimization_module.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`docs/technical/TASK4T_PRESENTATION_FINALISATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4T_PRESENTATION_FINALISATION_REPORT.md)

## Exact Reason For Each Change
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - added a concise explanation of how the actionable shortlist is prioritized
  - added a narrow `What-if Prediction` panel seeded from a real eligible canonical machine-hour row
  - forced the What-if path to reuse the active saved predictor only and block when the result is not `source == model`
  - surfaced support-path honesty for the What-if seed row (`direct`, `adapted`, `defaulted`)
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - added deterministic narrow support filters for `machine_family`, minimum `eligible_rows`, and minimum `total_good_qty`
  - added a proper selected-machine drill-down with the required presentation fields and plain-language follow-up action
  - kept score decomposition tied to the selected machine and kept the page explicitly in phase-1 rule-based language
- [`tests/test_ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_module.py)
  - added helper coverage for the saved-model What-if path and support-label behavior
- [`tests/test_optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_optimization_module.py)
  - added helper coverage for the narrow opportunity filters and drill-down snapshot output
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - marked Task 4T passed and recorded direct-source-verified routed-page closure plus evidence-based smoke results
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this closeout report for future recovery
- [`docs/technical/TASK4T_PRESENTATION_FINALISATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4T_PRESENTATION_FINALISATION_REPORT.md)
  - recorded the exact closure evidence and final scope boundary

## P0 Items Completed
- ML routed page remains reviewer-facing above the fold, with model summary first and governance kept subordinate
- ML routed page keeps blocked behavior honest and visible
- ML routed page now explicitly explains shortlist prioritization
- ML routed page keeps local full runtime paths off the main presentation surface
- Operational Decision Support keeps the honest phase-1 rule-based framing
- Operational Decision Support now has a richer selected-machine drill-down with:
  - machine ID
  - machine family
  - opportunity score
  - top driver
  - eligible rows
  - total good qty
  - productive vs non-productive hours
  - weighted kWh / good unit
  - scrap rate
  - average hours since maintenance
  - recommended follow-up action
- Operational Decision Support keeps score decomposition visibly tied to the selected machine
- Historical Hour Signals remain descriptive rather than solver-like

## Optional P1 Decisions
- ML What-if panel:
  - added
  - narrow and honest
  - seeded from a real eligible canonical machine-hour row
  - limited to `team_size`, `hours_since_last_maintenance`, `production_qty`, and `task_difficulty`
  - blocked when the active predictor cannot return a real saved-model result
- Optimization filters:
  - added
  - limited to `machine_family`, minimum `eligible_rows`, and minimum `total_good_qty`
  - explicitly disclosed on-screen as ranking/drill-down filters only

## Tests Run
- `py_compile`
  - `app.py`
  - `modules/ml_module.py`
  - `modules/optimization_module.py`
  - `core/canonical_ml_reader.py`
  - `core/canonical_optimization_reader.py`
  - `tests/test_ml_module.py`
  - `tests/test_optimization_module.py`
  - `tests/test_canonical_ml_reader.py`
  - `tests/test_canonical_optimization_reader.py`
  - `tests/test_ml_predictor.py`
- `unittest`
  - `tests.test_ml_predictor`
  - `tests.test_canonical_ml_reader`
  - `tests.test_canonical_optimization_reader`
  - `tests.test_ml_module`
  - `tests.test_optimization_module`
  - result: `31` tests passed

## Streamlit Smoke Summary
- AppTest routed render:
  - ML route rendered with `0` exceptions
  - Operational Decision Support route rendered with `0` exceptions
- Local Streamlit server:
  - started with `.conda311/bin/python -m streamlit run app.py --server.port 8502 --server.address 0.0.0.0 --server.headless true`
  - verified with `curl -I http://127.0.0.1:8502`
  - response: `HTTP/1.1 200 OK`
  - process stopped cleanly after smoke
- Non-fatal runtime note:
  - Streamlit still emits the existing invalid config-option warnings for `client.model_context_window` and `client.model_auto_compact_token_limit`

## Real-Month Demo Smoke Summary
- Month used: `June 2025`
- ML:
  - canonical input rows: `62,639`
  - latest eligible machine candidates: `76`
  - saved-model predictions returned: `76`
  - predictor-gate blocked rows: `0`
  - blocked input reasons still remain honest, led by:
    - `missing_positive_good_qty`: `26,524`
    - `missing_hours_since_last_maintenance`: `2,317`
  - one real-row What-if scenario succeeded with `source == model`
- Operational Decision Support:
  - machine summaries rendered for `87` machines
  - action queue returned `5` rows
  - narrow family/support filter produced a non-empty honest subset for machine family `024`
  - selected-machine drill-down returned the expected fields for machine `024-081`

## Remaining Limitations
- The ML What-if panel is intentionally narrow and does not fabricate unsupported scenario rows
- Operational Decision Support remains deterministic prioritization support, not a scheduling solver
- Historical Hour Signals remain descriptive only
- Maintenance remains appendix/admin rather than part of the main presentation path
- Retraining still runs synchronously on user action

## Presentation Readiness Decision
Yes.

For the current presentation scope, the routed ML and Operational Decision Support modules should now be considered presentation-ready.
