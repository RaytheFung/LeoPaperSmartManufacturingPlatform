# Post-FYP Stage B8.3 Boundary-Month CSI Carry-Forward Policy Report

## Purpose

Stage B8.3 records the policy decision for boundary-month CSI carry-forward and overlap handling after the August 2025 temp-only rehearsal.
The decision is needed because B8.2 proved that an August-only clean ingestion can successfully run August ETL and canonical materialization while still failing to recover July-package CSI rows that canonicalize to August.

This report defines the boundary problem, compares policy options, selects the recommended direction, and defines the Stage B9 evidence requirement before any broader multi-month rehearsal.

## Scope

This is a documentation, policy, and design stage.
It adds this decision report, updates the rebuild docs index, and adds a short data-contract note.

It does not run ETL, run historical backfill, run canonical materialization, write the original runtime `manufacturing_data.db`, write any DB inside the GitHub-safe tree, promote a temp DB, retrain or promote ML artifacts, change source-discovery defaults, change runtime canonical predicates, wire DQ rules into runtime behavior, stage raw Excel files, stage generated `etl_outputs`, or modify `app.py`.

## Evidence summary from B7/B8

| Stage | Evidence | Result |
| --- | --- | --- |
| B7.1 | July-package CSI extracted-versus-canonical audit | `235` July-package rows canonicalize to August, not July. |
| B7.2 | CSI month-assignment policy decision | Current first-available timestamp canonical month policy was accepted for Stage B7 evidence. |
| B7.3 | August spill traceability audit on the B6.4 temp DB | `235/235` spill identities were traceable in August raw and silver scope while July-package provenance was present. |
| B8.1 | August rehearsal preflight | Required B8.2 to prove spill identity capture under August raw and silver scope. |
| B8.2 | August-only clean-baseline rehearsal | August ETL/backfill/materialization succeeded, but B7.3 spill traceability returned raw matched `0/235` and silver matched `0/235`. |

B8.2 also showed that August-only canonical materialization itself completed successfully:

| B8.2 surface | Result |
| --- | ---: |
| extracted Energy rows | `99695` |
| extracted CSI rows | `22572` |
| extracted MES rows | `20884` |
| Bronze `raw_csi_event` August rows | `22399` |
| Silver `csi_job_event` August rows | `22399` |
| Gold `fact_machine_hour` August rows | `64727` |
| duplicate August raw/silver CSI source-row-hash groups | `0` |

Therefore the B8.2 failure is not a general August execution failure.
It is a boundary-month source-provenance failure: the missing identities are timestamp-August CSI rows carried by the July source package.

## Boundary problem definition

Source package month and canonical event month can diverge.
A CSI row may be extracted from the July source package but assigned to August canonical scope by timestamp semantics.
Running only the August source package can therefore omit rows whose canonical month is August but whose source provenance belongs to the previous package.

This creates a concrete completeness problem:

- source discovery by target month can select the current month package;
- ETL extraction can successfully load current-package rows;
- canonical materialization can correctly assign rows by timestamp;
- but target-month canonical completeness is still not guaranteed unless adjacent-package spill rows are included or reconciled.

The B8.2 result demonstrates this exact case.
The August-only package begins canonical raw CSI at `2025-08-01 08:00:00`, while the B7.1 July-package spill identities include rows beginning at `2025-08-01 00:02:01`.
Those rows canonicalize to August but are not reintroduced by August-only ingestion.

## Policy options considered

### Option A: Accept package-month isolation

This option accepts that August completeness excludes July-package spill rows.
It is operationally simple because a target month only ingests its same-month package.

This option is rejected as the default policy because it silently weakens canonical August completeness while preserving timestamp semantics.
It would allow August dashboards and Gold facts to omit valid timestamp-August CSI identities unless every report clearly subtracts boundary exclusions.

### Option B: Carry-forward spill rows

This option captures previous-package rows whose canonical month belongs to the current target month and reconciles them before materialization.
It preserves timestamp semantics and directly addresses the B8.2 failure.

This option is recommended as the next design direction.
It should be introduced first as a temp-only preflight/helper stage, not as immediate runtime wiring.

### Option C: Multi-package boundary ingestion

This option ingests the current package plus adjacent previous/next package windows for each target month.
It gives stronger boundary completeness and may generalize beyond July/August, but it has higher duplicate, runtime, and governance complexity.

This option remains a viable future extension, but it is too broad for immediate adoption before a narrow carry-forward preflight proves identity preservation and duplicate control.

### Option D: Change canonical predicate to package month

This option assigns canonical month by source package or staging month instead of event timestamp.
It simplifies package accounting and would make package-month row counts easier to explain.

This option is rejected for now because it weakens event-time semantics and would reverse the B7.2 policy without broader downstream evidence.
Changing canonical predicates would require month-by-month regression evidence, Gold impact analysis, report compatibility review, and an explicit rollback plan.

### Option E: Hybrid audit-only boundary exclusions

This option keeps runtime unchanged and reports boundary spill rows as exclusions.
It is low-risk for code but does not solve canonical monthly completeness.

This option is acceptable only as an interim reporting posture.
It is not sufficient before claiming complete August canonical output.

## Policy decision

The Stage B8.3 policy decision is:

