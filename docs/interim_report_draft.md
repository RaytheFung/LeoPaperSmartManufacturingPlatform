# FYP Interim Report (Draft)
## A Maintenance‑Aware, Multi‑Source Integration and Predictive Analytics Platform for Smart Manufacturing

**Student Name:** Fung Cheuk Hin  
**University Number (UID):** 3036068943  
**Programme/Course:** DASE4174 Final Year Project (FYP)  
**Supervisor:** _[Insert Supervisor Name]_  
**Submission Date:** _[Insert Date]_  

---

## Abstract (300–500 words)

Manufacturing organisations increasingly rely on data-driven decision support to improve productivity, energy efficiency, and equipment reliability. In practice, however, many factories still operate with fragmented data silos: energy monitoring, production execution, planning (MES), and maintenance are stored in separate systems with inconsistent identifiers and different temporal granularity. This fragmentation makes monthly reporting slow, error-prone, and largely descriptive, and it prevents cross-system analysis such as quantifying how maintenance timing affects energy efficiency.

This project develops a maintenance-aware smart manufacturing platform that integrates four data streams—Energy (hourly kWh and cost), CSI execution (production quantities, speed, and team information), MES planning (tasks and planned quantities), and maintenance work orders—into a unified hourly “source of truth” stored in SQLite. A modular ETL pipeline extracts raw Excel data, normalises machine identifiers across systems, produces three-way machine matches, and persists cleaned datasets for downstream analysis. A Streamlit application then provides interactive dashboards for ETL monitoring, data exploration, energy/production analytics, machine learning (ML) predictions, and optimisation-oriented insights.

At the interim stage, the core data integration pipeline and the Streamlit application are operational. Using January–June 2025 data, the unified hourly dataset currently contains **195,374** machine-hour rows spanning **61** machines. The ETL process achieves **59–60** three-way matched machines per month, corresponding to an average match rate of **62.18%** against the available MES resources. Basic data quality checks and anomaly filters are implemented to handle missing production, near-zero output periods, and outlier kWh-per-unit values. A baseline production-efficiency model has been trained using a Random Forest regressor, achieving **R² = 0.747** and **MAE = 0.0323** (kWh/unit) on a held-out split, and the model is integrated into the dashboard for live scoring and driver-oriented explanations.

Remaining work focuses on (i) fully backfilling maintenance features (e.g., hours since last maintenance, maintenance intensity) into the unified view to realise “maintenance-aware” learning, (ii) strengthening energy attribution from raw meter readings into operational states (production/setup/idle/maintenance), (iii) hardening the pipeline via automated tests and validations, and (iv) finalising a monetised optimisation layer that ranks high-ROI interventions such as idle-energy reduction and improved team–task pairing.

---

## Table of Contents

1. **Introduction**  
   1.1 Project Background and Motivation  
   1.2 Problem Identification  
   1.3 Project Scope and Objectives  
   1.4 Expected Outcomes  
   1.5 Significance  
   1.6 Organisation of this Report  
2. **Literature Review**  
   2.1 Industry 4.0 and Smart Manufacturing Integration  
   2.2 Energy Management and Energy Attribution in Manufacturing  
   2.3 Predictive Maintenance and Maintenance-Aware Analytics  
   2.4 Record Linkage and Entity Resolution for Industrial Data  
   2.5 Machine Learning for Efficiency Modelling and Interpretability  
3. **Research Methodology**  
   3.1 System Architecture Overview  
   3.2 Data Sources and Pre-processing  
   3.3 ETL Pipeline and Machine Matching  
   3.4 Unified Hourly View Construction and Feature Engineering  
   3.5 ML Training, Evaluation, and Deployment  
   3.6 Optimisation and Decision Support Design  
4. **System Development and Interim Progress**  
   4.1 Implementation Overview (Codebase and Modules)  
   4.2 Database Design and Data Model  
   4.3 ETL Results and Data Volumes (Jan–Jun 2025)  
   4.4 ML Baseline Model Results  
   4.5 Maintenance Data Ingestion Status  
   4.6 Streamlit Dashboard and User Interaction  
   4.7 Testing and Validation Activities  
