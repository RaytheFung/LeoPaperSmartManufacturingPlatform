# Smart Manufacturing FYP Rebuild Intent and System Spec

## 1. Why we are rebuilding

This project is **not being restarted from zero**. The product direction is still valid:

- monthly Excel ingestion;
- manufacturing ETL over `Energy + CSI + MES + Maintenance`;
- SQLite-backed unified analytics store;
- Streamlit decision-support application;
- ML-assisted operational insight generation.

However, the current implementation has several structural trust problems that make the project harder to defend as an FYP:

1. **Machine identity is not governed well enough**.
   - The same physical machine appears under different codes across CSI, MES, Energy, and Maintenance.
   - Example families include `024 ↔ 1024`, `035 ↔ 1035`, `166 ↔ 1166`, `256 ↔ 1234`.
   - Some machines also have dual-ID Energy labels such as `1024-10032/024-147...`.

2. **Some current unified-view logic is not trustworthy enough**.
   - Formal analysis must not rely on synthetic fallback records.
   - Every inference must be traceable and confidence-scored.

3. **Schema assumptions do not fully match raw source reality**.
   - Raw CSI files do not contain `準備開始時間`, so setup start must be inferred.
   - Energy labels include total meters and component meters, so naive summation can double-count.

4. **ML credibility depends on the data backbone being stable first**.
   - If joins, setup windows, or machine identities are unstable, model outputs are not defensible.

Therefore, this rebuild is a **controlled rebuild of the data backbone**, not a broad rewrite of the whole application.

---

## 2. What we are building after the rebuild

We are building a **Smart Manufacturing Decision-Support Platform** with a trustworthy canonical data layer.

### Product identity
The rebuilt system should be described as:

> A monthly smart manufacturing data integration and decision-support platform with ML-assisted efficiency benchmarking.

### What it is NOT claiming yet
This FYP should **not** overclaim the following unless better labels are later obtained:

- full predictive maintenance system;
- production-grade scheduling optimizer;
- company-grade ROI engine;
- closed-loop autonomous factory control.

### FYP-safe AI positioning
The AI / ML element should be framed as:

- contextual efficiency prediction;
- machine opportunity ranking;
- ML-assisted recommendation;
- anomaly-style excess-energy identification.

---

## 3. Rebuild principles

1. **Do not break the current product shell unless necessary**.
   - Keep the existing Streamlit product concept.
   - Keep the monthly ETL workflow.
   - Keep the ML / Maintenance / Optimization feature families.

2. **Rebuild from the bottom up**.
   - Fix machine mapping first.
   - Then normalize raw source contracts.
   - Then rebuild unified operational truth.
   - Only then stabilize ML and front-end outputs.

3. **No silent fabrication in formal analysis paths**.
   - No synthetic fallback rows for user-facing analytics.
   - If data is inferred, store `method`, `confidence`, and `assumption_note`.

4. **Bronze → Silver → Gold architecture**.
   - Bronze preserves raw Excel truth.
   - Silver canonicalizes each source.
   - Gold builds one trustworthy machine-hour fact table.

5. **Be explicit about uncertainty**.
   - `machine_alias_registry` stores confidence and evidence.
   - setup inference stores method and confidence.
   - state attribution stores source flags and method.

---

## 4. Current repo issues that justify the rebuild

Codex should assume the current repo contains useful code, but also these likely issues:

- `app.py` mixes legacy demo logic with production-style flows.
- `etl_module.py` orchestrates uploads and downstream processing, but current persistence / replay assumptions need review.
- `unified_view_module.py` must be treated as high-risk because synthetic fallback and placeholder paths must not remain in formal analysis.
- `euvg_module.py` should not remain a competing source of truth for formal analytics.
- `ml_trainer.py` and `ml_predictor.py` should not be redesigned first; they should be retargeted after canonical data becomes stable.
- `optimization_module.py` and `maintenance_module.py` should consume only the canonical Gold layer once available.

