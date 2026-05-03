# Task6E Maintenance Evidence Convergence Report

## Verdict

Task6E is passed.

This run stayed inside the approved maintenance-evidence convergence boundary. It did not retrain or promote ML artifacts, did not broaden scenario templates, did not change ML review-queue or Optimization scoring logic, and did not write `manufacturing_data.db`.

## Evidence Boundary

- Direct-source-verified:
  - [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - [`core/maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/maintenance_evidence.py)
  - [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - [`tests/test_maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_maintenance_evidence.py)
- Evidence-based only:
  - `py_compile`
  - focused `unittest`
  - read-only routed render smoke for Maintenance, ML, and Optimization
  - read-only June 2025 maintenance-context smoke
  - DB hash comparison before and after the read-only smokes
- Explicitly out of scope:
  - predictive-maintenance model work
  - artifact retraining or promotion
  - `manufacturing_data.db` writes outside explicit upload action
  - ML queue re-ranking changes
  - Optimization score/driver redesign
  - solver or scheduling-engine work

## Manual-Review Packet Note

- The prompt referenced zipped `.rtfd` bundles.
- On disk, the packets were present as live `.rtfd` bundles under [`/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents):
  - [`1st Manual Operating on 'Maintnance' Module.rtfd`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents/1st Manual Operating on 'Maintnance' Module.rtfd)
  - [`1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Model Governance).rtfd`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents/1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Model Governance).rtfd)
  - [`1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Appendix).rtfd`](/Users/rayfung/Library/Mobile Documents/com~apple~TextEdit/Documents/1st Manual Operating on 'Efficiency Prediction & Model Governance' Module(Appendix).rtfd)
- Reviewer prose was extracted from each `TXT.rtf`.
- Screenshot attachments were mapped before implementation, while the live routed repo files stayed the primary truth source.

## Screenshot Mapping

- Maintenance screenshot `2026-04-06 05:32:38` showed the month dropdown in lexicographic order rather than chronological order.
- Maintenance screenshot `2026-04-06 05:33:05` showed the conflicting blue/yellow top banners.
- Maintenance screenshot `2026-04-06 05:33:13` showed storage/integration metrics buried below upload/admin framing.
- Maintenance screenshot `2026-04-06 05:33:34` showed the machine-history contract mismatch: `166-002 (165 events)` paired with a limited recent-history table and an ambiguous PM ratio.
- Maintenance screenshot `2026-04-06 05:33:58` showed the statistics month order still rendered lexicographically.
- The ML governance / appendix screenshots were treated as secondary review signals only; the current routed ML surface already reflected Task6D, so this run only aligned the maintenance-context block and reused the shared card language.

## Routed Path Clarification

- The live routed maintenance page is now the sidebar item `🔧 Maintenance` in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py).
- That route still renders [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py).
- The routed ML page remains `🤖 Efficiency Prediction & Governance` in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py), rendered by [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py).
- The routed Optimization page remains `🎯 Operational Decision Support` in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py), rendered by [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py).
- No archived `History/` files or stale duplicate routes were edited.

## Exact File List Touched

- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
- [`core/maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/maintenance_evidence.py)
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
- [`tests/test_maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_maintenance_evidence.py)
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
- [`docs/technical/TASK6E_MAINTENANCE_EVIDENCE_CONVERGENCE_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK6E_MAINTENANCE_EVIDENCE_CONVERGENCE_REPORT.md)

## Exact Reason For Each Change

- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - renamed the routed sidebar label from `🔧 Maintenance Appendix` to `🔧 Maintenance`
  - updated the global app description so maintenance is framed as evidence rather than appendix-only admin space
- [`core/maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/maintenance_evidence.py)
  - added the one approved narrow read-only helper for maintenance coverage snapshots, machine evidence summaries, chronological month parsing/sorting, and compact cross-module maintenance context payloads
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - rebuilt the routed page around `Maintenance Evidence & Coverage`
  - replaced the conflicting top notes with one unified status banner plus subordinate reference wording
  - moved storage/coverage cards to the first screen
  - replaced the ambiguous machine-history block with explicit all-time vs recent-window metrics and honest recent-window labeling
  - moved upload/raw browsing into `Admin / Details`
  - removed the page-load `MaintenanceDataIntegration()` initialization so routed read-only renders no longer touch schema setup
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - added a compact `Maintenance Evidence Context` block inside `Scenario Lab`
  - kept the new block read-only and explicitly non-ranking
- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - added the same compact `Maintenance Evidence Context` block inside the selected-machine review
  - kept the worklist scoring and model-backed preview logic unchanged
- [`tests/test_maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_maintenance_evidence.py)
  - added focused coverage for the new helper, the chronological month-sorting rule, the machine-history contract, and the compact cross-module maintenance context payload