5. **Preliminary Findings and Discussion**  
   5.1 Data Quality Observations  
   5.2 Model Performance and Practical Interpretation  
   5.3 Current Limitations and Risks  
6. **Future Plans**  
7. **References**  
8. **Appendices**  

---

## List of Illustrations / Diagrams / Tables / Appendices (Planned)

### Figures (Planned)
- **Figure 3.1** System architecture of the Smart Manufacturing Platform (Streamlit + ETL + SQLite + ML).  
- **Figure 3.2** ETL workflow: Extract → Match → Report → Persist.  
- **Figure 3.3** Unified view construction at hourly granularity (energy, production, planning, maintenance).  
- **Figure 4.1** Screenshot of the Streamlit application navigation and main pages.  
- **Figure 5.1** Example ML prediction output with driver narrative (SHAP-style explanation).  

### Tables (Included)
- **Table 4.1** Unified hourly dataset summary (Jan–Jun 2025).  
- **Table 4.2** ETL run summary and three-way matching results.  
- **Table 4.3** Raw ETL data volumes (Energy/CSI/MES) by month.  
- **Table 4.4** Baseline ML model performance (Random Forest).  
- **Table 5.1** Data quality indicators (missingness and anomaly counts).  

### Appendices (Planned)
- **Appendix A** Database tables and key fields.  
- **Appendix B** Feature list for ML model training.  
- **Appendix C** Risk register and mitigation actions.  

---

## Abbreviations / Nomenclatures / Symbols

- **CSI**: Execution/production reporting system (site-specific)  
- **MES**: Manufacturing Execution System (planning/scheduling data)  
- **ETL**: Extract–Transform–Load  
- **PdM**: Predictive Maintenance  
- **PHM**: Prognostics and Health Management  
- **ML**: Machine Learning  
- **MLOps**: Practices for maintaining ML systems in production  
- **kWh**: Kilowatt-hour  
- **kWh/unit**: Energy efficiency metric (energy per production unit)  
- **R²**: Coefficient of determination  
- **MAE**: Mean Absolute Error  
- **RMSE**: Root Mean Squared Error  
- **SHAP**: SHapley Additive exPlanations  
- **ISO 50001**: International standard for energy management systems  

---

# Chapter 1 — Introduction

## 1.1 Project Background and Motivation

Industry 4.0 promotes the integration of cyber-physical production systems, where operational decisions are supported by real-time or near-real-time data and advanced analytics (Kagermann, Wahlster and Helbig, 2013; Monostori, 2014; Lee, Bagheri and Kao, 2015). In many “brownfield” factories, however, digitalisation is uneven: different departments adopt different systems, and integration often relies on periodic spreadsheet reconciliation rather than automated pipelines. This situation is especially common when energy monitoring, production execution, planning (MES), and maintenance management are maintained independently.

Energy is a major controllable manufacturing cost, and energy management frameworks such as ISO 50001 emphasise metered, actionable insights rather than high-level monthly aggregates (ISO, 2018). At the same time, predictive maintenance and PHM research highlights the operational benefits of proactive maintenance scheduling (Jardine, Lin and Banjevic, 2006; Lee et al., 2014). Yet, many practical implementations assume a single clean sensor source and do not reconcile planned versus actual execution, nor link maintenance to energy efficiency at an operational time scale.

This project is motivated by a practical site pain point: analysts spend significant time (5+ hours monthly) reconciling spreadsheets to produce reports, while key questions—such as energy wasted during non-productive periods and the measurable effect of maintenance actions—remain difficult to answer. The goal is therefore to build a unified data foundation and analytics layer that reduces reporting time and enables cross-system insights.

## 1.2 Problem Identification

The project targets three main problems:

