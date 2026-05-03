import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.gold_fact_builder import GoldFactBuilder
from core.silver_normalizer import SilverNormalizer


class GoldFactBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "gold_test.db"
        self.silver_normalizer = SilverNormalizer(self.db_path)
        self.builder = GoldFactBuilder(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _insert_energy_meter_rows(self, rows):
        defaults = {
            "source_row_hash": None,
            "canonical_machine_id": None,
            "meter_label": None,
            "meter_component": None,
            "meter_is_aggregate": 0,
            "hour_ts": None,
            "kwh": None,
            "cost": None,
            "source_file": "data/june_energy.xlsx",
            "parse_confidence": "high",
            "raw_machine_id_or_label": None,
        }
        prepared_rows = []
        for index, row in enumerate(rows, 1):
            merged = dict(defaults)
            merged.update(row)
            if merged["source_row_hash"] is None:
                merged["source_row_hash"] = f"hash-{index}"
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO energy_meter_hour (
                source_row_hash, canonical_machine_id, meter_label, meter_component,
                meter_is_aggregate, hour_ts, kwh, cost, source_file,
                parse_confidence, raw_machine_id_or_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["source_row_hash"],
                    row["canonical_machine_id"],
                    row["meter_label"],
                    row["meter_component"],
                    row["meter_is_aggregate"],
                    row["hour_ts"],
                    row["kwh"],
                    row["cost"],
                    row["source_file"],
                    row["parse_confidence"],
                    row["raw_machine_id_or_label"],
                )
                for row in prepared_rows
            ],
        )
        conn.commit()
        conn.close()

    def _insert_fact_machine_hour_rows(self, rows):
        defaults = {
            "canonical_machine_id": None,
            "hour_ts": None,
            "machine_state": "energy_only",
            "state_confidence": "low",
            "energy_total_kwh": None,
            "energy_total_cost": None,
            "energy_main_kwh": None,
            "energy_uv_kwh": None,
            "energy_ir_kwh": None,
            "energy_motor_kwh": None,
            "source_flags": json.dumps({"has_energy": True}, sort_keys=True),
            "energy_total_source_method": "aggregate_total_preferred",
            "energy_source_row_count": 1,
            "energy_source_row_hashes_json": json.dumps(["energy-hash"], ensure_ascii=False),
            "order_id": None,
            "order_suffix": None,
            "material_code": None,
            "task_name": None,
            "setup_minutes": None,
            "production_minutes": None,
            "planned_stop_minutes": None,
            "unplanned_stop_minutes": None,
            "maintenance_minutes": None,
            "idle_minutes": None,
            "good_qty": None,
            "scrap_qty": None,
            "csi_qty_basis_method": None,
            "csi_qty_row_basis_minutes": None,
            "csi_qty_event_basis_minutes": None,
            "csi_qty_minutes_vs_production_diff": None,
            "csi_qty_minutes_vs_production_abs_diff": None,
            "csi_qty_alignment_status": None,
            "csi_qty_material_misalignment_flag": None,
            "csi_qty_minute_budget_anomaly_flag": None,
            "csi_qty_minute_budget_anomaly_reason": None,
            "actual_speed_per_hour": None,
            "team_leader": None,
            "csi_source_row_hash": None,
            "csi_overlap_minutes": None,
            "multiple_csi_overlap_flag": 0,
            "setup_inference_method": None,
            "setup_confidence": None,
            "mes_source_row_hash": None,
            "mes_report_ts": None,
            "mes_match_method": None,
            "mes_match_confidence": None,
            "last_maintenance_txn_ts": None,
            "last_maintenance_source_row_hash": None,
            "last_maintenance_work_order_type": None,
            "team_size": None,
            "manpower": None,
            "hours_since_last_maintenance": None,
            "days_since_last_maintenance": None,
            "attribution_method": "energy_only_projection",
        }
        prepared_rows = []
        for row in rows:
            merged = dict(defaults)
            merged.update(row)
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        columns = list(prepared_rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)
        cursor.executemany(
            f"INSERT INTO fact_machine_hour ({column_list}) VALUES ({placeholders})",
            [
                tuple(row[column] for column in columns)
                for row in prepared_rows
            ],
        )
        conn.commit()
        conn.close()

    def _insert_maintenance_txn_rows(self, rows):
        defaults = {
            "source_row_hash": None,
            "canonical_machine_id": None,
            "txn_ts": None,
            "work_order_id": None,
            "work_order_desc": None,
            "work_order_type": None,
            "txn_type": None,
            "item_code": None,
            "item_desc": None,
            "quantity": None,
            "asset_id": None,
            "asset_legacy_id": None,
            "asset_parent_id": None,
            "asset_desc": None,
            "maint_team": None,
            "maint_department": None,
            "source_file": "data/maintenance.xlsx",
        }
        prepared_rows = []
        for index, row in enumerate(rows, 1):
            merged = dict(defaults)
            merged.update(row)
            if merged["source_row_hash"] is None:
                merged["source_row_hash"] = f"maint-hash-{index}"
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO maintenance_txn_event (
                source_row_hash, canonical_machine_id, txn_ts, work_order_id,
                work_order_desc, work_order_type, txn_type, item_code, item_desc,
                quantity, asset_id, asset_legacy_id, asset_parent_id, asset_desc,
                maint_team, maint_department, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["source_row_hash"],
                    row["canonical_machine_id"],
                    row["txn_ts"],
                    row["work_order_id"],
                    row["work_order_desc"],
                    row["work_order_type"],
                    row["txn_type"],
                    row["item_code"],
                    row["item_desc"],
                    row["quantity"],
                    row["asset_id"],
                    row["asset_legacy_id"],
                    row["asset_parent_id"],
                    row["asset_desc"],
                    row["maint_team"],
                    row["maint_department"],
                    row["source_file"],
                )
                for row in prepared_rows
            ],
        )
        conn.commit()
        conn.close()

    def _insert_mes_report_rows(self, rows):
        defaults = {
            "source_row_hash": None,
            "canonical_machine_id": None,
            "report_ts": None,
            "order_id": None,
            "suffix": None,
            "operation": None,
            "task_name": None,
            "material_code": None,
            "required_qty": None,
            "reported_qty": None,
            "cumulative_qty": None,
            "report_type": None,
            "equipment_total_hours": None,
            "prep_hours": None,
            "equipment_prod_hours": None,
            "manpower": None,
            "shift_name": None,
            "resource_id_raw": None,
            "csi_upload_status": None,
            "status_changed_ts": None,
            "record_created_ts": None,
            "source_file": "data/june_mes.xlsx",
        }
        prepared_rows = []
        for index, row in enumerate(rows, 1):
            merged = dict(defaults)
            merged.update(row)
            if merged["source_row_hash"] is None:
                merged["source_row_hash"] = f"mes-hash-{index}"
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO mes_report_event (
                source_row_hash, canonical_machine_id, report_ts, order_id, suffix,
                operation, task_name, material_code, required_qty, reported_qty,
                cumulative_qty, report_type, equipment_total_hours, prep_hours,
                equipment_prod_hours, manpower, shift_name, resource_id_raw,
                csi_upload_status, status_changed_ts, record_created_ts, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["source_row_hash"],
                    row["canonical_machine_id"],
                    row["report_ts"],
                    row["order_id"],
                    row["suffix"],
                    row["operation"],
                    row["task_name"],
                    row["material_code"],
                    row["required_qty"],
                    row["reported_qty"],
                    row["cumulative_qty"],
                    row["report_type"],
                    row["equipment_total_hours"],
                    row["prep_hours"],
                    row["equipment_prod_hours"],
                    row["manpower"],
                    row["shift_name"],
                    row["resource_id_raw"],
                    row["csi_upload_status"],
                    row["status_changed_ts"],
                    row["record_created_ts"],
                    row["source_file"],
                )
                for row in prepared_rows
            ],
        )
        conn.commit()
        conn.close()

    def _insert_csi_job_rows(self, rows):
        defaults = {
            "source_row_hash": None,
            "canonical_machine_id": None,
            "shift_date": None,
            "shift_name": None,
            "csi_area": None,
            "order_id": None,
            "suffix": None,
            "operation": None,
            "material_code": None,
            "task_name": None,
            "prod_start_ts": None,
            "prep_end_ts": None,
            "prod_end_ts": None,
            "good_qty": None,
            "scrap_qty": None,
            "cumulative_qty": None,
            "actual_run_minutes": None,
            "actual_prod_minutes": None,
            "actual_speed_per_hour": None,
            "actual_changeover_minutes": None,
            "planned_stop_minutes": None,
            "unplanned_stop_minutes": None,
            "stop_reason": None,
            "stop_count": None,
            "team_leader": None,
            "team_members_raw": "[]",
            "source_file": "data/june_csi.xlsx",
            "raw_machine_id_or_label": None,
        }
        prepared_rows = []
        for index, row in enumerate(rows, 1):
            merged = dict(defaults)
            merged.update(row)
            if merged["source_row_hash"] is None:
                merged["source_row_hash"] = f"csi-hash-{index}"
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO csi_job_event (
                source_row_hash, canonical_machine_id, shift_date, shift_name,
                csi_area, order_id, suffix, operation, material_code, task_name,
                prod_start_ts, prep_end_ts, prod_end_ts, good_qty, scrap_qty,
                cumulative_qty, actual_run_minutes, actual_prod_minutes,
                actual_speed_per_hour, actual_changeover_minutes, planned_stop_minutes,
                unplanned_stop_minutes, stop_reason, stop_count, team_leader,
                team_members_raw, source_file, raw_machine_id_or_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["source_row_hash"],
                    row["canonical_machine_id"],
                    row["shift_date"],
                    row["shift_name"],
                    row["csi_area"],
                    row["order_id"],
                    row["suffix"],
                    row["operation"],
                    row["material_code"],
                    row["task_name"],
                    row["prod_start_ts"],
                    row["prep_end_ts"],
                    row["prod_end_ts"],
                    row["good_qty"],
                    row["scrap_qty"],
                    row["cumulative_qty"],
                    row["actual_run_minutes"],
                    row["actual_prod_minutes"],
                    row["actual_speed_per_hour"],
                    row["actual_changeover_minutes"],
                    row["planned_stop_minutes"],
                    row["unplanned_stop_minutes"],
                    row["stop_reason"],
                    row["stop_count"],
                    row["team_leader"],
                    row["team_members_raw"],
                    row["source_file"],
                    row["raw_machine_id_or_label"],
                )
                for row in prepared_rows
            ],
        )
        conn.commit()
        conn.close()

    def test_aggregate_total_is_preferred_over_component_sum(self):
        self._insert_energy_meter_rows(
            [
                {
                    "source_row_hash": "aggregate-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T01:00:00",
                    "meter_component": "aggregate_total",
                    "meter_is_aggregate": 1,
                    "kwh": 100.0,
                    "cost": 10.0,
                },
                {
                    "source_row_hash": "main-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T01:00:00",
                    "meter_component": "main",
                    "kwh": 60.0,
                    "cost": 6.0,
                },
                {
                    "source_row_hash": "uv-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T01:00:00",
                    "meter_component": "uv",
                    "kwh": 40.0,
                    "cost": 4.0,
                },
            ]
        )

        gold_df = self.builder.build_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(len(gold_df), 1)
        self.assertEqual(row["energy_total_source_method"], "aggregate_total_preferred")
        self.assertEqual(row["energy_total_kwh"], 100.0)
        self.assertEqual(row["energy_total_cost"], 10.0)
        self.assertEqual(row["energy_main_kwh"], 60.0)
        self.assertEqual(row["energy_uv_kwh"], 40.0)

    def test_component_sum_fallback_is_used_when_no_aggregate_total_exists(self):
        self._insert_energy_meter_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T02:00:00",
                    "meter_component": "main",
                    "kwh": 60.0,
                    "cost": 6.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T02:00:00",
                    "meter_component": "uv",
                    "kwh": 20.0,
                    "cost": 2.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T02:00:00",
                    "meter_component": "ir",
                    "kwh": 10.0,
                    "cost": 1.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T02:00:00",
                    "meter_component": "motor",
                    "kwh": 5.0,
                    "cost": 0.5,
                },
            ]
        )

        gold_df = self.builder.build_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["energy_total_source_method"], "component_sum_fallback")
        self.assertEqual(row["energy_total_kwh"], 95.0)
        self.assertEqual(row["energy_total_cost"], 9.5)
        self.assertEqual(row["energy_main_kwh"], 60.0)
        self.assertEqual(row["energy_uv_kwh"], 20.0)
        self.assertEqual(row["energy_ir_kwh"], 10.0)
        self.assertEqual(row["energy_motor_kwh"], 5.0)

    def test_combo_handling_is_explicit_and_does_not_double_count(self):
        self._insert_energy_meter_rows(
            [
                {
                    "source_row_hash": "combo-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T03:00:00",
                    "meter_component": "combo",
                    "meter_is_aggregate": 1,
                    "kwh": 70.0,
                    "cost": 7.0,
                },
                {
                    "source_row_hash": "main-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T03:00:00",
                    "meter_component": "main",
                    "kwh": 20.0,
                    "cost": 2.0,
                },
            ]
        )

        gold_df = self.builder.build_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["energy_total_source_method"], "component_sum_fallback")
        self.assertEqual(row["energy_total_kwh"], 20.0)
        self.assertEqual(row["energy_total_cost"], 2.0)
        self.assertEqual(row["energy_main_kwh"], 20.0)
        self.assertIsNone(row["energy_uv_kwh"])
        self.assertTrue(flags["has_combo_meter"])
        self.assertTrue(flags["combo_rows_excluded_from_total"])

    def test_rows_with_null_canonical_machine_id_do_not_enter_gold(self):
        self._insert_energy_meter_rows(
            [
                {
                    "canonical_machine_id": None,
                    "hour_ts": "2025-06-01T04:00:00",
                    "meter_component": "aggregate_total",
                    "meter_is_aggregate": 1,
                    "kwh": 100.0,
                    "cost": 10.0,
                }
            ]
        )

        gold_df = self.builder.build_fact_machine_hour()
        self.assertTrue(gold_df.empty)

    def test_gold_grain_is_one_row_per_machine_hour(self):
        self._insert_energy_meter_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T05:00:00",
                    "meter_component": "main",
                    "kwh": 30.0,
                    "cost": 3.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T05:00:00",
                    "meter_component": "uv",
                    "kwh": 10.0,
                    "cost": 1.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T06:00:00",
                    "meter_component": "aggregate_total",
                    "meter_is_aggregate": 1,
                    "kwh": 50.0,
                    "cost": 5.0,
                },
            ]
        )

        gold_df = self.builder.build_fact_machine_hour()

        self.assertEqual(len(gold_df), 2)
        self.assertEqual(
            set(zip(gold_df["canonical_machine_id"], gold_df["hour_ts"])),
            {
                ("024-018", "2025-06-01T05:00:00"),
                ("024-018", "2025-06-01T06:00:00"),
            },
        )

    def test_traceability_audit_fields_are_deterministic(self):
        self._insert_energy_meter_rows(
            [
                {
                    "source_row_hash": "b-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T07:00:00",
                    "meter_component": "main",
                    "kwh": 10.0,
                    "cost": 1.0,
                },
                {
                    "source_row_hash": "a-hash",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T07:00:00",
                    "meter_component": "uv",
                    "kwh": 5.0,
                    "cost": 0.5,
                },
            ]
        )

        gold_df = self.builder.build_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["energy_source_row_count"], 2)
        self.assertEqual(
            row["energy_source_row_hashes_json"],
            json.dumps(["a-hash", "b-hash"], ensure_ascii=False),
        )

    def test_csi_production_overlap_attribution(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                    "energy_total_cost": 10.0,
                    "energy_main_kwh": 60.0,
                    "energy_uv_kwh": 40.0,
                    "energy_source_row_hashes_json": json.dumps(["energy-a"], ensure_ascii=False),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-prod",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-100",
                    "material_code": "MAT-100",
                    "task_name": "印刷",
                    "prep_end_ts": "2025-06-01T09:50:00",
                    "prod_end_ts": "2025-06-01T10:30:00",
                    "actual_changeover_minutes": 15,
                    "actual_speed_per_hour": 12000.0,
                    "team_leader": "張展鵬",
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["machine_state"], "production")
        self.assertEqual(row["order_id"], "JOB-100")
        self.assertEqual(row["order_suffix"], None)
        self.assertEqual(row["material_code"], "MAT-100")
        self.assertEqual(row["task_name"], "印刷")
        self.assertEqual(row["team_leader"], "張展鵬")
        self.assertEqual(row["actual_speed_per_hour"], 12000.0)
        self.assertIsNone(row["setup_minutes"])
        self.assertEqual(row["production_minutes"], 30.0)
        self.assertEqual(row["csi_source_row_hash"], "csi-prod")
        self.assertEqual(row["csi_overlap_minutes"], 30.0)
        self.assertEqual(row["energy_total_kwh"], 100.0)
        self.assertEqual(row["energy_total_cost"], 10.0)

    def test_csi_setup_overlap_attribution(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 90.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-setup",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-200",
                    "material_code": "MAT-200",
                    "task_name": "轉版",
                    "prep_end_ts": "2025-06-01T10:20:00",
                    "prod_end_ts": "2025-06-01T10:20:00",
                    "actual_changeover_minutes": 20,
                    "actual_speed_per_hour": 0.0,
                    "team_leader": "李日晨",
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["machine_state"], "setup_changeover")
        self.assertEqual(row["setup_minutes"], 20.0)
        self.assertIsNone(row["production_minutes"])
        self.assertEqual(
            row["setup_inference_method"],
            "csi_prep_end_minus_actual_changeover_minutes",
        )
        self.assertEqual(row["setup_confidence"], "high")

    def test_csi_overlay_derives_team_size_from_team_roster(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 90.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-team-size",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-205",
                    "material_code": "MAT-205",
                    "task_name": "印刷",
                    "prep_end_ts": "2025-06-01T10:10:00",
                    "prod_end_ts": "2025-06-01T10:50:00",
                    "actual_changeover_minutes": 10,
                    "team_leader": "李日晨",
                    "team_members_raw": json.dumps(["組員甲", "組員乙"], ensure_ascii=False),
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["team_leader"], "李日晨")
        self.assertEqual(row["team_size"], 3.0)

    def test_dominant_event_selection(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-short",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-SHORT",
                    "material_code": "MAT-SHORT",
                    "task_name": "印刷",
                    "prep_end_ts": "2025-06-01T10:10:00",
                    "prod_end_ts": "2025-06-01T10:20:00",
                    "actual_changeover_minutes": 10,
                },
                {
                    "source_row_hash": "csi-long",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-LONG",
                    "material_code": "MAT-LONG",
                    "task_name": "印刷",
                    "prep_end_ts": "2025-06-01T10:05:00",
                    "prod_end_ts": "2025-06-01T10:50:00",
                    "actual_changeover_minutes": 5,
                },
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["order_id"], "JOB-LONG")
        self.assertEqual(row["csi_source_row_hash"], "csi-long")
        self.assertEqual(row["csi_overlap_minutes"], 50.0)

    def test_multi_event_overlap_flagging(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-a",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-A",
                    "prep_end_ts": "2025-06-01T10:05:00",
                    "prod_end_ts": "2025-06-01T10:15:00",
                    "actual_changeover_minutes": 5,
                },
                {
                    "source_row_hash": "csi-b",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-B",
                    "prep_end_ts": "2025-06-01T10:20:00",
                    "prod_end_ts": "2025-06-01T10:40:00",
                    "actual_changeover_minutes": 10,
                },
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["multiple_csi_overlap_flag"], 1)
        self.assertTrue(flags["multiple_csi_overlap_flag"])
        self.assertEqual(flags["csi_overlap_event_count"], 2)

    def test_multi_event_sequential_minutes_sum_within_coverage_budget(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-seq-a",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-A",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T10:25:00",
                    "actual_prod_minutes": 20.0,
                    "planned_stop_minutes": 5.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                },
                {
                    "source_row_hash": "csi-seq-b",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-B",
                    "prep_end_ts": "2025-06-01T10:25:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 15.0,
                    "planned_stop_minutes": 20.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                },
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["order_id"], "JOB-B")
        self.assertEqual(row["csi_source_row_hash"], "csi-seq-b")
        self.assertEqual(row["csi_overlap_minutes"], 60.0)
        self.assertEqual(row["production_minutes"], 35.0)
        self.assertEqual(row["planned_stop_minutes"], 25.0)
        self.assertEqual(row["machine_state"], "production")
        self.assertEqual(flags["csi_row_minute_contract"], "multi_event_sum_within_coverage_budget")
        self.assertFalse(flags["csi_row_competing_overlap"])
        self.assertEqual(flags["csi_row_minute_scale_factor"], 1.0)

    def test_multi_event_competing_minutes_are_scaled_to_coverage_budget(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-compete-a",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-A",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 60.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                },
                {
                    "source_row_hash": "csi-compete-b",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-B",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 60.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                },
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["csi_source_row_hash"], "csi-compete-a")
        self.assertEqual(row["csi_overlap_minutes"], 60.0)
        self.assertEqual(row["production_minutes"], 60.0)
        self.assertEqual(flags["csi_row_minute_contract"], "multi_event_sum_capped_to_coverage_budget")
        self.assertTrue(flags["csi_row_competing_overlap"])
        self.assertAlmostEqual(flags["csi_row_minute_scale_factor"], 0.5)

    def test_multi_event_tie_break_stays_deterministic_after_blending(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-tie-b",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-B",
                    "prep_end_ts": "2025-06-01T10:10:00",
                    "prod_end_ts": "2025-06-01T10:40:00",
                    "actual_prod_minutes": 30.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 10.0,
                },
                {
                    "source_row_hash": "csi-tie-a",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-A",
                    "prep_end_ts": "2025-06-01T10:10:00",
                    "prod_end_ts": "2025-06-01T10:40:00",
                    "actual_prod_minutes": 30.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 10.0,
                },
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["order_id"], "JOB-A")
        self.assertEqual(row["csi_source_row_hash"], "csi-tie-a")

    def test_multi_event_stop_minutes_can_coexist_after_blending(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-stop-a",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-A",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 0.0,
                    "planned_stop_minutes": 60.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                },
                {
                    "source_row_hash": "csi-stop-b",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-B",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 0.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 60.0,
                    "actual_changeover_minutes": 0.0,
                },
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["planned_stop_minutes"], 30.0)
        self.assertEqual(row["unplanned_stop_minutes"], 30.0)
        self.assertEqual(row["machine_state"], "planned_stop")

    def test_safe_null_behavior_when_no_csi_event_matches(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                    "machine_state": "energy_only",
                    "state_confidence": "low",
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["order_id"])
        self.assertIsNone(row["machine_state"])
        self.assertIsNone(row["state_confidence"])
        self.assertEqual(row["energy_total_kwh"], 100.0)
        self.assertFalse(flags["has_csi_overlap"])

    def test_existing_energy_fields_are_preserved_after_csi_overlay(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "energy_total_kwh": 88.0,
                    "energy_total_cost": 8.8,
                    "energy_main_kwh": 50.0,
                    "energy_uv_kwh": 20.0,
                    "energy_ir_kwh": 10.0,
                    "energy_motor_kwh": 8.0,
                    "energy_total_source_method": "component_sum_fallback",
                    "energy_source_row_count": 4,
                    "energy_source_row_hashes_json": json.dumps(
                        ["e1", "e2", "e3", "e4"], ensure_ascii=False
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-preserve",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-PRESERVE",
                    "prep_end_ts": "2025-06-01T11:00:00",
                    "prod_end_ts": "2025-06-01T11:30:00",
                    "actual_changeover_minutes": 10,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["energy_total_kwh"], 88.0)
        self.assertEqual(row["energy_total_cost"], 8.8)
        self.assertEqual(row["energy_main_kwh"], 50.0)
        self.assertEqual(row["energy_uv_kwh"], 20.0)
        self.assertEqual(row["energy_ir_kwh"], 10.0)
        self.assertEqual(row["energy_motor_kwh"], 8.0)
        self.assertEqual(row["energy_total_source_method"], "component_sum_fallback")
        self.assertEqual(row["energy_source_row_count"], 4)
        self.assertEqual(
            row["energy_source_row_hashes_json"],
            json.dumps(["e1", "e2", "e3", "e4"], ensure_ascii=False),
        )

    def test_csi_production_only_minutes_use_safe_fractional_reconciliation(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-safe-prod",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-SAFE",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 60.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["production_minutes"], 60.0)
        self.assertIsNone(row["planned_stop_minutes"])
        self.assertIsNone(row["unplanned_stop_minutes"])
        self.assertEqual(row["machine_state"], "production")
        self.assertEqual(flags["csi_minute_attribution_method"], "csi_fractional_minute_reconciliation")
        self.assertFalse(flags["csi_totals_exceed_window"])
        self.assertFalse(flags["csi_used_wall_clock_fallback"])

    def test_csi_planned_stop_minutes_are_allocated_when_reconciliation_is_safe(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-planned",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-PLANNED",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T12:00:00",
                    "actual_prod_minutes": 60.0,
                    "planned_stop_minutes": 60.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["production_minutes"], 30.0)
        self.assertEqual(row["planned_stop_minutes"], 30.0)
        self.assertIsNone(row["unplanned_stop_minutes"])
        self.assertEqual(row["machine_state"], "production")

    def test_csi_unplanned_stop_minutes_are_allocated_when_reconciliation_is_safe(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-unplanned",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-UNPLANNED",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 0.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 60.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertIsNone(row["production_minutes"])
        self.assertIsNone(row["planned_stop_minutes"])
        self.assertEqual(row["unplanned_stop_minutes"], 60.0)
        self.assertEqual(row["machine_state"], "unplanned_stop")

    def test_csi_safe_reconciliation_sums_back_to_source_minutes_across_hours(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 90.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "energy_total_kwh": 92.0,
                },
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-sum-safe",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-SUM",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T12:00:00",
                    "actual_prod_minutes": 90.0,
                    "planned_stop_minutes": 30.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour().sort_values("hour_ts")

        self.assertAlmostEqual(gold_df["production_minutes"].fillna(0).sum(), 90.0)
        self.assertAlmostEqual(gold_df["planned_stop_minutes"].fillna(0).sum(), 30.0)
        self.assertAlmostEqual(gold_df["unplanned_stop_minutes"].fillna(0).sum(), 0.0)

    def test_csi_totals_exceed_window_uses_wall_clock_fallback_and_marks_warning(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-exceed",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-EXCEED",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 50.0,
                    "planned_stop_minutes": 20.0,
                    "unplanned_stop_minutes": 10.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["production_minutes"], 60.0)
        self.assertIsNone(row["planned_stop_minutes"])
        self.assertIsNone(row["unplanned_stop_minutes"])
        self.assertEqual(flags["csi_minute_attribution_method"], "csi_wall_clock_overlap_fallback")
        self.assertEqual(
            flags["csi_minute_reconciliation_warning"],
            "csi_totals_exceed_window_tolerance",
        )
        self.assertTrue(flags["csi_totals_exceed_window"])
        self.assertTrue(flags["csi_used_wall_clock_fallback"])

    def test_csi_state_priority_prefers_setup_over_production_and_stop(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-priority-setup",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-PRIORITY",
                    "prep_end_ts": "2025-06-01T10:20:00",
                    "prod_end_ts": "2025-06-01T11:20:00",
                    "actual_prod_minutes": 40.0,
                    "planned_stop_minutes": 20.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 20.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["setup_minutes"], 20.0)
        self.assertEqual(row["production_minutes"], 26.666666666666664)
        self.assertEqual(row["planned_stop_minutes"], 13.333333333333332)
        self.assertEqual(row["machine_state"], "setup_changeover")

    def test_csi_state_priority_uses_planned_stop_before_unplanned_stop(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-priority-planned",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-STOP",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 0.0,
                    "planned_stop_minutes": 20.0,
                    "unplanned_stop_minutes": 10.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["planned_stop_minutes"], 20.0)
        self.assertEqual(row["unplanned_stop_minutes"], 10.0)
        self.assertEqual(row["machine_state"], "planned_stop")

    def test_mes_primary_match_uses_machine_order_and_suffix(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 88.0,
                    "order_id": "JOB-300",
                    "order_suffix": "02",
                    "material_code": "MAT-300",
                    "task_name": "印刷",
                    "team_leader": "張展鵬",
                    "setup_minutes": 10.0,
                    "production_minutes": 40.0,
                    "csi_source_row_hash": "csi-300",
                    "attribution_method": "energy_csi_overlay",
                }
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-match",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:58:00",
                    "order_id": "JOB-300",
                    "suffix": "02",
                    "manpower": 4.0,
                    "report_type": "完工",
                    "prep_hours": 0.3,
                    "resource_id_raw": "1024-00018",
                    "csi_upload_status": "已上傳",
                },
                {
                    "source_row_hash": "mes-wrong-suffix",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:59:00",
                    "order_id": "JOB-300",
                    "suffix": "03",
                    "manpower": 9.0,
                },
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["manpower"], 4.0)
        self.assertEqual(row["team_size"], 4.0)
        self.assertEqual(row["mes_source_row_hash"], "mes-match")
        self.assertEqual(row["mes_report_ts"], "2025-06-01T10:58:00")
        self.assertEqual(
            row["mes_match_method"],
            "canonical_order_suffix_same_date_prefer_positive_manpower_then_closest_hour_end",
        )
        self.assertEqual(row["mes_match_confidence"], "high")
        self.assertEqual(row["attribution_method"], "energy_csi_mes_overlay")
        self.assertEqual(row["order_id"], "JOB-300")
        self.assertEqual(row["order_suffix"], "02")
        self.assertEqual(row["material_code"], "MAT-300")
        self.assertEqual(row["task_name"], "印刷")
        self.assertEqual(row["team_leader"], "張展鵬")
        self.assertEqual(flags["mes_report_type"], "完工")
        self.assertEqual(flags["mes_csi_upload_status"], "已上傳")
        self.assertEqual(flags["mes_resource_id_raw"], "1024-00018")
        self.assertEqual(flags["mes_prep_hours_candidate"], 0.3)
        self.assertTrue(flags["mes_match_used_order_suffix"])

    def test_mes_suffix_matching_normalizes_excel_style_numeric_suffixes(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-300A",
                    "order_suffix": "1.0",
                    "attribution_method": "energy_csi_overlay",
                }
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-suffix-normalized",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:58:00",
                    "order_id": "JOB-300A",
                    "suffix": "1",
                    "manpower": 4.0,
                }
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["mes_source_row_hash"], "mes-suffix-normalized")
        self.assertEqual(row["manpower"], 4.0)

    def test_mes_candidate_selection_prefers_report_closest_to_hour_end(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-301",
                    "order_suffix": "01",
                    "attribution_method": "energy_csi_overlay",
                }
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-far",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:20:00",
                    "order_id": "JOB-301",
                    "suffix": "01",
                    "manpower": 2.0,
                },
                {
                    "source_row_hash": "mes-close",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:57:00",
                    "order_id": "JOB-301",
                    "suffix": "01",
                    "manpower": 3.0,
                },
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["mes_source_row_hash"], "mes-close")
        self.assertEqual(row["manpower"], 3.0)

    def test_mes_candidate_selection_prefers_positive_manpower_over_closer_zero_row(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-301B",
                    "order_suffix": "01",
                    "team_size": 2.0,
                    "attribution_method": "energy_csi_overlay",
                }
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-positive",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:20:00",
                    "order_id": "JOB-301B",
                    "suffix": "01",
                    "manpower": 3.0,
                },
                {
                    "source_row_hash": "mes-zero-closer",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:59:00",
                    "order_id": "JOB-301B",
                    "suffix": "01",
                    "manpower": 0.0,
                },
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["mes_source_row_hash"], "mes-positive")
        self.assertEqual(row["manpower"], 3.0)
        self.assertEqual(row["team_size"], 3.0)
        self.assertEqual(
            row["mes_match_method"],
            "canonical_order_suffix_same_date_prefer_positive_manpower_then_closest_hour_end",
        )

    def test_mes_safe_null_when_no_strong_job_identity_match_exists(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 77.0,
                    "order_id": "JOB-302",
                    "order_suffix": "01",
                    "material_code": "MAT-302",
                    "task_name": "印刷",
                    "team_leader": "李日晨",
                    "setup_minutes": 5.0,
                    "production_minutes": 45.0,
                    "csi_source_row_hash": "csi-302",
                    "attribution_method": "energy_csi_overlay",
                }
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-other-day",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-02T10:15:00",
                    "order_id": "JOB-302",
                    "suffix": "01",
                    "manpower": 6.0,
                },
                {
                    "source_row_hash": "mes-other-suffix",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:15:00",
                    "order_id": "JOB-302",
                    "suffix": "02",
                    "manpower": 7.0,
                },
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["manpower"])
        self.assertIsNone(row["mes_source_row_hash"])
        self.assertEqual(row["attribution_method"], "energy_csi_overlay")
        self.assertEqual(row["order_id"], "JOB-302")
        self.assertEqual(row["order_suffix"], "01")
        self.assertEqual(row["material_code"], "MAT-302")
        self.assertEqual(row["task_name"], "印刷")
        self.assertEqual(row["team_leader"], "李日晨")
        self.assertEqual(row["setup_minutes"], 5.0)
        self.assertEqual(row["production_minutes"], 45.0)
        self.assertFalse(flags["has_mes_match"])

    def test_mes_overlay_preserves_row_grain(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-401",
                    "order_suffix": "01",
                    "attribution_method": "energy_csi_overlay",
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "order_id": "JOB-402",
                    "order_suffix": "01",
                    "attribution_method": "energy_csi_overlay",
                },
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:55:00",
                    "order_id": "JOB-401",
                    "suffix": "01",
                    "manpower": 4.0,
                },
                {
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T11:55:00",
                    "order_id": "JOB-402",
                    "suffix": "01",
                    "manpower": 5.0,
                },
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()

        self.assertEqual(len(gold_df), 2)
        self.assertEqual(
            set(zip(gold_df["canonical_machine_id"], gold_df["hour_ts"])),
            {
                ("024-018", "2025-06-01T10:00:00"),
                ("024-018", "2025-06-01T11:00:00"),
            },
        )

    def test_mes_rerun_clears_stale_mes_fields_when_no_current_match_exists(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-500",
                    "order_suffix": "01",
                    "csi_source_row_hash": "csi-500",
                    "mes_source_row_hash": "stale-mes-hash",
                    "mes_report_ts": "2025-06-01T10:55:00",
                    "mes_match_method": "canonical_order_suffix_same_date_closest_hour_end",
                    "mes_match_confidence": "high",
                    "manpower": 5.0,
                    "attribution_method": "energy_csi_mes_overlay",
                    "source_flags": json.dumps(
                        {
                            "has_energy": True,
                            "has_mes_match": True,
                            "mes_match_candidate_count": 1,
                            "mes_report_type": "完工",
                            "mes_resource_id_raw": "1024-00018",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["mes_source_row_hash"])
        self.assertIsNone(row["mes_report_ts"])
        self.assertIsNone(row["mes_match_method"])
        self.assertIsNone(row["mes_match_confidence"])
        self.assertIsNone(row["manpower"])
        self.assertEqual(row["attribution_method"], "energy_csi_overlay")
        self.assertFalse(flags["has_mes_match"])
        self.assertEqual(flags["mes_match_candidate_count"], 0)
        self.assertNotIn("mes_report_type", flags)
        self.assertNotIn("mes_resource_id_raw", flags)

    def test_mes_rerun_restores_csi_team_size_when_mes_match_disappears(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 90.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-team-restore",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-510",
                    "suffix": "01",
                    "material_code": "MAT-510",
                    "task_name": "印刷",
                    "prep_end_ts": "2025-06-01T10:10:00",
                    "prod_end_ts": "2025-06-01T10:50:00",
                    "actual_changeover_minutes": 10,
                    "team_leader": "李日晨",
                    "team_members_raw": json.dumps(["組員甲", "組員乙"], ensure_ascii=False),
                }
            ]
        )

        csi_df = self.builder.overlay_csi_on_fact_machine_hour()
        self.assertEqual(csi_df.iloc[0]["team_size"], 3.0)

        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-team-override",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:58:00",
                    "order_id": "JOB-510",
                    "suffix": "01",
                    "manpower": 5.0,
                }
            ]
        )

        mes_df = self.builder.overlay_mes_on_fact_machine_hour()
        self.assertEqual(mes_df.iloc[0]["team_size"], 5.0)
        self.assertEqual(mes_df.iloc[0]["manpower"], 5.0)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM mes_report_event")
            conn.commit()
        finally:
            conn.close()

        rerun_df = self.builder.overlay_mes_on_fact_machine_hour()
        row = rerun_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["team_size"], 3.0)
        self.assertIsNone(row["manpower"])
        self.assertIsNone(row["mes_source_row_hash"])
        self.assertIsNone(row["mes_report_ts"])
        self.assertEqual(row["attribution_method"], "energy_csi_overlay")
        self.assertFalse(flags["has_mes_match"])
        self.assertEqual(flags["mes_match_candidate_count"], 0)

    def test_latest_prior_maintenance_is_selected_and_fields_are_preserved(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 88.0,
                    "energy_total_cost": 8.8,
                    "order_id": "JOB-600",
                    "order_suffix": "01",
                    "material_code": "MAT-600",
                    "task_name": "印刷",
                    "team_leader": "張展鵬",
                    "setup_minutes": 10.0,
                    "production_minutes": 40.0,
                    "csi_source_row_hash": "csi-600",
                    "csi_overlap_minutes": 50.0,
                    "mes_source_row_hash": "mes-600",
                    "mes_report_ts": "2025-06-01T10:58:00",
                    "mes_match_method": "canonical_order_suffix_same_date_closest_hour_end",
                    "mes_match_confidence": "high",
                    "team_size": 4.0,
                    "manpower": 4.0,
                    "attribution_method": "energy_csi_mes_overlay",
                }
            ]
        )
        self._insert_maintenance_txn_rows(
            [
                {
                    "source_row_hash": "maint-earlier",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-05-20T09:00:00",
                    "work_order_id": "WO-100",
                    "work_order_type": "PM",
                    "txn_type": "Issue",
                },
                {
                    "source_row_hash": "maint-latest",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T09:45:00",
                    "work_order_id": "WO-200",
                    "work_order_type": "Corrective",
                    "txn_type": "Return",
                },
                {
                    "source_row_hash": "maint-current-a",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T10:10:00",
                    "work_order_id": "WO-300",
                    "work_order_type": "Inspection",
                    "txn_type": "Issue",
                },
                {
                    "source_row_hash": "maint-current-b",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T10:20:00",
                    "work_order_id": "WO-300",
                    "work_order_type": "Inspection",
                    "txn_type": "Return",
                },
            ]
        )

        gold_df = self.builder.overlay_maintenance_context_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["last_maintenance_txn_ts"], "2025-06-01T09:45:00")
        self.assertEqual(row["last_maintenance_source_row_hash"], "maint-latest")
        self.assertEqual(row["last_maintenance_work_order_type"], "Corrective")
        self.assertEqual(row["hours_since_last_maintenance"], 0.25)
        self.assertEqual(row["days_since_last_maintenance"], 0.25 / 24.0)
        self.assertEqual(row["energy_total_kwh"], 88.0)
        self.assertEqual(row["energy_total_cost"], 8.8)
        self.assertEqual(row["order_id"], "JOB-600")
        self.assertEqual(row["order_suffix"], "01")
        self.assertEqual(row["material_code"], "MAT-600")
        self.assertEqual(row["task_name"], "印刷")
        self.assertEqual(row["team_leader"], "張展鵬")
        self.assertEqual(row["setup_minutes"], 10.0)
        self.assertEqual(row["production_minutes"], 40.0)
        self.assertEqual(row["csi_source_row_hash"], "csi-600")
        self.assertEqual(row["csi_overlap_minutes"], 50.0)
        self.assertEqual(row["mes_source_row_hash"], "mes-600")
        self.assertEqual(row["mes_report_ts"], "2025-06-01T10:58:00")
        self.assertEqual(
            row["mes_match_method"],
            "canonical_order_suffix_same_date_closest_hour_end",
        )
        self.assertEqual(row["mes_match_confidence"], "high")
        self.assertEqual(row["manpower"], 4.0)
        self.assertEqual(row["team_size"], 4.0)
        self.assertEqual(row["has_maintenance_history"], 1)
        self.assertEqual(row["maintenance_txn_in_hour"], 1)
        self.assertEqual(row["maintenance_distinct_work_order_count_30d"], 2)
        self.assertEqual(row["maintenance_distinct_work_order_count_7d"], 1)
        self.assertEqual(row["maintenance_distinct_work_order_in_hour_count"], 1)
        self.assertEqual(row["cumulative_maintenance_count"], 2)
        self.assertTrue(flags["has_maintenance_history"])
        self.assertTrue(flags["maintenance_txn_in_hour"])
        self.assertEqual(flags["maintenance_distinct_work_order_count_30d"], 2)
        self.assertEqual(flags["maintenance_distinct_work_order_count_7d"], 1)
        self.assertEqual(flags["maintenance_distinct_work_order_in_hour_count"], 1)
        self.assertEqual(flags["maintenance_last_work_order_type"], "Corrective")
        self.assertEqual(flags["maintenance_current_hour_work_order_types"], ["Inspection"])
        self.assertEqual(flags["maintenance_current_hour_txn_types"], ["Issue", "Return"])

    def test_same_hour_maintenance_does_not_leak_into_recency(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-601",
                    "order_suffix": "01",
                    "csi_source_row_hash": "csi-601",
                }
            ]
        )
        self._insert_maintenance_txn_rows(
            [
                {
                    "source_row_hash": "maint-current",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T10:05:00",
                    "work_order_id": "WO-400",
                    "work_order_type": "Inspection",
                    "txn_type": "Issue",
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_context_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["last_maintenance_txn_ts"])
        self.assertIsNone(row["hours_since_last_maintenance"])
        self.assertIsNone(row["days_since_last_maintenance"])
        self.assertEqual(row["has_maintenance_history"], 0)
        self.assertEqual(row["maintenance_txn_in_hour"], 1)
        self.assertEqual(row["maintenance_distinct_work_order_in_hour_count"], 1)
        self.assertEqual(row["cumulative_maintenance_count"], 0)
        self.assertFalse(flags["has_maintenance_history"])
        self.assertTrue(flags["maintenance_txn_in_hour"])
        self.assertEqual(flags["maintenance_distinct_work_order_in_hour_count"], 1)

    def test_future_and_other_machine_maintenance_are_ignored_for_recency(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-602",
                    "order_suffix": "01",
                }
            ]
        )
        self._insert_maintenance_txn_rows(
            [
                {
                    "source_row_hash": "maint-future",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T11:05:00",
                    "work_order_id": "WO-500",
                    "work_order_type": "PM",
                },
                {
                    "source_row_hash": "maint-other-machine",
                    "canonical_machine_id": "035-017",
                    "txn_ts": "2025-06-01T09:30:00",
                    "work_order_id": "WO-501",
                    "work_order_type": "Corrective",
                },
            ]
        )

        gold_df = self.builder.overlay_maintenance_context_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["last_maintenance_txn_ts"])
        self.assertIsNone(row["last_maintenance_source_row_hash"])
        self.assertIsNone(row["hours_since_last_maintenance"])
        self.assertEqual(row["has_maintenance_history"], 0)
        self.assertEqual(row["maintenance_txn_in_hour"], 0)
        self.assertEqual(row["cumulative_maintenance_count"], 0)
        self.assertFalse(flags["has_maintenance_history"])
        self.assertFalse(flags["maintenance_txn_in_hour"])

    def test_maintenance_distinct_work_order_count_prefers_ids_and_falls_back_to_row_count(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-10T10:00:00",
                }
            ]
        )
        self._insert_maintenance_txn_rows(
            [
                {
                    "source_row_hash": "maint-wo-1a",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-09T09:00:00",
                    "work_order_id": "WO-700",
                    "work_order_type": "PM",
                },
                {
                    "source_row_hash": "maint-wo-1b",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-09T09:30:00",
                    "work_order_id": "WO-700",
                    "work_order_type": "PM",
                },
                {
                    "source_row_hash": "maint-wo-2",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-08T10:00:00",
                    "work_order_id": "WO-701",
                    "work_order_type": "Corrective",
                },
                {
                    "source_row_hash": "maint-current-no-wo-a",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-10T10:10:00",
                    "work_order_id": None,
                    "work_order_type": "Inspection",
                },
                {
                    "source_row_hash": "maint-current-no-wo-b",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-10T10:20:00",
                    "work_order_id": None,
                    "work_order_type": "Inspection",
                },
            ]
        )

        gold_df = self.builder.overlay_maintenance_context_on_fact_machine_hour()
        flags = json.loads(gold_df.iloc[0]["source_flags"])

        self.assertEqual(flags["maintenance_distinct_work_order_count_30d"], 2)
        self.assertEqual(flags["maintenance_distinct_work_order_count_7d"], 2)
        self.assertEqual(flags["maintenance_distinct_work_order_in_hour_count"], 2)

    def test_maintenance_overlay_preserves_row_grain(self):
        self._insert_fact_machine_hour_rows(
            [
                {"canonical_machine_id": "024-018", "hour_ts": "2025-06-01T10:00:00"},
                {"canonical_machine_id": "024-018", "hour_ts": "2025-06-01T11:00:00"},
            ]
        )
        self._insert_maintenance_txn_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T09:00:00",
                    "work_order_id": "WO-900",
                    "work_order_type": "PM",
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_context_on_fact_machine_hour()

        self.assertEqual(len(gold_df), 2)
        self.assertEqual(
            set(zip(gold_df["canonical_machine_id"], gold_df["hour_ts"])),
            {
                ("024-018", "2025-06-01T10:00:00"),
                ("024-018", "2025-06-01T11:00:00"),
            },
        )

    def test_full_gold_path_preserves_mes_and_maintenance_fields_after_csi_refinement(self):
        self._insert_energy_meter_rows(
            [
                {
                    "source_row_hash": "energy-full-path",
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "meter_component": "aggregate_total",
                    "meter_is_aggregate": 1,
                    "kwh": 100.0,
                    "cost": 10.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-full-path",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-FULL",
                    "suffix": "01",
                    "material_code": "MAT-FULL",
                    "task_name": "印刷",
                    "team_leader": "張展鵬",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 50.0,
                    "planned_stop_minutes": 10.0,
                    "unplanned_stop_minutes": 0.0,
                    "actual_changeover_minutes": 0.0,
                }
            ]
        )
        self._insert_mes_report_rows(
            [
                {
                    "source_row_hash": "mes-full-path",
                    "canonical_machine_id": "024-018",
                    "report_ts": "2025-06-01T10:55:00",
                    "order_id": "JOB-FULL",
                    "suffix": "01",
                    "manpower": 4.0,
                }
            ]
        )
        self._insert_maintenance_txn_rows(
            [
                {
                    "source_row_hash": "maint-full-path",
                    "canonical_machine_id": "024-018",
                    "txn_ts": "2025-06-01T09:30:00",
                    "work_order_id": "WO-FULL",
                    "work_order_type": "PM",
                }
            ]
        )

        self.builder.build_fact_machine_hour()
        self.builder.overlay_csi_on_fact_machine_hour()
        self.builder.overlay_mes_on_fact_machine_hour()
        gold_df = self.builder.overlay_maintenance_context_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["energy_total_kwh"], 100.0)
        self.assertEqual(row["order_id"], "JOB-FULL")
        self.assertEqual(row["order_suffix"], "01")
        self.assertEqual(row["material_code"], "MAT-FULL")
        self.assertEqual(row["task_name"], "印刷")
        self.assertEqual(row["team_leader"], "張展鵬")
        self.assertEqual(row["production_minutes"], 50.0)
        self.assertEqual(row["planned_stop_minutes"], 10.0)
        self.assertEqual(row["mes_source_row_hash"], "mes-full-path")
        self.assertEqual(row["mes_report_ts"], "2025-06-01T10:55:00")
        self.assertEqual(
            row["mes_match_method"],
            "canonical_order_suffix_same_date_prefer_positive_manpower_then_closest_hour_end",
        )
        self.assertEqual(row["mes_match_confidence"], "high")
        self.assertEqual(row["manpower"], 4.0)
        self.assertEqual(row["team_size"], 4.0)
        self.assertEqual(row["last_maintenance_source_row_hash"], "maint-full-path")
        self.assertEqual(row["last_maintenance_work_order_type"], "PM")
        self.assertEqual(row["cumulative_maintenance_count"], 1)

    def test_csi_good_qty_allocation_sums_back_to_event_total_across_hours(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "csi_source_row_hash": "csi-qty-good",
                    "production_minutes": 20.0,
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "csi_source_row_hash": "csi-qty-good",
                    "production_minutes": 40.0,
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                },
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-qty-good",
                    "canonical_machine_id": "024-018",
                    "good_qty": 180.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour().sort_values("hour_ts")
        flags = [json.loads(flag) for flag in gold_df["source_flags"]]

        self.assertAlmostEqual(gold_df["good_qty"].sum(), 180.0)
        self.assertAlmostEqual(gold_df.iloc[0]["good_qty"], 60.0)
        self.assertAlmostEqual(gold_df.iloc[1]["good_qty"], 120.0)
        self.assertTrue(gold_df["scrap_qty"].isna().all())
        self.assertEqual(flags[0]["csi_qty_allocation_method"], "csi_production_minutes_share_by_dominant_event")
        self.assertEqual(flags[0]["csi_qty_allocation_confidence"], "high")
        self.assertEqual(flags[0]["csi_qty_basis_minutes"], 60.0)
        self.assertEqual(flags[0]["csi_qty_source_row_hash"], "csi-qty-good")
        self.assertEqual(flags[0]["csi_qty_allocation_warning"], "csi_qty_missing_scrap_qty")
        self.assertEqual(gold_df.iloc[0]["csi_qty_basis_method"], "csi_dominant_event_production_minutes_share")
        self.assertEqual(gold_df.iloc[0]["csi_qty_row_basis_minutes"], 20.0)
        self.assertEqual(gold_df.iloc[0]["csi_qty_event_basis_minutes"], 60.0)
        self.assertEqual(gold_df.iloc[0]["csi_qty_minutes_vs_production_diff"], 0.0)
        self.assertEqual(gold_df.iloc[0]["csi_qty_minutes_vs_production_abs_diff"], 0.0)
        self.assertEqual(gold_df.iloc[0]["csi_qty_alignment_status"], "aligned")
        self.assertEqual(gold_df.iloc[0]["csi_qty_material_misalignment_flag"], 0)
        self.assertEqual(gold_df.iloc[0]["csi_qty_minute_budget_anomaly_flag"], 0)
        self.assertIsNone(gold_df.iloc[0]["csi_qty_minute_budget_anomaly_reason"])

    def test_csi_scrap_qty_allocation_sums_back_to_event_total_across_hours(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "csi_source_row_hash": "csi-qty-scrap",
                    "production_minutes": 15.0,
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_wall_clock_overlap_fallback"},
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "csi_source_row_hash": "csi-qty-scrap",
                    "production_minutes": 45.0,
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_wall_clock_overlap_fallback"},
                        sort_keys=True,
                    ),
                },
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-qty-scrap",
                    "canonical_machine_id": "024-018",
                    "scrap_qty": 12.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour().sort_values("hour_ts")
        flags = [json.loads(flag) for flag in gold_df["source_flags"]]

        self.assertAlmostEqual(gold_df["scrap_qty"].sum(), 12.0)
        self.assertAlmostEqual(gold_df.iloc[0]["scrap_qty"], 3.0)
        self.assertAlmostEqual(gold_df.iloc[1]["scrap_qty"], 9.0)
        self.assertTrue(gold_df["good_qty"].isna().all())
        self.assertEqual(flags[0]["csi_qty_allocation_confidence"], "medium")
        self.assertEqual(flags[0]["csi_qty_allocation_warning"], "csi_qty_missing_good_qty")

    def test_mixed_setup_and_production_hour_still_receives_quantity(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "setup_changeover",
                    "setup_minutes": 25.0,
                    "production_minutes": 15.0,
                    "csi_source_row_hash": "csi-mixed-hour",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "machine_state": "production",
                    "production_minutes": 45.0,
                    "csi_source_row_hash": "csi-mixed-hour",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                },
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-mixed-hour",
                    "canonical_machine_id": "024-018",
                    "good_qty": 120.0,
                    "scrap_qty": 6.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour().sort_values("hour_ts")

        self.assertAlmostEqual(gold_df.iloc[0]["good_qty"], 30.0)
        self.assertAlmostEqual(gold_df.iloc[0]["scrap_qty"], 1.5)
        self.assertEqual(gold_df.iloc[0]["machine_state"], "setup_changeover")

    def test_multi_event_blended_minutes_do_not_rewrite_dominant_event_quantity_basis(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "energy_total_kwh": 100.0,
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "a-dominant",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-A",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 20.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "good_qty": 100.0,
                    "scrap_qty": 5.0,
                    "actual_changeover_minutes": 0.0,
                },
                {
                    "source_row_hash": "z-other",
                    "canonical_machine_id": "024-018",
                    "order_id": "JOB-B",
                    "prep_end_ts": "2025-06-01T10:00:00",
                    "prod_end_ts": "2025-06-01T11:00:00",
                    "actual_prod_minutes": 60.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "good_qty": 999.0,
                    "scrap_qty": 99.0,
                    "actual_changeover_minutes": 0.0,
                },
            ]
        )

        self.builder.overlay_csi_on_fact_machine_hour()
        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["csi_source_row_hash"], "a-dominant")
        self.assertEqual(row["production_minutes"], 60.0)
        self.assertEqual(row["good_qty"], 100.0)
        self.assertEqual(row["scrap_qty"], 5.0)
        self.assertEqual(flags["csi_qty_basis_minutes"], 20.0)
        self.assertEqual(row["csi_qty_basis_method"], "csi_dominant_event_production_minutes_share")
        self.assertEqual(row["csi_qty_row_basis_minutes"], 20.0)
        self.assertEqual(row["csi_qty_event_basis_minutes"], 20.0)
        self.assertEqual(row["csi_qty_minutes_vs_production_diff"], 40.0)
        self.assertEqual(row["csi_qty_minutes_vs_production_abs_diff"], 40.0)
        self.assertEqual(row["csi_qty_alignment_status"], "material_misaligned")
        self.assertEqual(row["csi_qty_material_misalignment_flag"], 1)
        self.assertEqual(row["csi_qty_minute_budget_anomaly_flag"], 0)
        self.assertIsNone(row["csi_qty_minute_budget_anomaly_reason"])

    def test_overlap_quantity_audit_reconstructs_missing_basis_from_dominant_source_flags(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 33.0,
                    "good_qty": 999.0,
                    "scrap_qty": 99.0,
                    "csi_source_row_hash": "csi-reconstruct",
                    "multiple_csi_overlap_flag": 1,
                    "source_flags": json.dumps(
                        {
                            "dominant_csi_source_row_hash": "csi-reconstruct",
                            "csi_dominant_production_minutes": 18.0,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-reconstruct",
                    "canonical_machine_id": "024-018",
                    "good_qty": 120.0,
                    "scrap_qty": 6.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 120.0)
        self.assertEqual(row["scrap_qty"], 6.0)
        self.assertEqual(row["csi_qty_basis_method"], "csi_dominant_event_production_minutes_share")
        self.assertEqual(row["csi_qty_row_basis_minutes"], 18.0)
        self.assertEqual(row["csi_qty_event_basis_minutes"], 18.0)
        self.assertEqual(row["csi_qty_minutes_vs_production_diff"], 15.0)
        self.assertEqual(row["csi_qty_minutes_vs_production_abs_diff"], 15.0)
        self.assertEqual(row["csi_qty_alignment_status"], "material_misaligned")
        self.assertEqual(row["csi_qty_material_misalignment_flag"], 1)
        self.assertEqual(row["csi_qty_minute_budget_anomaly_flag"], 0)
        self.assertIsNone(row["csi_qty_minute_budget_anomaly_reason"])

    def test_overlap_quantity_audit_blocks_source_flag_reconstruction_on_dominant_hash_conflict(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 33.0,
                    "good_qty": 999.0,
                    "scrap_qty": 99.0,
                    "csi_source_row_hash": "csi-conflict-row",
                    "multiple_csi_overlap_flag": 1,
                    "source_flags": json.dumps(
                        {
                            "dominant_csi_source_row_hash": "different-dominant-hash",
                            "csi_dominant_production_minutes": 18.0,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-conflict-row",
                    "canonical_machine_id": "024-018",
                    "good_qty": 120.0,
                    "scrap_qty": 6.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 120.0)
        self.assertEqual(row["scrap_qty"], 6.0)
        self.assertIsNone(row["csi_qty_row_basis_minutes"])
        self.assertIsNone(row["csi_qty_event_basis_minutes"])
        self.assertEqual(row["csi_qty_alignment_status"], "missing_positive_row_basis_minutes")
        self.assertEqual(row["csi_qty_material_misalignment_flag"], 0)
        self.assertEqual(row["csi_qty_minute_budget_anomaly_flag"], 0)

    def test_overlap_quantity_audit_leaves_missing_basis_null_without_dominant_evidence(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 12.0,
                    "csi_source_row_hash": "csi-no-reconstruct",
                    "multiple_csi_overlap_flag": 1,
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_wall_clock_overlap_fallback"},
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-no-reconstruct",
                    "canonical_machine_id": "024-018",
                    "good_qty": 90.0,
                    "scrap_qty": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 90.0)
        self.assertEqual(row["scrap_qty"], 0.0)
        self.assertIsNone(row["csi_qty_row_basis_minutes"])
        self.assertIsNone(row["csi_qty_event_basis_minutes"])
        self.assertEqual(row["csi_qty_alignment_status"], "missing_positive_row_basis_minutes")
        self.assertEqual(row["csi_qty_material_misalignment_flag"], 0)
        self.assertEqual(row["csi_qty_minute_budget_anomaly_flag"], 0)

    def test_overlap_quantity_audit_excludes_anomaly_rows_from_basis_reconstruction(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 65.0,
                    "csi_source_row_hash": "csi-anomaly",
                    "multiple_csi_overlap_flag": 1,
                    "source_flags": json.dumps(
                        {
                            "csi_dominant_production_minutes": 20.0,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-anomaly",
                    "canonical_machine_id": "024-018",
                    "good_qty": 50.0,
                    "scrap_qty": 2.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 50.0)
        self.assertEqual(row["scrap_qty"], 2.0)
        self.assertIsNone(row["csi_qty_row_basis_minutes"])
        self.assertIsNone(row["csi_qty_event_basis_minutes"])
        self.assertEqual(row["csi_qty_alignment_status"], "missing_positive_row_basis_minutes")
        self.assertEqual(row["csi_qty_minute_budget_anomaly_flag"], 1)
        self.assertEqual(row["csi_qty_minute_budget_anomaly_reason"], "production_minutes_gt_60")

    def test_overlap_quantity_audit_preserves_existing_valid_landed_basis(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-preserve-basis",
                    "multiple_csi_overlap_flag": 1,
                    "csi_qty_row_basis_minutes": 12.0,
                    "source_flags": json.dumps(
                        {
                            "csi_dominant_production_minutes": 12.0,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-preserve-basis",
                    "canonical_machine_id": "024-018",
                    "good_qty": 60.0,
                    "scrap_qty": 3.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 60.0)
        self.assertEqual(row["scrap_qty"], 3.0)
        self.assertEqual(row["csi_qty_row_basis_minutes"], 12.0)
        self.assertEqual(row["csi_qty_event_basis_minutes"], 12.0)
        self.assertEqual(row["csi_qty_minutes_vs_production_diff"], 18.0)
        self.assertEqual(row["csi_qty_alignment_status"], "material_misaligned")

    def test_explicit_zero_good_qty_is_preserved_as_zero(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-zero-good",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-zero-good",
                    "canonical_machine_id": "024-018",
                    "good_qty": 0.0,
                    "scrap_qty": 5.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 0.0)
        self.assertEqual(row["scrap_qty"], 5.0)

    def test_explicit_zero_scrap_qty_is_preserved_as_zero(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-zero-scrap",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-zero-scrap",
                    "canonical_machine_id": "024-018",
                    "good_qty": 9.0,
                    "scrap_qty": 0.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 9.0)
        self.assertEqual(row["scrap_qty"], 0.0)

    def test_missing_quantity_stays_null(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-missing-qty",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-missing-qty",
                    "canonical_machine_id": "024-018",
                    "good_qty": None,
                    "scrap_qty": None,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["good_qty"])
        self.assertIsNone(row["scrap_qty"])
        self.assertIsNone(flags["csi_qty_allocation_method"])
        self.assertEqual(flags["csi_qty_allocation_warning"], "csi_qty_missing_all")

    def test_no_production_minutes_means_no_quantity_allocation(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "planned_stop",
                    "planned_stop_minutes": 25.0,
                    "production_minutes": None,
                    "csi_source_row_hash": "csi-no-prod",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_wall_clock_overlap_fallback"},
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-no-prod",
                    "canonical_machine_id": "024-018",
                    "good_qty": 20.0,
                    "scrap_qty": 1.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["good_qty"])
        self.assertIsNone(row["scrap_qty"])
        self.assertEqual(flags["csi_qty_allocation_warning"], "csi_qty_no_positive_production_minutes")

    def test_csi_quantity_rerun_clears_stale_values_and_flags(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "good_qty": 99.0,
                    "scrap_qty": 7.0,
                    "production_minutes": None,
                    "csi_source_row_hash": None,
                    "source_flags": json.dumps(
                        {
                            "csi_qty_allocation_method": "stale_method",
                            "csi_qty_allocation_confidence": "high",
                            "csi_qty_source_row_hash": "stale-hash",
                            "csi_qty_basis_minutes": 12.0,
                            "csi_qty_allocation_warning": "stale_warning",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["good_qty"])
        self.assertIsNone(row["scrap_qty"])
        self.assertIsNone(flags["csi_qty_allocation_method"])
        self.assertIsNone(flags["csi_qty_source_row_hash"])
        self.assertEqual(flags["csi_qty_allocation_warning"], "csi_qty_missing_source_row_hash")

    def test_csi_quantity_overlay_preserves_mes_and_maintenance_fields(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "order_id": "JOB-700",
                    "order_suffix": "01",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-qty-preserve",
                    "mes_source_row_hash": "mes-700",
                    "mes_report_ts": "2025-06-01T10:55:00",
                    "mes_match_method": "canonical_order_suffix_same_date_closest_hour_end",
                    "mes_match_confidence": "high",
                    "manpower": 4.0,
                    "last_maintenance_txn_ts": "2025-06-01T09:30:00",
                    "last_maintenance_source_row_hash": "maint-700",
                    "last_maintenance_work_order_type": "PM",
                    "hours_since_last_maintenance": 0.5,
                    "days_since_last_maintenance": 0.5 / 24.0,
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                }
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-qty-preserve",
                    "canonical_machine_id": "024-018",
                    "good_qty": 30.0,
                    "scrap_qty": 3.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["good_qty"], 30.0)
        self.assertEqual(row["scrap_qty"], 3.0)
        self.assertEqual(row["mes_source_row_hash"], "mes-700")
        self.assertEqual(row["mes_report_ts"], "2025-06-01T10:55:00")
        self.assertEqual(row["mes_match_method"], "canonical_order_suffix_same_date_closest_hour_end")
        self.assertEqual(row["mes_match_confidence"], "high")
        self.assertEqual(row["manpower"], 4.0)
        self.assertEqual(row["last_maintenance_source_row_hash"], "maint-700")
        self.assertEqual(row["last_maintenance_work_order_type"], "PM")

    def test_csi_quantity_overlay_preserves_gold_row_grain_and_deterministic_flags(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 20.0,
                    "csi_source_row_hash": "csi-qty-grain",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "production_minutes": 40.0,
                    "csi_source_row_hash": "csi-qty-grain",
                    "source_flags": json.dumps(
                        {"csi_minute_attribution_method": "csi_fractional_minute_reconciliation"},
                        sort_keys=True,
                    ),
                },
            ]
        )
        self._insert_csi_job_rows(
            [
                {
                    "source_row_hash": "csi-qty-grain",
                    "canonical_machine_id": "024-018",
                    "good_qty": 60.0,
                    "scrap_qty": 6.0,
                }
            ]
        )

        gold_df = self.builder.overlay_csi_quantity_on_fact_machine_hour().sort_values("hour_ts")
        flags = [json.loads(flag) for flag in gold_df["source_flags"]]

        self.assertEqual(len(gold_df), 2)
        self.assertEqual(
            set(zip(gold_df["canonical_machine_id"], gold_df["hour_ts"])),
            {
                ("024-018", "2025-06-01T10:00:00"),
                ("024-018", "2025-06-01T11:00:00"),
            },
        )
        self.assertEqual(
            gold_df.iloc[0]["source_flags"],
            json.dumps(
                {
                    "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                    "csi_qty_allocation_confidence": "high",
                    "csi_qty_allocation_method": "csi_production_minutes_share_by_dominant_event",
                    "csi_qty_allocation_warning": None,
                    "csi_qty_basis_minutes": 60.0,
                    "csi_qty_source_row_hash": "csi-qty-grain",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        self.assertEqual(flags[1]["csi_qty_basis_minutes"], 60.0)

    def test_idle_is_assigned_for_full_hour_fractional_csi_with_positive_residual(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "setup_minutes": None,
                    "production_minutes": 50.0,
                    "planned_stop_minutes": None,
                    "unplanned_stop_minutes": None,
                    "csi_source_row_hash": "csi-idle-positive",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["idle_minutes"], 10.0)
        self.assertIsNone(row["machine_state"])
        self.assertEqual(flags["idle_attribution_method"], "residual_minutes_after_fractional_csi_full_hour_coverage")
        self.assertEqual(flags["idle_match_confidence"], "high")
        self.assertTrue(flags["idle_full_hour_csi_coverage"])
        self.assertEqual(flags["idle_assigned_minutes_basis"], 50.0)
        self.assertIsNone(flags["idle_attribution_warning"])
        self.assertIsNone(flags["idle_skipped_reason"])

    def test_idle_state_is_used_when_positive_idle_exists_without_higher_priority_minutes(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "setup_minutes": None,
                    "production_minutes": None,
                    "planned_stop_minutes": None,
                    "unplanned_stop_minutes": None,
                    "csi_source_row_hash": "csi-idle-state",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["idle_minutes"], 60.0)
        self.assertEqual(row["machine_state"], "idle")
        self.assertEqual(row["state_confidence"], "high")

    def test_idle_zero_residual_does_not_create_false_idle_state(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "production_minutes": 60.0,
                    "csi_source_row_hash": "csi-idle-zero",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["idle_minutes"], 0.0)
        self.assertIsNone(row["machine_state"])

    def test_idle_is_skipped_for_partial_csi_coverage(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-idle-partial",
                    "csi_overlap_minutes": 45.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["idle_minutes"])
        self.assertEqual(flags["idle_skipped_reason"], "idle_partial_csi_coverage")
        self.assertFalse(flags["idle_full_hour_csi_coverage"])

    def test_idle_is_skipped_for_wall_clock_fallback_rows(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-idle-fallback",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": False,
                            "csi_minute_attribution_method": "csi_wall_clock_overlap_fallback",
                            "csi_totals_exceed_window": True,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        flags = json.loads(gold_df.iloc[0]["source_flags"])

        self.assertIsNone(gold_df.iloc[0]["idle_minutes"])
        self.assertEqual(flags["idle_skipped_reason"], "idle_non_fractional_csi_minutes")

    def test_idle_is_assigned_for_full_hour_multi_overlap_when_all_minutes_are_fractional(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 40.0,
                    "csi_source_row_hash": "csi-idle-multi",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 1,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        flags = json.loads(gold_df.iloc[0]["source_flags"])

        self.assertEqual(gold_df.iloc[0]["idle_minutes"], 20.0)
        self.assertIsNone(flags["idle_skipped_reason"])

    def test_idle_is_skipped_for_same_hour_maintenance(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-idle-maint",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": True,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        flags = json.loads(gold_df.iloc[0]["source_flags"])

        self.assertIsNone(gold_df.iloc[0]["idle_minutes"])
        self.assertEqual(flags["idle_skipped_reason"], "idle_same_hour_maintenance")

    def test_idle_rerun_clears_stale_idle_fields_and_state(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "idle",
                    "state_confidence": "high",
                    "idle_minutes": 12.0,
                    "csi_source_row_hash": None,
                    "source_flags": json.dumps(
                        {
                            "idle_attribution_method": "residual_minutes_after_fractional_csi_full_hour_coverage",
                            "idle_match_confidence": "high",
                            "idle_full_hour_csi_coverage": True,
                            "idle_assigned_minutes_basis": 48.0,
                            "idle_attribution_warning": None,
                            "idle_skipped_reason": None,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["idle_minutes"])
        self.assertIsNone(row["machine_state"])
        self.assertIsNone(row["state_confidence"])
        self.assertEqual(flags["idle_skipped_reason"], "idle_missing_csi_source")
        self.assertIsNone(flags["idle_attribution_method"])

    def test_idle_keeps_higher_priority_setup_over_idle(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "setup_changeover",
                    "state_confidence": "high",
                    "setup_minutes": 10.0,
                    "production_minutes": 20.0,
                    "planned_stop_minutes": 10.0,
                    "unplanned_stop_minutes": 0.0,
                    "csi_source_row_hash": "csi-idle-priority",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "good_qty": 100.0,
                    "scrap_qty": 2.0,
                    "mes_source_row_hash": "mes-keep",
                    "mes_report_ts": "2025-06-01T10:55:00",
                    "mes_match_method": "canonical_order_suffix_same_date_closest_hour_end",
                    "mes_match_confidence": "high",
                    "manpower": 4.0,
                    "last_maintenance_source_row_hash": "maint-keep",
                    "last_maintenance_work_order_type": "PM",
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["idle_minutes"], 20.0)
        self.assertEqual(row["machine_state"], "setup_changeover")
        self.assertEqual(row["good_qty"], 100.0)
        self.assertEqual(row["scrap_qty"], 2.0)
        self.assertEqual(row["mes_source_row_hash"], "mes-keep")
        self.assertEqual(row["last_maintenance_source_row_hash"], "maint-keep")

    def test_idle_negative_residual_sets_warning_without_forcing_negative_idle(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "setup_minutes": 25.0,
                    "production_minutes": 25.0,
                    "planned_stop_minutes": 15.0,
                    "unplanned_stop_minutes": 5.0,
                    "csi_source_row_hash": "csi-idle-negative",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["idle_minutes"])
        self.assertEqual(flags["idle_attribution_warning"], "idle_negative_residual")
        self.assertEqual(flags["idle_skipped_reason"], "idle_negative_residual")

    def test_idle_overlay_preserves_row_grain_and_deterministic_flags(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "production_minutes": 50.0,
                    "csi_source_row_hash": "csi-idle-grain-a",
                    "csi_overlap_minutes": 60.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "production_minutes": 30.0,
                    "csi_source_row_hash": "csi-idle-grain-b",
                    "csi_overlap_minutes": 30.0,
                    "multiple_csi_overlap_flag": 0,
                    "source_flags": json.dumps(
                        {
                            "csi_all_minutes_fractional": True,
                            "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                            "csi_totals_exceed_window": False,
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                },
            ]
        )

        gold_df = self.builder.overlay_idle_on_fact_machine_hour().sort_values("hour_ts")
        row_a = gold_df.iloc[0]
        row_b = gold_df.iloc[1]

        self.assertEqual(len(gold_df), 2)
        self.assertEqual(
            set(zip(gold_df["canonical_machine_id"], gold_df["hour_ts"])),
            {
                ("024-018", "2025-06-01T10:00:00"),
                ("024-018", "2025-06-01T11:00:00"),
            },
        )
        self.assertEqual(
            row_a["source_flags"],
            json.dumps(
                {
                    "csi_all_minutes_fractional": True,
                    "csi_minute_attribution_method": "csi_fractional_minute_reconciliation",
                    "csi_totals_exceed_window": False,
                    "idle_assigned_minutes_basis": 50.0,
                    "idle_attribution_method": "residual_minutes_after_fractional_csi_full_hour_coverage",
                    "idle_attribution_warning": None,
                    "idle_full_hour_csi_coverage": True,
                    "idle_match_confidence": "high",
                    "idle_skipped_reason": None,
                    "maintenance_txn_in_hour": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        self.assertEqual(json.loads(row_b["source_flags"])["idle_skipped_reason"], "idle_partial_csi_coverage")

    def test_same_hour_maintenance_without_conflicting_operational_evidence_promotes_state(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "energy_total_kwh": 20.0,
                    "csi_source_row_hash": None,
                    "csi_overlap_minutes": None,
                    "good_qty": None,
                    "scrap_qty": None,
                    "mes_source_row_hash": "mes-keep",
                    "mes_report_ts": "2025-06-01T10:40:00",
                    "mes_match_method": "canonical_order_suffix_same_date_closest_hour_end",
                    "mes_match_confidence": "high",
                    "manpower": 3.0,
                    "last_maintenance_source_row_hash": "maint-keep",
                    "last_maintenance_work_order_type": "PM",
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["PM"],
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["machine_state"], "maintenance")
        self.assertEqual(row["state_confidence"], "low")
        self.assertIsNone(row["maintenance_minutes"])
        self.assertEqual(row["energy_total_kwh"], 20.0)
        self.assertEqual(row["mes_source_row_hash"], "mes-keep")
        self.assertEqual(row["manpower"], 3.0)
        self.assertEqual(row["last_maintenance_source_row_hash"], "maint-keep")
        self.assertEqual(
            flags["maintenance_state_promotion_method"],
            "same_hour_maintenance_txn_without_conflicting_operational_evidence",
        )
        self.assertEqual(flags["maintenance_state_confidence"], "low")
        self.assertTrue(flags["maintenance_state_review_passed"])
        self.assertIsNone(flags["maintenance_state_blocked_reason"])
        self.assertEqual(flags["maintenance_state_same_hour_work_order_count"], 1)
        self.assertEqual(flags["maintenance_state_current_hour_work_order_types"], ["PM"])

    def test_same_hour_maintenance_with_positive_production_keeps_production(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "production",
                    "state_confidence": "high",
                    "production_minutes": 15.0,
                    "csi_source_row_hash": "csi-prod-maint",
                    "csi_overlap_minutes": 0.5,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["PM"],
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["machine_state"], "production")
        self.assertEqual(flags["maintenance_state_blocked_reason"], "maintenance_state_conflicting_operational_minutes")
        self.assertFalse(flags["maintenance_state_review_passed"])

    def test_same_hour_maintenance_with_positive_planned_stop_keeps_planned_stop(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "planned_stop",
                    "state_confidence": "high",
                    "planned_stop_minutes": 20.0,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["Inspection"],
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertEqual(row["machine_state"], "planned_stop")
        self.assertEqual(flags["maintenance_state_blocked_reason"], "maintenance_state_conflicting_operational_minutes")

    def test_same_hour_maintenance_with_positive_quantity_does_not_promote(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "good_qty": 12.0,
                    "scrap_qty": 0.0,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["PM"],
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        flags = json.loads(gold_df.iloc[0]["source_flags"])

        self.assertIsNone(gold_df.iloc[0]["machine_state"])
        self.assertEqual(flags["maintenance_state_blocked_reason"], "maintenance_state_conflicting_quantity")

    def test_existing_idle_row_may_be_replaced_by_maintenance_when_eligible(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "idle",
                    "state_confidence": "high",
                    "idle_minutes": 60.0,
                    "csi_source_row_hash": None,
                    "good_qty": None,
                    "scrap_qty": None,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["AM"],
                            "idle_attribution_method": "residual_minutes_after_fractional_csi_full_hour_coverage",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        row = gold_df.iloc[0]

        self.assertEqual(row["machine_state"], "maintenance")
        self.assertEqual(row["state_confidence"], "low")
        self.assertEqual(row["idle_minutes"], 60.0)

    def test_same_hour_maintenance_with_meaningful_csi_overlap_does_not_promote(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "csi_source_row_hash": "csi-overlap",
                    "csi_overlap_minutes": 12.0,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["PM"],
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        flags = json.loads(gold_df.iloc[0]["source_flags"])

        self.assertIsNone(gold_df.iloc[0]["machine_state"])
        self.assertEqual(flags["maintenance_state_blocked_reason"], "maintenance_state_existing_csi_overlap")

    def test_maintenance_state_review_rerun_clears_stale_maintenance_state(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "maintenance",
                    "state_confidence": "low",
                    "source_flags": json.dumps(
                        {
                            "maintenance_state_promotion_method": "same_hour_maintenance_txn_without_conflicting_operational_evidence",
                            "maintenance_state_confidence": "low",
                            "maintenance_state_review_passed": True,
                            "maintenance_state_blocked_reason": None,
                            "maintenance_state_same_hour_work_order_count": 1,
                            "maintenance_state_current_hour_work_order_types": ["PM"],
                            "maintenance_txn_in_hour": False,
                            "maintenance_distinct_work_order_in_hour_count": 0,
                            "maintenance_current_hour_work_order_types": [],
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour()
        row = gold_df.iloc[0]
        flags = json.loads(row["source_flags"])

        self.assertIsNone(row["machine_state"])
        self.assertIsNone(row["state_confidence"])
        self.assertFalse(flags["maintenance_state_review_passed"])
        self.assertEqual(flags["maintenance_state_blocked_reason"], "maintenance_state_no_same_hour_maintenance")

    def test_maintenance_state_review_preserves_row_grain_and_deterministic_flags(self):
        self._insert_fact_machine_hour_rows(
            [
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": None,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["PM"],
                        },
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-018",
                    "hour_ts": "2025-06-01T11:00:00",
                    "machine_state": None,
                    "production_minutes": 10.0,
                    "source_flags": json.dumps(
                        {
                            "maintenance_txn_in_hour": True,
                            "maintenance_distinct_work_order_in_hour_count": 1,
                            "maintenance_current_hour_work_order_types": ["PM"],
                        },
                        sort_keys=True,
                    ),
                },
            ]
        )

        gold_df = self.builder.overlay_maintenance_state_review_on_fact_machine_hour().sort_values("hour_ts")
        row_a = gold_df.iloc[0]
        row_b = gold_df.iloc[1]

        self.assertEqual(len(gold_df), 2)
        self.assertEqual(
            set(zip(gold_df["canonical_machine_id"], gold_df["hour_ts"])),
            {
                ("024-018", "2025-06-01T10:00:00"),
                ("024-018", "2025-06-01T11:00:00"),
            },
        )
        self.assertEqual(
            row_a["source_flags"],
            json.dumps(
                {
                    "maintenance_current_hour_work_order_types": ["PM"],
                    "maintenance_distinct_work_order_in_hour_count": 1,
                    "maintenance_state_blocked_reason": None,
                    "maintenance_state_confidence": "low",
                    "maintenance_state_current_hour_work_order_types": ["PM"],
                    "maintenance_state_promotion_method": "same_hour_maintenance_txn_without_conflicting_operational_evidence",
                    "maintenance_state_review_passed": True,
                    "maintenance_state_same_hour_work_order_count": 1,
                    "maintenance_txn_in_hour": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        self.assertEqual(
            json.loads(row_b["source_flags"])["maintenance_state_blocked_reason"],
            "maintenance_state_conflicting_operational_minutes",
        )


if __name__ == "__main__":
    unittest.main()