- [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
  - marked Task6E passed and recorded the routed maintenance-evidence closure plus smoke evidence
- [`docs/technical/REBUILD_DOCS_INDEX.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md)
  - indexed this closeout report for future recovery
- [`docs/technical/TASK6E_MAINTENANCE_EVIDENCE_CONVERGENCE_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK6E_MAINTENANCE_EVIDENCE_CONVERGENCE_REPORT.md)
  - recorded the exact Task6E scope, validation, and pass outcome

## New Maintenance Evidence Helper

Yes.

[`core/maintenance_evidence.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/maintenance_evidence.py) was added as the one narrow read-only helper for this task.

Its scope is limited to:

- maintenance storage/coverage snapshots
- chronological month parsing and ordering for maintenance month labels
- deterministic machine-level maintenance evidence summaries from existing maintenance tables
- readable recent-history windows
- compact cross-module maintenance context payloads for ML and Optimization

It does not create new persistence, does not write the live DB, and does not invent new maintenance labels or risk scores.

## Exact Machine-History Contract Chosen

Option A was chosen.

The maintenance page now preserves:

- `Total Events (All Time)`
- `Recent Events Shown`
- `PM Ratio (All Time)`
- `PM Ratio (Recent Window)`
- `Latest Work Order Type`
- `Days Since Last Maintenance`

The recent history table is explicitly labeled as a limited recent window and currently shows the latest `50` events for readability. The page no longer mixes all-time counts with unlabeled recent-window ratios.

## Exact Month-Sorting Rule Chosen

The maintenance page now parses month labels with the deterministic rule `pd.to_datetime(label, format="%B %Y", errors="coerce")`.

Applied behavior:

- valid `Month YYYY` labels are sorted chronologically ascending
- invalid labels, if any, are pushed after valid labels in deterministic text order
- the same helper-backed rule is used for:
  - maintenance coverage snapshot month range
  - `Browse Records` month filters
  - `Records by Month` visual ordering

## Top Banner Resolution

The old blue/yellow contradiction was removed.

New behavior:

- one page-level status banner answers the storage/coverage question only
- subordinate caption text explains that legacy risk outputs and maintenance-age energy context are supporting evidence only
- advanced/legacy reference sections no longer contradict the page-level coverage state

## ML Maintenance Evidence Added

The routed ML page now shows `Maintenance Evidence Context` inside `Scenario Lab`.

Fields added:

- `Days Since Last Maintenance`
- `Total Events`
- `PM Ratio (All Time)`
- `Recent Events Shown`
- `Latest Work Order Type`

Context note:

- the block states explicitly that it is direct maintenance-table context reused from `🔧 Maintenance`
- the block states explicitly that it enriches the review story but does not change review-queue ranking

## Optimization Maintenance Evidence Added

The routed Optimization page now shows the same `Maintenance Evidence Context` inside the selected-machine review.

Fields added:

- `Days Since Last Maintenance`
- `Total Events`
- `PM Ratio (All Time)`
- `Recent Events Shown`
- `Latest Work Order Type`

Context note:

- the block states explicitly that it is direct maintenance-table context reused from `🔧 Maintenance`
- the block states explicitly that it does not re-score the worklist

## Tests Run

- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m py_compile app.py core/maintenance_evidence.py modules/maintenance_module.py modules/ml_module.py modules/optimization_module.py tests/test_maintenance_evidence.py tests/test_ml_module.py tests/test_optimization_module.py`
- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.conda311/bin/python -m unittest tests.test_maintenance_evidence tests.test_ml_module tests.test_optimization_module tests.test_intervention_preview`
  - result: `27` tests passed

## Routed Smoke Summary

- read-only routed render smoke:
  - Maintenance render: `ok`
  - ML render: `ok`
  - Optimization render: `ok`
- runtime notes:
  - Streamlit still emitted the existing invalid config-option warnings for `client.model_context_window` and `client.model_auto_compact_token_limit`
  - the ML render still shows the existing non-fatal `Session state does not function when running a script without streamlit run` note in plain-script smoke mode
- DB write check:
  - `shasum manufacturing_data.db` before smokes: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - `shasum manufacturing_data.db` after smokes: `ac891558ddeec25119f6e7ac3cbd7fee427de8c1`
  - result: no active DB write was detected during the read-only routed smokes

## Real-Month Maintenance Smoke Summary

- month used: `June 2025`
- maintenance coverage snapshot:
  - stored records: `14,378`
  - integrated machines: `61`
  - months covered: `20`
  - chronological month range: `January 2024` -> `August 2025`
- selected-machine evidence:
  - machine: `166-002`
  - all-time events: `165`
  - recent events shown: `50`
  - latest work-order type: `AM`
  - latest maintenance datetime: `2025-08-05 16:36`
- ML maintenance context:
  - first live review-queue machine with maintenance evidence: `166-002`
  - days since last maintenance: `244`
  - total events: `165`
  - latest work-order type: `AM`
- Optimization maintenance context:
  - first live selected-machine candidate with maintenance evidence: `024-081`
  - days since last maintenance: `257`
  - total events: `89`
  - latest work-order type: `AM`
- DB write check:
  - live DB hash remained unchanged across the real-month smoke

## Remaining Limitations

- the maintenance page is now reviewer-facing for evidence and coverage, but upload/raw browsing still remains intentionally lower under `Admin / Details`
- the legacy/admin `maintenance_ml_features` risk table is still available only as reference; it is not the primary maintenance contract
- the recent machine-history table intentionally shows the latest `50` events for readability rather than full raw history
- maintenance evidence remains descriptive context only; it is not a predictive-maintenance model or scheduling engine

## Should Task6E Be Considered Passed

Yes.

For the accepted final-stage evidence-convergence scope, the routed maintenance surface is now closed through Task6E and the cross-module maintenance evidence chain should be considered complete for presentation use.