1. **Fragmented data silos and inconsistent identifiers.** Machines may be referenced differently across systems (e.g., component-level energy meter names vs. execution machine codes vs. MES resource IDs). Without robust identifier alignment, cross-system joins are unreliable.
2. **Lack of actionable energy attribution.** Hourly meter readings alone cannot explain whether energy is used for production, setup, idle time, or maintenance activity. Without attribution, cost reduction opportunities are hard to prioritise.
3. **Limited predictive and decision support capability.** Even when historical data exists, the lack of an integrated dataset makes it difficult to train and deploy models that predict energy efficiency and recommend interventions such as maintenance timing or improved team–task pairing.

## 1.3 Project Scope and Objectives

### Scope (Interim Definition)
This project builds a data integration and analytics platform that:
- Integrates **Energy**, **CSI execution**, **MES planning**, and **Maintenance** records at **hourly** granularity.
- Produces a unified dataset suitable for analytics and ML (the “unified view”).
- Provides an interactive dashboard (Streamlit) for ETL monitoring, analytics, and ML-driven insights.

Out of scope for the interim stage:
- Real-time ingestion and streaming infrastructure (the system is batch-oriented).
- Full integration with external CMMS APIs and automated work order issuance.
- Multi-site scaling and enterprise authentication/authorisation (planned as stretch goals).

### Objectives
The measurable objectives (with success criteria) are adapted from the project proposal:
- **Data integration:** achieve high-precision cross-system machine matching (target ≥95% precision for confirmed matches) and stable monthly processing.
- **Cycle-time reduction:** reduce manual monthly report preparation from hours to minutes by automating ETL and dashboard generation.
- **Prediction:** build a baseline energy efficiency model targeting approximately **R² ≥ 0.75** for kWh/unit.
- **Decision support:** surface monetised improvement opportunities (idle-energy reduction, scheduling and maintenance timing) with clear prioritisation logic.

## 1.4 Expected Outcomes

By completion, the project is expected to deliver:
1. A reproducible ETL pipeline and database schema enabling consistent monthly processing of Energy/CSI/MES/Maintenance data.
2. A unified hourly dataset with engineered features for analytics and ML.
3. An operational dashboard that supports stakeholders in exploring efficiency, team and task patterns, and maintenance implications.
4. A predictive model that estimates kWh/unit and provides interpretable drivers.
5. A ranked list of improvement opportunities, translated into expected kWh and cost savings.

## 1.5 Significance

**Academic significance.** The project contributes an applied approach to brownfield manufacturing data fusion at hourly granularity, combining entity resolution, energy attribution concepts, and maintenance-aware modelling in a deployable system. It also reflects deployment-oriented ML practices, such as data quality management and model persistence.

**Practical significance.** The platform reduces the time and effort required to prepare recurring reports and enables fact-based discussion on energy efficiency and maintenance effectiveness. By framing predictive insights in operational terms (kWh/unit and cost), the system helps bridge the common gap between analytics metrics and business impact.

## 1.6 Organisation of this Report

Chapter 2 reviews literature relevant to smart manufacturing integration, energy analytics, predictive maintenance, record linkage, and ML interpretability. Chapter 3 describes the methodology and system design. Chapter 4 documents the system implementation and current progress. Chapter 5 presents preliminary findings and limitations. Chapter 6 outlines future plans toward project completion.

---

# Chapter 2 — Literature Review

## 2.1 Industry 4.0 and Smart Manufacturing Integration

Industry 4.0 highlights the need for connected systems and cyber-physical integration to enable responsive and optimised manufacturing operations (Kagermann, Wahlster and Helbig, 2013). Monostori (2014) emphasises the research perspective of cyber-physical production systems and the challenges of integration. Lee, Bagheri and Kao (2015) propose architectures that connect industrial assets and analytics layers. These works motivate the platform’s end-to-end architecture: data integration, storage, analytics, and a user-facing decision support interface.

However, many Industry 4.0 case studies focus on relatively homogeneous “greenfield” deployments. In brownfield settings, the primary barrier is often not the absence of data but the absence of reliable integration. This project therefore prioritises robust data linkage and a practical ETL workflow over high-frequency sensing.

