# Canonical Schema v1

## Design principle
Use a **Bronze → Silver → Gold** contract.

- **Bronze** = raw Excel preservation
- **Silver** = canonicalized source-specific tables
- **Gold** = machine-hour fact table for analytics / ML

## 1) Bronze tables

### raw_energy_hourly
- source_file
- raw_area
- raw_timestamp
- raw_kwh
- raw_cost

### raw_csi_event
- source_file
- all raw CSI columns
- ingested_at

### raw_mes_report
- source_file
- all raw MES columns
- ingested_at

### raw_maintenance_txn
- source_file
- all raw maintenance columns
- ingested_at

## 2) Silver tables

### machine_alias_registry
- canonical_machine_id
- csi_machine_id
- mes_primary_resource
- mes_secondary_aliases
- maintenance_asset_id
- maintenance_legacy_id
- maintenance_asset_desc
- evidence_sources
- confidence
- notes

### energy_meter_hour
- canonical_machine_id
- meter_label
- meter_component
- meter_is_aggregate
- hour_ts
- kwh
- cost
- source_file
- parse_confidence

### csi_job_event
- canonical_machine_id
- shift_date
- shift_name
- csi_area
- order_id
- suffix
- operation
- material_code
- task_name
- prod_start_ts
- prep_end_ts
- prod_end_ts
- good_qty
- scrap_qty
- cumulative_qty
- actual_run_minutes
- actual_prod_minutes
- actual_speed_per_hour
- actual_changeover_minutes
- planned_stop_minutes
- unplanned_stop_minutes
- stop_reason
- stop_count
- engineer_leader
- team_members_raw
- source_file

### mes_report_event
- canonical_machine_id
- report_ts
- order_id
- suffix
- operation
- task_name
- material_code
- required_qty
- reported_qty
- cumulative_qty
- report_type
- equipment_total_hours
- prep_hours
- equipment_prod_hours
- manpower
- shift_name
- resource_id_raw
- csi_upload_status
- status_changed_ts
- record_created_ts
- source_file

### maintenance_txn_event
- canonical_machine_id
- txn_ts
- work_order_id
- work_order_desc
- work_order_type
- txn_type
- item_code
- item_desc
- quantity
- asset_id
- asset_legacy_id
- asset_parent_id
- asset_desc
- maint_team
- maint_department
- source_file

## 3) Gold table

### fact_machine_hour
- canonical_machine_id
- hour_ts
- machine_state
- state_confidence
- order_id
- material_code
- task_name
- energy_total_kwh
- energy_total_cost
- energy_main_kwh
- energy_uv_kwh
- energy_ir_kwh
- energy_motor_kwh
- setup_minutes
- production_minutes
- planned_stop_minutes
- unplanned_stop_minutes
- maintenance_minutes
- idle_minutes
- good_qty
- scrap_qty
- actual_speed_per_hour
- team_leader
- team_size
- manpower
- has_maintenance_history
- maintenance_txn_in_hour
- maintenance_distinct_work_order_count_7d
- maintenance_distinct_work_order_count_30d
- maintenance_distinct_work_order_in_hour_count
- cumulative_maintenance_count
- hours_since_last_maintenance
- days_since_last_maintenance
- source_flags
- attribution_method

## 4) State hierarchy for machine-hour attribution
Apply in this priority order:
1. maintenance
2. setup_changeover
3. production
4. planned_stop
5. unplanned_stop
6. idle

## 5) Critical inference rule
CSI raw files do not contain `準備開始時間`, so setup must be inferred.

Preferred logic:
- setup_start_ts = prep_end_ts - actual_changeover_minutes

Fallback order:
- use refined/planned changeover duration from CSI
- then use MES prep_hours
- always store:
  - setup_inference_method
  - setup_confidence
