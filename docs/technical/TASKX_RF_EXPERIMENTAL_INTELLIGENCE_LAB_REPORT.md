# TaskX-RF Experimental Intelligence Lab Report

## Verdict

TaskX-RF is passed.

This run added one clearly sandboxed experimental route, `🧪 Experimental Intelligence Lab`, with:

- a read-only constraint-aware scheduling prototype
- a read-only predictive-maintenance prototype

The defended core boundary did not change:

- `🎯 Operational Decision Support` remains phase-1 prioritization support, not a solver
- `🤖 Efficiency Prediction & Governance` remains active-saved-model review/governance, not a scheduling engine
- `🔧 Maintenance` remains evidence-first, not a production predictive-maintenance engine
- no active model/preprocessor paths were overwritten
- no DB write path was added
- `manufacturing_data.db` stayed unchanged during validation

## Exact File List Touched

- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- [`core/experimental_scheduling.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/experimental_scheduling.py)
- [`core/experimental_maintenance_prototype.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/experimental_maintenance_prototype.py)
- [`modules/experimental_intelligence_lab_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/experimental_intelligence_lab_module.py)
- [`tests/test_experimental_scheduling.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_scheduling.py)
- [`tests/test_experimental_maintenance_prototype.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_maintenance_prototype.py)
- [`tests/test_experimental_intelligence_lab_route.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_intelligence_lab_route.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`docs/technical/TASKX_RF_EXPERIMENTAL_INTELLIGENCE_LAB_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASKX_RF_EXPERIMENTAL_INTELLIGENCE_LAB_REPORT.md)

## Exact Reason For Each Change

- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - added one isolated sidebar route for the experimental lab and kept the existing core route labels/dispatch intact
- [`core/experimental_scheduling.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/experimental_scheduling.py)
  - added the deterministic real-seeded queue builder, compatibility/support ledger, maintenance-aware penalties, greedy scheduling pass, naive baseline, and single swap pass
- [`core/experimental_maintenance_prototype.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/experimental_maintenance_prototype.py)
  - added the machine-day weak-label builder, explainable trailing operational features, time-aware logistic-regression prototype path, and fallback evidence-score path
- [`modules/experimental_intelligence_lab_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/experimental_intelligence_lab_module.py)
  - added the routed experimental UI, banner/disclaimer contract, provenance labeling, and the two prototype tabs
- [`tests/test_experimental_scheduling.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_scheduling.py)
  - added focused coverage for queue determinism, compatibility/family filtering, baseline output, and read-only DB behavior
- [`tests/test_experimental_maintenance_prototype.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_maintenance_prototype.py)
  - added focused coverage for real future-horizon label construction, fallback triggering on sparse labels, and read-only DB behavior
- [`tests/test_experimental_intelligence_lab_route.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_intelligence_lab_route.py)
  - added a routed smoke that loads `app.py`, switches to the new experimental route, and verifies the banner plus both tab labels
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - marked TaskX-RF passed as experimental bonus scope and recorded the new route/evidence without changing the defended core boundary
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this closeout report for future recovery
- [`docs/technical/TASKX_RF_EXPERIMENTAL_INTELLIGENCE_LAB_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASKX_RF_EXPERIMENTAL_INTELLIGENCE_LAB_REPORT.md)
  - recorded exact scope, rules, provenance, validation, remaining limitations, and pass decision

## Whether A New Experimental Route Was Added

Yes.

The new route is the sidebar item `🧪 Experimental Intelligence Lab` in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py).

It is explicitly labeled as:

- experimental bonus function
- not part of current defended production scope
- no DB writes
- no artifact promotion
- no solver claim
- no predictive-maintenance production claim

## Exact Queue-Generation Rule

The default scheduling queue uses a strict real-first, real-seeded synthetic rule:

