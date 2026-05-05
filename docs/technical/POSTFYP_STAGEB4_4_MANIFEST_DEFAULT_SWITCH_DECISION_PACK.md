# Post-FYP Stage B4.4 Manifest Default-Switch Decision Pack

## Purpose

Stage B4.4 records the decision criteria for a possible future switch from legacy source discovery to manifest-backed source discovery.
This is a governance and decision pack only.
It does not switch the default source-discovery mode.

## Scope

This stage reviews the Stage B1 through Stage B4.3 evidence, runs the current compare diagnostic in text and JSON modes, defines approval and abort criteria for a future Stage B5, and records a rollback plan.
It changes documentation only.

No ETL, canonical materialization, runtime database write, model retraining, model artifact promotion, Streamlit write-control change, or data-quality rule runtime enforcement is included.

## Evidence basis

Evidence was reviewed from:

- `docs/technical/POSTFYP_STAGEB1_DATA_CONTRACT_FOUNDATION_REPORT.md`
- `docs/technical/POSTFYP_STAGEB2_SOURCE_DISCOVERY_EQUIVALENCE_REPORT.md`
- `docs/technical/POSTFYP_STAGEB3_SOURCE_DISCOVERY_OPTIONAL_INTEGRATION_REPORT.md`
- `docs/technical/POSTFYP_STAGEB4_1_SOURCE_DISCOVERY_MODE_GOVERNANCE_AUDIT_REPORT.md`
- `docs/technical/POSTFYP_STAGEB4_2_SOURCE_DISCOVERY_COMPARE_DIAGNOSTIC_REPORT.md`
- `docs/technical/POSTFYP_STAGEB4_3_ETL_SOURCE_DISCOVERY_DIAGNOSTIC_SURFACE_REPORT.md`
- `docs/technical/DATA_CONTRACTS_GUIDE.md`
- `config/source_manifest.v1.json`
- `config/data_quality_rules.v1.json`
- `core/data_contracts.py`
- `core/source_manifest_discovery.py`
- `scripts/compare_source_discovery_modes.py`
- `modules/etl_module.py`
- `tests/test_source_discovery_integration.py`
- `tests/test_source_discovery_compare_diagnostic.py`
- `tests/test_etl_source_discovery_diagnostic_surface.py`
- `tests/test_task13_source_discovery.py`

The current compare diagnostic was run in both text and JSON modes.
Both runs reported `success: true`, `month_count: 9`, `accepted_month_count: 8`, and `expected_blocked_month_count: 1`.

## Summary of B1-B4.3 evidence

Stage B1 created the source manifest and data-quality rule metadata foundation.
It documented accepted canonical months `2025-01` through `2026-02`, kept `2026-03` excluded by default, rejected absolute paths through contract validation, and left active ETL behavior unchanged.

Stage B2 added manifest-backed source-discovery helpers and `month_source_files` for July 2025 through February 2026 plus blocked March 2026.
The read-only manifest comparison reported no differences against the legacy extension mapping.

Stage B3 integrated source discovery into `ETLPipelineModule.resolve_historical_month_sources()` as optional `legacy`, `manifest`, and `compare` modes.
The default remained `legacy`.

Stage B4.1 audited source-discovery callers and found no active non-test caller selecting manifest or compare mode by default.
The upload workflow uses uploaded files directly and does not use the historical source resolver.

Stage B4.2 added `scripts/compare_source_discovery_modes.py`, a read-only diagnostic that calls compare mode without running ETL or initializing schema.
It treats March 2026 as expected blocked.

Stage B4.3 surfaced the B4.2 diagnostic on the ETL page as a collapsed read-only reference expander and added a pure snapshot helper.
It did not add an operational manifest-mode option.

## What has been proven

- The source manifest validates as structured metadata and does not require absolute local paths.
- Manifest-backed source discovery can reproduce legacy extension-month source-path payloads for July 2025 through February 2026.
- March 2026 remains blocked in both legacy and manifest discovery paths.
- The optional ETL resolver supports explicit `legacy`, `manifest`, and `compare` modes.
- Existing callers that omit `discovery_mode` still use legacy behavior.
- The compare diagnostic and ETL diagnostic snapshot are read-only and do not create DB files in focused tests.
- The diagnostic surface makes comparison evidence visible without adding write-capable Streamlit controls.

## What has not been proven

- ETL output equivalence has not been proven.
- Canonical materialization equivalence has not been proven.
- Runtime performance under a manifest default has not been proven.
- Initial January 2025 through June 2025 source discovery has not been migrated to the `month_source_files` map.
- Data-quality rule metadata has not been enforced in Silver or Gold runtime code.
- A manifest default has not been exercised as the active production/default path.

## Default-switch decision

Recommendation: **D. Switch only for extension-month historical resolver, not upload/runtime manual path.**

A future Stage B5 may proceed with a narrow controlled default switch only for the historical extension-month resolver boundary, and only if all approval criteria below pass.
The ETL upload/manual workflow should remain unchanged because it uses uploaded files directly and is outside the evidence proven by B1 through B4.4.

This decision does not approve a broad ETL behavior change.
It approves preparation for a narrow Stage B5 implementation candidate with explicit rollback and smoke evidence.

## Approval criteria for Stage B5

