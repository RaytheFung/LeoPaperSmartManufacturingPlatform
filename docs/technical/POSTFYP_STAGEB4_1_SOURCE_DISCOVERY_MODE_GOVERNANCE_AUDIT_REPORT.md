# Post-FYP Stage B4.1 Source Discovery Mode Governance Audit Report

## Purpose

Stage B4.1 audits the governance and caller impact of the optional source-discovery modes added in Stage B3.
The goal is to decide what is safe to expose or switch later, without changing defaults or runtime behavior in this task.

## Scope

This is an audit and documentation task.
It inventories current references to the source-discovery resolver, classifies caller impact, checks default-mode governance, and records recommended next steps.
It does not run ETL, run canonical materialization, write `manufacturing_data.db`, expose manifest mode in Streamlit, or change the default `discovery_mode`.

## Evidence basis

Evidence came from direct source review and `rg` reference scans for:

- `resolve_historical_month_sources`
- `discovery_mode`
- `EXTENSION_MONTH_SOURCE_MAPPINGS`
- `build_extension_source_availability`
- `_build_extension_source_availability_dataframe`

Files reviewed included the Stage B0/B1/B2/B3 reports, `DATA_CONTRACTS_GUIDE.md`, `REBUILD_DOCS_INDEX.md`, `config/source_manifest.v1.json`, `core/source_manifest_discovery.py`, `modules/etl_module.py`, `tests/test_source_discovery_integration.py`, `tests/test_task13_source_discovery.py`, `scripts/process_jan_to_june_2025.py`, `scripts/run_task16f_integrated_internal_landing_rehearsal.py`, and `app.py`.

## Caller inventory

Active runtime callers:

- `app.py` imports `render_etl_page` from `modules.etl_module`; it does not expose or pass `discovery_mode`.
- `modules/etl_module.py` routed ETL page builds the extension availability matrix through `_build_extension_source_availability_dataframe()`.
- `modules/etl_module.py` `run_historical_canonical_backfill()` calls `resolve_historical_month_sources(month_year, data_root=data_root)` without `discovery_mode`, so it remains legacy by default.
- `modules/etl_module.py` upload processing uses uploaded files directly and does not call the historical source resolver.

Diagnostic/script callers:

- `scripts/run_task13r_temp_sweep.py` calls `resolve_historical_month_sources(month, data_root=data_root)` without `discovery_mode`, so it remains legacy.
- `scripts/run_historical_canonical_backfill.py` constructs `ETLPipelineModule` and calls the historical backfill path; no manifest mode is selected by default.
- `scripts/run_task16f_integrated_internal_landing_rehearsal.py` reads `_build_extension_source_availability_dataframe()`, `EXTENSION_MONTH_SOURCE_MAPPINGS`, and `_resolve_extension_source_mapping()` for read-only rehearsal reporting.
- `scripts/process_jan_to_june_2025.py` creates `ETLPipelineModule` for legacy Jan-Jun processing support but does not use the Stage B3 discovery modes.

Test callers:

- `tests/test_source_discovery_integration.py` explicitly tests default, `legacy`, `manifest`, `compare`, March blocking, and invalid mode behavior.
- `tests/test_task13_source_discovery.py` verifies the legacy Task13 source mapping and March block unchanged.
- `tests/test_source_manifest_discovery.py` compares manifest and legacy extension mapping behavior.
- `tests/test_canonical_materializer.py` has legacy resolver coverage for missing initial-scope files and historical backfill reuse.

Dormant/legacy callers:

- Dormant app compatibility wrappers exist in `app.py`, but they delegate legacy pages and do not select source-discovery modes.
- No dormant path was found that enables manifest mode by default.

Documentation-only references:

- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB2_SOURCE_DISCOVERY_EQUIVALENCE_REPORT.md`
- `docs/technical/POSTFYP_STAGEB3_SOURCE_DISCOVERY_OPTIONAL_INTEGRATION_REPORT.md`
- This B4.1 report and `REBUILD_DOCS_INDEX.md`

## Active runtime impact assessment

Default runtime impact remains none.
The routed ETL page does not expose manifest or compare mode, and the historical resolver signature defaults to `discovery_mode="legacy"`.
Existing callers that omit `discovery_mode` continue to receive the pre-Stage-B3 legacy payload shape.

The source-discovery mode itself does not execute ETL, materialize canonical tables, or write the database.
Database writes still occur only in the pre-existing ETL/backfill execution paths after source discovery returns file paths and the caller proceeds into ETL processing.

## Discovery mode governance findings

- `legacy` remains the default mode and is the only mode reached by existing non-test callers.
- `manifest` is available only when explicitly requested by code.
- `compare` is available only when explicitly requested by code and returns the legacy operational payload when legacy resolution succeeds.
- No Streamlit UI control exposes `manifest` or `compare`.
- No app route silently switches to manifest-backed discovery.
- No data-quality rule file is wired into `core/silver_normalizer.py` or Gold materialization.

The clean future integration point is a read-only diagnostic helper or ETL diagnostics surface that calls compare mode for selected months and displays differences without running ETL.
Any default switch should remain a later gate after compare-mode evidence is collected and reviewed.

## March 2026 boundary check

March 2026 remains blocked in both legacy and manifest discovery paths.
Legacy mapping marks March 2026 family status as blocked, and manifest resolution blocks March 2026 because its canonical scope status is `blocked_out_of_scope`.
Stage B3 tests verify that default legacy resolution raises for March 2026, manifest mode raises for March 2026, and compare mode reports both blocked errors honestly.

## Risks before default switch

- Manifest mode is callable but has not been exercised by an active routed UI diagnostic on real filesystem state.
- Compare mode currently validates path payload equivalence, not downstream ETL output equivalence.
- Initial Jan-Jun source discovery still uses legacy static month mappings rather than `month_source_files`.
- A default switch could change error wording or metadata shape for callers if not guarded.
- Data-quality rules remain metadata-only, so a source-discovery switch must not be conflated with anomaly-rule runtime enforcement.

## Recommended B4.2

Add a read-only compare-mode diagnostic helper or CLI that checks all accepted extension months against an explicit data root and returns a compact JSON/table report.
It should not run ETL, should not write a database, and should keep March 2026 blocked.
This gives evidence for a later B4.3 default-switch gate without exposing manifest mode in the UI prematurely.

## Out of scope

- Changing `discovery_mode` defaults.
- Exposing manifest or compare mode in Streamlit.
- Running ETL or canonical materialization.
- Writing `manufacturing_data.db`.
- Wiring `data_quality_rules.v1.json` into Silver or Gold runtime behavior.
- Retraining or promoting ML artifacts.
- Removing legacy source-discovery code.

## Validation

Validation for this audit task used Python 3.11 and kept test behavior unchanged:

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`

The required unsafe-file scans are part of the pre-commit gate for this task.

## Remaining risks

The audit is source-based and test-backed, but it does not run ETL or prove ETL output equality.
The original runtime repo remains outside the GitHub-safe publication boundary.
A future default switch still needs its own guarded implementation task, rollback path, and validation evidence.