## 2.2 Energy Management and Energy Attribution in Manufacturing

ISO 50001 provides a systematic framework for energy management, emphasising continual improvement supported by measurement and evidence (ISO, 2018). Reviews of energy management in smart factories (Shrouf, Ordieres and Miragliotta, 2014) motivate the need to transform raw energy readings into operationally meaningful insights. Hart (1992) introduced ideas related to disaggregation (NILM) but many approaches require high-frequency signals that are unavailable in typical factories. This project instead explores attribution at hourly granularity by combining meter data with production and maintenance traces.

## 2.3 Predictive Maintenance and Maintenance-Aware Analytics

Predictive maintenance and PHM research provides methods to anticipate failures and plan interventions using condition monitoring and historical maintenance data (Jardine, Lin and Banjevic, 2006; Lee et al., 2014). In many industrial applications, maintenance analytics focus on reliability targets (e.g., failure prediction). This project adopts an “energy efficiency” framing: maintenance is evaluated through its relationship with kWh/unit and operational outcomes, providing a cost-oriented lens for prioritising maintenance actions.

## 2.4 Record Linkage and Entity Resolution for Industrial Data

Entity resolution methods support the alignment of records and identifiers across systems (Christen, 2012; Winkler, 2006). Classic edit-distance approaches such as Levenshtein (1966) underpin similarity scoring when identifiers vary in format. In industrial data, identifier inconsistency is common (prefixes, separators, component descriptors, and legacy naming). This project applies rule-based normalisation and pattern extraction to achieve stable cross-system joins, while maintaining auditability and match statistics to support validation.

## 2.5 Machine Learning for Efficiency Modelling and Interpretability

For tabular operational datasets, tree ensembles such as Random Forests (Breiman, 2001) and gradient boosting (Chen and Guestrin, 2016) often deliver strong predictive performance. Interpretability methods such as SHAP (Lundberg and Lee, 2017) support adoption by explaining key drivers. Deployment-focused literature also highlights the hidden technical debt in ML systems (Sculley et al., 2015), motivating disciplined data validation, model versioning, and monitoring. The interim system therefore includes a reproducible training pipeline, saved preprocessing artifacts, and model performance logging.

---

# Chapter 3 — Research Methodology

## 3.1 System Architecture Overview

The platform follows a layered architecture:
- **Data sources:** monthly Excel reports from Energy meters, CSI execution, MES planning, and Maintenance work orders.
- **ETL layer:** extraction, cleaning, machine ID normalisation, three-way matching, and persistence to SQLite.
- **Unified view layer:** hourly integration of energy, production, and planning fields into a single dataset; engineered features for ML and analytics.
- **Analytics/ML layer:** dashboards, model training/inference, and optimisation calculations.
- **Presentation layer:** Streamlit application with modular pages (overview, ETL, unified view, energy analysis, ML predictions, optimisation, maintenance).

The design goal is to ensure each layer can be tested and evolved independently (e.g., refactoring ETL into extractor/mapper/reporter modules).

## 3.2 Data Sources and Pre-processing

The system uses four primary data sources:

1. **Energy (hourly):** machine-level meter readings containing `datetime`, `electricity_kwh`, and cost. Raw files may contain component-level names (e.g., UV/IR units) and totals; ETL excludes totals and retains valid machine readings.
2. **CSI (execution):** production traces including machine ID, start/end times, good quantity, speed, and team member information.
3. **MES (planning):** planned tasks, material codes, and planned quantities with `resource` IDs and scheduling timestamps.
4. **Maintenance:** work orders and transactions containing asset identifiers in multiple formats (MES-like and legacy IDs), maintenance type, part consumption, and organisational metadata.

All timestamps are standardised to pandas datetime, and the pipeline performs basic filtering (e.g., excluding non-positive kWh).

## 3.3 ETL Pipeline and Machine Matching

