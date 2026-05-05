# Post-FYP Stage B5 Source Discovery Default Switch Closeout Report

## Purpose

Stage B5 closes the controlled source-discovery default switch for accepted extension historical months.
This closeout records the final policy, validation evidence, boundaries, rollback path, and remaining proof gaps.

## Scope

Stage B5.3 is a validation and documentation closeout.
It adds a read-only closeout snapshot test, this report, and documentation index updates.
It does not change the Stage B5.1 default policy, run ETL, run canonical materialization, write `manufacturing_data.db`, change manual upload/runtime ETL behavior, or expose manifest mode as a manual upload execution option.

## Stage B5.1 summary

Stage B5.1 changed `ETLPipelineModule.resolve_historical_month_sources()` default source-discovery policy from `legacy` to `auto`.
In `auto` mode, accepted extension months July 2025 through February 2026 resolve through manifest-backed discovery by default.
January 2025 through June 2025 remain legacy, March 2026 remains blocked, and explicit `legacy`, `manifest`, and `compare` modes remain available.

## Stage B5.2 summary

Stage B5.2 added `build_source_discovery_default_policy_audit()` and hardened the ETL diagnostic wording.
The diagnostic expander now states the active `auto` policy and shows a read-only policy audit table beside the legacy-vs-manifest comparison evidence.

## Stage B5.3 validation

Stage B5.3 adds `tests/test_source_discovery_stage_b5_closeout.py`.
The test builds the B5.2 policy audit and compare snapshot using placeholder source files, verifies no DB file is created, and patches ETL extraction, canonical materialization, and historical backfill paths to fail if invoked.
This is the selected smoke approach; AppTest route rendering was not added to avoid expanding scope beyond stable pure helpers.

## Final default policy

Final policy:

- `auto`: default.
- `legacy`: explicit rollback/legacy path.
- `manifest`: explicit manifest path.
- `compare`: explicit diagnostic path.

The default `auto` policy is narrow and applies manifest-backed discovery only to accepted extension historical months.

## Extension-month behavior

Accepted extension months July 2025 through February 2026 default to manifest-backed discovery and report `source_discovery_mode: auto_manifest`.
Compare diagnostics continue to report legacy/manifest matches for those accepted extension months.

## Jan-Jun legacy behavior

January 2025 through June 2025 remain legacy by default.
These months were not migrated to the manifest `month_source_files` map in Stage B5 and should not be described as manifest-backed.

## March 2026 blocked behavior

March 2026 remains blocked and out of canonical scope.
Default auto resolution blocks it, explicit manifest mode blocks it through `canonical_scope_status: blocked_out_of_scope`, and compare diagnostics treat it as expected blocked.

## Manual upload behavior

Manual upload/runtime ETL behavior remains unchanged.
No manifest operational selector, upload-mode switch, write-capable control, ETL trigger, or materialization action was added.

## DQ rules boundary

`config/data_quality_rules.v1.json` remains metadata-only.
Stage B5 does not wire it into `core/silver_normalizer.py`, `core/canonical_materializer.py`, Gold fact building, model training, or routed runtime behavior.

## Runtime behavior impact

The only runtime policy change in Stage B5 is the historical source resolver default for accepted extension months.
No ETL execution, canonical materialization, database write, model retraining, model artifact promotion, or app route change is part of this closeout.

## Tests and diagnostics run

Stage B5.3 validation used Python 3.11 with `PYTHONPYCACHEPREFIX` outside the working tree.

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface tests.test_source_discovery_default_switch`
- `python3.11 -m unittest tests.test_source_discovery_post_switch_audit`
- `python3.11 -m unittest tests.test_source_discovery_stage_b5_closeout`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

## Unsafe file scan

The intended staged set is limited to tests and documentation.
Required scans must show no database files, local environment folders, raw Excel files, generated `etl_outputs`, model artifacts, or unintended report-stage clutter staged.
`manufacturing_data.db` remains local-only and ignored by the `*.db` rule.

## What has been proven

- Accepted extension historical months default to manifest-backed source discovery.
- Jan-Jun historical months remain legacy by default.
- March 2026 remains blocked.
- Manual upload behavior is unchanged.
- The policy audit and compare snapshot can be built read-only without DB creation.
- The closeout smoke does not invoke ETL extraction, historical backfill, or canonical materialization.
- Legacy and compare modes remain available for rollback and diagnostics.

## What has not been proven

- ETL output equivalence has not been proven.
- Canonical materialization equivalence has not been proven.
- Runtime performance under actual historical backfill execution has not been proven.
- Jan-Jun manifest-backed discovery has not been implemented.
- Data-quality rule runtime enforcement has not been implemented.

## Rollback path

Rollback remains simple:

- Change `resolve_historical_month_sources()` default back to `legacy`, or revert the small `auto` extension-month dispatch.
- Continue using explicit `legacy` mode as the immediate fallback.
- Keep compare diagnostics available before and after any rollback.

No DB rollback is expected because source discovery itself does not write the database.

## Remaining risks

The switch is validated at source-discovery payload level only.
Any future task that runs ETL or materialization must treat output equivalence, performance, and DB safety as separate evidence requirements.
Jan-Jun remaining legacy is intentional but can be misread unless documentation keeps the boundary explicit.

## Recommended Stage B6

Stage B6 should move beyond source-discovery policy only if explicitly scoped.
Recommended options are a read-only ETL-output equivalence design pack, a temp-only historical backfill rehearsal plan, or a Jan-Jun manifest mapping feasibility audit.
Any Stage B6 execution path must keep DB safety, rollback, and no-raw-file-staging rules explicit.
