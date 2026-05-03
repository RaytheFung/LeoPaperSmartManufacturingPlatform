# TASK4S Downstream Impact Audit Report

## Outcome

This separate read-only downstream impact audit passed.

No live DB write was performed.
No live `good_qty` / `scrap_qty` semantics changed in this task.
No production code changed in this task.

## Direct-Source-Verified Evidence Used

- live execution ledger:
  - [`CURRENT_REBUILD_STATUS.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/CURRENT_REBUILD_STATUS.md)
- Task 4S report chain:
  - [`docs/technical/TASK4S_IMPLEMENTATION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_IMPLEMENTATION_REPORT.md)
  - [`docs/technical/TASK4S_PHASEB_METADATA_LANDING_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_PHASEB_METADATA_LANDING_REPORT.md)
  - [`docs/technical/TASK4S_POST_LANDING_DECISION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_POST_LANDING_DECISION_REPORT.md)
  - [`docs/technical/TASK4S_APPROVAL_REVIEW_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_APPROVAL_REVIEW_REPORT.md)
  - [`docs/technical/TASK4S_LIVE_REPLACEMENT_EXECUTION_REPORT.md`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/docs/technical/TASK4S_LIVE_REPLACEMENT_EXECUTION_REPORT.md)
- active source code:
  - [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py)
  - [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py)
  - [`modules/euvg_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/euvg_module.py)
  - [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py)
  - [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py)
  - [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)
  - [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py)
  - [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py)
  - [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py)
  - [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py)
  - [`core/canonical_materializer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_materializer.py)
  - [`core/gold_fact_builder.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/gold_fact_builder.py)
  - [`core/fact_machine_hour_repair.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/fact_machine_hour_repair.py)
  - [`core/csi_quantity_shadow.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/csi_quantity_shadow.py)
- read-only DB evidence:
  - active DB: `manufacturing_data.db`
  - pre-Task 4S full backup from the live execution report:
    - [`backups/manufacturing_data_task4s_live_qty_replace_20260402_172313.db`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/backups/manufacturing_data_task4s_live_qty_replace_20260402_172313.db)

## Direct-Consumer Map