The ETL pipeline is modularised into:
- **Extractor:** reads Excel files into standardised DataFrames.
- **Mapper:** normalises machine identifiers and constructs cross-system mappings.
- **Reporter:** calculates integrated metrics and generates ETL reports (Excel summaries and JSON mappings).

Machine matching is performed using rule-based normalisation and pattern extraction, designed to handle:
- prefixes and padding differences (e.g., `1024-00094` → `024-094`)
- separators (`-`, `_`, `#`, whitespace)
- component descriptors (e.g., “UV”, “IR”, “主機”)

A three-way match is accepted when the normalised pattern is consistent across Energy, CSI, and MES. Partial matches are retained for review (e.g., Energy–CSI only).

## 3.4 Unified Hourly View Construction and Feature Engineering

The unified view aggregates all sources into an hourly machine-level dataset with:
- energy metrics (kWh, cost proxies)
- production quantity and time
- team leader and team composition
- material code and task type
- temporal features (hour of day, day of week, weekend flags)
- lag/rolling statistics for stability (e.g., 1h lag and 4–24h moving averages)

The target variable for ML is **kWh per unit**, computed as `energy_kwh / production_qty` with guards against divide-by-zero and outlier values.

Maintenance-aware fields (e.g., hours since last maintenance, maintenance intensity) are supported in the schema and are being integrated from the maintenance tables.

## 3.5 ML Training, Evaluation, and Deployment

The training pipeline:
1. Loads data from the unified view and filters anomalous rows (e.g., near-zero output).
2. Engineers time, machine, team, and maintenance features.
3. Encodes categorical fields (e.g., machine type, team leader, material code) and scales numerical inputs.
4. Trains multiple models (baseline linear regression and tree ensembles) and evaluates them using R²/MAE/RMSE.
5. Persists the best-performing model and preprocessing bundle for consistent inference.

The system records model performance in the database for traceability and supports inference from the dashboard.

## 3.6 Optimisation and Decision Support Design

Optimisation in this project focuses on ranking feasible interventions by estimated ROI, such as:
- reducing idle energy for machines with high idle ratios
- improving team–task allocation using historical performance signals
- prioritising maintenance actions where performance degrades with time since last maintenance

The optimisation module integrates ML predictions with production volumes and (where available) energy tariffs to estimate the kWh and cost impact.

---

# Chapter 4 — System Development and Interim Progress

## 4.1 Implementation Overview (Codebase and Modules)

The current system is implemented in Python with a Streamlit frontend. The repository is organised into:
- `app.py`: application entry point and navigation.
- `core/`: ETL orchestration, data utilities, ML training/prediction, and maintenance integration.
- `modules/`: Streamlit page modules (ETL, unified view, energy analysis, ML, optimisation, maintenance).
- `manufacturing_data.db`: SQLite database containing processed datasets and metadata tables.

## 4.2 Database Design and Data Model

The SQLite database stores:
- raw ETL tables: `etl_energy_data`, `etl_csi_data`, `etl_mes_data`
- mapping metadata: `three_way_matches`, `etl_runs`
- the main integrated dataset: `unified_view`
- ML metadata: `ml_models`
- maintenance ingestion tables: `maintenance_records`, `maintenance_summary`

The unified view contains hourly-level fields across energy, production, team, task, and lag features (see Appendix A for selected columns).

## 4.3 ETL Results and Data Volumes (Jan–Jun 2025)

This section summarises the current processed dataset in `manufacturing_data.db`.

### Table 4.1 Unified hourly dataset summary (Jan–Jun 2025)

| Month | Rows (machine-hours) | Machines | Avg kWh/unit |
|---|---:|---:|---:|
| January 2025 | 23,430 | 59 | 0.097 |
| February 2025 | 24,425 | 60 | 0.091 |
| March 2025 | 36,155 | 60 | 0.124 |
| April 2025 | 35,526 | 59 | 0.101 |
| May 2025 | 37,897 | 60 | 0.103 |
| June 2025 | 37,941 | 60 | 0.084 |
| **Total** | **195,374** | **61 (distinct)** | **0.1007 (overall avg)** |

