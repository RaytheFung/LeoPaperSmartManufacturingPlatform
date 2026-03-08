# Technical Overview (Stage 3)

This document orients new contributors and points to the living context.

Canonical reference
- See `project_context.md` for the authoritative architecture, goals, and acceptance criteria.

Architecture map
- ETL façade: `core/enhanced_etl_solution_CURRENT.py`
- ETL modules: `core/etl/{extractor.py, mapper.py, reporter.py}`
- Unified View (EUVG): `modules/euvg_module.py` (+ `modules/unified_view_module.py` entry)
- ML pipeline: `core/ml_trainer.py` (train) and `core/ml_predictor.py` (inference)
- Maintenance integration: `core/maintenance_integration.py`
- Streamlit app: `app.py`, pages in `modules/`
- DB: `manufacturing_data.db` (see `project_context.md` for key tables)

Stage 3 scope
- Monthly Excel uploads (Energy, CSI, MES, Maintenance); no real‑time feeds
- Unified hourly dataset with kWh/unit and maintenance/teams/material context
- ML predictions on `kwh_per_unit` with driver insights
- Insights: Team × Task and Team‑composition × Task rankings

Verification
- ETL: `python3 scripts/process_jan_to_june_2025.py`
- Train: `python3 core/ml_trainer.py`
- Predict: `python3 core/ml_predictor.py`
- Health: `sqlite3 manufacturing_data.db "SELECT month_year, COUNT(*), AVG(kwh_per_unit) FROM unified_view GROUP BY month_year;"`

Notes
- Prefer small, testable modules; don’t expand monoliths
- Guard against near‑zero denominators; keep `kwh_per_unit` realistic (0.3–10)
