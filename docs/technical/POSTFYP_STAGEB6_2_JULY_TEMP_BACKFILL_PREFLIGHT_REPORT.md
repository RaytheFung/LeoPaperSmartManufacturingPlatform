# Post-FYP Stage B6.2 July Temp Backfill Preflight Report

## Purpose

Stage B6.2 adds a read-only preflight helper and rehearsal plan for a future July 2025 temp-only historical backfill rehearsal.
It follows the Stage B6.1 call-chain audit and prepares the evidence contract required before any execution task is approved.

## Scope

This stage adds a source-discovery-only planning helper, focused tests, and documentation.
It does not run ETL, run historical backfill, run canonical materialization, copy or create a DB, write `manufacturing_data.db`, alter Streamlit upload/manual ETL behavior, retrain or promote models, or wire data-quality rules into runtime materialization.

## Files changed

- `core/backfill_rehearsal_preflight.py`
- `tests/test_backfill_rehearsal_preflight.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB6_2_JULY_TEMP_BACKFILL_PREFLIGHT_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Preflight helper behavior

`core.backfill_rehearsal_preflight.build_historical_backfill_preflight_plan()` builds a structured plan for a future temp-only rehearsal.
The default target is `July 2025`.

The helper returns:

- target month and month key
- Stage B5 source-discovery policy summary
- default resolver mode and rollback availability
- source payload summary
- source payload equivalence status
- expected source files and source-family status
- planned future execution steps
- planned write surfaces
- temp DB and live/repo DB boundaries
- staging and model-artifact prohibitions
- rollback boundary
- abort criteria
- required post-run evidence
- proof gaps

The helper uses `ETLPipelineModule(initialize_schema=False)` and the existing compare diagnostic path.
It does not call `extract_all_sources()`, `run_historical_canonical_backfill()`, `save_etl_results()`, or canonical materialization.
It does not connect to SQLite, create DB files, copy DB files, load raw Excel content, or write output files.

## July 2025 candidate rationale

July 2025 remains the recommended first rehearsal candidate because it is the first accepted extension month and has complete Energy/CSI/MES source-family status.
It avoids the first-pass ambiguity introduced by August 2025 sentinel-anomaly flags and February 2026 partial/quarantine handling.

July still requires month-scoping proof in a future execution task because source workbooks can include spill rows outside the target month.

## Planned execution steps for future rehearsal

The plan describes the future rehearsal sequence only:

1. Confirm July 2025 remains accepted and source-discovery compare diagnostics pass.
2. Create a temp-only DB copy outside the Git working tree in the future execution task.
3. Run `ETLPipelineModule.run_historical_canonical_backfill()` for July 2025 against the temp DB only.
4. Capture extracted Energy/CSI/MES row counts after month scoping.
5. Capture machine mapping and partial-match counts.
6. Capture ETL staging, Bronze, Silver, Gold, and `fact_machine_hour` row counts.
7. Capture aggregate energy, quantity, source-flag, and quarantine checks.
8. Run downstream regression tests and unsafe-file scans before staging evidence.

## Planned write surfaces

The future rehearsal write surfaces are explicitly limited to:

- temp DB copy only
- ETL staging tables on the temp DB
- Bronze raw tables on the temp DB
- Silver month partitions on the temp DB
- Gold `fact_machine_hour` month partition on the temp DB

No live DB, repo-local DB, raw source file, generated `etl_outputs` file, model artifact, or Streamlit runtime state may be written or staged.

## Temp DB boundary

The preflight helper marks `temp_db_required` as true and `live_db_write_allowed` / `repo_db_write_allowed` as false.
It accepts an optional `db_path` only as a planned path string in the returned dict.
It does not validate, create, copy, open, or connect to that path.

## Abort criteria

A future rehearsal must abort if:

- the DB path is not temp-only or is inside the Git working tree
- repo-local `manufacturing_data.db` or another live/shared DB would be written
- source payload comparison mismatches
- March 2026 becomes accepted or leaks into target-month output
- extracted, mapping, ETL staging, Bronze, Silver, or Gold row counts materially diverge
- canonical materialization writes outside the temp DB
- runtime exceeds the declared safe threshold
- downstream regression tests fail
- DB files, raw Excel files, generated outputs, model artifacts, or local env folders would be staged

## Required post-run evidence

A future execution task must capture:

- source payload summary and compare diagnostic result
- extracted Energy/CSI/MES row counts after month scoping
- machine mapping counts and partial-match counts
- ETL staging row counts
- Bronze/Silver/Gold row counts
- `fact_machine_hour` month row count
- aggregate kWh, good quantity, scrap quantity, and quantity-basis checks
- source flag and quarantine consistency checks
- runtime duration and stage timing
- temp DB path proof plus live/repo DB non-write proof
- post-run regression tests and unsafe-file scans

## What remains unproven

The helper does not prove ETL output equivalence, canonical Silver/Gold materialization equivalence, runtime duration, or month-scoping behavior on real workbook rows.
It only makes the future execution contract explicit.

## Runtime behavior impact

No active runtime behavior changed.
The helper is not wired into Streamlit, upload/manual ETL execution, historical backfill buttons, materialization controls, ML training, optimization, or maintenance modules.

## Tests run

Stage B6.2 validation uses Python 3.11 with `PYTHONPYCACHEPREFIX` outside the working tree.

Required commands:

- `python3.11 -m unittest tests.test_backfill_rehearsal_preflight`
- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_source_discovery_post_switch_audit tests.test_source_discovery_stage_b5_closeout`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Unsafe file scan

The intended staged set is limited to the helper, focused tests, and documentation.
Required scans must show no database files, local environment folders, raw Excel files, generated `etl_outputs`, model artifacts, or unintended report-stage clutter staged.
`manufacturing_data.db` remains local-only and ignored by the `*.db` rule.

## Out of scope

- ETL execution.
- Historical backfill execution.
- Canonical materialization.
- DB copy, DB creation, DB write, or DB staging.
- Streamlit runtime or upload/manual ETL behavior changes.
- Write-capable controls.
- Data-quality rule runtime enforcement.
- ML retraining or model artifact promotion.
- Raw Excel or generated `etl_outputs` staging.
- March 2026 acceptance.

## Remaining risks

- The future July rehearsal still needs real execution evidence on a temp DB.
- Month-scoping and spill-row behavior remain execution-time proof gaps.
- Later accepted months still require separate flag/quarantine review after July is proven.
- A future execution task must keep DB path proof and unsafe-file scans explicit.

## Recommended B6.3

Recommended B6.3 is an explicitly approved July 2025 temp-only execution rehearsal.
It should copy the DB to a temp path outside Git, run one July backfill against that temp DB only, capture the full evidence set defined by B6.1 and B6.2, and stop before any shared DB promotion, Streamlit behavior change, data-quality rule enforcement, or model artifact work.
