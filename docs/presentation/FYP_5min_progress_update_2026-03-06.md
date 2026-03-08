# 5‑Minute FYP Progress Update (HW105, 2026‑03‑06)

## Slide 1 — Title (0:00–0:20)
**Smart Manufacturing ETL + ML Platform**  
Progress update (Stage 3) — 6 Mar 2026  
Fung Cheuk Hin (UID: 3036068943)

**Say:** One sentence: goal = unify factory data and deliver actionable efficiency + maintenance insights.

---

## Slide 2 — Problem & Goal (0:20–1:05)
**Problem**
- Monthly reporting is slow + manual (Excel) and data is siloed (Energy / CSI / MES / Maintenance)
- Machine IDs + timestamps don’t align → hard to join and analyze

**Goal**
- Build a *single “source of truth”* at hourly machine level
- Provide dashboards + ML-driven insights to reduce wasted energy and improve production decisions

**Say:** Emphasize integration pain + why the unified dataset matters more than “fancy ML”.

---

## Slide 3 — What We Built (1:05–2:00)
**End-to-end pipeline**
1) Monthly Excel uploads (Energy, CSI, MES, Maintenance)  
2) ETL mapping (extract → normalize IDs → match)  
3) SQLite storage (`etl_*`, `three_way_matches`, `unified_view`)  
4) Streamlit app modules (ETL / Unified View / ML / Optimization / Maintenance)

**Engineering**
- ETL refactored into modular components (`core/etl/*`) with a backward-compatible façade
- Verification scripts in `tests/` for key logic paths

**Say:** Point to the modular architecture and “repeatable monthly workflow”.

---

## Slide 4 — Integration Results (2:00–3:05)
**ETL mapping (Jan–Jun 2025)**
- Three-way matches: **59–60 machines / month**
- MES coverage: **~60.6% – 63.2%**

**Unified hourly dataset (SQLite)**
- `unified_view`: **195,374** machine-hour rows, **61** machines
- Valid `kwh_per_unit` samples: **178,958** rows
- Totals: **3,994,724.7 kWh**, **340,968,378 units**, avg **0.1007 kWh/unit**

**Say:** These numbers prove the integration is working at scale (not a toy demo).

---

## Slide 5 — Analytics & ML Progress (3:05–4:20)
**ML baseline (kWh/unit prediction)**
- RandomForest integrated with the app
- Latest recorded training: **R² = 0.747**, **MAE = 0.0323** (stored in `ml_models`)

**Decision support (in-app)**
- ML-driven opportunity ranking (low-performing machines → potential savings)
- “Action logging” path exists (creates `ml_action_log` on first use)

**Maintenance status**
- Maintenance data is ingested (e.g., `maintenance_records` has **14,378** rows)
- Next: backfill maintenance features into `unified_view` for true “maintenance-aware” learning

**Say:** Be explicit: ML works; maintenance-aware features are the next big upgrade.

---

## Slide 6 — Next 4 Weeks Plan (4:20–5:00)
**Week 1–2 (Data correctness + joins)**
- Regenerate `unified_view` with corrected **energy attribution** + **maintenance joins/backfill**
- Add guardrails + tests for edge cases (near-zero output, timestamp overlaps, mapping drift)

**Week 3 (Deliverable for supervisor)**
- One-click **Monthly Insights Report export** (KPIs + top opportunities)

**Week 4 (Finalization)**
- Model evaluation + narrative results
- Final report + final demo story

**Ask from supervisor**
- Confirm final evaluation rubric + what “success” should emphasize (integration quality vs ML novelty)

