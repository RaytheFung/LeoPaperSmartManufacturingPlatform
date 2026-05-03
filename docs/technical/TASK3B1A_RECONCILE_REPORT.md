# Task 3B1a Reconcile Report

## Objective
Reconcile the live repository state with the previously reported Task 3B1a Bronze stability outcome, and confirm that the code evidence matches the report before Task 3B2 starts.

## Live Repo Check Result
The live working-tree versions of [core/bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/bronze_raw_store.py) and [tests/test_bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_bronze_raw_store.py) already contain the intended Task 3B1a fixes.

Exact statement:
The previous terminal reply was not ahead of the actual live code state at reconcile time. The intended Task 3B1a changes were already present in the current repo files, but the Bronze files were still untracked in git relative to the current commit history.

## Confirmed Code Evidence
- `source_row_hash` is built from raw-source truth only, plus `source_system` and normalized `source_file`.
- Derived mapping fields are excluded from the hash input, including `canonical_machine_id`, `matched_on`, `matched_value`, `exception_applied`, `scope_status`, and `join_status`.
- Bronze upsert remains idempotent through `ON CONFLICT(source_row_hash) DO UPDATE`.
- MES Bronze extraction prefers real raw MES columns first, with explicit fallback handling only for alternate field names when the raw columns are absent.
- `raw_payload_json` remains intact as the full original row payload.

## Regression Coverage Confirmed
- `test_source_row_hash_ignores_derived_mapping_metadata`
- `test_upsert_updates_existing_bronze_row_without_duplicate`
- `test_mes_row_prefers_real_raw_fields_over_fallback_fields`
- `test_mes_row_uses_explicit_fallbacks_when_raw_fields_absent`

## Tests Run
- `python3 -m unittest tests/test_bronze_raw_store.py`
  - Result: `Ran 6 tests ... OK`
- `python3 -m unittest tests/test_machine_alias_registry.py tests/test_etl_modules.py tests/test_bronze_raw_store.py`
  - Result: `Ran 23 tests ... OK`
- `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/bronze_raw_store.py tests/test_bronze_raw_store.py`
  - Result: passed

## Exported Live Repo Files
- [TASK3B1A_RECONCILE_core_bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK3B1A_RECONCILE_core_bronze_raw_store.py)
- [TASK3B1A_RECONCILE_tests_test_bronze_raw_store.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK3B1A_RECONCILE_tests_test_bronze_raw_store.py)
