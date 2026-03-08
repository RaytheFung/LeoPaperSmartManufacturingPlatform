# Progress Update (for HW105) — Smart Manufacturing ETL + ML Platform

**As of:** 2026-03-05  
**Presentation date:** 2026-03-06  

## 1) What we have today (end-to-end)

### Streamlit app (working UI modules)
- `app.py` orchestrates pages: ETL upload, Unified View, Energy Analysis, Maintenance, ML, Optimization.
- Key modules in `modules/`:
  - `etl_module.py` — upload monthly Energy/CSI/MES → run ETL mapping → persist results into SQLite
  - `unified_view_module.py` — generate the unified hourly dataset into SQLite
  - `ml_module.py` + `core/ml_trainer.py` + `core/ml_predictor.py` — training + live inference UI
  - `optimization_module.py` — opportunity ranking + (optional) action logging
  - `maintenance_module.py` + `core/maintenance_integration.py` — maintenance data ingestion + summaries (risk layer partially wired)

### ETL pipeline (modularized + testable)
- `core/enhanced_etl_solution_CURRENT.py` is now a façade over `core/etl/{extractor.py,mapper.py,reporter.py}`.
- Output: three-way mapping between Energy ↔ CSI ↔ MES with mapping stats + exports.
- SQLite persistence:
  - `etl_runs`, `machine_inventory`, `three_way_matches`
  - raw extracted tables: `etl_energy_data`, `etl_csi_data`, `etl_mes_data`

### Unified hourly “source of truth” (SQLite)
- Unified machine-hour dataset in table `unified_view`:
  - energy + production merged hourly
  - team leader / composition, material, task type
  - engineered time features and lags
  - `is_near_zero_output` guard to suppress divide-by-zero spikes

### ML baseline (already trained + integrated)
- Regression target: `kwh_per_unit`
- Training/inference: `core/ml_trainer.py`, `core/ml_predictor.py`
- Saved artifacts in `models/` + training metrics stored in SQLite table `ml_models`.

## 2) Current measured status (from `manufacturing_data.db`)

### Data volume (Jan–Jun 2025)
- `unified_view`: **195,374** machine-hour rows, **61** machines
- Valid efficiency samples (`kwh_per_unit IS NOT NULL`): **178,958** rows
- Totals across Jan–Jun 2025:
  - Energy: **3,994,724.7 kWh**
  - Production: **340,968,378 units**
  - Avg efficiency: **0.1007 kWh/unit**

### ETL mapping quality (per month)
- Three-way matches: **59–60** machines/month
- MES coverage rate (from `etl_runs.match_rate`): **~60.6% – 63.2%**

### Maintenance data ingestion (available in DB)
- `maintenance_records`: **14,378** rows
- `maintenance_summary`: **990** rows
- `machine_maintenance_history`: **3,711** rows

### ML status (latest recorded)
- `ml_models` contains **13** training records
- Latest model in DB: **RandomForest**, **R² = 0.747**, **MAE = 0.0323** (training date: 2025-10-13)

## 3) What is “implemented” vs “still to finalize”

### Implemented (demo-ready tomorrow)
- ETL mapping + stats + SQLite persistence
- Unified hourly dataset + quality guard (`is_near_zero_output`)
- ML training + saved preprocessing bundle + inference UI hooks
- Optimization UI with opportunity ranking; action logging table (`ml_action_log`) is created on first use

### Still to finalize (next 4 weeks focus)
- **Maintenance-aware features in `unified_view`**: current DB shows `maintenance_in_hour` and `hours_since_last_maintenance` not populated (pipeline exists, needs final join/backfill + regeneration).
- **Energy attribution breakdown**: `setup_energy/production_energy/maintenance_energy/energy_state` are currently not populated in the stored unified dataset (needs reprocessing with the corrected attribution logic path).
- **Monthly Insights Report export** (one-click report for professor/industry audience).
- **Tests hardening**: there are verification scripts in `tests/`, but coverage can be expanded for ETL edge cases + unified view attribution/maintenance joins.

## 4) Commands (if we need to refresh or demo)

### Run app safely on macOS (recommended)
```bash
bash scripts/bootstrap_py311_and_run.sh
```
Open: http://localhost:8502

### Quick database health checks
```bash
sqlite3 manufacturing_data.db "SELECT month_year, COUNT(*), COUNT(DISTINCT machine_id), ROUND(AVG(kwh_per_unit),4) FROM unified_view GROUP BY month_year ORDER BY month_year;"
sqlite3 manufacturing_data.db "SELECT month_processed, three_way_matches, ROUND(match_rate,1) || '%' FROM etl_runs ORDER BY run_date DESC LIMIT 6;"
sqlite3 manufacturing_data.db "SELECT model_name, model_type, ROUND(r2_score,3), ROUND(mae,4), training_date FROM ml_models ORDER BY training_date DESC LIMIT 3;"
```

