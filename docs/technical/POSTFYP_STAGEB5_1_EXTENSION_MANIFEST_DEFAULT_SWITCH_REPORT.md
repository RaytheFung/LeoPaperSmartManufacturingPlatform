# Post-FYP Stage B5.1 Extension Manifest Default Switch Report

## Purpose

Stage B5.1 implements the narrow controlled default switch approved by the Stage B4.4 decision pack.
The historical source resolver now defaults to `auto`, using manifest-backed discovery for accepted extension months while preserving legacy behavior for the initial January 2025 through June 2025 historical path.

## Scope

This stage changes only `ETLPipelineModule.resolve_historical_month_sources()` default policy and the focused tests/docs around that policy.
It does not run ETL, run canonical materialization, write `manufacturing_data.db`, change manual upload/runtime ETL behavior, expose manifest mode as an operational Streamlit option, or wire data-quality rules into runtime processing.

## Files changed

- `modules/etl_module.py`
- `tests/test_source_discovery_integration.py`
- `tests/test_source_discovery_default_switch.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB5_1_EXTENSION_MANIFEST_DEFAULT_SWITCH_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Default policy before/after

Before Stage B5.1, `resolve_historical_month_sources()` defaulted to `discovery_mode="legacy"`.
Callers that omitted the mode used hard-coded legacy source discovery for both Jan-Jun historical months and extension months.

After Stage B5.1, the default is `discovery_mode="auto"`.
Explicit modes remain:

- `auto`: default policy.
- `legacy`: force legacy discovery.
- `manifest`: force manifest-backed discovery.
- `compare`: run both paths and return the legacy payload plus `manifest_equivalence`.

## Auto mode behavior

`auto` dispatch is intentionally small and reversible.
For accepted extension months covered by `EXTENSION_MONTH_SOURCE_MAPPINGS`, auto mode resolves through `core.source_manifest_discovery.resolve_manifest_month_sources()` and returns downstream-compatible source keys.
For blocked extension months, auto mode preserves blocked behavior.
For non-extension historical months, auto mode falls back to legacy discovery.

Rollback is a one-line default-policy restoration or a small dispatch revert.

## Legacy rollback path

Legacy source discovery remains fully available through `discovery_mode="legacy"`.
`EXTENSION_MONTH_SOURCE_MAPPINGS` remains in place.
Compare mode remains in place for preflight and regression evidence.

The rollback path is to change the default back to `legacy` or revert the `auto` extension-month dispatch.
No DB rollback is expected because source discovery itself does not write the database.

## Extension-month behavior

Accepted extension months July 2025 through February 2026 now resolve through manifest-backed discovery by default when callers omit `discovery_mode`.
The default payload retains the operational keys expected by downstream code:

- `dataset_root`
- `energy_files`
- `csi_file`
- `mes_file`
- `family_status`
- `notes`
- `backfill_readiness`

The default extension payload also includes `source_discovery_mode: auto_manifest` as diagnostic metadata.
Explicit legacy and compare modes still work for July 2025 and related accepted extension months.

## Jan-Jun behavior

January 2025 through June 2025 continue to use legacy historical file mappings in auto mode.
Those months are not covered by the Stage B2-B5.1 manifest `month_source_files` equivalence proof, so Stage B5.1 does not migrate them.

## March 2026 blocked behavior

March 2026 remains blocked and out of canonical scope.
Default auto resolution for March 2026 still raises a blocked-source error, and explicit manifest mode continues to block March 2026 through `canonical_scope_status: blocked_out_of_scope`.
The compare diagnostic continues to treat March 2026 as expected blocked rather than a failure.

## Runtime behavior impact

The only active default change is the historical resolver path for accepted extension months.
Manual upload/runtime ETL behavior is unchanged because upload processing uses uploaded files directly and no manifest operational selector was added.
`run_historical_canonical_backfill()` still calls the resolver, but Stage B5.1 validation did not run that backfill path or materialization.

## Tests run

Stage B5.1 validation used Python 3.11 with `PYTHONPYCACHEPREFIX` outside the working tree.

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Unsafe file scan

The intended staged set is limited to source, tests, and documentation.
Required scans must show no database files, local environment folders, raw Excel files, generated `etl_outputs`, model artifacts, or unintended report-stage clutter staged.
`manufacturing_data.db` remains local-only and ignored by the `*.db` rule.

## Out of scope

- ETL execution.
- Canonical materialization.
- Runtime database writes.
- Manual upload/runtime ETL behavior changes.
- Streamlit write-capable controls.
- Manifest mode as a manual upload execution option.
- Jan-Jun manifest migration.
- Data-quality rule runtime enforcement.
- ML retraining or artifact promotion.
- Raw Excel, generated ETL output, model artifact, or DB staging.

## Remaining risks

This stage switches source-path discovery defaults for accepted extension months only.
It still proves source payload equivalence, not ETL output equivalence or materialized canonical table equivalence.
Jan-Jun source discovery remains legacy and should not be described as manifest-backed.
Runtime performance under actual historical backfill execution remains unproven because ETL/materialization were intentionally not run.

## Recommended B5.2

Stage B5.2 should be a read-only post-switch verification/audit task.
It should rerun compare diagnostics, verify default auto payloads for all accepted extension months, confirm Jan-Jun legacy behavior, confirm March 2026 remains blocked, and optionally add a read-only route smoke that does not trigger upload, backfill, or materialization.
