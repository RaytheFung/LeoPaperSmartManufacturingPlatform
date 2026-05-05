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

## Data-Quality Rules Boundary

The data-quality rules file documents rule intent and identifiers only. Stage B4.3 still does not wire these rules into `core/silver_normalizer.py` or `core/canonical_materializer.py`; current runtime behavior remains unchanged.

Future hardening stages can use this file as the source of truth for anomaly exclusion, partial-meter flags, unresolved quarantine IDs, and quantity-overlay audit categories.

## Local DB Boundary

`manufacturing_data.db` remains local-only runtime state. It is not part of the GitHub-safe working tree and must not be staged, committed, or pushed.

## Claim Boundary

This is data-governance hardening. It is not a new ML capability, optimizer, scheduler, predictive-maintenance feature, or autonomous execution feature.
