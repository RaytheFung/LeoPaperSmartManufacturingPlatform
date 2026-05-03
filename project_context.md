# Project Context – Smart Manufacturing ETL + ML Platform

_Last updated: 2026-03-13 (post-presentation cleanup and Stage 3 follow-through)_

## Runtime Authority Note

- This file is retained as broad historical architecture context.
- Do not treat it as the live routed-runtime ledger.
- For current defended runtime ownership, trust `CURRENT_REBUILD_STATUS.md` and `docs/technical/ACTIVE_RUNTIME_OWNERSHIP_MANIFEST.md` first.

## 0. Execution Plan (Near‑Term)
- Current priority: complete Stage 3 follow-through after the March 6, 2026 presentation, with emphasis on maintenance-feature backfill, data verification, and cleanup of stale repo artifacts.
- Next after Stage 3: ML Quality & Reliability upgrades (feature engineering, time-aware validation, model metadata/registry, drift checks, explainability enhancements).

## 1. Architecture Overview

### Frontend (Streamlit)
- `app.py` orchestrates pages (ETL, unified view, energy analysis, team performance, maintenance, ML, optimization).
- `modules/` contains page modules:
  * `etl_module.py` – file uploads + ETL status
  * `unified_view_module.py` – browse unified dataset
  * `ml_module.py` – train/infer efficiency model
  * `optimization_module.py` – ML-driven production recommendations and action logging
  * `maintenance_module.py` – maintenance analytics and PM scheduling support
  * `shared_ml_components.py` – reusable live prediction tabs

### ETL Pipeline (modularized)
- `core/enhanced_etl_solution_CURRENT.py` now acts as a façade over:
  * `core/etl/extractor.py` (`DataExtractor`, `ExtractedData`)
  * `core/etl/mapper.py` (`MachineMapper`, `MappingResult`)
  * `core/etl/reporter.py` (`ETLReporter`, `ReportContext`)
- Monthly processing script `scripts/process_jan_to_june_2025.py` uses the façade; parameterized ETL now returns 60–61 three-way matches per month.
- Unified view schema stored in `manufacturing_data.db` includes transition energy, team roster, baseline/lag features, and `is_near_zero_output` to suppress divide-by-zero spikes.

### ML Pipeline
- Training (`core/ml_trainer.py`): filters anomalies, trains RandomForest (`models/production_efficiency_model.pkl`, R²≈0.75), and saves preprocessing bundle (`models/production_preprocessor.pkl`) containing feature order, label encoders, scaler, and medians.
- Inference (`core/ml_predictor.py`): reloads model + bundle, returns efficiency, confidence, and driver narratives; also exposes helper lookups (`get_machine_list`, etc.).
- Maintenance action log (`ml_action_log`) stores operator-triggered follow-up actions from the optimization module.

## 2. Current Goals (Stage 3 Focus)
1. **Perfect monthly ETL uploads (Energy, CSI, MES, Maintenance)** – seamless processing from Excel with stable three‑way mapping and quality checks; no real‑time ingestion required.
2. **Maintain “intelligent mode”** – retraining + inference in sync; predictions in a realistic range and explanatory drivers available.
3. **Actionable insights** – produce Team × Task and Team‑composition analyses from the unified view with sample thresholds; surface ML‑driven opportunities and maintenance hotspots.
4. **Harden codebase** – unit tests for `core/etl/*` and critical EUVG paths; continue splitting residual monolithic logic only where beneficial.

## 3. Recent Design Decisions
- Switched from heuristics to real ML predictions across the app; live predictions now display key drivers instead of random impacts.
- Refactored ETL into extractor/mapper/reporter modules; `EnhancedSmartManufacturingETL` remains for backwards compatibility but is now thin.
- Unified view filtering uses `MIN_PRODUCTION_THRESHOLD = 0.5` to avoid near-zero denominators; `is_near_zero_output` is persisted for downstream modules to ignore zero-load hours.
- Optimization tab ranks ML-driven efficiency opportunities, calculates potential kWh/cost savings from actual production totals, and allows one-click logging of maintenance actions.
- Maintenance analytics include an efficiency-vs-maintenance-age curve derived from the cleaned unified view data.

## 4. Unresolved Bugs / TODOs
- **ETL Subcomponents Tests** – add unit tests for `core/etl/…` (pattern normalization, partial matches) and EUVG critical paths.
- **Maintenance Feature Backfill** – live DB check on March 13, 2026 showed `unified_view.maintenance_in_hour` and `unified_view.hours_since_last_maintenance` still unpopulated even though the schema and downstream modules expect them; regenerate/backfill before treating maintenance-aware insights as complete.
- **Action Workflow** – `ml_action_log` captures actions; no CMMS automation or notifications yet (deferred).
- **Anomaly Detection** – simple outlier checks only; full alerting deferred.
- **API Integration** – Streamlit only; external API endpoints deferred.

## 4.1 Stage 3 Acceptance Criteria
- ETL: Monthly Excel uploads for Energy/CSI/MES + Maintenance complete without manual fixes; ≥60 three‑way matches; mapping stats persisted.
- Data quality: `kwh_per_unit` realistic (0.3–10), `is_near_zero_output` suppresses divide‑by‑zero spikes, energy attribution totals consistent.
- ML: Retraining succeeds; R² ≥ 0.70 on hold‑out; predictions used by app; preprocessing bundle saved; narratives available.
- Insights: Leader × Task and Team‑composition × Task rankings with min samples (leader ≥20, composition ≥10) and drill‑downs; Optimization tab surfaces top opportunities with savings.
- Reporting: Monthly Insights Report exported (key KPIs, top leaders/teams/tasks, opportunities, maintenance hotspots) and linked from the app.

## 5. Key Verification Commands
```bash
# Re-run ETL (Jan–Jun sample data)
python3 scripts/process_jan_to_june_2025.py

# Retrain ML model and persist preprocessing bundle
python3 core/ml_trainer.py

# Smoke-test inference & ROI helper
python3 core/ml_predictor.py

# Check unified view aggregate health
sqlite3 manufacturing_data.db "SELECT month_year, COUNT(*), AVG(kwh_per_unit) FROM unified_view GROUP BY month_year;"

# Launch the Streamlit app
streamlit run app.py
```

## 6. Useful Paths
- Raw sample data: `source_data/2025_jan_jun_initial/…`
- Latest ETL outputs: `etl_outputs/`
- Monthly summaries: `etl_outputs/summaries/processing_summary_*.csv`
- ML models + preprocessors: `models/`
- Maintenance action log (table): `ml_action_log` in `manufacturing_data.db`

## 7. Next Suggested Steps (Stage 3)
1. Add unit tests for `core/etl/extractor.py`, `mapper.py`, `reporter.py`, and EUVG allocation/attribution logic.
2. Implement Team × Task and Team‑composition × Task analytics with sample thresholds and exports; wire into UI.
3. Produce a Monthly Insights Report (export) and link from Streamlit.
4. Tighten data quality checks in ETL/EUVG (thresholds, guards, sanity queries) and document them.
5. Optional (deferred): simple anomaly scoring for dashboards; CMMS integration stubs for actions.

---
Keep this file updated whenever major structural changes, new workflows, or critical TODOs appear.