Important note:
The uploaded review snapshot and the live repo may not have identical structure. The live repo screenshot shows a `core/` directory and a `core/etl/` folder, so **Codex must audit the actual repo tree first** before applying changes.

---

## 5. Canonical data architecture

## 5.1 Bronze layer
These tables preserve source truth without business reinterpretation.

### `raw_energy_hourly`
- `source_file`
- `raw_area`
- `raw_timestamp`
- `raw_kwh`
- `raw_cost`

### `raw_csi_event`
- `source_file`
- all raw CSI columns
- `ingested_at`

### `raw_mes_report`
- `source_file`
- all raw MES columns
- `ingested_at`

### `raw_maintenance_txn`
- `source_file`
- all raw maintenance columns
- `ingested_at`

## 5.2 Silver layer
These tables normalize each source into stable contracts.

### `machine_alias_registry`
Purpose:
- provide one canonical machine identity layer;
- store cross-system aliases;
- store evidence and confidence;
- support join governance.

Minimum fields:
- `canonical_machine_id`
- `csi_machine_id`
- `mes_primary_resource`
- `mes_secondary_aliases`
- `maintenance_asset_id`
- `maintenance_legacy_id`
- `maintenance_asset_desc`
- `energy_meter_labels`
- `evidence_sources`
- `confidence`
- `notes`
- `join_status`

### `energy_meter_hour`
Purpose:
- separate machine-level and component-level energy data;
- avoid double counting;
- make meter composition explicit.

Minimum fields:
- `canonical_machine_id`
- `meter_label`
- `meter_component`
- `meter_is_aggregate`
- `hour_ts`
- `kwh`
- `cost`
- `source_file`
- `parse_confidence`

### `csi_job_event`
Purpose:
- represent CSI production / setup / stop context as canonical job events.

Minimum fields:
- `canonical_machine_id`
- `shift_date`
- `shift_name`
- `csi_area`
- `order_id`
- `suffix`
- `operation`
- `material_code`
- `task_name`
- `prod_start_ts`
- `prep_end_ts`
- `prod_end_ts`
- `good_qty`
- `scrap_qty`
- `cumulative_qty`
- `actual_run_minutes`
- `actual_prod_minutes`
- `actual_speed_per_hour`
- `actual_changeover_minutes`
- `planned_stop_minutes`
- `unplanned_stop_minutes`
- `stop_reason`
- `stop_count`
- `team_leader`
- `team_members_raw`
- `source_file`

### `mes_report_event`
Purpose:
- represent MES report-level execution logs as canonical operational events.

Minimum fields:
- `canonical_machine_id`
- `report_ts`
- `order_id`
- `suffix`
- `operation`
- `task_name`
- `material_code`
- `required_qty`
- `reported_qty`
- `cumulative_qty`
- `report_type`
- `equipment_total_hours`
- `prep_hours`
- `equipment_prod_hours`
- `manpower`
- `shift_name`
- `resource_id_raw`
- `csi_upload_status`
- `status_changed_ts`
- `record_created_ts`
- `source_file`

### `maintenance_txn_event`
Purpose:
- represent maintenance transaction / parts movement / work-order-linked activity.
- use it first as maintenance context and machine crosswalk support.

Minimum fields:
- `canonical_machine_id`
- `txn_ts`
- `work_order_id`
- `work_order_desc`
- `work_order_type`
- `txn_type`
- `item_code`
- `item_desc`
- `quantity`
- `asset_id`
- `asset_legacy_id`
- `asset_parent_id`
- `asset_desc`
- `maint_team`
- `maint_department`
- `source_file`

## 5.3 Gold layer
This is the single formal operational fact layer.

### `fact_machine_hour`
Purpose:
- become the only formal input for app analytics and ML;
- unify energy, production, setup, stops, maintenance, team, and machine state.

