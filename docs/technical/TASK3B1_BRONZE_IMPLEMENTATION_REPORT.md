# Task 3B1 Bronze Implementation Report

Date: 2026-03-23

## Objective

Introduce Bronze canonical raw tables while preserving the existing legacy ETL tables and current UI behavior.

This task added explicit Bronze raw persistence for:
- Energy rows
- CSI rows
- MES rows
- maintenance rows

The Bronze layer is dual-written during the transition. Legacy ETL tables remain intact.

## New Bronze Tables

- `raw_energy_hourly`
- `raw_csi_event`
- `raw_mes_report`
- `raw_maintenance_txn`

## Minimum Mapping Metadata Persisted Per Bronze Row

- `source_system`
- `source_file`
- `source_row_hash`
- `ingested_at`
- `raw_machine_id_or_label`
- `canonical_machine_id`
- `matched_on`
- `matched_value`
- `exception_applied`
- `scope_status`
- `join_status`

## Touched Files

### [core/bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/bronze_raw_store.py)
- Added one dedicated Bronze storage helper.
- Owns Bronze schema creation and idempotent dual-write logic.
- Uses deterministic row hashes and repo-relative source-file normalization.

### [core/etl/extractor.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/etl/extractor.py)
- Added `source_file` to loaded Energy / CSI / MES rows.
- Keeps raw-source identity available for Bronze persistence.

### [modules/etl_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/etl_module.py)
- Instantiates the Bronze raw store.
- Dual-writes Energy / CSI / MES rows into Bronze tables before legacy table writes.
- Legacy writes remain unchanged.

### [core/maintenance_integration.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/maintenance_integration.py)
- Uses repo-relative DB path by default.
- Adds `source_file` to loaded maintenance rows.
- Dual-writes raw maintenance rows into Bronze before downstream linked maintenance writes.

### [tests/test_bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_bronze_raw_store.py)
- Added Bronze schema creation and representative insert tests.

## Validation Summary

Validation performed:
- source compilation checks for all touched files;
- `python3 -m unittest tests/test_machine_alias_registry.py tests/test_etl_modules.py tests/test_bronze_raw_store.py`

Result:
- tests passed.

## Task 3B2 Build-On Note

Task 3B2 should build Silver normalizers on top of these Bronze raw tables instead of reading directly from the legacy ETL tables.

Recommended next step:
- implement source-specific Bronze-to-Silver transforms that read:
  - `raw_energy_hourly`
  - `raw_csi_event`
  - `raw_mes_report`
  - `raw_maintenance_txn`
- preserve the Bronze mapping metadata in Silver, then add canonical source contracts without removing the legacy pipeline yet.
