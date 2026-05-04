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

## Data-Quality Rules Boundary

The data-quality rules file documents rule intent and identifiers only. Stage B2 still does not wire these rules into `core/silver_normalizer.py` or `core/canonical_materializer.py`; current runtime behavior remains unchanged.

Future hardening stages can use this file as the source of truth for anomaly exclusion, partial-meter flags, unresolved quarantine IDs, and quantity-overlay audit categories.

## Local DB Boundary

`manufacturing_data.db` remains local-only runtime state. It is not part of the GitHub-safe working tree and must not be staged, committed, or pushed.

## Claim Boundary

This is data-governance hardening. It is not a new ML capability, optimizer, scheduler, predictive-maintenance feature, or autonomous execution feature.