- keep current first-available timestamp CSI canonical month semantics;
- do not accept silent exclusion of previous-package rows that canonicalize to the target month;
- do not change runtime canonical predicates in this stage;
- do not wire carry-forward behavior into runtime in this stage;
- treat B8.2 as evidence that August-only ingestion is insufficient for canonical August completeness;
- design a future controlled carry-forward or adjacent-package boundary reconciliation preflight before broader multi-month rehearsal.

This is a hold-and-design decision.
It preserves the B7.2 timestamp policy while acknowledging that source package selection must account for boundary overlap.

## Recommended future carry-forward strategy

Stage B9 should define a read-only or temp-only carry-forward preflight helper for boundary-month CSI rows.
The helper should identify previous-package rows whose canonical month equals the target month and prepare them for reconciliation before materialization evidence is claimed.

Minimum strategy:

1. For a target month, inspect the previous package and current package under the current CSI canonical month expression.
2. Identify previous-package CSI rows whose canonical month equals the target month.
3. Preserve stable identity fields and `source_row_hash` wherever available.
4. Compare carry-forward candidates against current-package target-month rows to prevent duplicate identities.
5. Produce an inclusion/reconciliation plan without writing live DB state.
6. Run any execution only against a temp DB outside Git.
7. Compare carry-forward-enhanced output with the B8.2 August-only baseline.

For August 2025, the expected proof target is the B7.1/B7.3 set of `235` July-package spill identities.
The future helper should prove whether those identities can be included or reconciled without duplicate raw/silver source-row-hash groups.

## Why runtime is not changed now

Runtime is not changed in B8.3 because the evidence identifies a policy and design gap, not a safe narrow implementation patch.
Carry-forward affects source discovery, extraction scope, duplicate protection, Bronze/Silver provenance, Gold aggregation, and report interpretation.

Immediate runtime wiring would risk:

- introducing duplicate CSI rows when both packages contain overlapping identities;
- changing canonical row counts without a formal comparison baseline;
- conflating source package month, ETL staging month, and canonical event month;
- hiding the B8.2 evidence gap behind unreviewed implementation behavior;
- expanding scope beyond the approved documentation/policy stage.

## Impact on future multi-month rehearsal

A broader multi-month rehearsal should not proceed directly from B8.2 as if August-only ingestion proved complete August canonical scope.
Future multi-month evidence must include boundary-month handling before making completeness claims.

At minimum, future rehearsal reports must separate:

- source package month;
- ETL staging month label;
- canonical Bronze/Silver event month;
- previous-package spill rows carried into target-month scope;
- duplicate identity/hash checks;
- Gold row-count and aggregate impact with and without carry-forward.

Stage B9 should produce the carry-forward preflight design and evidence contract first.
Only after that should a broader temp-only multi-month rehearsal be considered.

## Risks if ignored

If the boundary issue is ignored, the platform can produce apparently successful monthly canonical runs that are incomplete for timestamp semantics.
Specific risks include:

- August canonical CSI and Gold output can omit valid timestamp-August rows from the July package.
- Reviewers may interpret the B8.2 August success as full August completeness even though spill traceability failed.
- Future multi-month runs may produce inconsistent boundary treatment between adjacent months.
- Monthly KPI, production quantity, source-flag, and Gold aggregation evidence may be understated at month boundaries.
- Later attempts to fix the issue may need retroactive reconciliation if boundary exclusions are not tracked early.

## Out of scope

- ETL execution.
- Historical backfill execution.
- Canonical materialization execution.
- Runtime source-discovery default changes.
- Runtime canonical predicate changes.
- Carry-forward runtime implementation.
- DQ runtime wiring.
- Live or temp DB promotion.
- ML retraining or model artifact promotion.
- Streamlit UI changes.
- `app.py` changes.
- March 2026 reopening.
- Broad multi-month rehearsal execution.

## Validation

B8.3 is documentation-focused and does not change runtime code.
The required validation set was still run before commit:

- `python3.11 -m unittest tests.test_backfill_rehearsal_preflight`
- `python3.11 -m unittest tests.test_august_temp_backfill_rehearsal_safety`
- `python3.11 -m unittest tests.test_august_csi_spill_traceability_safety`
- `python3.11 -m unittest tests.test_july_csi_spill_audit_safety`
- `python3.11 -m unittest tests.test_temp_backfill_rehearsal_safety`
- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_source_discovery_post_switch_audit tests.test_source_discovery_stage_b5_closeout`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Remaining risks

- B8.3 selects a policy direction but does not implement carry-forward logic.
- The current B8.2 August-only baseline remains incomplete for the `235` July-package spill identities.
- A future carry-forward design may reveal additional edge cases in later month boundaries.
- Duplicate avoidance must be proven before any carry-forward output is trusted.
- Business stakeholders may still need to approve whether timestamp semantics remain the permanent CSI canonical rule.

## Recommended Stage B9

Recommended Stage B9: boundary-month CSI carry-forward preflight.

Stage B9 should:

- identify previous-package spill rows for a target month;
- preserve and compare `source_row_hash` and stable composite identity;
- generate a carry-forward/reconciliation plan without live DB writes;
- prove duplicate prevention;
- compare carry-forward-enhanced August evidence with the B8.2 August-only baseline;
- remain temp-only or read-only;
- avoid live DB promotion, runtime predicate changes, and broad multi-month execution until the carry-forward evidence is accepted.