1. read the selected canonical month from `fact_machine_hour`
2. keep only positive-good-qty, positive-energy rows with non-empty `material_code`, non-empty `task_name`, mappable task difficulty, and a resolvable machine family
3. collapse that month into distinct `machine_family + material_code + task_name + task_difficulty` seed combinations
4. weight those combinations by observed row count
5. sample a small fixed number of combinations with a deterministic SHA1-derived seed
6. preserve material/task/family provenance from the selected month
7. derive synthetic queue quantity from the representative median `good_qty`, scaled by a fixed deterministic multiplier cycle and rounded to `25`-unit steps
8. derive a simple urgency proxy from quantity percentile because no live ERP due-date feed exists

Synthetic usage stayed limited to this queue only. Those demo rows are never written to the live DB.

## Exact Scheduling Objective Rule

The scheduling prototype uses one transparent composite objective:

`total_score = predicted_energy_cost_term + transition_penalty + maintenance_penalty + support_penalty + urgency_penalty + model_unavailable_penalty`

Exact rule details:

- `predicted_energy_cost_term`
  - only used when the active Task 4L predictor returns `source == model`
  - computed as `predicted_kwh_per_unit * queue_quantity * selected_month_cost_per_kwh`
- `transition_penalty`
  - added when consecutive jobs on the same machine change material
  - sized from the selected-month median setup-energy cost proxy
- `maintenance_penalty`
  - derived from selected-machine maintenance evidence:
    - days since last maintenance
    - PM ratio
    - event-count depth
    - or evidence-gap fallback when no direct maintenance history is available
- `support_penalty`
  - based on compatibility tier:
    - `Material + task history`
    - `Material + task-difficulty history`
    - `Material history only`
    - `Task-difficulty history only`
    - `Machine-family fallback`
- `urgency_penalty`
  - grows with later slot position on the machine
  - weighted by the queue urgency proxy (`High`, `Medium`, `Low`)
- `model_unavailable_penalty`
  - added when the active predictor cannot score the candidate honestly as a saved-model result

Maintenance blackout heuristic:

- blackout when direct maintenance evidence is stale and weak (`days_since_last_maintenance >= 180` and `PM ratio <= 0.05`)
- or when no evidence is present and latest canonical maintenance age is extremely high (`latest_hours_since_last_maintenance >= 3000`)

Solving approach:

- deterministic greedy assignment
- one best swap pass
- explicit naive baseline comparison

## Whether The Scheduling Prototype Is Deterministic

Yes.

Determinism comes from:

- fixed SHA1-derived queue seed
- fixed quantity multiplier cycle
- fixed candidate sort order
- deterministic greedy selection
- one deterministic best-improvement swap pass

## Exact Maintenance Label Logic Attempted

The predictive-maintenance prototype attempts weak labels from actual maintenance history only.

Exact rule:

- snapshot unit: machine-day
- positive label:
  - `1` when a maintenance event exists for that machine with `event_date > snapshot_date` and `event_date <= snapshot_date + horizon_days`
- negative label:
  - `0` only when the full future window is observable and no such event exists
- sufficient future observation window:
  - `snapshot_date + horizon_days <= max(event_date in maintenance_records)`
- unlabeled:
  - rows without sufficient future observation stay unlabeled and are excluded from weak-label training/evaluation

The feature set stays explainable and read-only:

- `hours_since_last_maintenance`
- `days_since_last_maintenance`
- `pm_ratio_all_time`
- `pm_ratio_recent_30d`
- `recent_events_count_30d`
- `maintenance_intensity_30d`
- `cumulative_maintenance_count`
- `weighted_kwh_per_good_unit_30d`
- `nonproductive_share_30d`
- `total_good_qty_30d`
- `machine_family`

## Whether Predictive Maintenance Used Actual Weak Labels Or Fallback

On the live June 2025 run, it used actual weak labels and a weak-label model.

Live June 2025 result:

- horizon: `14` days
- labeled machine-day snapshots: `15,766`
- positive labels: `2,965`
- negative labels: `12,801`
- model type: logistic regression with a time-aware split
- eval ROC AUC: `0.7130975686388245`
- eval average precision: `0.4028519508452373`
- train rows: `12,540`
- eval rows: `3,226`

