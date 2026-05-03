# Task 4E Implementation Report

## Preflight Repo Check
- Confirmed live locations before editing:
  - `CURRENT_REBUILD_STATUS.md`
  - `docs/technical/`
  - `core/ml_trainer.py`
  - `core/ml_predictor.py`
  - `core/canonical_ml_reader.py`
  - `core/gold_fact_builder.py`
  - `core/canonical_materializer.py`
  - `modules/ml_module.py`
  - `tests/test_canonical_ml_reader.py`
  - `tests/test_gold_fact_builder.py`
  - `models/`
- Confirmed there was no live `tests/test_ml_trainer.py` before this task.
- Confirmed the remaining Task 4E seam before editing:
  - inference path was already canonical from Task 4D
  - retraining still read legacy `unified_view`
  - retraining still filtered through `three_way_matches`
  - model metadata still wrote to hardcoded `manufacturing_data.db`

## What Changed
- Rewrote [core/ml_trainer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py) so the ML training / retraining pipeline now reads canonical Gold `fact_machine_hour` only.
- Added [tests/test_ml_trainer.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_trainer.py) for canonical load behavior, adapter rules, feature-contract compatibility, honest failure on too little data, temp-artifact training, and no-legacy-source assertions.
- Updated [modules/ml_module.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) so the ML page training tab no longer claims the trainer is still legacy-backed.
- Updated [CURRENT_REBUILD_STATUS.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md) so the live execution ledger reflects Task 4E.
- Updated [docs/technical/REBUILD_DOCS_INDEX.md](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/REBUILD_DOCS_INDEX.md) so Task 4E is indexed with the other rebuild reports.

## Exact Canonical Training Read Rule Used
- Trainer reads from `fact_machine_hour` only.
- Trainer does not:
  - query `unified_view`
  - require `three_way_matches`
  - recreate compatibility tables
  - silently switch back to legacy data when canonical Gold is unavailable
- If `fact_machine_hour` is missing or the required columns are absent, training fails explicitly and honestly.

## Exact Canonical Training Contract Used
- Required canonical fields:
  - `canonical_machine_id`
  - `hour_ts`
  - `energy_total_kwh`
  - `good_qty`
  - `team_leader`
  - `material_code`
  - `task_name`
  - `hours_since_last_maintenance`
  - `source_flags`
- Used when present:
  - `team_size`
  - `manpower`
  - `days_since_last_maintenance`
  - `last_maintenance_work_order_type`
  - `machine_state`
- Derived canonical training fields:
  - `machine_id = canonical_machine_id`
  - `datetime = hour_ts`
  - `energy_kwh = energy_total_kwh`
  - `production_qty = good_qty`
  - `kwh_per_unit = energy_total_kwh / good_qty` when `good_qty > 0`
  - `hour_of_day`, `day_of_week`, `month`, `is_weekend`, `is_night_shift` from `hour_ts`
  - `task_difficulty` using the same mapping family as Task 4D

## Exact Adapter Rules Used
- `team_size` uses canonical `team_size`, then rounded `manpower`, then the saved preprocessor default.
- `last_maintenance_type` uses canonical `last_maintenance_work_order_type`, then `source_flags.maintenance_last_work_order_type`, then `unknown`.
- `maintenance_intensity_30d` uses `source_flags.maintenance_distinct_work_order_count_30d`, else `0.0`.
- `cumulative_maintenance_count` uses the saved preprocessor default when available; otherwise it remains an explicit `0.0` adapter default rather than fabricated history.
- `days_since_last_maintenance` uses canonical `days_since_last_maintenance` when present; otherwise it is derived from canonical hours.
- `team_leader` and `material_code` fall back to `unknown` with adapter notes when missing.

## Exact Filtering / Honesty Rules Used
- Hard-block rows with:
  - missing machine ID
  - missing timestamp
  - missing or non-positive `good_qty`
  - missing `hours_since_last_maintenance`
  - missing or non-positive `energy_total_kwh`
- Conservative training filters then keep only rows where:
  - `production_qty >= 1.0`
  - `kwh_per_unit <= 20.0`
  - `energy_kwh >= 0.25`
- If too few rows remain after filtering, training fails explicitly.
- If too few machines remain after filtering, training fails explicitly.

