import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.bronze_raw_store import BronzeRawStore
from core.fact_machine_hour_repair import (
    execute_task4s_live_quantity_replacement,
    repair_fact_machine_hour_operational_overlays,
    repair_fact_machine_hour_quantity_audit_metadata,
)
from core.gold_fact_builder import GoldFactBuilder
from core.silver_normalizer import SilverNormalizer


class FactMachineHourRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "fact_repair_test.db"
        self.bronze = BronzeRawStore(self.db_path)
        self.silver = SilverNormalizer(self.db_path)
        self.gold = GoldFactBuilder(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_minimal_task4s_live_table(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DROP TABLE IF EXISTS fact_machine_hour")
            conn.execute(
                """
                CREATE TABLE fact_machine_hour (
                    canonical_machine_id TEXT,
                    hour_ts TEXT,
                    machine_state TEXT,
                    order_id TEXT,
                    material_code TEXT,
                    task_name TEXT,
                    csi_source_row_hash TEXT,
                    source_flags TEXT,
                    multiple_csi_overlap_flag INTEGER,
                    setup_minutes REAL,
                    production_minutes REAL,
                    planned_stop_minutes REAL,
                    unplanned_stop_minutes REAL,
                    idle_minutes REAL,
                    good_qty REAL,
                    scrap_qty REAL,
                    csi_qty_basis_method TEXT,
                    csi_qty_row_basis_minutes REAL,
                    csi_qty_event_basis_minutes REAL,
                    csi_qty_minutes_vs_production_diff REAL,
                    csi_qty_minutes_vs_production_abs_diff REAL,
                    csi_qty_alignment_status TEXT,
                    csi_qty_material_misalignment_flag INTEGER,
                    csi_qty_minute_budget_anomaly_flag INTEGER,
                    csi_qty_minute_budget_anomaly_reason TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _seed_minimal_task4s_live_rows(self):
        self._create_minimal_task4s_live_table()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executemany(
                """
                INSERT INTO fact_machine_hour (
                    canonical_machine_id,
                    hour_ts,
                    machine_state,
                    order_id,
                    material_code,
                    task_name,
                    csi_source_row_hash,
                    source_flags,
                    multiple_csi_overlap_flag,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    unplanned_stop_minutes,
                    idle_minutes,
                    good_qty,
                    scrap_qty,
                    csi_qty_basis_method,
                    csi_qty_row_basis_minutes,
                    csi_qty_event_basis_minutes,
                    csi_qty_minutes_vs_production_diff,
                    csi_qty_minutes_vs_production_abs_diff,
                    csi_qty_alignment_status,
                    csi_qty_material_misalignment_flag,
                    csi_qty_minute_budget_anomaly_flag,
                    csi_qty_minute_budget_anomaly_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "024-143",
                        "2025-01-01T00:00:00",
                        "production",
                        "JOB-ELIGIBLE",
                        "MAT-ELIGIBLE",
                        "Print",
                        "hash-eligible",
                        None,
                        1,
                        0.0,
                        45.0,
                        0.0,
                        0.0,
                        0.0,
                        20.0,
                        2.0,
                        "csi_dominant_event_production_minutes_share",
                        10.0,
                        50.0,
                        35.0,
                        35.0,
                        "material_misaligned",
                        1,
                        0,
                        None,
                    ),
                    (
                        "024-143",
                        "2025-01-01T01:00:00",
                        "production",
                        "JOB-ELIGIBLE",
                        "MAT-ELIGIBLE",
                        "Print",
                        "hash-eligible",
                        None,
                        1,
                        0.0,
                        15.0,
                        0.0,
                        0.0,
                        0.0,
                        80.0,
                        8.0,
                        "csi_dominant_event_production_minutes_share",
                        40.0,
                        50.0,
                        -25.0,
                        25.0,
                        "material_misaligned",
                        1,
                        0,
                        None,
                    ),
                    (
                        "166-002",
                        "2025-01-01T02:00:00",
                        "production",
                        "JOB-ANOMALY",
                        "MAT-ANOMALY",
                        "UV",
                        "hash-anomaly",
                        None,
                        1,
                        0.0,
                        10.0,
                        0.0,
                        0.0,
                        0.0,
                        30.0,
                        0.0,
                        "csi_dominant_event_production_minutes_share",
                        10.0,
                        60.0,
                        0.0,
                        0.0,
                        "aligned",
                        0,
                        1,
                        "production_minutes_gt_60",
                    ),
                    (
                        "166-002",
                        "2025-01-01T03:00:00",
                        "production",
                        "JOB-ANOMALY",
                        "MAT-ANOMALY",
                        "UV",
                        "hash-anomaly",
                        None,
                        1,
                        0.0,
                        50.0,
                        0.0,
                        0.0,
                        0.0,
                        70.0,
                        0.0,
                        "csi_dominant_event_production_minutes_share",
                        50.0,
                        60.0,
                        0.0,
                        0.0,
                        "aligned",
                        0,
                        0,
                        None,
                    ),
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def _seed_energy_backbone(self):
        self.bronze.write_energy_rows(
            pd.DataFrame(
                [
                    {
                        "machine": "D-024-001主機",
                        "datetime": pd.Timestamp("2025-01-01 00:00:00"),
                        "electricity_kwh": 10.0,
                        "electricity_cost": 100.0,
                        "canonical_machine_id": "024-001",
                        "source_file": "energy.xlsx",
                    },
                    {
                        "machine": "D-024-001主機",
                        "datetime": pd.Timestamp("2025-01-01 01:00:00"),
                        "electricity_kwh": 12.0,
                        "electricity_cost": 120.0,
                        "canonical_machine_id": "024-001",
                        "source_file": "energy.xlsx",
                    },
                ]
            )
        )
        self.bronze.write_csi_rows(
            pd.DataFrame(
                [
                    {
                        "機台編號": "D-024-001",
                        "班次內日期": pd.Timestamp("2025-01-01").date(),
                        "班次": "D",
                        "區域": "A",
                        "作业": "JOB-001",
                        "作业后缀": "1",
                        "操作": "印刷",
                        "物料": "MAT-001",
                        "任務": "Print",
                        "工程開始時間": pd.Timestamp("2025-01-01 00:00:00"),
                        "準備結束時間": pd.Timestamp("2025-01-01 00:10:00"),
                        "工程結束時間": pd.Timestamp("2025-01-01 01:00:00"),
                        "正品數量": 100.0,
                        "廢品數量": 0.0,
                        "纍計數量": 100.0,
                        "實際生產時間": 45.0,
                        "心電圖實際轉版時間": 10.0,
                        "實際計劃停機時間": 5.0,
                        "實際無計劃停機時間": 0.0,
                        "實際速度_本_時": 200.0,
                        "機長姓名1": "Alice",
                        "canonical_machine_id": "024-001",
                        "source_file": "csi.xlsx",
                    }
                ]
            )
        )
        self.bronze.write_mes_rows(
            pd.DataFrame(
                [
                    {
                        "資源": "1024-00001",
                        "報工時間": pd.Timestamp("2025-01-01 00:50:00"),
                        "作業": "JOB-001",
                        "後綴": "1",
                        "操作": "印刷",
                        "任務": "Print",
                        "物料": "MAT-001",
                        "要求生產數量": 120.0,
                        "生產數量": 100.0,
                        "累計生產數量": 100.0,
                        "報工類型": "NORMAL",
                        "設備總用時": 1.0,
                        "準備時間": 0.2,
                        "設備生產時間": 0.75,
                        "人數": 4.0,
                        "班次": "D",
                        "上傳CSI狀態": "Y",
                        "狀態變更時間": pd.Timestamp("2025-01-01 00:55:00"),
                        "記錄新增時間": pd.Timestamp("2025-01-01 00:56:00"),
                        "canonical_machine_id": "024-001",
                        "source_file": "mes.xlsx",
                    }
                ]
            )
        )
        self.bronze.write_maintenance_rows(
            pd.DataFrame(
                [
                    {
                        "資產": "1024-00001",
                        "資產老編號": "024-001",
                        "交易日期": pd.Timestamp("2025-01-01 00:20:00"),
                        "工單": "WO-001",
                        "工單描述": "Routine PM",
                        "工單類型": "PM",
                        "交易類型": "發出",
                        "物料編碼": "PART-001",
                        "數量": 1.0,
                        "canonical_machine_id": "024-001",
                        "source_file": "maintenance.xlsx",
                    }
                ]
            )
        )

        self.silver.normalize_all()
        self.gold.build_fact_machine_hour()

    def test_repair_recovers_ml_critical_operational_overlays(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            before = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN good_qty IS NOT NULL THEN 1 ELSE 0 END),
                    SUM(CASE WHEN team_leader IS NOT NULL THEN 1 ELSE 0 END),
                    SUM(CASE WHEN manpower IS NOT NULL THEN 1 ELSE 0 END),
                    SUM(CASE WHEN hours_since_last_maintenance IS NOT NULL THEN 1 ELSE 0 END)
                FROM fact_machine_hour
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(before, (0, 0, 0, 0))

        result = repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_rows = pd.read_sql_query(
                """
                SELECT
                    hour_ts,
                    machine_state,
                    order_id,
                    order_suffix,
                    material_code,
                    task_name,
                    team_leader,
                    team_size,
                    manpower,
                    good_qty,
                    scrap_qty,
                    has_maintenance_history,
                    maintenance_txn_in_hour,
                    maintenance_distinct_work_order_count_7d,
                    maintenance_distinct_work_order_count_30d,
                    maintenance_distinct_work_order_in_hour_count,
                    cumulative_maintenance_count,
                    hours_since_last_maintenance,
                    last_maintenance_work_order_type
                FROM fact_machine_hour
                ORDER BY hour_ts
                """,
                conn,
            )
        finally:
            conn.close()

        hour0 = repaired_rows.iloc[0]
        hour1 = repaired_rows.iloc[1]

        self.assertEqual(result["before"]["rows_with_good_qty"], 0)
        self.assertEqual(result["after"]["rows_with_good_qty"], 1)
        self.assertEqual(result["after"]["rows_with_team_leader"], 1)
        self.assertEqual(result["after"]["rows_with_manpower"], 1)
        self.assertEqual(result["after"]["rows_with_team_size"], 1)
        self.assertEqual(result["after"]["rows_with_maintenance_history"], 1)
        self.assertEqual(result["after"]["rows_with_maintenance_txn_in_hour"], 1)
        self.assertEqual(result["after"]["rows_with_hours_since_last_maintenance"], 1)

        self.assertEqual(hour0["machine_state"], "setup_changeover")
        self.assertEqual(hour0["order_id"], "JOB-001")
        self.assertEqual(hour0["order_suffix"], "1")
        self.assertEqual(hour0["material_code"], "MAT-001")
        self.assertEqual(hour0["task_name"], "Print")
        self.assertEqual(hour0["team_leader"], "Alice")
        self.assertEqual(hour0["team_size"], 4.0)
        self.assertEqual(hour0["manpower"], 4.0)
        self.assertAlmostEqual(hour0["good_qty"], 100.0, places=6)
        self.assertAlmostEqual(hour0["scrap_qty"], 0.0, places=6)
        self.assertEqual(hour0["has_maintenance_history"], 0)
        self.assertEqual(hour0["maintenance_txn_in_hour"], 1)
        self.assertEqual(hour0["maintenance_distinct_work_order_count_7d"], 0)
        self.assertEqual(hour0["maintenance_distinct_work_order_count_30d"], 0)
        self.assertEqual(hour0["maintenance_distinct_work_order_in_hour_count"], 1)
        self.assertEqual(hour0["cumulative_maintenance_count"], 0)
        self.assertTrue(pd.isna(hour0["hours_since_last_maintenance"]))

        self.assertTrue(pd.isna(hour1["good_qty"]))
        self.assertTrue(pd.isna(hour1["team_leader"]))
        self.assertTrue(pd.isna(hour1["team_size"]))
        self.assertEqual(hour1["has_maintenance_history"], 1)
        self.assertEqual(hour1["maintenance_txn_in_hour"], 0)
        self.assertEqual(hour1["maintenance_distinct_work_order_count_7d"], 1)
        self.assertEqual(hour1["maintenance_distinct_work_order_count_30d"], 1)
        self.assertEqual(hour1["maintenance_distinct_work_order_in_hour_count"], 0)
        self.assertEqual(hour1["cumulative_maintenance_count"], 1)
        self.assertAlmostEqual(hour1["hours_since_last_maintenance"], 40.0 / 60.0, places=6)
        self.assertEqual(hour1["last_maintenance_work_order_type"], "PM")

    def test_repair_blends_multi_event_minutes_without_rewriting_dominant_quantity(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO csi_job_event (
                    source_row_hash, canonical_machine_id, shift_date, shift_name, csi_area,
                    order_id, suffix, operation, material_code, task_name,
                    prep_end_ts, prod_end_ts, actual_prod_minutes, planned_stop_minutes,
                    unplanned_stop_minutes, actual_changeover_minutes, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "csi-extra-overlap",
                    "024-001",
                    "2025-01-01",
                    "D",
                    "A",
                    "JOB-EXTRA",
                    "2",
                    "印刷",
                    "MAT-EXTRA",
                    "Extra",
                    "2025-01-01T00:30:00",
                    "2025-01-01T01:00:00",
                    30.0,
                    0.0,
                    0.0,
                    0.0,
                    "csi_extra.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    machine_state,
                    order_id,
                    csi_source_row_hash,
                    csi_overlap_minutes,
                    multiple_csi_overlap_flag,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    idle_minutes,
                    good_qty,
                    scrap_qty,
                    csi_qty_basis_method,
                    csi_qty_row_basis_minutes,
                    csi_qty_event_basis_minutes,
                    csi_qty_minutes_vs_production_diff,
                    csi_qty_minutes_vs_production_abs_diff,
                    csi_qty_alignment_status,
                    csi_qty_material_misalignment_flag,
                    csi_qty_minute_budget_anomaly_flag,
                    csi_qty_minute_budget_anomaly_reason
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(repaired_row[0], "setup_changeover")
        self.assertEqual(repaired_row[1], "JOB-001")
        self.assertEqual(repaired_row[2] is not None, True)
        self.assertAlmostEqual(repaired_row[3], 60.0, places=6)
        self.assertEqual(repaired_row[4], 1)
        self.assertAlmostEqual(repaired_row[5], (10.0 * (60.0 / 90.0)), places=6)
        self.assertAlmostEqual(repaired_row[6], (75.0 * (60.0 / 90.0)), places=6)
        self.assertAlmostEqual(repaired_row[7], (5.0 * (60.0 / 90.0)), places=6)
        self.assertTrue(pd.isna(repaired_row[8]))
        self.assertAlmostEqual(repaired_row[9], 100.0, places=6)
        self.assertAlmostEqual(repaired_row[10], 0.0, places=6)
        self.assertEqual(repaired_row[11], "csi_dominant_event_production_minutes_share")
        self.assertAlmostEqual(repaired_row[12], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[13], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[14], 5.0, places=6)
        self.assertAlmostEqual(repaired_row[15], 5.0, places=6)
        self.assertEqual(repaired_row[16], "material_misaligned")
        self.assertEqual(repaired_row[17], 1)
        self.assertEqual(repaired_row[18], 0)
        self.assertIsNone(repaired_row[19])

    def test_repair_derives_team_size_from_csi_roster_when_mes_manpower_missing(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE csi_job_event
                SET team_members_raw = '["Bob","Cara"]'
                WHERE canonical_machine_id = '024-001'
                """
            )
            conn.execute(
                """
                UPDATE mes_report_event
                SET manpower = NULL
                WHERE canonical_machine_id = '024-001'
                """
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT team_leader, team_size, manpower
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(repaired_row, ("Alice", 3.0, None))

    def test_quantity_audit_metadata_backfill_populates_overlap_rows_without_rewriting_quantities(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO csi_job_event (
                    source_row_hash, canonical_machine_id, shift_date, shift_name, csi_area,
                    order_id, suffix, operation, material_code, task_name,
                    prep_end_ts, prod_end_ts, actual_prod_minutes, planned_stop_minutes,
                    unplanned_stop_minutes, actual_changeover_minutes, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "csi-extra-overlap",
                    "024-001",
                    "2025-01-01",
                    "D",
                    "A",
                    "JOB-EXTRA",
                    "2",
                    "印刷",
                    "MAT-EXTRA",
                    "Extra",
                    "2025-01-01T00:30:00",
                    "2025-01-01T01:00:00",
                    30.0,
                    0.0,
                    0.0,
                    0.0,
                    "csi_extra.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE fact_machine_hour
                SET
                    csi_qty_basis_method = NULL,
                    csi_qty_row_basis_minutes = NULL,
                    csi_qty_event_basis_minutes = NULL,
                    csi_qty_minutes_vs_production_diff = NULL,
                    csi_qty_minutes_vs_production_abs_diff = NULL,
                    csi_qty_alignment_status = NULL,
                    csi_qty_material_misalignment_flag = NULL,
                    csi_qty_minute_budget_anomaly_flag = NULL,
                    csi_qty_minute_budget_anomaly_reason = NULL
                """
            )
            conn.commit()
        finally:
            conn.close()

        result = repair_fact_machine_hour_quantity_audit_metadata(
            self.db_path,
            start_ts="2025-01-01T00:00:00",
            end_ts="2025-02-01T00:00:00",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    good_qty,
                    scrap_qty,
                    csi_qty_basis_method,
                    csi_qty_row_basis_minutes,
                    csi_qty_event_basis_minutes,
                    csi_qty_minutes_vs_production_diff,
                    csi_qty_minutes_vs_production_abs_diff,
                    csi_qty_alignment_status,
                    csi_qty_material_misalignment_flag,
                    csi_qty_minute_budget_anomaly_flag,
                    csi_qty_minute_budget_anomaly_reason
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(result["audit_rows"], 1)
        self.assertEqual(result["material_misaligned_rows"], 1)
        self.assertEqual(result["minute_budget_anomaly_rows"], 0)
        self.assertAlmostEqual(repaired_row[0], 100.0, places=6)
        self.assertAlmostEqual(repaired_row[1], 0.0, places=6)
        self.assertEqual(repaired_row[2], "csi_dominant_event_production_minutes_share")
        self.assertAlmostEqual(repaired_row[3], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[4], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[5], 5.0, places=6)
        self.assertAlmostEqual(repaired_row[6], 5.0, places=6)
        self.assertEqual(repaired_row[7], "material_misaligned")
        self.assertEqual(repaired_row[8], 1)
        self.assertEqual(repaired_row[9], 0)
        self.assertIsNone(repaired_row[10])

    def test_quantity_audit_metadata_backfill_excludes_overlap_rows_without_quantity_by_default(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO csi_job_event (
                    source_row_hash, canonical_machine_id, shift_date, shift_name, csi_area,
                    order_id, suffix, operation, material_code, task_name,
                    prep_end_ts, prod_end_ts, actual_prod_minutes, planned_stop_minutes,
                    unplanned_stop_minutes, actual_changeover_minutes, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "csi-extra-overlap",
                    "024-001",
                    "2025-01-01",
                    "D",
                    "A",
                    "JOB-EXTRA",
                    "2",
                    "印刷",
                    "MAT-EXTRA",
                    "Extra",
                    "2025-01-01T00:30:00",
                    "2025-01-01T01:00:00",
                    30.0,
                    0.0,
                    0.0,
                    0.0,
                    "csi_extra.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE fact_machine_hour
                SET
                    good_qty = NULL,
                    scrap_qty = NULL,
                    csi_qty_basis_method = NULL,
                    csi_qty_row_basis_minutes = NULL,
                    csi_qty_event_basis_minutes = NULL,
                    csi_qty_minutes_vs_production_diff = NULL,
                    csi_qty_minutes_vs_production_abs_diff = NULL,
                    csi_qty_alignment_status = NULL,
                    csi_qty_material_misalignment_flag = NULL,
                    csi_qty_minute_budget_anomaly_flag = NULL,
                    csi_qty_minute_budget_anomaly_reason = NULL
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            )
            conn.commit()
        finally:
            conn.close()

        result = repair_fact_machine_hour_quantity_audit_metadata(
            self.db_path,
            start_ts="2025-01-01T00:00:00",
            end_ts="2025-02-01T00:00:00",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    csi_source_row_hash,
                    multiple_csi_overlap_flag,
                    good_qty,
                    scrap_qty,
                    csi_qty_row_basis_minutes,
                    csi_qty_alignment_status
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(repaired_row[0])
        self.assertEqual(repaired_row[1], 1)
        self.assertIsNone(repaired_row[2])
        self.assertIsNone(repaired_row[3])
        self.assertEqual(result["quantity_rows_only"], True)
        self.assertEqual(result["target_rows"], 0)
        self.assertEqual(result["audit_rows"], 0)
        self.assertIsNone(repaired_row[4])
        self.assertIsNone(repaired_row[5])

    def test_quantity_audit_metadata_backfill_reconstructs_missing_basis_from_source_flags(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO csi_job_event (
                    source_row_hash, canonical_machine_id, shift_date, shift_name, csi_area,
                    order_id, suffix, operation, material_code, task_name,
                    prep_end_ts, prod_end_ts, actual_prod_minutes, planned_stop_minutes,
                    unplanned_stop_minutes, actual_changeover_minutes, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "csi-extra-overlap",
                    "024-001",
                    "2025-01-01",
                    "D",
                    "A",
                    "JOB-EXTRA",
                    "2",
                    "印刷",
                    "MAT-EXTRA",
                    "Extra",
                    "2025-01-01T00:30:00",
                    "2025-01-01T01:00:00",
                    30.0,
                    0.0,
                    0.0,
                    0.0,
                    "csi_extra.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            dominant_hash = conn.execute(
                """
                SELECT csi_source_row_hash
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()[0]
            conn.execute(
                """
                UPDATE fact_machine_hour
                SET
                    source_flags = json_set(
                        json_set(
                            source_flags,
                            '$.csi_dominant_production_minutes',
                            45.0
                        ),
                        '$.dominant_csi_source_row_hash',
                        csi_source_row_hash
                    ),
                    csi_qty_basis_method = NULL,
                    csi_qty_row_basis_minutes = NULL,
                    csi_qty_event_basis_minutes = NULL,
                    csi_qty_minutes_vs_production_diff = NULL,
                    csi_qty_minutes_vs_production_abs_diff = NULL,
                    csi_qty_alignment_status = NULL,
                    csi_qty_material_misalignment_flag = NULL,
                    csi_qty_minute_budget_anomaly_flag = NULL,
                    csi_qty_minute_budget_anomaly_reason = NULL
                """
            )
            conn.execute(
                "DELETE FROM csi_job_event WHERE source_row_hash = ?",
                (dominant_hash,),
            )
            conn.commit()
        finally:
            conn.close()

        result = repair_fact_machine_hour_quantity_audit_metadata(
            self.db_path,
            start_ts="2025-01-01T00:00:00",
            end_ts="2025-02-01T00:00:00",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    good_qty,
                    scrap_qty,
                    csi_qty_row_basis_minutes,
                    csi_qty_event_basis_minutes,
                    csi_qty_minutes_vs_production_diff,
                    csi_qty_alignment_status
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(result["newly_reconstructible_rows"], 1)
        self.assertEqual(result["still_unreconstructible_rows"], 0)
        self.assertEqual(result["excluded_anomaly_rows"], 0)
        self.assertEqual(result["dominant_identity_conflict_rows"], 0)
        self.assertEqual(result["quantity_rows_only"], True)
        self.assertEqual(result["target_rows"], 1)
        self.assertAlmostEqual(repaired_row[0], 100.0, places=6)
        self.assertAlmostEqual(repaired_row[1], 0.0, places=6)
        self.assertAlmostEqual(repaired_row[2], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[3], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[4], 5.0, places=6)
        self.assertEqual(repaired_row[5], "material_misaligned")

    def test_quantity_audit_metadata_backfill_reconstructs_missing_basis_when_dominant_hash_flag_is_absent(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO csi_job_event (
                    source_row_hash, canonical_machine_id, shift_date, shift_name, csi_area,
                    order_id, suffix, operation, material_code, task_name,
                    prep_end_ts, prod_end_ts, actual_prod_minutes, planned_stop_minutes,
                    unplanned_stop_minutes, actual_changeover_minutes, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "csi-extra-overlap",
                    "024-001",
                    "2025-01-01",
                    "D",
                    "A",
                    "JOB-EXTRA",
                    "2",
                    "印刷",
                    "MAT-EXTRA",
                    "Extra",
                    "2025-01-01T00:30:00",
                    "2025-01-01T01:00:00",
                    30.0,
                    0.0,
                    0.0,
                    0.0,
                    "csi_extra.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            dominant_hash = conn.execute(
                """
                SELECT csi_source_row_hash
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()[0]
            conn.execute(
                """
                UPDATE fact_machine_hour
                SET
                    source_flags = json_remove(
                        json_set(
                            source_flags,
                            '$.csi_dominant_production_minutes',
                            45.0
                        ),
                        '$.dominant_csi_source_row_hash'
                    ),
                    csi_qty_basis_method = NULL,
                    csi_qty_row_basis_minutes = NULL,
                    csi_qty_event_basis_minutes = NULL,
                    csi_qty_minutes_vs_production_diff = NULL,
                    csi_qty_minutes_vs_production_abs_diff = NULL,
                    csi_qty_alignment_status = NULL,
                    csi_qty_material_misalignment_flag = NULL,
                    csi_qty_minute_budget_anomaly_flag = NULL,
                    csi_qty_minute_budget_anomaly_reason = NULL
                """
            )
            conn.execute(
                "DELETE FROM csi_job_event WHERE source_row_hash = ?",
                (dominant_hash,),
            )
            conn.commit()
        finally:
            conn.close()

        result = repair_fact_machine_hour_quantity_audit_metadata(
            self.db_path,
            start_ts="2025-01-01T00:00:00",
            end_ts="2025-02-01T00:00:00",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    good_qty,
                    scrap_qty,
                    csi_qty_row_basis_minutes,
                    csi_qty_event_basis_minutes,
                    csi_qty_minutes_vs_production_diff,
                    csi_qty_alignment_status
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(result["quantity_rows_only"], True)
        self.assertEqual(result["target_rows"], 1)
        self.assertEqual(result["newly_reconstructible_rows"], 1)
        self.assertEqual(result["dominant_identity_conflict_rows"], 0)
        self.assertEqual(result["still_unreconstructible_rows"], 0)
        self.assertAlmostEqual(repaired_row[0], 100.0, places=6)
        self.assertAlmostEqual(repaired_row[1], 0.0, places=6)
        self.assertAlmostEqual(repaired_row[2], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[3], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[4], 5.0, places=6)
        self.assertEqual(repaired_row[5], "material_misaligned")

    def test_quantity_audit_metadata_backfill_blocks_source_flag_reconstruction_on_dominant_hash_conflict(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO csi_job_event (
                    source_row_hash, canonical_machine_id, shift_date, shift_name, csi_area,
                    order_id, suffix, operation, material_code, task_name,
                    prep_end_ts, prod_end_ts, actual_prod_minutes, planned_stop_minutes,
                    unplanned_stop_minutes, actual_changeover_minutes, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "csi-extra-overlap",
                    "024-001",
                    "2025-01-01",
                    "D",
                    "A",
                    "JOB-EXTRA",
                    "2",
                    "印刷",
                    "MAT-EXTRA",
                    "Extra",
                    "2025-01-01T00:30:00",
                    "2025-01-01T01:00:00",
                    30.0,
                    0.0,
                    0.0,
                    0.0,
                    "csi_extra.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            dominant_hash = conn.execute(
                """
                SELECT csi_source_row_hash
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()[0]
            conn.execute(
                """
                UPDATE fact_machine_hour
                SET
                    source_flags = json_set(
                        json_set(
                            source_flags,
                            '$.csi_dominant_production_minutes',
                            45.0
                        ),
                        '$.dominant_csi_source_row_hash',
                        'conflicting-source-hash'
                    ),
                    csi_qty_basis_method = NULL,
                    csi_qty_row_basis_minutes = NULL,
                    csi_qty_event_basis_minutes = NULL,
                    csi_qty_minutes_vs_production_diff = NULL,
                    csi_qty_minutes_vs_production_abs_diff = NULL,
                    csi_qty_alignment_status = NULL,
                    csi_qty_material_misalignment_flag = NULL,
                    csi_qty_minute_budget_anomaly_flag = NULL,
                    csi_qty_minute_budget_anomaly_reason = NULL
                """
            )
            conn.execute(
                "DELETE FROM csi_job_event WHERE source_row_hash = ?",
                (dominant_hash,),
            )
            conn.commit()
        finally:
            conn.close()

        result = repair_fact_machine_hour_quantity_audit_metadata(
            self.db_path,
            start_ts="2025-01-01T00:00:00",
            end_ts="2025-02-01T00:00:00",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    good_qty,
                    scrap_qty,
                    csi_qty_row_basis_minutes,
                    csi_qty_event_basis_minutes,
                    csi_qty_alignment_status
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(result["newly_reconstructible_rows"], 0)
        self.assertEqual(result["dominant_identity_conflict_rows"], 1)
        self.assertEqual(result["still_unreconstructible_rows"], 1)
        self.assertEqual(result["excluded_anomaly_rows"], 0)
        self.assertAlmostEqual(repaired_row[0], 100.0, places=6)
        self.assertAlmostEqual(repaired_row[1], 0.0, places=6)
        self.assertIsNone(repaired_row[2])
        self.assertIsNone(repaired_row[3])
        self.assertEqual(repaired_row[4], "missing_positive_row_basis_minutes")

    def test_repair_prefers_positive_mes_manpower_over_closer_zero_row(self):
        self._seed_energy_backbone()

        conn = sqlite3.connect(self.db_path)
        try:
            positive_hash = conn.execute(
                """
                SELECT source_row_hash
                FROM mes_report_event
                WHERE canonical_machine_id = '024-001'
                ORDER BY report_ts
                LIMIT 1
                """
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO mes_report_event (
                    source_row_hash, canonical_machine_id, report_ts, order_id, suffix, operation,
                    task_name, material_code, required_qty, reported_qty, cumulative_qty, report_type,
                    equipment_total_hours, prep_hours, equipment_prod_hours, manpower, shift_name,
                    resource_id_raw, csi_upload_status, status_changed_ts, record_created_ts, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mes-zero",
                    "024-001",
                    "2025-01-01T00:59:00",
                    "JOB-001",
                    "1",
                    "印刷",
                    "Print",
                    "MAT-001",
                    120.0,
                    100.0,
                    100.0,
                    "NORMAL",
                    1.0,
                    0.2,
                    0.75,
                    0.0,
                    "D",
                    "1024-00001",
                    "Y",
                    "2025-01-01T00:59:00",
                    "2025-01-01T00:59:00",
                    "mes.xlsx",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        repair_fact_machine_hour_operational_overlays(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT manpower, team_size, mes_source_row_hash, mes_match_method
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-01-01T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(repaired_row[0], 4.0)
        self.assertEqual(repaired_row[1], 4.0)
        self.assertEqual(repaired_row[2], positive_hash)
        self.assertEqual(
            repaired_row[3],
            "canonical_order_suffix_same_date_prefer_positive_manpower_then_closest_hour_end",
        )

    def test_live_quantity_replacement_updates_only_eligible_rows_and_writes_rollback_snapshot(self):
        self._seed_minimal_task4s_live_rows()
        backup_dir = Path(self.temp_dir.name) / "backups"

        result = execute_task4s_live_quantity_replacement(
            self.db_path,
            start_ts="2025-01-01T00:00:00",
            end_ts="2025-02-01T00:00:00",
            backup_dir=backup_dir,
            expected_baseline={
                "eligible_rows": 2,
                "anomaly_excluded_rows": 2,
                "eligible_groups": 1,
                "ineligible_groups": 1,
                "dominant_identity_conflict_rows": 0,
            },
            timestamp_override="20260403_000000",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    hour_ts,
                    order_id,
                    material_code,
                    task_name,
                    good_qty,
                    scrap_qty
                FROM fact_machine_hour
                ORDER BY hour_ts
                """
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(result["row_unique_key"], "rowid")
        self.assertEqual(result["row_unique_key_count"], 4)
        self.assertEqual(result["row_unique_key_distinct_count"], 4)
        self.assertEqual(result["write_scope_exact_rows"], 4)
        self.assertEqual(result["write_scope_target_rows"], 2)
        self.assertEqual(result["write_scope_anomaly_excluded_rows"], 2)
        self.assertEqual(result["materially_changed_row_count"], 2)
        self.assertEqual(result["post_write_residual_materially_changed_row_count"], 0)
        self.assertEqual(result["rollback_needed"], False)
        self.assertTrue(result["per_group_conservation_passed"])
        self.assertTrue(Path(result["backup_path"]).exists())
        self.assertTrue(Path(result["rollback_snapshot_path"]).exists())

        self.assertEqual(rows[0][0], "2025-01-01T00:00:00")
        self.assertEqual(rows[0][1], "JOB-ELIGIBLE")
        self.assertEqual(rows[0][2], "MAT-ELIGIBLE")
        self.assertEqual(rows[0][3], "Print")
        self.assertAlmostEqual(rows[0][4], 75.0, places=6)
        self.assertAlmostEqual(rows[0][5], 7.5, places=6)

        self.assertEqual(rows[1][0], "2025-01-01T01:00:00")
        self.assertEqual(rows[1][1], "JOB-ELIGIBLE")
        self.assertEqual(rows[1][2], "MAT-ELIGIBLE")
        self.assertEqual(rows[1][3], "Print")
        self.assertAlmostEqual(rows[1][4], 25.0, places=6)
        self.assertAlmostEqual(rows[1][5], 2.5, places=6)

        self.assertEqual(rows[2][0], "2025-01-01T02:00:00")
        self.assertAlmostEqual(rows[2][4], 30.0, places=6)
        self.assertAlmostEqual(rows[2][5], 0.0, places=6)

        self.assertEqual(rows[3][0], "2025-01-01T03:00:00")
        self.assertAlmostEqual(rows[3][4], 70.0, places=6)
        self.assertAlmostEqual(rows[3][5], 0.0, places=6)

    def test_live_quantity_replacement_aborts_before_backup_on_baseline_mismatch(self):
        self._seed_minimal_task4s_live_rows()
        backup_dir = Path(self.temp_dir.name) / "backups"

        with self.assertRaisesRegex(ValueError, "eligible row baseline drifted"):
            execute_task4s_live_quantity_replacement(
                self.db_path,
                start_ts="2025-01-01T00:00:00",
                end_ts="2025-02-01T00:00:00",
                backup_dir=backup_dir,
                expected_baseline={
                    "eligible_rows": 99,
                    "anomaly_excluded_rows": 2,
                    "eligible_groups": 1,
                    "ineligible_groups": 1,
                    "dominant_identity_conflict_rows": 0,
                },
                timestamp_override="20260403_000001",
            )

        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT hour_ts, good_qty, scrap_qty
                FROM fact_machine_hour
                ORDER BY hour_ts
                """
            ).fetchall()
        finally:
            conn.close()

        self.assertAlmostEqual(rows[0][1], 20.0, places=6)
        self.assertAlmostEqual(rows[0][2], 2.0, places=6)
        self.assertAlmostEqual(rows[1][1], 80.0, places=6)
        self.assertAlmostEqual(rows[1][2], 8.0, places=6)
        self.assertEqual(list(backup_dir.glob("*")), [])


if __name__ == "__main__":
    unittest.main()