Fallback logic is still implemented and tested for sparse/degenerate label cases.

## Synthetic Data Usage And Exact Placement

Synthetic usage was narrow and explicit:

- used only in the scheduling tab as `Real-seeded synthetic queue`
- not used in the predictive-maintenance weak-label training data
- not written to `manufacturing_data.db`
- not mixed silently into any live canonical table

No synthetic labels were used for predictive maintenance.

## Provenance Labeling Rules

The route surfaces these labels explicitly:

- `real data`
  - canonical `fact_machine_hour` or existing maintenance tables
- `real-seeded synthetic queue`
  - scheduling demo queue derived from the selected canonical month
- `manual demo input`
  - user-edited scheduling queue in the experimental tab
- `weak-label model`
  - predictive-maintenance prototype trained on actual future-horizon maintenance labels
- `fallback evidence score`
  - predictive-maintenance fallback when weak labels are too sparse or degenerate

## Tests Run

- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile app.py core/experimental_scheduling.py core/experimental_maintenance_prototype.py modules/experimental_intelligence_lab_module.py tests/test_experimental_scheduling.py tests/test_experimental_maintenance_prototype.py tests/test_experimental_intelligence_lab_route.py`
- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_experimental_scheduling tests.test_experimental_maintenance_prototype tests.test_experimental_intelligence_lab_route`
  - result: `8` tests passed

## Routed Smoke Summary

- read-only AppTest smoke loaded [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- switched the sidebar route to `🧪 Experimental Intelligence Lab`
- rendered with the expected warning:
  - `Experimental bonus function only. Not part of current defended production scope. No DB writes. No artifact promotion. No solver claim. No predictive-maintenance production claim.`
- rendered both tabs:
  - `Constraint-Aware Scheduling Prototype`
  - `Predictive Maintenance Prototype`
- selected prototype month in the routed smoke: `June 2025`

## Real-Month Prototype Smoke Summary

Month used:

- `June 2025`

Scheduling prototype:

- queue rows: `6`
- feasible candidate rows shown: `30`
- optimized scheduled rows: `6`
- optimized composite score: `70.5559`
- naive composite score: `300.5539`
- optimized predicted energy cost term: `20.2492`
- naive predicted energy cost term: `205.758`
- material-transition delta (`optimized - naive`): `-28.5315`
- one best swap pass landed:
  - `SYN-04 <-> SYN-03`
  - improvement: `2.57` prototype points
- a non-empty optimized-vs-naive comparison was produced

Predictive-maintenance prototype:

- mode: `Weak-label model`
- labeled snapshots: `15,766`
- positives: `2,965`
- negatives: `12,801`
- eval ROC AUC: `0.7130975686388245`
- eval average precision: `0.4028519508452373`
- current top machine in the live June table: `166-002`
- top-machine risk score: `0.8606`

Core-boundary protection:

- the core routed labels remain:
  - `🎯 Operational Decision Support`
  - `🤖 Efficiency Prediction & Governance`
  - `🔧 Maintenance`
- the new bonus route is separate and additive only
- no core-page claim text was repurposed into solver or production predictive-maintenance language

DB write check:

- pre-run hash: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- post-validation hash: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- result: unchanged

## Remaining Limitations

- the scheduling queue is still demo-only and uses real-seeded synthetic rows rather than a live ERP/MES order book
- the scheduling prototype keeps compatibility inside family-first support logic and does not claim full shop-floor feasibility
- not every scheduling candidate receives a saved-model energy term; unsupported candidates are penalized honestly instead
- the predictive-maintenance prototype uses weak labels from existing maintenance history; it is not a production failure-prediction contract
- the predictive-maintenance explanation is evidence-factor based, not a full causal attribution layer
- the route is intentionally bonus-only and does not create a new artifact-promotion basis

## Should The Experimental Bonus Task Now Be Considered Passed

Yes.

The route is live, read-only, validated on real June 2025 data, clearly separated from the defended core platform, and honest about where it remains prototype-only.
