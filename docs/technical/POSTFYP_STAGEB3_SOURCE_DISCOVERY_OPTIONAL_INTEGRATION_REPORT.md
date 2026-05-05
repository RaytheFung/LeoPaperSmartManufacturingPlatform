# Post-FYP Stage B3 Source Discovery Optional Integration Report

## Purpose

Stage B3 integrates the manifest-backed source-discovery layer into the ETL module boundary as an optional, guarded resolver mode.
The goal is to make the Stage B2 manifest path callable from the ETL resolver without changing active runtime defaults.

## Scope

This stage updates the ETL source resolver, adds focused integration tests, updates the data-contract guide, and records this technical report.
It does not run ETL, run canonical materialization, write `manufacturing_data.db`, retrain models, promote artifacts, or change Streamlit route behavior.

## Files changed

- `modules/etl_module.py`
- `tests/test_source_discovery_integration.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB3_SOURCE_DISCOVERY_OPTIONAL_INTEGRATION_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Optional discovery modes

`ETLPipelineModule.resolve_historical_month_sources()` now accepts `discovery_mode`.

- `legacy`: current default behavior.
- `manifest`: resolves source files through `core.source_manifest_discovery.resolve_manifest_month_sources()`.
- `compare`: runs both legacy and manifest discovery, returns the legacy operational payload when available, and adds `manifest_equivalence`.

Invalid mode values raise `ValueError`.

## Default runtime behavior impact

Default behavior remains legacy.
Existing callers that omit `discovery_mode` receive the same legacy payload shape as before, without a new `source_discovery_mode` field.
The ETL UI is not switched to manifest mode in Stage B3.

## Manifest mode behavior

Manifest mode accepts the same month labels as the legacy extension resolver, including `July 2025`, `February 2026`, and `March 2026`.
It uses the same explicit `data_root` semantics as the legacy resolver and returns the downstream-compatible keys `dataset_root`, `energy_files`, `csi_file`, `mes_file`, `family_status`, `notes`, and `backfill_readiness`.
March 2026 remains blocked.

## Compare mode behavior

Compare mode resolves both paths and compares `energy_files`, `csi_file`, `mes_file`, `family_status`, and `backfill_readiness`.
For July 2025 with placeholder source files, the mode returns the legacy operational payload plus `manifest_equivalence = {"matches": True, "differences": []}`.
For March 2026, both paths report blocked status and the diagnostic preserves both error messages instead of hiding the block.

## Tests run

Stage B3 validation used Python 3.11.

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`

## Unsafe file scan

Required pre-commit scans must show no database files, local environment folders, raw Excel files, model artifacts, generated `etl_outputs`, or report-stage files staged.
`manufacturing_data.db` remains ignored through the `*.db` rule and must remain local-only runtime state.

## Out of scope

- ETL execution.
- Canonical materialization.
- Runtime database writes.
- Streamlit UI mode switching.
- Replacing legacy source discovery defaults.
- Wiring `data_quality_rules.v1.json` into Silver or Gold runtime behavior.
- ML retraining or artifact promotion.

## Remaining risks

The manifest path is now callable from the ETL resolver, but it is still optional.
Any future default switch still needs a separate guarded task with explicit rollout, rollback, and runtime smoke evidence.
Data-quality rule metadata remains separate from runtime enforcement.

## Recommended Stage B4

Stage B4 should evaluate whether a controlled default-switch plan is justified.
It should use compare-mode evidence first, keep March 2026 blocked, preserve a rollback path to legacy discovery, and avoid wiring data-quality rules into Silver until that is explicitly scoped.
