# TaskX2 Experimental Scope Refinement Report

## Verdict

TaskX2 is passed.

This run kept the `🧪 Experimental Intelligence Lab` route inside experimental bonus scope, did not retrain or promote active artifacts, did not write `manufacturing_data.db`, and did not change any defended core route contracts.

## Changed File List

- [`modules/experimental_intelligence_lab_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/experimental_intelligence_lab_module.py)
- [`tests/test_experimental_intelligence_lab_route.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_intelligence_lab_route.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`docs/technical/TASKX2_EXPERIMENTAL_SCOPE_REFINEMENT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASKX2_EXPERIMENTAL_SCOPE_REFINEMENT_REPORT.md)

## Exact Reason For Each Change

- [`modules/experimental_intelligence_lab_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/experimental_intelligence_lab_module.py)
  - reframed the month selector as a current-state anchor instead of a single-month-only prototype boundary
  - added route-level scope/provenance cards that separate anchor month, broader historical support/training scope, scheduling queue provenance, and maintenance mode/provenance
  - made scheduling explicitly real-first by keeping `Real-seeded synthetic queue` as the default path and moving manual queue editing into a collapsed stress-test expander
  - added scheduling-tab scope cards for anchor month, support window, queue provenance, and machine pool scope
  - split predictive maintenance into explicit `Historical Training / Label Scope` and `Current-State Risk View` sections without changing the underlying prototype algorithms
  - added a narrow read-only scope summary query so the UI can disclose actual fact-history and maintenance-event windows honestly
- [`tests/test_experimental_intelligence_lab_route.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_experimental_intelligence_lab_route.py)
  - updated the routed smoke to verify the new anchor-month wording, visible scope sections, and manual-queue demotion contract
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - marked TaskX2 passed and recorded the refinement as experimental bonus scope only, with the defended core boundary unchanged
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this TaskX2 closeout report for future recovery
- [`docs/technical/TASKX2_EXPERIMENTAL_SCOPE_REFINEMENT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASKX2_EXPERIMENTAL_SCOPE_REFINEMENT_REPORT.md)
  - recorded the exact wording changes, scope/provenance contract, validation evidence, remaining limitations, and pass decision

## Exact New Wording Chosen For The Anchor Month Control

- `Anchor month for current-state view`

Support caption used directly below it:

- `The anchor month sets the current machine pool and latest month slice shown on each prototype. Historical support and weak-label training use broader real history.`

## Exact Route-Level Provenance / Scope Cards Added Or Changed

- `Current-State Anchor`
- `Historical Support / Training Scope`
- `Scheduling Queue Provenance`
- `Maintenance Prototype Mode`

Exact scheduling-tab scope cards:

- `Current-State Anchor`
- `Historical Support Window`
- `Queue Provenance`
- `Machine Pool Scope`

Exact predictive-maintenance section headers/cards used to separate scope:

- `Historical Training / Label Scope`
- `Historical Snapshot Window`
- `Weak-Label Observation Scope`
- `Prototype Mode`
- `Class Counts`
- `Current-State Risk View`
- `Current-State Anchor`
- `Latest Snapshot Date`
- `Machines Scored`
- `Future Horizon`

## Whether Manual Queue Was Demoted

Yes.

The former equal-weight queue-mode radio was removed. Manual queue editing now lives under the collapsed expander `Stress-test mode: Manual demo queue`, behind the checkbox `Use manual demo queue instead of the default real-seeded queue`.

## How The Predictive-Maintenance Training / Current-State Split Was Clarified

- the tab now opens with an explicit info block stating that the selected month anchors the current-state risk view only
- `Historical Training / Label Scope` now reports the broader machine-day snapshot window, eligible weak-label snapshot count, class counts, and prototype mode
- `Current-State Risk View` now reports the selected anchor month, latest snapshot date inside that month, machine count in the risk table, and the active future horizon
- the current risk table heading is now `Current-State At-Risk Machine Table`

## Tests Run

- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile modules/experimental_intelligence_lab_module.py tests/test_experimental_intelligence_lab_route.py tests/test_experimental_scheduling.py tests/test_experimental_maintenance_prototype.py`
- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_experimental_scheduling tests.test_experimental_maintenance_prototype`
  - result: `7` tests passed
- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_experimental_intelligence_lab_route`
  - result: routed AppTest smoke passed

## Routed Smoke Summary

- loaded [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) through `streamlit.testing.v1.AppTest`
- switched the route to `🧪 Experimental Intelligence Lab`
- verified the experimental warning still appears unchanged
- verified the routed month selector now says `Anchor month for current-state view`
- verified the route still renders both tabs:
  - `Constraint-Aware Scheduling Prototype`
  - `Predictive Maintenance Prototype`
- verified the new scope/provenance text is present:
  - `Current-State Anchor`
  - `Historical Support / Training Scope`
  - `Historical Training / Label Scope`
  - `Current-State Risk View`
- verified the old equal-weight queue radio is gone and the manual-queue override is now the checkbox `Use manual demo queue instead of the default real-seeded queue`

## Real-Month Scope / Provenance Smoke Summary

Month used:

- `June 2025`

Read-only June AppTest checks:

- anchor month selected: `June 2025`
- anchor wording visible: yes
- historical support / training scope visible: yes
- predictive-maintenance `Historical Training / Label Scope` visible: yes
- predictive-maintenance `Current-State Risk View` visible: yes
- scheduling default queue heading visible as `Default Real-Seeded Queue`: yes
- manual queue default enabled: `False`
- explicit `Real-seeded synthetic queue` wording visible: yes

Read-only live-data diagnostics captured for June 2025:

- available anchor months: `June 2025`, `May 2025`, `April 2025`, `March 2025`, `February 2025`, `January 2025`
- scheduling queue rows: `6`
- scheduling machine pool: `87`
- predictive-maintenance mode: `Weak-label model`
- labeled machine-day snapshots: `15,766`
- positive labels: `2,965`
- negative labels: `12,801`
- current risk-table rows: `87`

DB write check:

- pre-smoke hash: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- post-smoke hash: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
- result: unchanged

## Remaining Limitations

- the route remains experimental bonus scope only; it is not part of the defended core platform
- scheduling still depends on a real-seeded synthetic pending queue because there is no live ERP/MES future order book in the current platform
- predictive maintenance still remains a weak-label prototype / fallback evidence scorer, not a production maintenance recommendation contract
- the refinement clarifies scope and provenance only; it does not broaden scheduling feasibility, add new prototype families, retrain models, or create a new artifact-promotion basis

## Should TaskX2 Now Be Considered Passed

Yes.

The route now explains the real historical scope honestly, defaults visibly to the real-seeded queue path, distinguishes maintenance training scope from the current risk slice, preserves the experimental boundary, and passed compile/tests/read-only routed validation without changing the live DB.