## Exact Predictor / Feature Contract Preservation
- Task 4E preserves the predictor bundle contract used by [core/ml_predictor.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py).
- Training still emits the same ordered feature bundle:
  - `hour_of_day`
  - `day_of_week`
  - `month`
  - `is_weekend`
  - `is_night_shift`
  - `machine_type_encoded`
  - `machine_number`
  - `team_size`
  - `task_complexity`
  - `hours_since_last_maintenance`
  - `maintenance_urgency`
  - `needs_maintenance`
  - `maintenance_intensity_30d`
  - `cumulative_maintenance_count`
  - `production_qty`
  - `last_maintenance_type_encoded`
  - `team_leader_encoded`
  - `material_code_encoded`
- No predictor rewrite was required.

## Exact Path / Persistence Fixes
- Trainer now accepts explicit:
  - `db_path`
  - `model_path`
  - `preprocessor_path`
- Default paths now use active runtime helpers instead of hardcoded literals.
- Model metadata is now written to the active DB path only.
- Saved artifact paths can be redirected to temp paths for controlled validation.

## What Stayed Deliberately Out Of Scope
- broad ML redesign
- new model-family search project
- synthetic/demo/fallback revival
- broad rewrite of [core/ml_predictor.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
- rewrite of `modules/shared_ml_components.py`
- Gold schema redesign
- maintenance page rewrite
- optimization advanced-tab rewrite
- historical backfill automation
- inline Streamlit training execution

## Validation Performed
- Compile checks:
  - `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile core/ml_trainer.py modules/ml_module.py tests/test_ml_trainer.py`
- Focused Task 4E tests:
  - `python3 -m unittest tests/test_ml_trainer.py`
  - Result: `Ran 5 tests ... OK`
- Cross-task canonical regression:
  - `python3 -m unittest tests/test_ml_trainer.py tests/test_canonical_ml_reader.py tests/test_canonical_gold_reader.py tests/test_canonical_optimization_reader.py`
  - Result: `Ran 22 tests ... OK`
- Broader regression:
  - `python3 -m unittest tests/test_bronze_raw_store.py tests/test_silver_normalizer.py tests/test_gold_fact_builder.py tests/test_canonical_gold_reader.py tests/test_canonical_materializer.py tests/test_canonical_optimization_reader.py tests/test_canonical_ml_reader.py tests/test_ml_trainer.py`
  - Result: `Ran 105 tests ... OK`
- No-legacy-source verification:
  - `rg -n "unified_view|three_way_matches" core/ml_trainer.py -S`
  - Result: no matches

## Live Smoke Validation
- Shared DB note:
  - the current repo `manufacturing_data.db` still does not provide a reliable canonical training-month slice for honest retraining validation
  - validation therefore used a temp canonical DB seeded directly with realistic `fact_machine_hour` rows
- Smoke steps:
  - created a temp DB and initialized canonical Gold schema
  - seeded `12` realistic `fact_machine_hour` rows across `2` machines
  - ran `train_production_model(db_path=temp_db, model_path=temp_model, preprocessor_path=temp_preprocessor)`
  - instantiated [core/ml_predictor.py](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) against those temp artifacts
  - ran one canonical prediction using the newly trained bundle
- Smoke results:
  - `canonical_fact_rows_seeded 12`
  - `rows_after_filtering 12`
  - `distinct_machines_after_filtering 2`
  - `feature_columns` matched the preserved predictor contract exactly
  - `best_model_name linear_regression`
  - `model_metadata_count 1`
  - `predictor_loaded_model True`
  - `predictor_loaded_preprocessor True`
  - `prediction_source model`
  - `prediction_efficiency 2.2188`
  - `prediction_confidence 0.9023`

## Remaining Limitations
- Task 4E retargets the retraining pipeline, not the inline Streamlit training UX.
- Canonical retraining still uses a documented adapter layer for features that are not yet first-class Gold columns.
- Existing saved production artifacts under `models/` were not force-replaced by this task.
- The current training smoke used a controlled temp canonical DB, not the shared repo DB.
- `maintenance_minutes` remains intentionally null in Gold.

## Pass Status
Task 4E should be considered passed.

The ML training / retraining pipeline now reads canonical Gold `fact_machine_hour` only, no longer depends on legacy `unified_view` or `three_way_matches`, preserves the predictor bundle contract used by the live canonical inference path, and writes model metadata to the active DB path instead of a hardcoded database.
