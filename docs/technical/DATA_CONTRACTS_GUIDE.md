# Data Contracts Guide

## Purpose

Stage B1 introduces a versioned source and data-quality contract foundation for the canonical ETL backbone.
It does not change active ETL, Silver normalization, Gold materialization, routed Streamlit pages, model artifacts, or optimization logic.

## Files

- `config/source_manifest.v1.json` records accepted source scopes, canonical month coverage, source-family status, and relative source-folder expectations.
- `config/data_quality_rules.v1.json` records known data-quality rule categories for sentinel anomalies, partial-energy flags, unresolved quarantines, quantity-overlay anomaly types, allowed energy scope statuses, and the accepted canonical month range.
- `core/data_contracts.py` provides lightweight JSON loaders and shape validators. It has no Streamlit, pandas, SQLite, ETL, or model dependency.

## Source Manifest Boundary

The manifest currently documents:

- `source_data/2025_jan_jun_initial/` for accepted `2025-01` through `2025-06` source scope.
- `source_data/2025_jul_2026_feb_collected/` for accepted `2025-07` through `2026-02` source scope.
- `2026-03` energy rows as supplementary/out-of-scope unless a later task explicitly reopens that boundary.

Paths in the manifest are relative to the repository root. The manifest must not require absolute local paths.

## Stage B2 Source Discovery Equivalence

Stage B2 adds a lightweight `month_source_files` map for the accepted extended source months and a read-only helper layer in `core/source_manifest_discovery.py`.
These helpers can resolve manifest-backed source paths under an explicitly supplied data root, build an availability matrix, and compare the manifest map with the legacy `modules.etl_module` extension mapping.

This is an equivalence layer only. Active ETL, canonical materialization, Streamlit runtime defaults, Silver normalization, Gold fact building, ML training, and model artifacts remain unchanged.
`2026-03` remains blocked and out of canonical scope even though grouped source workbooks can contain March rows.

## Stage B3 Optional ETL Resolver Integration

Stage B3 integrates manifest-backed source discovery into `ETLPipelineModule.resolve_historical_month_sources()` as an optional `discovery_mode`.
The default remains `legacy`, so existing callers and Streamlit runtime behavior continue to use the current hard-coded source discovery path.
The optional `manifest` mode resolves through `core.source_manifest_discovery.resolve_manifest_month_sources()`, while `compare` mode runs both paths and returns the legacy operational payload with an explicit equivalence diagnostic.

This is a guarded integration step only. It does not switch ETL defaults, run ETL, run canonical materialization, or write the runtime database.
Data-quality rules remain metadata-only and are still not wired into Silver or Gold runtime behavior.

## Stage B4.2 Compare Diagnostic

Stage B4.2 adds `scripts/compare_source_discovery_modes.py`, a read-only diagnostic script/helper for comparing legacy and manifest-backed discovery across July 2025 through March 2026.
It calls the optional compare mode only, does not run ETL, does not run canonical materialization, and does not write output files or the runtime database.
March 2026 is treated as an expected blocked/out-of-scope month rather than a failure.

The diagnostic is evidence for a future default-switch decision, not the switch itself.
Default runtime source discovery remains legacy, and manifest mode is still not exposed in the Streamlit UI.

## Stage B4.3 ETL Diagnostic Surface

Stage B4.3 adds a collapsed Streamlit ETL-page reference expander named `Reference & Audit: Source Discovery Contract Check`.
The expander displays the B4.2 compare diagnostic as a read-only audit table for July 2025 through March 2026.
It uses a pure snapshot helper, `modules.etl_module.build_source_discovery_diagnostic_snapshot()`, which reuses `scripts.compare_source_discovery_modes.build_source_discovery_compare_diagnostics()` and does not call Streamlit runtime APIs.

This is a diagnostic surface only.
It does not add a manifest operational ETL option, does not change the default `discovery_mode`, does not run ETL, does not run canonical materialization, and does not write `manufacturing_data.db`.
March 2026 remains expected blocked/out-of-scope in the displayed diagnostic.

## Stage B5.1 Extension-Month Manifest Default

Stage B5.1 changes `ETLPipelineModule.resolve_historical_month_sources()` default source-discovery policy from `legacy` to `auto`.
In `auto` mode, accepted extension months July 2025 through February 2026 resolve through manifest-backed discovery by default, while the initial January 2025 through June 2025 historical path remains legacy.
Explicit `legacy`, `manifest`, and `compare` modes remain available for rollback, diagnostics, and tests.

This is a narrow historical-source resolver default only.
Manual upload/runtime ETL behavior is unchanged, no Streamlit operational manifest selector is added, March 2026 remains blocked, and data-quality rules remain metadata-only.

## Stage B5.2 Post-Switch Audit

Stage B5.2 adds `modules.etl_module.build_source_discovery_default_policy_audit()`, a read-only helper that summarizes the active post-switch policy.
It reports `default_policy: auto`, accepted extension months using manifest-backed discovery by default, Jan-Jun historical months remaining legacy, manual upload behavior remaining unchanged, and March 2026 remaining blocked.

The ETL diagnostic expander now states the active default policy directly and displays a low-prominence policy audit table alongside the legacy-vs-manifest comparison evidence.
This audit is source-discovery evidence only; it still does not run ETL, run canonical materialization, write the database, or prove ETL output/materialization equivalence.