Minimum fields:
- `canonical_machine_id`
- `hour_ts`
- `machine_state`
- `state_confidence`
- `order_id`
- `material_code`
- `task_name`
- `energy_total_kwh`
- `energy_total_cost`
- `energy_main_kwh`
- `energy_uv_kwh`
- `energy_ir_kwh`
- `energy_motor_kwh`
- `setup_minutes`
- `production_minutes`
- `planned_stop_minutes`
- `unplanned_stop_minutes`
- `maintenance_minutes`
- `idle_minutes`
- `good_qty`
- `scrap_qty`
- `actual_speed_per_hour`
- `team_leader`
- `team_size`
- `manpower`
- `hours_since_last_maintenance`
- `days_since_last_maintenance`
- `source_flags`
- `attribution_method`
- `setup_inference_method`
- `setup_confidence`

---

## 6. Canonical machine identity rules

### Rule 1 — Prefer one canonical machine per physical asset
Every source alias must resolve to exactly one `canonical_machine_id`.

### Rule 2 — Use production-recognizable canonical forms
For families like `024`, `035`, `166`, `256`, prefer the production-recognizable identity that best aligns CSI + Energy + maintenance crosswalk.

### Rule 3 — Preserve stable newer IDs when already dominant
For families already stable in production data, such as `1042`, `1099`, `1262`, `1264`, preserve the current form instead of forcing a legacy format.

### Rule 4 — Store exceptions explicitly
Known exceptions such as:
- `035-017`: prefer `1035-10005` over `1035-00017`
- `035-018`: prefer `1035-10007` over `1035-00018`

must be explicit in registry logic, not hidden inside ad hoc code.

---

## 7. Machine-hour state model

Formal state priority must be:

1. `maintenance`
2. `setup_changeover`
3. `production`
4. `planned_stop`
5. `unplanned_stop`
6. `idle`

### Why this matters
This project should not just show machine KPIs; it should explain **where the energy was consumed in operational terms**.

---

## 8. Setup inference logic

Raw CSI does not provide `準備開始時間`.
Therefore setup start must be inferred.

### Preferred inference
- `setup_start_ts = prep_end_ts - actual_changeover_minutes`

### Fallback order
1. use CSI refined or planned changeover durations;
2. then use MES `prep_hours`;
3. if inference is weak, still store the row but reduce `setup_confidence`.

### Mandatory metadata
Every inferred setup window must store:
- `setup_inference_method`
- `setup_confidence`
- optional `assumption_note`

---

## 9. Maintenance integration strategy

The current maintenance export should be treated as a **maintenance transaction log**, not yet as a full CMMS event log.

### Immediate FYP-safe uses
- enrich `machine_alias_registry`;
- compute maintenance type counts by machine;
- compute latest maintenance timestamp proxy;
- compute parts-consumption hotspots;
- derive maintenance-age context features.

### Avoid overclaiming
Do not claim this file alone provides exact failure labels or exact downtime windows.

---

## 10. ML scope after the rebuild

ML should be rebuilt only after `fact_machine_hour` is available.

### Keep
- contextual efficiency regression;
- machine opportunity ranking;
- excess-energy style flagging;
- ML-assisted recommendations.

### Avoid overclaiming
- no strong predictive-maintenance claim unless labels improve;
- no full scheduling optimizer claim;
- no strong financial ROI claim.

### Formal rule
All ML and optimization outputs must consume **canonical Gold-layer data only**.

---

## 11. Definition of done for the rebuild

The rebuild is considered successful when:

1. Apr / May / Jun sample files can be ingested into Bronze and normalized into Silver.
2. `machine_alias_registry` is loaded and used consistently in joins.
3. `fact_machine_hour` is built without synthetic fallback.
4. Energy attribution reconciles to total machine-hour energy.
5. App pages read from canonical layers instead of legacy ad hoc paths.
6. ML and recommendation pages consume `fact_machine_hour` only.
7. The final FYP story becomes defensible as:
   - real manufacturing ETL;
   - governed cross-system machine mapping;
   - canonical machine-hour operational truth;
   - ML-assisted decision support.
