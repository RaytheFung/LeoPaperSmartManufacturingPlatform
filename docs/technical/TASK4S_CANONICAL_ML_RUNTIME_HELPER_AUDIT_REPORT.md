# TASK4S Canonical ML Runtime Helper Audit Report

## Outcome

This separate canonical ML runtime helper audit passed.

Scope stayed ML-runtime-only:

- no live DB write was performed
- no active artifact path under `models/` was overwritten
- no model retraining or promotion ran
- no Task 4S quantity logic was reopened
- no energy / maintenance / optimization page code was changed

Decision:

- no meaningful routed ML legacy-helper debt remains
- no separate routed ML runtime retargeting task should be opened now
- if cleanup is desired later, keep it to dormant legacy ML helper cleanup only

## Direct-Source-Verified Evidence Used

- live execution ledger:
  - [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- task-report chain:
  - [`docs/technical/TASK4D_IMPLEMENTATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4D_IMPLEMENTATION_REPORT.md)
  - [`docs/technical/TASK4L_IMPLEMENTATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4L_IMPLEMENTATION_REPORT.md)
  - [`docs/technical/TASK4M_IMPLEMENTATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4M_IMPLEMENTATION_REPORT.md)
  - [`docs/technical/TASK4N_IMPLEMENTATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4N_IMPLEMENTATION_REPORT.md)
  - [`docs/technical/TASK4S_DOWNSTREAM_IMPACT_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_DOWNSTREAM_IMPACT_AUDIT_REPORT.md)
  - [`docs/technical/TASK4S_POST_QUANTITY_ML_ARTIFACT_REFRESH_AUDIT_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_POST_QUANTITY_ML_ARTIFACT_REFRESH_AUDIT_REPORT.md)
- active source code:
  - [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py)
  - [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
  - [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py)
  - [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py)
  - [`tests/test_canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_canonical_ml_reader.py)
  - [`tests/test_ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_predictor.py)
  - [`tests/test_ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/tests/test_ml_module.py)
- active runtime assets:
  - active DB: `manufacturing_data.db`
  - active model: `models/production_efficiency_model.pkl`
  - active preprocessor: `models/production_preprocessor.pkl`

## Current Routed ML Surfaces

### Currently routed ML page behavior

Direct-source-verified routed path:

- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `page == "🤖 Machine Learning"` -> `show_ml_module()`
- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) `render_ml_module()`

Current routed ML tabs inside that page:

- `🔮 Canonical Predictions`
- `📘 Canonical ML Contract`
- `🧪 Model Training`

The routed prediction tab is canonical-runtime-only. It uses [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) plus the saved [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) artifact bundle. It does not import or call [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py).

The routed training tab is separate from the prediction helper question. It goes through the formal canonical trainer status/execution path and is not a `unified_view` helper path.

### Helper-only behavior

Legacy helper-only ML behavior still present in code:

- [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) dropdown helpers:
  - `_fetch_distinct()`
  - `get_machine_list()`
  - `get_team_leaders()`
  - `get_material_codes()`
- [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) comparison / recommendation helpers:
  - `_get_baseline_efficiency()`
  - `calculate_real_time_savings()`
  - `get_optimization_recommendations()`
- [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py) legacy month helper:
  - `get_available_months_from_data()`

These helpers still depend on persisted `unified_view`, but the current routed ML page does not call them.

### Dormant / unused helper code

Direct-source-verified dormant ML helper surfaces:

- [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py)
  - `render_live_predictions_tab()`
  - `render_feature_insights_tab()`
  - `render_recommendations_tab()`
- repo-wide search found no live imports/callers for those functions in routed app code
- [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `quick_predict()` is only used in the module `__main__` smoke stub
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `show_overview_page()` and `show_team_performance_page()` still exist, but they are not current sidebar routes and are outside the routed ML page path

## Direct ML Runtime Consumer Map

| Consumer | File / function | Source used now | Routed status | Canonical or legacy |
| --- | --- | --- | --- | --- |
| Month selector | [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) `render_ml_module()` -> [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) `get_available_months()` | `SELECT DISTINCT substr(hour_ts, 1, 7)` from `fact_machine_hour` | routed | canonical |
| Month input rows | [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) `_read_month_fact_dataframe()` / `build_month_input_dataframe()` | selected-month `fact_machine_hour` rows | routed | canonical |
| Machine-level candidate selection | [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) `build_prediction_candidates()` | in-memory canonical month input rows | routed | canonical |
| Prediction execution | [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) `build_prediction_dataframe()` -> [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `predict_efficiency()` | active saved model + preprocessor artifacts | routed | canonical artifact path |
| Model / bundle status | [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) `get_predictor_status()` | artifact load flags only | routed | canonical artifact path |
| Prediction chart/table | [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) `_render_prediction_results()` | in-memory `prediction_df`, `blocked_df`, `input_df` | routed | canonical |
| Training status tab | [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) `_render_training_controls()` | formal canonical trainer status path | routed | canonical trainer path |
| Machine dropdown helper | [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `_fetch_distinct()` / `get_machine_list()` | `unified_view.machine_id` | helper-only | legacy |
| Team dropdown helper | [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `get_team_leaders()` | `unified_view.team_leader` | helper-only | legacy |
| Material dropdown helper | [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `get_material_codes()` | `unified_view.material_code` | helper-only | legacy |
| Baseline efficiency helper | [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `_get_baseline_efficiency()` / `calculate_real_time_savings()` | `AVG(unified_view.kwh_per_unit)` | helper-only | legacy |
| Recommendation helper | [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `get_optimization_recommendations()` | `unified_view` 30-day machine history | helper-only | legacy |
| Legacy month helper | [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py) `get_available_months_from_data()` | `unified_view.datetime` | unused | legacy |
| Shared ML tabs | [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py) `render_live_predictions_tab()`, `render_feature_insights_tab()`, `render_recommendations_tab()` | `unified_view` plus legacy predictor helpers | dormant | legacy |

## Read-Only Runtime Smoke

Read-only smoke method:

- used the active DB path `manufacturing_data.db`
- used the active artifact bundle under `models/`
- patched SQLite connections open in read-only mode
- denied `unified_view` and `three_way_matches` reads explicitly through a SQLite authorizer
- loaded the current routed ML path as narrowly as possible through:
  - [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) `get_available_months()`
  - `build_month_input_dataframe()`
  - `build_prediction_candidates()`
  - `build_prediction_dataframe()`
  - plus [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `predict_efficiency()`

Direct-source-verified routed smoke results:

- selected month: `June 2025`
- available routed months: `January 2025` through `June 2025`
- active model artifact loaded: yes
- active preprocessor loaded: yes
- canonical inference enabled: yes
- canonical rows loaded for routed ML: `62,639`
- distinct machines in routed month input: `87`
- rows eligible for inference: `33,798`
- latest machine-level candidate rows: `76`
- machine-level predictions returned: `76`
- predictor-blocked rows after artifact gate: `0`
- input blocked reasons:
  - `missing_positive_good_qty`: `26,524`
  - `missing_hours_since_last_maintenance`: `2,317`
- SQL authorizer read log on the routed path:
  - `sqlite_master`
  - `fact_machine_hour`
- no `unified_view` read was attempted on the routed path

Conclusion from the routed smoke:

- canonical inference works on the active DB with legacy `unified_view` access denied
- no currently routed ML helper on that path still depends on `unified_view`

## Legacy Helper Probe

Separate helper-only probe under the same read-only deny rule:

- `get_machine_list()` returned only the built-in fallback list length `3`
- `get_team_leaders()` returned only the built-in fallback list length `3`
- `get_material_codes()` returned only the built-in fallback list length `3`
- `_get_baseline_efficiency()` returned the hardcoded fallback `0.12`
- `get_optimization_recommendations("024-001")` failed with a denied read against `unified_view`
- helper SQL read log showed `unified_view` access attempts

Interpretation:

- legacy predictor helper lookups still depend on `unified_view`
- that dependence is real
- it is not currently routed ML runtime debt because the current routed ML page does not call those helpers

## Exact Statement Of Current Routed ML Legacy Dependence

Direct-source-verified statement:

- no currently routed ML page helper on the active prediction path depends on legacy `unified_view` or `three_way_matches`
- the routed ML page path is `app.py` -> `modules/ml_module.py` -> `core/canonical_ml_reader.py` -> `fact_machine_hour`, with [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) used only for artifact-backed feature preparation and prediction

Direct-source-verified residual legacy code statement:

- legacy `unified_view`-backed ML dropdown, baseline, recommendation, and shared-tab helpers still exist in code
- those helpers are dormant / helper-only now, not active routed runtime consumers

## Recommendation

Recommended decision:

- no separate routed ML runtime retargeting task

Reason:

- the live routed ML page already runs canonically on the active DB and active artifacts
- the remaining `unified_view` helper dependence is isolated to dormant or helper-only code
- widening into helper cleanup now would not improve the current routed ML runtime path

If later cleanup is desired:

- open a separate dormant legacy ML cleanup task only
- do not widen it into retraining, artifact promotion, active-path rewrites, or Task 4S quantity work

## Validation

Commands run:

```bash
./.conda311/bin/python -m unittest tests.test_ml_predictor tests.test_canonical_ml_reader tests.test_ml_module
```

Read-only smoke also run:

- active DB + active artifact routed-path smoke with SQLite read-only mode and explicit denial of legacy `unified_view` / `three_way_matches`

## Remaining Limitations

- This audit did not remove dormant legacy ML helper code; it only verified routed-vs-dormant status.
- This audit did not run a full Streamlit browser smoke; it exercised the routed ML data/prediction path directly at function level, which is the narrowest honest runtime check for this question.
- This audit did not rerun model training or training-tab execution, because the question was routed runtime helper dependence, not artifact reevaluation.