The unified view currently spans **2025-01-02 08:00** to **2025-06-30 23:00**.

### Table 4.2 ETL run summary (three-way matching)

| Month processed | Status | Three-way matches | Match rate (%) | Run date |
|---|---|---:|---:|---|
| January 2025 | Success | 59 | 62.8 | 2025-08-11 |
| February 2025 | Success | 60 | 63.2 | 2025-08-11 |
| March 2025 | Success | 60 | 62.5 | 2025-08-11 |
| April 2025 | Success | 59 | 61.5 | 2025-08-11 |
| May 2025 | Success | 60 | 62.5 | 2025-08-11 |
| June 2025 | Success | 60 | 60.6 | 2025-08-19 |
| **Average** | — | — | **62.18** | — |

### Table 4.3 Raw ETL data volumes by month

| Month | Energy rows | CSI rows | MES rows |
|---|---:|---:|---:|
| January 2025 | 95,973 | 15,201 | 14,360 |
| February 2025 | 87,357 | 16,963 | 15,747 |
| March 2025 | 96,717 | 22,703 | 21,079 |
| April 2025 | 92,877 | 22,257 | 20,839 |
| May 2025 | 97,157 | 23,137 | 21,477 |
| June 2025 | 94,319 | 23,946 | 22,400 |

These volumes demonstrate that the pipeline supports large monthly extracts, especially for Energy data which may contain component-level readings.

## 4.4 ML Baseline Model Results

The baseline model predicts **kWh per unit** using machine, time, team, and (placeholder) maintenance features. The best-performing current model is a Random Forest regressor logged in the database.

### Table 4.4 Baseline ML model performance (Random Forest)

| Model | Type | Training date | Features | R² | MAE (kWh/unit) |
|---|---|---|---:|---:|---:|
| production_efficiency_20251013_0009 | Random Forest | 2025-10-13 | 18 | 0.747 | 0.0323 |

The interim performance meets the target magnitude (≈0.75 R²) stated in the proposal. Further improvements are expected after maintenance features are fully integrated and time-aware validation is strengthened.

## 4.5 Maintenance Data Ingestion Status

Maintenance ingestion tables exist and contain **14,378** maintenance transaction records spanning **2024-01-02** to **2025-08-14**. At the interim stage, maintenance records are stored and normalised to the same machine ID format used in the unified view. However, maintenance-derived features (e.g., “hours since last maintenance”) have not yet been fully backfilled into the unified hourly dataset, and this is a priority for the next milestone.

## 4.6 Streamlit Dashboard and User Interaction

The Streamlit application provides pages for:
- **Overview:** high-level KPI summaries and trend visualisations.
- **ETL Pipeline:** file ingestion, mapping statistics, and ETL reports.
- **Unified View:** browsing and filtering the integrated dataset.
- **Energy Analysis:** energy consumption and efficiency comparisons across machines.
- **ML Predictions:** model training and inference with interpretable drivers.
- **Optimisation:** ranking of improvement opportunities and (planned) action logging.
- **Maintenance:** summary views for maintenance history and scheduling support (in progress).

The app is configured to run on `http://localhost:8502` with logs under `.streamlit/`.

## 4.7 Testing and Validation Activities

The repository includes unit and integration tests for key components (ETL modules, energy attribution fixes, and ML prediction behaviour). Current validation focuses on:
- schema and column presence checks for ETL outputs
- sanity checks for outliers (e.g., kWh/unit ranges)
- regression tests for critical calculations (e.g., production allocation and model stability)

Further work will expand coverage, particularly around maintenance feature computation and optimisation outputs.

---

# Chapter 5 — Preliminary Findings and Discussion

## 5.1 Data Quality Observations

Initial data quality indicators computed from `unified_view` are summarised below.

### Table 5.1 Data quality indicators (current dataset)