| Surface | File / function | Source used now | Quantity-like field | Task 4S downstream impact |
|---|---|---|---|---|
| Canonical Unified View page | [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) `render_unified_view_page()` via [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py) | `fact_machine_hour` | `good_qty`, `scrap_qty`, derived `production_qty = good_qty`, `kwh_per_good_unit` | direct active now |
| Canonical ML page | [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) `render_ml_module()` via [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) | `fact_machine_hour` | `good_qty`, derived `production_qty = good_qty` | direct active now |
| Canonical ML training path | [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py) `MLDataPreparer.load_data()` | `fact_machine_hour` | `good_qty`, derived `production_qty`, derived `kwh_per_unit` | indirect / offline now |
| Canonical Optimization page | [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py) `render_optimization_module()` via [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py) | `fact_machine_hour` | `good_qty`, `scrap_qty`, derived `avg_kwh_per_good_unit`, `scrap_rate` | direct active now |
| Energy Analysis page | [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `show_energy_analysis_page()` | EUVG in-memory dataframe from [`modules/euvg_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/euvg_module.py) | `production_qty`, `kwh_per_unit` | no practical impact now |
| Overview page helper | [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `show_overview_page()` | EUVG in-memory dataframe | `production_qty`, `kwh_per_unit` | no practical impact now; function not currently routed |
| Team Performance page helper | [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `show_team_performance_page()` | EUVG in-memory dataframe | `production_qty`, `kwh_per_unit` | no practical impact now; function not currently routed |
| Legacy `unified_view` persistence path | [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) `UnifiedViewProcessor` | persisted `unified_view` table | `production_qty`, `kwh_per_unit` | no practical impact now on this task; table remained untouched |
| Legacy predictor dropdown / baseline / recommendations | [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) `_fetch_distinct()`, `_get_baseline_efficiency()`, `get_optimization_recommendations()` | persisted `unified_view` table | `production_qty`, `kwh_per_unit` | latent semantic divergence now |
| Shared ML helper tabs | [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py) `render_feature_insights_tab()`, `render_recommendations_tab()` | persisted `unified_view` table | `production_qty`, `kwh_per_unit` | latent / likely unused now |
| Maintenance page efficiency curve | [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) | persisted `unified_view` table | `kwh_per_unit` | no practical impact now |
| Legacy month helper | [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py) `get_available_months_from_data()` | persisted `unified_view` table | none directly; month discovery only | no practical impact now |

## Read-Only DB Comparison Summary

### Exact Task 4S hardened scope

Direct-source-verified comparison between active DB and pre-Task 4S backup:

- scope row count in both DBs: `31,677`
- materially changed rows in that exact scope: `3,388`
- active exact-scope `good_qty` total: `76,513,478.70666946`
- backup exact-scope `good_qty` total: `76,513,478.70666946`
- active exact-scope `scrap_qty` total: `0.0`
- backup exact-scope `scrap_qty` total: `0.0`

Interpretation:

- the live replacement changed row-level quantity distribution, not the exact-scope totals
- this is direct-source-verified from the active DB versus the pre-write backup

### Persisted legacy `unified_view`

Direct-source-verified active vs backup comparison:

- active `unified_view`: `(195,374 rows, total_production_qty 340,968,377.75817364, avg_kwh_per_unit 0.10065726148178249)`
- backup `unified_view`: `(195,374 rows, total_production_qty 340,968,377.75817364, avg_kwh_per_unit 0.10065726148178249)`
- active `unified_view_runs`: `19`
- backup `unified_view_runs`: `19`

Interpretation:

- persisted `unified_view` remained untouched
- no automatic downstream rematerialization happened

## Active Impact Now

### Canonical Unified View page

Direct-source-verified from code:

- [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) now routes the page through [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py)
- [`core/canonical_gold_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_gold_reader.py) sets `production_qty = good_qty` and derives `kwh_per_good_unit` from `energy_total_kwh / good_qty`

Direct-source-verified DB effect:

- month-level `total_good_qty` and `total_scrap_qty` stayed effectively conserved
- month-level `avg_kwh_per_good_unit` changed slightly in February through June
- delta range observed: about `-7.545647079561235e-08` to `8.16851860093587e-08`

Conclusion:

- user-visible canonical Unified View exports and row-level values changed now
- the headline quantity totals did not move materially
- the immediate visible KPI change is subtle and concentrated in row-level `good_qty` and derived efficiency, not in total-volume metrics

### Canonical Optimization page

Direct-source-verified from code:

- [`modules/optimization_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/optimization_module.py) reads canonical summaries only
- [`core/canonical_optimization_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_optimization_reader.py) uses `good_qty`, `scrap_qty`, `safe_good_qty`, `avg_kwh_per_good_unit`, and `scrap_rate` from `fact_machine_hour`

Direct-source-verified active vs backup comparison:

- January 2025: `1` machine summary changed
- February 2025: `1` machine summary changed
- March 2025: `3` machine summaries changed
- April 2025: `2` machine summaries changed
- May 2025: `1` machine summary changed
- June 2025: `1` machine summary changed
- top-10 optimization ranking set/order stayed unchanged in every month audited

Conclusion:

- current Optimization outputs are affected now
- the effect is real but narrow
- the most visible rankings did not materially reshuffle

### Canonical ML prediction page

Direct-source-verified from code:

- [`modules/ml_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/ml_module.py) reads canonical ML inputs only
- [`core/canonical_ml_reader.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/canonical_ml_reader.py) maps `production_qty = good_qty`
- predictor inference uses `production_qty` directly in [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py)

Direct-source-verified DB effect on changed rows:

- changed rows: `3,388`
- changed rows with changed `good_qty`: `3,388`
- changed rows where `good_qty > 0` status flipped: `0`
- changed rows where `hours_since_last_maintenance` changed: `0`
- changed rows where `task_name` changed: `0`
- changed rows with changed derived `kwh_per_unit`: `3,332`

Evidence-based conclusion:

- canonical ML numeric inputs changed now on the affected fact rows
- ML eligibility did not materially broaden or shrink from Task 4S itself
- current prediction results can change immediately where the month’s latest eligible machine row falls inside the changed slice
- this audit did not rerun a full end-to-end predictor diff for every visible month panel, so the immediate inference effect is evidence-based rather than fully enumerated

## Indirect / Offline Impact Now

### Canonical ML training path

Direct-source-verified from code:

- [`core/ml_trainer.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_trainer.py) loads training rows from `fact_machine_hour`
- training uses `production_qty = good_qty`
- training target is derived `kwh_per_unit = energy_total_kwh / production_qty`

Direct-source-verified changed-row evidence:

- `3,388` changed production rows
- `3,332` changed derived `kwh_per_unit` rows

Conclusion:

- Task 4S changes the canonical training data now
- no model artifact changed automatically
- no retraining occurred automatically
- the impact is offline until a separate retraining run happens

## No Practical Impact Now

### Persisted legacy `unified_view` consumers

Direct-source-verified from code and DB:

- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `show_energy_analysis_page()` uses the EUVG dataframe, not canonical `fact_machine_hour`
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) `show_overview_page()` and `show_team_performance_page()` also use EUVG/unified-view style data, but those helpers are not currently routed from the sidebar
- [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py) still queries `unified_view.kwh_per_unit`
- persisted `unified_view` is unchanged in active DB versus backup

Conclusion:

- Energy Analysis page: no practical impact now
- Maintenance analytics efficiency curve: no practical impact now
- Overview and Team Performance helper surfaces: no practical impact now because they are not currently user-routed

## Latent Semantic Impact / Technical Debt

The repo still has a canonical/runtime split.

Direct-source-verified examples:

- [`modules/unified_view_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/unified_view_module.py) user page is canonical, but the same file still contains legacy `unified_view` table generation code
- [`core/ml_predictor.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/ml_predictor.py) still fetches dropdown values, baseline efficiency, and machine recommendations from `unified_view`
- [`modules/shared_ml_components.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/shared_ml_components.py) still queries `unified_view`
- [`core/data_utils.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/core/data_utils.py) still exposes a `unified_view` month helper
- [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py) still ships both canonical-routed pages and legacy EUVG-backed analysis helpers side by side

Interpretation:

- Task 4S improved canonical data correctness and auditability
- it did not align every runtime-facing surface to that canonical quantity contract
- the remaining divergence is architectural, not a failure of the live replacement itself

## FYP / Product Significance

Grounded judgment:

- Task 4S now improves real runtime behavior on canonical surfaces:
  - canonical Unified View
  - canonical Optimization
  - canonical ML inference inputs
- the practical user-visible effect is currently modest, not dramatic:
  - quantity totals are conserved
  - optimization top-10 rankings stayed unchanged
  - canonical efficiency metrics only moved slightly at aggregate month level
- the larger significance is correctness and auditability groundwork:
  - canonical fact quantities now match the approved non-anomalous replacement contract
  - downstream canonical readers no longer sit on the old eligible-group mismatch
- the product still contains a canonical/runtime split and that should be treated as a documented limitation until aligned

## Exact Statement Of Current Runtime Change

- Canonical Unified View page: changed now, but mostly at row-level quantity and derived efficiency; not a major total-volume KPI shift.
- Canonical Optimization page: changed now, but narrowly; some machine summaries changed, while top-10 rankings stayed unchanged.
- Canonical ML prediction page: changed now at the input layer and can change visible predictions immediately where the latest eligible machine row is in the changed slice.
- Canonical ML training artifacts: did not change now; they would only change after a separate retraining step.
- Energy Analysis page in [`app.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/app.py): did not change now.
- Maintenance efficiency curve in [`modules/maintenance_module.py`](/Users/rayfung/Documents/VCC/LeoPaper/LeoPaperSmartManufacturingPlatform/modules/maintenance_module.py): did not change now.
- Persisted `unified_view` analytics: did not change now.

## Recommendation

Recommended next clean task boundary:

- separate downstream alignment task

Reason:

- the canonical quantity correction is already landed
- the remaining issue is not quantity execution
- the remaining issue is runtime-surface alignment between canonical `fact_machine_hour` consumers and legacy `unified_view` / EUVG consumers

## Remaining Limitations

- This audit did not rerun a full end-to-end visible prediction diff for every month on the canonical ML page; the current ML inference impact is partly evidence-based from code plus changed inputs.
- This audit intentionally did not retrain models, rematerialize legacy tables, or change anomaly policy.
- The legacy `unified_view` table still exists and remains a separate semantic family from canonical `fact_machine_hour`.
