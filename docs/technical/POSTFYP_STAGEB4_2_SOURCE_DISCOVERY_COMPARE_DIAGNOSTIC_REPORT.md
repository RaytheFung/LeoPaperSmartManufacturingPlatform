# Post-FYP Stage B4.2 Source Discovery Compare Diagnostic Report

## Purpose

Stage B4.2 adds a read-only diagnostic helper and script for comparing legacy and manifest-backed source discovery across the accepted extension-month range before any default switch is considered.

## Scope

This stage adds a diagnostic script, focused tests, data-contract documentation, and this technical report.
It does not run ETL, run canonical materialization, write `manufacturing_data.db`, change default `discovery_mode`, or expose manifest mode in Streamlit.

## Files changed

- `scripts/compare_source_discovery_modes.py`
- `tests/test_source_discovery_compare_diagnostic.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB4_2_SOURCE_DISCOVERY_COMPARE_DIAGNOSTIC_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Diagnostic helper/script behavior

`scripts/compare_source_discovery_modes.py` provides `build_source_discovery_compare_diagnostics()` and a CLI entry point.
The helper instantiates `ETLPipelineModule(initialize_schema=False)`, calls `resolve_historical_month_sources(..., discovery_mode="compare")`, and returns structured rows with legacy status, manifest status, readiness, match status, differences, expected-blocked status, and errors.

The CLI prints a concise text report by default, supports `--json` for JSON stdout, and supports `--data-root <path>`.
It exits `0` when all accepted months match and March 2026 remains blocked, and exits non-zero for accepted-month mismatches or unexpected errors.

## Expected month coverage

The diagnostic checks:

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

March 2026 is expected blocked/out-of-scope.
The diagnostic treats March 2026 as passing only when both legacy and manifest paths report blocked status.

## Runtime behavior impact

None.
The diagnostic is opt-in, read-only, and not wired into the Streamlit UI or active ETL execution path.
Default source discovery remains legacy.

## Tests run

Stage B4.2 validation used Python 3.11:

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`

## Unsafe file scan

Required scans must show no database files, local environment folders, raw Excel files, model artifacts, generated `etl_outputs`, or report-stage files staged.
The diagnostic must not create a DB file.

## Out of scope

- ETL execution.
- Canonical materialization.
- Runtime database writes.
- Streamlit UI exposure.
- Default discovery-mode switching.
- Wiring `data_quality_rules.v1.json` into Silver or Gold runtime behavior.
- ML retraining or artifact promotion.

## Remaining risks

The diagnostic proves source-path payload equivalence, not ETL output equivalence.
It remains an evidence tool for future governance and does not itself justify changing defaults.

## Recommended B4.3

Use the B4.2 diagnostic as a preflight gate for a proposed default-switch plan.
B4.3 should define explicit pass/fail criteria, rollback to legacy discovery, and runtime smoke evidence before any default changes are made.