| Indicator | Value |
|---|---:|
| Total unified rows | 195,374 |
| Rows with `production_qty` ≤ 0 or NULL | 15,783 (≈8.1%) |
| Rows with `energy_kwh` ≤ 0 or NULL | 679 (≈0.35%) |
| Rows with `kwh_per_unit` ≤ 0 or NULL | 16,416 (≈8.4%) |
| Missing `team_leader` | 1.09% |
| Missing `material_code` | 8.0% |
| `energy_kwh` range | 0.00 to 166.02 (avg 20.45) |
| `kwh_per_unit` range | 0.00 to 78.97 (avg 0.1007) |

Observations:
- A non-trivial portion of machine-hours have zero production; these hours are important for identifying idle energy but can distort kWh/unit if not handled carefully.
- Outliers in kWh/unit exist and require filtering for ML training. The current training pipeline applies thresholds and excludes near-zero output periods.
- Team and material fields are largely present, enabling team–task analysis; however, missingness should be monitored to avoid biased insights.

## 5.2 Model Performance and Practical Interpretation

The baseline ML model achieves R² ≈ 0.75, which is a strong starting point for operational prediction on noisy, multi-source industrial data. In practice, prediction usefulness depends not only on accuracy but also on interpretability and actionability:
- **Interpretability:** driver narratives (e.g., “time of day”, “machine type”, “recent production quantity”) help users understand why an efficiency level is predicted.
- **Actionability:** the model must support counterfactual reasoning, such as how efficiency is expected to change after maintenance or under different team–task assignments.

At the interim stage, the model is most reliable as a baseline predictor and as an input to exploratory dashboards. Maintenance-aware modelling will be strengthened once maintenance features are fully computed and integrated.

## 5.3 Current Limitations and Risks

Key limitations and risks include:
- **Maintenance-aware features not fully backfilled:** although maintenance records are ingested, the unified view still requires systematic enrichment (hours since last maintenance, intensity, type).
- **Energy attribution maturity:** the operational classification of energy into production/setup/idle/maintenance requires careful validation and may initially be heuristic-based.
- **Matching coverage:** three-way match rates (~62%) imply that some machines remain unmatched; improving coverage without harming precision is a trade-off.
- **Evaluation design:** model performance should be validated using time-aware splits and robustness checks across months to reduce leakage risk.

---

# Chapter 6 — Future Plans

The remaining work is planned across four workstreams:

1. **Maintenance integration completion**
   - Backfill maintenance-derived features into the unified view.
   - Generate maintenance ML feature table (rolling counts, days since last event).
   - Add maintenance dashboards and maintenance-sensitive optimisation signals.

2. **Energy attribution and deeper analytics**
   - Implement and validate production/setup/idle/maintenance energy attribution rules.
   - Add diagnostics to confirm attribution consistency (sums and edge cases).
   - Produce machine-level opportunity rankings for idle-energy reduction.

3. **ML hardening and evaluation**
   - Add time-aware validation, drift checks, and model metadata/versioning.
   - Improve feature engineering (lags, rolling windows, task complexity signals).
   - Expand interpretability output for dashboard users.

4. **Optimisation and reporting**
   - Finalise ROI calculation model and prioritisation logic.
   - Implement action logging workflow (e.g., maintenance action log table and UI).
   - Produce a reproducible “Monthly Insights Report” export from the dashboard.

### Milestone schedule (proposed)

| Period | Milestone |
|---|---|
| Weeks 1–2 | Maintenance feature backfill + validation queries |
| Weeks 3–4 | Energy attribution rules + dashboards + QA |
| Weeks 5–6 | ML improvements (time-aware validation, drift checks) |
| Weeks 7–8 | Optimisation ROI model + reporting export + final polishing |

---

# References

Batini, C. and Scannapieco, M. (2006) *Data Quality: Concepts, Methodologies and Techniques*. Berlin: Springer.

Breiman, L. (2001) ‘Random forests’, *Machine Learning*, 45(1), pp. 5–32.

Chen, T. and Guestrin, C. (2016) ‘XGBoost: A scalable tree boosting system’, *Proceedings of the 22nd ACM SIGKDD Conference*, pp. 785–794.

