# Post-FYP Stage B4.3 ETL Source Discovery Diagnostic Surface Report

## Purpose

Stage B4.3 exposes the Stage B4.2 source-discovery compare diagnostic on the ETL page as a collapsed, read-only reference surface.
The purpose is to make the legacy-vs-manifest source-discovery contract visible for audit without changing operational ETL behavior.

## Scope

This stage adds a pure diagnostic snapshot helper, a collapsed ETL-page expander, focused tests, data-contract documentation, and this technical report.
It does not run ETL, run canonical materialization, write `manufacturing_data.db`, change default `discovery_mode`, expose manifest as an operational ETL option, stage raw Excel files, or create generated ETL outputs.

## Files changed

- `modules/etl_module.py`
- `tests/test_etl_source_discovery_diagnostic_surface.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB4_3_ETL_SOURCE_DISCOVERY_DIAGNOSTIC_SURFACE_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Diagnostic surface behavior

`modules/etl_module.py` now renders a collapsed expander named `Reference & Audit: Source Discovery Contract Check` in the ETL upload tab after the existing historical source availability table.
The expander displays summary metrics, an OK/review status message, and a row-level table covering the same July 2025 through March 2026 diagnostic scope as Stage B4.2.

The UI is reference-only.
It contains no file upload action, no ETL trigger, no manifest-mode selector, no materialization action, and no database write path.

## Snapshot helper behavior

`modules.etl_module.build_source_discovery_diagnostic_snapshot(data_root=None)` builds a pure-data snapshot for the ETL page and tests.
It lazily imports `scripts.compare_source_discovery_modes.build_source_discovery_compare_diagnostics()` to avoid a module import cycle, then formats the diagnostic rows into display-ready dictionaries.

The helper does not use Streamlit runtime APIs and the underlying B4.2 diagnostic instantiates `ETLPipelineModule(initialize_schema=False)`.
This keeps the helper read-only and avoids schema initialization.

## Diagnostic month coverage

The diagnostic surface covers:

- July 2025
- August 2025
- September 2025
- October 2025
- November 2025
- December 2025
- January 2026
- February 2026
- March 2026

## March 2026 blocked behavior

March 2026 remains expected blocked/out-of-scope.
The diagnostic surface treats March 2026 as OK only when both legacy and manifest discovery report blocked status.

## Default runtime behavior impact

Default source discovery remains legacy.
No active ETL call path is switched to manifest mode, no new operational option is exposed, and no Streamlit write controls are added.

## Tests run

Stage B4.3 validation uses Python 3.11 and includes the existing B1 through B4.2 source-discovery regression suites plus the new ETL diagnostic-surface tests:

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`

## Unsafe file scan

The intended staged set is limited to source, tests, and documentation.
No database files, local environment folders, raw Excel files, model artifacts, generated `etl_outputs`, or report-stage clutter should be staged.

## Out of scope

- ETL execution.
- Canonical materialization.
- Runtime database writes.
- Default source-discovery switching.
- Manifest mode as an operational ETL option.
- Streamlit write-capable controls.
- `data_quality_rules.v1.json` runtime wiring.
- ML retraining or artifact promotion.
- Raw Excel, generated ETL output, or database staging.

## Remaining risks

The diagnostic surface proves source-discovery payload equivalence visibility only.
It does not prove ETL output equivalence, materialized canonical table equivalence, runtime performance, or readiness to change defaults.

## Recommended B4.4

Keep B4.4 as a governance gate before any default switch.
It should define explicit approval criteria, rollback criteria, runtime smoke evidence, and an operator-facing decision record before manifest-backed discovery can become the default.
