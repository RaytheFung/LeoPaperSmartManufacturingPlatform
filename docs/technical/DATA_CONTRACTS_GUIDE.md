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

## Data-Quality Rules Boundary

The data-quality rules file documents rule intent and identifiers only. Stage B1 does not wire these rules into `core/silver_normalizer.py` or `core/canonical_materializer.py`; current runtime behavior remains unchanged.

Future hardening stages can use this file as the source of truth for anomaly exclusion, partial-meter flags, unresolved quarantine IDs, and quantity-overlay audit categories.

## Local DB Boundary

`manufacturing_data.db` remains local-only runtime state. It is not part of the GitHub-safe working tree and must not be staged, committed, or pushed.

## Claim Boundary

This is data-governance hardening. It is not a new ML capability, optimizer, scheduler, predictive-maintenance feature, or autonomous execution feature.