Christen, P. (2012) *Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection*. Berlin: Springer.

Hart, G.W. (1992) ‘Nonintrusive appliance load monitoring’, *Proceedings of the IEEE*, 80(12), pp. 1870–1891.

International Organization for Standardization (ISO) (2018) *ISO 50001:2018 Energy management systems — Requirements with guidance for use*. Geneva: ISO.

Jardine, A.K.S., Lin, D. and Banjevic, D. (2006) ‘A review on machinery diagnostics and prognostics implementing condition-based maintenance’, *Mechanical Systems and Signal Processing*, 20(7), pp. 1483–1510.

Kagermann, H., Wahlster, W. and Helbig, J. (2013) *Recommendations for Implementing the Strategic Initiative INDUSTRIE 4.0*. Munich: acatech.

Kusiak, A. (2018) ‘Smart manufacturing’, *International Journal of Production Research*, 56(1–2), pp. 508–517.

Lee, J., Bagheri, B. and Kao, H.-A. (2015) ‘A cyber-physical systems architecture for Industry 4.0-based manufacturing systems’, *Manufacturing Letters*, 3, pp. 18–23.

Lee, J. et al. (2014) ‘Prognostics and health management design for rotary machinery systems—review, methodology and applications’, *Mechanical Systems and Signal Processing*, 42(1–2), pp. 314–334.

Levenshtein, V.I. (1966) ‘Binary codes capable of correcting deletions, insertions, and reversals’, *Soviet Physics Doklady*, 10(8), pp. 707–710.

Lundberg, S.M. and Lee, S.-I. (2017) ‘A unified approach to interpreting model predictions’, *Advances in Neural Information Processing Systems*, 30, pp. 4765–4774.

Monostori, L. (2014) ‘Cyber-physical production systems: A view from manufacturing research’, *Procedia CIRP*, 17, pp. 9–13.

Sculley, D. et al. (2015) ‘Hidden technical debt in machine learning systems’, *NIPS 2015 Workshop on ML Systems*.

Shrouf, F., Ordieres, J. and Miragliotta, G. (2014) ‘Smart factories in Industry 4.0: A review of the concept and of energy management approaches’, *2014 IEEE IEEM*, pp. 697–701.

Winkler, W.E. (2006) ‘Overview of record linkage and current research directions’, *U.S. Census Bureau Research Report Series* (RR2006/02).

Zhong, R.Y., Xu, C., Klotz, E. and Newman, S.T. (2017) ‘Intelligent manufacturing in the context of Industry 4.0: A review’, *Engineering*, 3(5), pp. 616–630.

---

# Appendices

## Appendix A — Database tables (selected)

**Core tables**
- `unified_view`: integrated hourly dataset for analytics and ML
- `three_way_matches`: confirmed cross-system machine mappings
- `etl_runs`: per-month ETL run metadata (match rate, counts, status)

**Raw ETL tables**
- `etl_energy_data`, `etl_csi_data`, `etl_mes_data`

**ML metadata**
- `ml_models`: model performance logs and training metadata

**Maintenance ingestion**
- `maintenance_records`, `maintenance_summary`

## Appendix B — ML feature list (baseline)

The baseline model uses features such as:
- time: hour of day, day of week, month, weekend flag, night-shift flag
- machine: machine type (prefix), machine number
- team/task: team size, (task complexity proxy), team leader/material code encodings
- maintenance placeholders: hours since last maintenance, intensity, counts (to be fully integrated)
- production context: production quantity

## Appendix C — Risk register (summary)

| Risk | Impact | Mitigation |
|---|---|---|
| Incomplete maintenance feature integration | Limits “maintenance-aware” modelling | Prioritise backfill pipeline; validate with spot checks |
| Outliers and missing production | Distorts efficiency metrics | Apply guards, missingness reporting, and robust filters |
| Overfitting / data leakage | Unreliable predictions in future months | Use time-aware validation and drift checks |
| Low match coverage | Reduced representativeness | Improve normalisation rules; manual review for partial matches |

