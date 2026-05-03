import contextlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from core.bronze_raw_store import BronzeRawStore
from core.canonical_gold_reader import CanonicalGoldReader
from core.canonical_materializer import CanonicalMaterializer
from modules.etl_module import ETLPipelineModule, process_uploaded_files
from modules.unified_view_module import auto_process_after_etl


class CanonicalMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "canonical_materializer_test.db"
        self.bronze_store = BronzeRawStore(self.db_path)
        self.materializer = CanonicalMaterializer(self.db_path)
        self.reader = CanonicalGoldReader(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _seed_month(self, month: str, day: int, energy_kwh: float) -> None:
        self.bronze_store.write_energy_rows(
            pd.DataFrame(
                [
                    {
                        "machine": "D-024-001主機",
                        "datetime": pd.Timestamp(f"2025-{month}-{day:02d} 00:00:00"),
                        "electricity_kwh": energy_kwh,
                        "electricity_cost": energy_kwh * 10.0,
                        "canonical_machine_id": "024-001",
                        "source_file": f"{month}_2025_energy_1.xlsx",
                    }
                ]
            )
        )
        self.bronze_store.write_csi_rows(
            pd.DataFrame(
                [
                    {
                        "機台編號": "D-024-001",
                        "班次內日期": pd.Timestamp(f"2025-{month}-{day:02d}").date(),
                        "班次": "D",
                        "區域": "A",
                        "作业": "JOB-001",
                        "作业后缀": "1",
                        "操作": "印刷",
                        "物料": "MAT-001",
                        "任務": "Print",
                        "工程開始時間": pd.Timestamp(f"2025-{month}-{day:02d} 00:00:00"),
                        "準備結束時間": pd.Timestamp(f"2025-{month}-{day:02d} 00:10:00"),
                        "工程結束時間": pd.Timestamp(f"2025-{month}-{day:02d} 01:00:00"),
                        "正品數量": 100.0,
                        "廢品數量": 0.0,
                        "纍計數量": 100.0,
                        "實際生產時間": 45.0,
                        "心電圖實際轉版時間": 10.0,
                        "實際計劃停機時間": 5.0,
                        "實際無計劃停機時間": 0.0,
                        "機長姓名1": "Alice",
                        "canonical_machine_id": "024-001",
                        "source_file": f"{month}_2025_csi.xlsx",
                    }
                ]
            )
        )
        self.bronze_store.write_mes_rows(
            pd.DataFrame(
                [
                    {
                        "資源": "1024-00001",
                        "報工時間": pd.Timestamp(f"2025-{month}-{day:02d} 00:50:00"),
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
                        "狀態變更時間": pd.Timestamp(f"2025-{month}-{day:02d} 00:55:00"),
                        "記錄新增時間": pd.Timestamp(f"2025-{month}-{day:02d} 00:56:00"),
                        "canonical_machine_id": "024-001",
                        "source_file": f"{month}_2025_mes.xlsx",
                    }
                ]
            )
        )
        self.bronze_store.write_maintenance_rows(
            pd.DataFrame(
                [
                    {
                        "資產": "1024-00001",
                        "資產老編號": "024-001",
                        "交易日期": pd.Timestamp(f"2025-{month}-{day:02d} 00:20:00"),
                        "工單": f"WO-{month}",
                        "工單描述": "Routine PM",
                        "工單類型": "PM",
                        "交易類型": "發出",
                        "物料編碼": "PART-001",
                        "數量": 1.0,
                        "canonical_machine_id": "024-001",
                        "source_file": f"{month}_2025_maintenance.xlsx",
                    }
                ]
            )
        )

    def _count(self, query: str, params=()):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(query, params).fetchone()[0]
        finally:
            conn.close()

    def test_month_scoped_materialization_creates_target_rows_and_preserves_other_months(self):
        self._seed_month("05", 1, 10.0)
        self._seed_month("06", 2, 20.0)

        may_result = self.materializer.materialize_month("May 2025")
        june_result = self.materializer.materialize_month("June 2025")

        self.assertEqual(may_result["status"], "success")
        self.assertEqual(june_result["status"], "success")
        self.assertEqual(june_result["silver_rows_materialized_by_table"]["energy_meter_hour"], 1)
        self.assertEqual(june_result["silver_rows_materialized_by_table"]["csi_job_event"], 1)
        self.assertEqual(june_result["silver_rows_materialized_by_table"]["mes_report_event"], 1)
        self.assertEqual(june_result["silver_rows_materialized_by_table"]["maintenance_txn_event"], 1)
        self.assertEqual(june_result["gold_fact_machine_hour_rows_created"], 1)

        self.assertEqual(
            self._count(
                "SELECT COUNT(*) FROM energy_meter_hour WHERE hour_ts >= ? AND hour_ts < ?",
                ("2025-05-01T00:00:00", "2025-06-01T00:00:00"),
            ),
            1,
        )
        self.assertEqual(
            self._count(
                "SELECT COUNT(*) FROM energy_meter_hour WHERE hour_ts >= ? AND hour_ts < ?",
                ("2025-06-01T00:00:00", "2025-07-01T00:00:00"),
            ),
            1,
        )
        self.assertEqual(
            self._count(
                "SELECT COUNT(*) FROM fact_machine_hour WHERE hour_ts >= ? AND hour_ts < ?",
                ("2025-05-01T00:00:00", "2025-06-01T00:00:00"),
            ),
            1,
        )
        self.assertEqual(
            self._count(
                "SELECT COUNT(*) FROM fact_machine_hour WHERE hour_ts >= ? AND hour_ts < ?",
                ("2025-06-01T00:00:00", "2025-07-01T00:00:00"),
            ),
            1,
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")
        self.assertEqual(len(page_df), 1)
        self.assertEqual(page_df.iloc[0]["machine_id"], "024-001")
        self.assertEqual(page_df.iloc[0]["energy_total_kwh"], 20.0)

    def test_rerun_same_month_is_idempotent_and_does_not_duplicate_rows(self):
        self._seed_month("06", 2, 20.0)

        first_result = self.materializer.materialize_month("June 2025")
        second_result = self.materializer.materialize_month("June 2025")

        self.assertEqual(first_result["gold_fact_machine_hour_rows_created"], 1)
        self.assertEqual(second_result["gold_fact_machine_hour_rows_created"], 1)
        self.assertEqual(self._count("SELECT COUNT(*) FROM energy_meter_hour"), 1)
        self.assertEqual(self._count("SELECT COUNT(*) FROM csi_job_event"), 1)
        self.assertEqual(self._count("SELECT COUNT(*) FROM mes_report_event"), 1)
        self.assertEqual(self._count("SELECT COUNT(*) FROM maintenance_txn_event"), 1)
        self.assertEqual(self._count("SELECT COUNT(*) FROM fact_machine_hour"), 1)

    def test_missing_required_bronze_rows_fails_explicitly(self):
        self._seed_month("06", 2, 20.0)
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM raw_mes_report")
        conn.commit()
        conn.close()

        with self.assertRaisesRegex(ValueError, "raw_mes_report"):
            self.materializer.materialize_month("June 2025")

    def test_summarize_month_coverage_reports_bronze_silver_gold_and_materializable_months(self):
        self._seed_month("05", 1, 10.0)
        self._seed_month("06", 2, 20.0)
        self.materializer.materialize_month("May 2025")

        summary = self.materializer.summarize_month_coverage()
        bronze_index = {
            (row["table_name"], row["month"]): row["row_count"]
            for row in summary["bronze"]
        }
        silver_index = {
            (row["table_name"], row["month"]): row["row_count"]
            for row in summary["silver"]
        }
        gold_index = {
            (row["table_name"], row["month"]): row["row_count"]
            for row in summary["gold"]
        }

        self.assertEqual(summary["materializable_months"], ["May 2025", "June 2025"])
        self.assertEqual(bronze_index[("raw_energy_hourly", "2025-05")], 1)
        self.assertEqual(bronze_index[("raw_energy_hourly", "2025-06")], 1)
        self.assertEqual(silver_index[("energy_meter_hour", "2025-05")], 1)
        self.assertNotIn(("energy_meter_hour", "2025-06"), silver_index)
        self.assertEqual(gold_index[("fact_machine_hour", "2025-05")], 1)
        self.assertNotIn(("fact_machine_hour", "2025-06"), gold_index)

    def test_mes_month_coverage_uses_report_time_not_created_or_status_time(self):
        self.bronze_store.write_mes_rows(
            pd.DataFrame(
                [
                    {
                        "資源": "1024-00075",
                        "報工時間": pd.Timestamp("2026-02-28 23:50:00"),
                        "作業": "JOB-075",
                        "任務": "印色",
                        "物料": "MAT-075",
                        "狀態變更時間": pd.Timestamp("2026-03-01 00:05:00"),
                        "記錄新增時間": pd.Timestamp("2026-03-01 00:06:00"),
                        "source_file": "task13_mes.xlsx",
                    }
                ]
            )
        )

        summary = self.materializer.summarize_month_coverage()
        bronze_index = {
            (row["table_name"], row["month"]): row["row_count"]
            for row in summary["bronze"]
        }

        self.assertEqual(bronze_index[("raw_mes_report", "2026-02")], 1)
        self.assertNotIn(("raw_mes_report", "2026-03"), bronze_index)

    def test_materialize_backfill_months_is_idempotent_and_returns_per_month_counts(self):
        self._seed_month("05", 1, 10.0)
        self._seed_month("06", 2, 20.0)

        first_run = self.materializer.materialize_backfill_months(["May 2025", "June 2025"])
        second_run = self.materializer.materialize_backfill_months(["May 2025", "June 2025"])

        self.assertEqual(first_run["status"], "success")
        self.assertEqual(second_run["status"], "success")
        self.assertEqual(len(first_run["monthly_results"]), 2)
        self.assertEqual(
            first_run["monthly_results"][0]["silver_rows_materialized_by_table"]["energy_meter_hour"],
            1,
        )
        self.assertEqual(
            first_run["monthly_results"][1]["gold_fact_machine_hour_rows_created"],
            1,
        )
        self.assertEqual(self._count("SELECT COUNT(*) FROM fact_machine_hour"), 2)
        self.assertEqual(self._count("SELECT COUNT(*) FROM energy_meter_hour"), 2)

    def test_materialize_backfill_month_uses_full_overlay_not_energy_only_backbone(self):
        self._seed_month("06", 2, 20.0)

        result = self.materializer.materialize_backfill_month("June 2025")
        page_df = self.reader.read_month_page_dataframe("June 2025")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["gold_materialization_mode"], "full_overlay")
        self.assertEqual(
            result["gold_overlay_execution_path"],
            "full_overlay_month_replace",
        )
        self.assertEqual(len(page_df), 1)
        self.assertEqual(page_df.iloc[0]["machine_state"], "setup_changeover")
        self.assertEqual(page_df.iloc[0]["order_id"], "JOB-001")
        self.assertEqual(page_df.iloc[0]["team_leader"], "Alice")
        self.assertEqual(page_df.iloc[0]["manpower"], 4.0)
        self.assertEqual(page_df.iloc[0]["good_qty"], 100.0)

        conn = sqlite3.connect(self.db_path)
        try:
            promoted_row = conn.execute(
                """
                SELECT
                    team_size,
                    has_maintenance_history,
                    maintenance_txn_in_hour,
                    maintenance_distinct_work_order_count_30d,
                    cumulative_maintenance_count
                FROM fact_machine_hour
                WHERE canonical_machine_id = '024-001'
                  AND hour_ts = '2025-06-02T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(promoted_row, (4.0, 0, 1, 0, 0))

    def test_materialize_backfill_month_preserves_dominant_quantity_under_multi_event_blend(self):
        self._seed_month("06", 2, 20.0)
        self.bronze_store.write_csi_rows(
            pd.DataFrame(
                [
                    {
                        "機台編號": "D-024-001",
                        "班次內日期": pd.Timestamp("2025-06-02").date(),
                        "班次": "D",
                        "區域": "A",
                        "作业": "JOB-EXTRA",
                        "作业后缀": "2",
                        "操作": "印刷",
                        "物料": "MAT-EXTRA",
                        "任務": "Extra",
                        "工程開始時間": pd.Timestamp("2025-06-02 00:30:00"),
                        "準備結束時間": pd.Timestamp("2025-06-02 00:30:00"),
                        "工程結束時間": pd.Timestamp("2025-06-02 01:00:00"),
                        "正品數量": 999.0,
                        "廢品數量": 99.0,
                        "纍計數量": 999.0,
                        "實際生產時間": 30.0,
                        "心電圖實際轉版時間": 0.0,
                        "實際計劃停機時間": 0.0,
                        "實際無計劃停機時間": 0.0,
                        "機長姓名1": "Bob",
                        "canonical_machine_id": "024-001",
                        "source_file": "06_2025_csi_extra.xlsx",
                    }
                ]
            )
        )

        self.materializer.materialize_backfill_month("June 2025")

        conn = sqlite3.connect(self.db_path)
        try:
            repaired_row = conn.execute(
                """
                SELECT
                    order_id,
                    multiple_csi_overlap_flag,
                    csi_overlap_minutes,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    good_qty,
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
                  AND hour_ts = '2025-06-02T00:00:00'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(repaired_row[0], "JOB-001")
        self.assertEqual(repaired_row[1], 1)
        self.assertAlmostEqual(repaired_row[2], 60.0, places=6)
        self.assertAlmostEqual(repaired_row[3], (10.0 * (60.0 / 90.0)), places=6)
        self.assertAlmostEqual(repaired_row[4], (75.0 * (60.0 / 90.0)), places=6)
        self.assertAlmostEqual(repaired_row[5], (5.0 * (60.0 / 90.0)), places=6)
        self.assertEqual(repaired_row[6], 100.0)
        self.assertEqual(repaired_row[7], "csi_dominant_event_production_minutes_share")
        self.assertAlmostEqual(repaired_row[8], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[9], 45.0, places=6)
        self.assertAlmostEqual(repaired_row[10], 5.0, places=6)
        self.assertAlmostEqual(repaired_row[11], 5.0, places=6)
        self.assertEqual(repaired_row[12], "material_misaligned")
        self.assertEqual(repaired_row[13], 1)
        self.assertEqual(repaired_row[14], 0)
        self.assertIsNone(repaired_row[15])

    def test_materialize_gold_month_debug_reports_all_cumulative_stages(self):
        self._seed_month("06", 2, 20.0)
        self.materializer._materialize_month_silver(
            self.materializer._parse_month_bounds("June 2025"),
            "June 2025",
        )

        debug_result = self.materializer.materialize_gold_month_debug("June 2025")

        self.assertEqual(debug_result["status"], "success")
        self.assertEqual(
            [stage["stage_name"] for stage in debug_result["stage_results"]],
            list(CanonicalMaterializer.GOLD_DEBUG_STAGE_NAMES),
        )
        self.assertEqual(
            debug_result["stage_results"][0]["rows_loaded_read"]["energy_meter_hour"],
            1,
        )
        self.assertEqual(
            debug_result["stage_results"][-1]["rows_written"],
            1,
        )
        self.assertEqual(
            self._count(
                "SELECT COUNT(*) FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ?",
                ("2025-06",),
            ),
            1,
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")
        self.assertEqual(len(page_df), 1)
        self.assertEqual(page_df.iloc[0]["machine_state"], "setup_changeover")

    def test_profile_gold_csi_overlay_hot_path_reports_internal_steps_and_machine_distribution(self):
        self._seed_month("06", 2, 20.0)
        self.materializer._materialize_month_silver(
            self.materializer._parse_month_bounds("June 2025"),
            "June 2025",
        )

        profile = self.materializer.profile_gold_csi_overlay_hot_path("June 2025")

        self.assertEqual(profile["status"], "success")
        self.assertEqual(profile["base_gold_row_count"], 1)
        self.assertEqual(profile["csi_job_event_row_count"], 1)
        self.assertEqual(profile["total_machine_groups_processed"], 1)
        self.assertEqual(profile["rows_with_csi_source_after_overlay"], 1)
        self.assertIn("active_event_window_maintenance_seconds", profile["internal_step_totals"])
        self.assertIn("overlap_candidate_construction_seconds", profile["internal_step_totals"])
        self.assertEqual(len(profile["top_slowest_machine_groups"]), 1)
        self.assertEqual(
            profile["top_slowest_machine_groups"][0]["canonical_machine_id"],
            "024-001",
        )
        self.assertEqual(
            profile["top_slowest_machine_groups"][0]["avg_candidate_overlap_count"],
            1.0,
        )

    def test_materialize_backfill_months_reports_missing_bronze_honestly(self):
        self._seed_month("05", 1, 10.0)

        result = self.materializer.materialize_backfill_months(["May 2025", "June 2025"])

        self.assertEqual(result["status"], "partial_error")
        self.assertEqual(result["successful_months"], ["May 2025"])
        self.assertEqual(result["failed_months"][0]["target_month"], "June 2025")
        self.assertIn("raw_energy_hourly", result["failed_months"][0]["message"])
        self.assertEqual(self._count("SELECT COUNT(*) FROM fact_machine_hour"), 1)


class AutoProcessAfterEtlTests(unittest.TestCase):
    @patch("modules.unified_view_module.CanonicalMaterializer")
    def test_auto_process_after_etl_routes_to_canonical_materializer(self, materializer_cls):
        materializer = MagicMock()
        materializer.materialize_month.return_value = {
            "status": "success",
            "target_month": "June 2025",
            "silver_materialized": True,
            "gold_materialized": True,
        }
        materializer_cls.return_value = materializer

        result = auto_process_after_etl("June 2025", db_path="/tmp/task4b.db")

        materializer_cls.assert_called_once_with(db_path="/tmp/task4b.db")
        materializer.materialize_month.assert_called_once_with("June 2025")
        self.assertEqual(result["status"], "success")


class ProcessUploadedFilesTests(unittest.TestCase):
    class _Upload:
        def __init__(self, payload: bytes):
            self._payload = payload

        def getbuffer(self):
            return self._payload

    @patch("modules.etl_module.EnhancedSmartManufacturingETL")
    @patch("modules.etl_module.get_repo_root")
    @patch("modules.etl_module.get_data_dir")
    @patch("modules.etl_module.st")
    @patch("modules.unified_view_module.auto_process_after_etl")
    @patch("core.maintenance_integration.integrate_maintenance_with_etl")
    def test_process_uploaded_files_passes_active_db_path_to_maintenance_integration(
        self,
        integrate_maintenance,
        auto_process,
        mock_st,
        get_data_dir,
        get_repo_root,
        etl_cls,
    ):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        temp_root = Path(temp_dir.name)
        temp_data_dir = temp_root / "data"
        temp_data_dir.mkdir(parents=True, exist_ok=True)
        temp_db_path = temp_root / "task4c_etl.db"

        (temp_root / "maintenance_june_2025.xlsx").write_bytes(b"maintenance")

        get_data_dir.return_value = temp_data_dir
        get_repo_root.return_value = temp_root
        mock_st.spinner.return_value = contextlib.nullcontext()
        mock_st.session_state = SimpleNamespace()

        etl_instance = MagicMock()
        etl_instance.create_comprehensive_mapping.return_value = {"mapping_stats": {}}
        etl_cls.return_value = etl_instance

        integrate_maintenance.return_value = {
            "maintenance_records": pd.DataFrame(
                [{"is_three_way_match": 1, "machine_id": "024-001"}]
            ),
            "metrics": pd.DataFrame([{"machine_id": "024-001", "total_events": 1}]),
            "predictions": pd.DataFrame(
                [{"machine_id": "024-001", "risk_level": "LOW"}]
            ),
        }
        auto_process.return_value = {
            "status": "success",
            "target_month": "June 2025",
            "silver_materialized": True,
            "gold_materialized": True,
            "silver_rows_materialized_by_table": {},
            "gold_fact_machine_hour_rows_created": 0,
        }

        etl_module = MagicMock()
        etl_module.db_path = str(temp_db_path)

        process_uploaded_files(
            energy_files=[self._Upload(b"energy")],
            csi_file=self._Upload(b"csi"),
            mes_file=self._Upload(b"mes"),
            month_year="June 2025",
            etl_module=etl_module,
        )

        integrate_maintenance.assert_called_once_with(
            str(temp_root / "maintenance_june_2025.xlsx"),
            "June 2025",
            db_path=str(temp_db_path),
        )
        auto_process.assert_called_once_with("June 2025", db_path=str(temp_db_path))


class HistoricalBackfillPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_root = Path(self.temp_dir.name)
        self.db_path = self.temp_root / "historical_backfill.db"
        self.data_root = self.temp_root / "2025 DataSet(JAN to JUN)"
        self.energy_dir = self.data_root / "Energy Usage 1hr Interval"
        self.csi_dir = self.data_root / "CSI Monthly"
        self.mes_dir = self.data_root / "MES Monthly"
        for directory in (self.energy_dir, self.csi_dir, self.mes_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def _write_month_files(self, month_name: str) -> None:
        mapping = ETLPipelineModule.HISTORICAL_MONTH_FILE_MAPPINGS[month_name]
        for file_name in mapping["energy"]:
            (self.energy_dir / file_name).write_bytes(b"energy")
        (self.csi_dir / mapping["csi"]).write_bytes(b"csi")
        (self.mes_dir / mapping["mes"]).write_bytes(b"mes")

    def test_resolve_historical_month_sources_fails_when_repo_files_are_missing(self):
        pipeline = ETLPipelineModule(db_path=self.db_path)

        with self.assertRaisesRegex(ValueError, "January 2025"):
            pipeline.resolve_historical_month_sources("January 2025", data_root=self.data_root)

    @patch("modules.etl_module.CanonicalMaterializer")
    @patch("modules.etl_module.EnhancedSmartManufacturingETL")
    def test_run_historical_canonical_backfill_reuses_existing_etl_path(
        self,
        etl_cls,
        materializer_cls,
    ):
        self._write_month_files("January")
        pipeline = ETLPipelineModule(db_path=self.db_path)

        etl = MagicMock()
        etl.create_comprehensive_mapping.return_value = {"mapping_stats": {}}
        etl_cls.return_value = etl

        materializer = MagicMock()
        materializer.materialize_backfill_month.return_value = {
            "status": "success",
            "target_month": "January 2025",
            "silver_rows_materialized_by_table": {"energy_meter_hour": 10},
            "gold_fact_machine_hour_rows_created": 5,
        }
        materializer_cls.return_value = materializer

        with patch.object(pipeline, "save_etl_results") as save_etl_results:
            result = pipeline.run_historical_canonical_backfill(
                ["January 2025"],
                data_root=self.data_root,
            )

        materializer_cls.assert_called_once_with(str(self.db_path))
        etl.extract_all_sources.assert_called_once()
        save_etl_results.assert_called_once_with({"mapping_stats": {}}, "January 2025", etl)
        materializer.materialize_backfill_month.assert_called_once_with("January 2025")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["successful_months"], ["January 2025"])
        self.assertTrue(
            result["monthly_results"][0]["source_files"]["mes_file"].endswith("MES生產數據Jan(Printer).xlsx")
        )


if __name__ == "__main__":
    unittest.main()