- July 2025 through February 2026 accepted months must match legacy source payloads in compare diagnostics.
- March 2026 must remain blocked and out of accepted canonical scope.
- `tests.test_data_contracts` must pass.
- `tests.test_source_manifest_discovery` and `tests.test_task13_source_discovery` must pass.
- `tests.test_source_discovery_integration` and `tests.test_source_discovery_compare_diagnostic` must pass.
- `tests.test_etl_source_discovery_diagnostic_surface` must pass.
- Runtime path and Silver normalizer regression tests must pass.
- `python3.11 -m compileall core modules scripts tests` must pass.
- Text and JSON compare diagnostics must pass.
- Source-discovery-only tests must not create any DB file.
- No raw Excel files, generated `etl_outputs`, model artifacts, local env folders, or DB files may be staged.
- Rollback must be one-line/simple: restore the resolver default to `legacy`.
- No `data_quality_rules.v1.json` runtime enforcement may be bundled into the switch.
- Upload/manual ETL workflow behavior must remain unchanged unless a separate task explicitly scopes it.

## Abort criteria for Stage B5

- Any accepted month source-payload mismatch.
- March 2026 becomes accepted or resolvable as a canonical month.
- A DB file is created, copied, staged, or pushed.
- ETL or canonical materialization runs during source-discovery-only validation.
- Any required regression test fails.
- Streamlit route behavior changes without explicit approval.
- Manifest source paths require absolute local paths.
- A hidden default switch occurs outside the resolver boundary.
- Raw Excel files, generated `etl_outputs`, model artifacts, local env folders, or DB files appear in the staged set.
- Data-quality rule enforcement is bundled into the source-discovery default switch.

## Rollback plan

Keep `discovery_mode` default as `legacy` until Stage B5.
If Stage B5 changes the historical resolver default, rollback must restore the default value to `legacy` and leave explicit `manifest` / `compare` modes available for diagnostics.

The compare diagnostic remains the preflight before and after any Stage B5 change.
No DB rollback should be needed for a discovery-only default switch because source discovery itself must not write the database.
If a future Stage B5 accidentally runs ETL or canonical materialization, abort the task and do not promote or reuse any generated output.

## Runtime smoke requirements for Stage B5

Stage B5 should include a focused read-only runtime smoke before commit:

- import the ETL module without initializing schema unexpectedly;
- render or snapshot the ETL diagnostic surface without exception;
- confirm the upload/manual path still does not expose manifest as an operational option;
- run the compare diagnostic immediately before and after the default-switch patch;
- verify no DB files appear after source-discovery-only validation;
- confirm `run_historical_canonical_backfill()` is not executed by the smoke.

If an AppTest route smoke is added, it must stay read-only and must not press upload, process, backfill, or materialization controls.

## March 2026 boundary

March 2026 is blocked in the manifest through `canonical_scope_status: blocked_out_of_scope` and in legacy discovery through blocked family status.
The compare diagnostic passes March 2026 only when both paths report blocked status.

Stage B5 must preserve that behavior.
Any change that accepts March 2026 by default is an abort condition.

## Data-quality rules boundary

`config/data_quality_rules.v1.json` remains metadata-only.
Stage B5 must not wire it into `core/silver_normalizer.py`, `core/canonical_materializer.py`, Gold fact building, model training, or routed runtime behavior.

The source-discovery default switch and data-quality rule enforcement are separate governance tracks.

## Risks

- Current evidence proves path-payload equivalence, not ETL output equivalence.
- Error message or metadata-shape differences could affect callers if Stage B5 is not narrowly scoped.
- January 2025 through June 2025 source discovery remains outside the manifest `month_source_files` default-switch proof.
- A future implementation could accidentally widen scope into upload/manual ETL behavior if not constrained.
- Data-quality rule metadata could be misread as active runtime enforcement unless the boundary remains explicit.

## Recommended Stage B5

Proceed to Stage B5 only as a narrow controlled default-switch candidate for extension-month historical source discovery.
Stage B5 should change as little code as possible, keep legacy rollback immediate, run the compare diagnostic before and after the patch, and avoid any ETL/materialization execution.

Do not switch upload/manual ETL behavior in Stage B5.

## Out of scope

- Switching the default in Stage B4.4.
- Running ETL.
- Running canonical materialization.
- Writing `manufacturing_data.db`.
- Modifying `app.py`.
- Adding write-capable Streamlit controls.
- Exposing manifest mode as an operational upload/manual ETL option.
- Wiring data-quality rules into Silver or Gold runtime behavior.
- Retraining or promoting ML artifacts.
- Staging raw Excel files, generated ETL outputs, model artifacts, or DB files.

## Validation

Stage B4.4 validation used the repo Python 3.11 environment with `PYTHONPYCACHEPREFIX` outside the working tree.

Required validation commands:

- `python3.11 -m unittest tests.test_data_contracts`
- `python3.11 -m unittest tests.test_source_manifest_discovery tests.test_task13_source_discovery`
- `python3.11 -m unittest tests.test_source_discovery_integration tests.test_source_discovery_compare_diagnostic`
- `python3.11 -m unittest tests.test_etl_source_discovery_diagnostic_surface`
- `python3.11 -m unittest tests.test_runtime_paths tests.test_silver_normalizer`
- `python3.11 -m compileall core modules scripts tests`
- `python3.11 scripts/compare_source_discovery_modes.py`
- `python3.11 scripts/compare_source_discovery_modes.py --json`

The compare diagnostic text and JSON runs passed before this report was written.
The pre-commit unsafe-file scan must show no DB files, local env folders, raw Excel files, model artifacts, generated `etl_outputs`, or unintended report-stage files staged.
