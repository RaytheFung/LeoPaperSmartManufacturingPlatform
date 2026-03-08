# Roadmap – Stage 3 (Consolidation)

Scope
- Monthly manual uploads of Energy, CSI, MES, and Maintenance Excel files
- High‑quality unified hourly dataset; no real‑time ingestion
- ML on `kwh_per_unit` with driver insights; optimization surfaced in app

Acceptance Criteria
- ETL: ≥60 three‑way matches/month; mapping stats saved; no manual fixes needed
- Data Quality: `kwh_per_unit` 0.3–10; `is_near_zero_output` guards; attribution sums consistent
- ML: R² ≥ 0.70; model + preprocessor saved; predictions and narratives used in UI
- Insights: Leader × Task (n≥20) and Team‑composition × Task (n≥10) rankings with drill‑downs
- Reporting: Monthly Insights Report export linked from Streamlit

Verification Commands
```bash
python3 scripts/process_jan_to_june_2025.py
python3 core/ml_trainer.py
python3 core/ml_predictor.py
sqlite3 manufacturing_data.db "SELECT month_year, COUNT(*), AVG(kwh_per_unit) FROM unified_view GROUP BY month_year;"
```

Cadence
- Upload new month → run ETL → train → verify metrics → generate insights report → review

Source of Truth
- See `project_context.md` for living details and changes.