## Stage B5.3 Source Discovery Switch Closeout

Stage B5.3 closes the Stage B5 source-discovery default switch for accepted extension historical source resolution only.
The final policy is still `auto`: July 2025 through February 2026 extension months default to manifest-backed discovery, January 2025 through June 2025 remain legacy, March 2026 remains blocked, and manual upload behavior remains unchanged.

The closeout evidence is read-only and source-discovery-only.
It does not prove ETL output equivalence or canonical materialization equivalence, and data-quality rules remain metadata-only.

## Stage B6.2 July Temp-Backfill Preflight

Stage B6.2 adds a read-only helper, `core.backfill_rehearsal_preflight.build_historical_backfill_preflight_plan()`, for planning a future July 2025 temp-only historical backfill rehearsal.
The helper uses source discovery and compare diagnostics only; it does not run ETL, run canonical materialization, connect to a DB, copy a DB, or write files.
It prepares the evidence contract for a later temp-only rehearsal while preserving the Stage B5 boundary that source-discovery switching proves source-path behavior only.

## Stage B6.3 July Temp-Only Rehearsal

Stage B6.3 runs the first July 2025 historical backfill rehearsal against a temp DB outside Git only.
The rehearsal does not promote data, write the original runtime DB, change source-discovery policy, or alter Streamlit/manual ETL behavior.
Its evidence proves temp-only execution safety and successful July completion, while leaving clean-baseline Bronze/Silver equivalence for a later isolated follow-up.

## Stage B6.4 July Baseline Isolation

Stage B6.4 reruns July 2025 once against a temp DB after pruning only clearly July-scoped copied partitions.
It keeps the original runtime DB and GitHub-safe tree DB-free, and it records duplicate `source_row_hash` evidence without promoting any temp DB or changing active Streamlit/manual ETL behavior.

## Stage B7.2 CSI Canonical Month Assignment

Stage B7.2 accepts the current first-available timestamp CSI canonical month-assignment policy for Stage B7.
CSI extracted package rows and canonical CSI event rows may differ because canonical month assignment follows timestamp semantics.
July 2025's `235` extracted-versus-canonical row gap was audited as August spill, not data loss, duplicate/hash contamination, or a runtime predicate mismatch.

## Stage B7.3 August Spill Traceability

Stage B7.3 audits the July-package CSI spill rows that canonicalized to August for August raw and silver traceability.
All `235` spill identities are traceable under August canonical scope in the current temp DB, while a future August temp-only rehearsal remains separate output-equivalence evidence.

## Stage B8.3 Boundary-Month CSI Carry-Forward Policy

August-only ingestion does not capture July-package CSI rows that canonicalize to August.
Future carry-forward or adjacent-package reconciliation is required before claiming canonical monthly completeness for boundary-month CSI scope.
This remains a policy/design boundary only; no runtime carry-forward logic or canonical predicate change is active through Stage B8.3.

## Stage B11.1 Disabled-by-Default Carry-Forward Hook Design

Stage B10 proves two temp-only CSI boundary-month cases: July 2025 package to August 2025 canonical month, and November 2025 package to December 2025 canonical month.
B11 designs a disabled-by-default runtime hook boundary only.
No live/shared DB promotion, runtime carry-forward wiring, source-discovery default change, runtime canonical predicate change, Streamlit write control, or DQ runtime wiring is approved by B11.1.

## Stage B11.2 Carry-Forward Configuration Scaffolding

Stage B11.2 adds disabled-by-default carry-forward configuration scaffolding in `core/csi_carry_forward_config.py`.
The default mode is `disabled`; `preflight_only` and `temp_reconcile` are explicit non-default modes for future guarded work only.
The proven-boundary allowlist is limited to July 2025 -> August 2025 and November 2025 -> December 2025 for future temp-only testing guardrails.
No active ETL runtime, canonical materialization, live/shared DB behavior, source-discovery default, runtime canonical predicate, Streamlit control, or DQ runtime behavior is changed.

## Stage B11.3 Carry-Forward Runtime Adapter Preflight

Stage B11.3 adds a read-only runtime adapter in `core/csi_carry_forward_runtime_adapter.py`.
Disabled mode is a no-op; `preflight_only` is allowed for read-only planning on proven boundaries; `temp_reconcile` remains guarded and is not executable through active runtime.
No active ETL runtime, historical backfill, canonical materialization, live/shared DB behavior, source-discovery default, runtime canonical predicate, Streamlit control, or DQ runtime behavior is changed.

## Data-Quality Rules Boundary

The data-quality rules file documents rule intent and identifiers only. Through Stage B11.3, these rules are still not wired into `core/silver_normalizer.py` or `core/canonical_materializer.py`; current runtime behavior remains unchanged.

Future hardening stages can use this file as the source of truth for anomaly exclusion, partial-meter flags, unresolved quarantine IDs, and quantity-overlay audit categories.

## Local DB Boundary

`manufacturing_data.db` remains local-only runtime state. It is not part of the GitHub-safe working tree and must not be staged, committed, or pushed.

## Claim Boundary

This is data-governance hardening. It is not a new ML capability, optimizer, scheduler, predictive-maintenance feature, or autonomous execution feature.
