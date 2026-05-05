# Post-FYP Stage B5.2 Post-Switch Audit and Diagnostics Report

## Purpose

Stage B5.2 adds read-only post-switch audit evidence and hardens the ETL diagnostic wording after the Stage B5.1 default-policy switch.
The goal is to make the active policy clear to reviewers without running ETL, materializing canonical tables, writing a database, or changing runtime execution behavior.

## Scope

This stage adds a pure policy-audit helper, updates the existing ETL diagnostic expander wording, adds focused tests, and records documentation.
It does not change the Stage B5.1 default policy, run ETL, run canonical materialization, write `manufacturing_data.db`, alter manual upload/runtime ETL behavior, or expose manifest mode as a manual upload execution option.

## Files changed

- `modules/etl_module.py`
- `tests/test_source_discovery_post_switch_audit.py`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `docs/technical/POSTFYP_STAGEB5_2_POST_SWITCH_AUDIT_AND_DIAGNOSTICS_REPORT.md`
- `docs/technical/REBUILD_DOCS_INDEX.md`

## Post-switch audit behavior

`modules.etl_module.build_source_discovery_default_policy_audit(data_root=None)` returns structured source-discovery policy evidence:

- `default_policy: auto`
- `extension_default: manifest`
- `initial_jan_jun_default: legacy`
- `manual_upload_behavior: unchanged`
- accepted extension months July 2025 through February 2026
- blocked month March 2026
- row-level default, explicit legacy, compare, readiness, expected policy, and OK status

The helper instantiates `ETLPipelineModule(initialize_schema=False)`.
It performs source-discovery resolution only and does not run ETL, canonical materialization, or file output.

## ETL diagnostic wording update

The collapsed `Reference & Audit: Source Discovery Contract Check` expander now states:

`Active default policy: auto. Accepted extension months use manifest-backed source discovery by default; Jan-Jun historical months remain legacy; manual uploads are unchanged.`

The expander also shows a low-prominence active default policy audit table before the existing legacy-vs-manifest comparison table.
No buttons, write controls, materialization actions, or operational discovery-mode selectors were added.

## Extension-month default behavior

Accepted extension months July 2025 through February 2026 are expected to resolve with `source_discovery_mode: auto_manifest` under the default resolver policy.
The compare diagnostic still reports legacy and manifest payload matches for accepted extension months.

## Jan-Jun legacy behavior

January 2025 through June 2025 remain legacy by default.
The audit helper marks these rows with expected policy `legacy` and compare status `not_applicable_initial_legacy`.
Placeholder source files are enough for tests; real raw Excel files are not required.

## March 2026 blocked behavior

March 2026 remains expected blocked.
The audit helper treats March 2026 as OK only when default auto mode, explicit legacy mode, and compare mode preserve blocked status.

## Manual upload behavior

Manual upload/runtime ETL behavior remains unchanged.
The audit reports `manual_upload_behavior: unchanged`, and the ETL diagnostic surface does not expose manifest mode as a manual upload execution option.

## Runtime behavior impact

No new runtime execution behavior was added.
The diagnostic surface remains read-only and collapsed.
Stage B5.2 does not alter the B5.1 resolver default policy, does not run historical backfill, and does not initialize schema through the audit helper.

## Tests run

Stage B5.2 validation used Python 3.11 with `PYTHONPYCACHEPREFIX` outside the working tree.

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_source_discovery_post_switch_audit`
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
- Stage B5.1 default-policy changes.
- Manual upload/runtime ETL behavior changes.
- Streamlit write-capable controls.
- Manifest mode as a manual upload execution option.
- Data-quality rule runtime enforcement.
- ML retraining or artifact promotion.
- Raw Excel, generated ETL output, model artifact, or DB staging.

## Remaining risks

The audit verifies source-discovery policy and path-resolution behavior only.
It does not prove ETL output equivalence, canonical materialization equivalence, or runtime performance under actual historical backfill execution.
Jan-Jun remains legacy and should not be described as manifest-backed.

## Recommended B5.3

Stage B5.3 should remain read-only unless explicitly scoped otherwise.
Recommended next evidence is a lightweight route/render smoke or operator-facing audit note that confirms the ETL page renders the post-switch diagnostics without triggering upload, backfill, materialization, or DB writes.
