# Post-FYP Stage B2 Source Discovery Equivalence Report

## Purpose

Stage B2 added a manifest-backed, read-only source-discovery equivalence layer for the accepted extended source months.
Its purpose was to prove that manifest-backed source discovery can match the existing hard-coded extension discovery behavior before any active ETL default is changed.

## Scope

Stage B2 covered source-discovery metadata, helper functions, equivalence tests, and documentation only.
It did not run ETL, run canonical materialization, write the database, retrain models, promote artifacts, or replace active runtime source-discovery defaults.

## Files changed

- `config/source_manifest.v1.json`
- `core/source_manifest_discovery.py`
- `tests/test_source_manifest_discovery.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`

## Manifest-backed discovery layer

`config/source_manifest.v1.json` now includes `month_source_files` for accepted extended months `2025-07` through `2026-02`, plus blocked `2026-03`.
`core/source_manifest_discovery.py` provides read-only helpers for month label/key conversion, manifest month source lookup, path resolution under an explicit data root, manifest-backed availability matrix construction, and comparison against the legacy extension mapping.

## Legacy equivalence result

The manifest comparison reported:

- `matches: True`
- Checked months: July 2025 through March 2026
- Differences: none

The helper and test coverage also prove readiness-class equivalence for July 2025, August 2025, February 2026, and March 2026 against the existing `_build_extension_source_availability_dataframe` behavior.

## March 2026 blocked-scope behavior

March 2026 remains blocked and out of accepted canonical scope.
The manifest includes it only to preserve the explicit blocked boundary for grouped source files that can contain March rows.
Manifest resolution raises a blocking error for March 2026 instead of treating it as an accepted canonical month.

## Tests run

Stage B2 passed:

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- Manifest equivalence diagnostic

## Runtime behavior impact

None.
Stage B2 did not replace `ETLPipelineModule.resolve_historical_month_sources` default behavior and did not wire data-quality rules into Silver or Gold runtime behavior.

## Out of scope

- ETL execution.
- Canonical materialization.
- Database writes.
- Active ETL default replacement.
- Data-quality rule enforcement in `core/silver_normalizer.py`.
- ML retraining or artifact promotion.

## Remaining risks

- The manifest-backed layer is still read-only.
- Active runtime source discovery still uses the existing legacy path by default.
- Data-quality rules are still metadata-only.

## Recommended next stage

Stage B3 is the earliest stage where controlled runtime wiring may be considered.
It should use the Stage B2 equivalence layer as the safety basis, preserve rollback boundaries, and continue to prove that runtime behavior does not drift unexpectedly.
