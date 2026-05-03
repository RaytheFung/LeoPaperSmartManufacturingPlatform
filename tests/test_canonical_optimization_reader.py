import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import core.canonical_optimization_reader as optimization_reader_module
from core.canonical_optimization_reader import (
    CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS,
    CANONICAL_OPTIMIZATION_SUMMARY_COLUMNS,
    CANONICAL_OPTIMIZATION_TEAM_COLUMNS,
    CanonicalOptimizationReader,
)
from core.gold_fact_builder import GoldFactBuilder


class CanonicalOptimizationReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "canonical_optimization_reader.db"
        GoldFactBuilder(self.db_path)
        self.reader = CanonicalOptimizationReader(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _insert_fact_rows(self, rows):
        defaults = {
            "canonical_machine_id": None,
            "hour_ts": None,
            "machine_state": None,
            "state_confidence": None,
            "energy_total_kwh": None,
            "energy_total_cost": None,
            "energy_main_kwh": None,
            "energy_uv_kwh": None,
            "energy_ir_kwh": None,
            "energy_motor_kwh": None,
            "source_flags": "{}",
            "energy_total_source_method": "aggregate_total_preferred",
            "energy_source_row_count": 1,
            "energy_source_row_hashes_json": '["energy-hash"]',
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
            "attribution_method": "energy_csi_overlay",
        }
        prepared_rows = []
        for row in rows:
            merged = dict(defaults)
            merged.update(row)
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(prepared_rows).to_sql("fact_machine_hour", conn, if_exists="append", index=False)
        conn.close()

    def test_available_months_and_summary_read_fact_machine_hour_without_legacy_table(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 20.0,
                    "production_minutes": 60.0,
                    "good_qty": 10.0,
                },
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-05-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 10.0,
                    "production_minutes": 60.0,
                    "good_qty": 5.0,
                },
            ]
        )

        conn = sqlite3.connect(self.db_path)
        legacy_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'unified_view'"
        ).fetchone()
        conn.close()

        months = self.reader.get_available_months()
        june_summary = self.reader.build_machine_summary("June 2025")

        self.assertIsNone(legacy_table)
        self.assertEqual(months, ["June 2025", "May 2025"])
        self.assertEqual(len(june_summary), 1)
        self.assertEqual(june_summary.iloc[0]["machine_id"], "024-001")

    def test_machine_summary_derives_safe_rates_and_hours(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 20.0,
                    "scrap_qty": 2.0,
                    "hours_since_last_maintenance": 10.0,
                },
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T01:00:00",
                    "machine_state": "idle",
                    "energy_total_kwh": 20.0,
                    "idle_minutes": 60.0,
                    "good_qty": 0.0,
                    "scrap_qty": 0.0,
                    "hours_since_last_maintenance": 14.0,
                },
            ]
        )

        summary_df = self.reader.build_machine_summary("June 2025")
        row = summary_df.iloc[0]

        self.assertEqual(row["total_energy_kwh"], 120.0)
        self.assertEqual(row["total_good_qty"], 20.0)
        self.assertEqual(row["total_scrap_qty"], 2.0)
        self.assertEqual(row["avg_kwh_per_good_unit"], 5.0)
        self.assertAlmostEqual(row["avg_hours_since_last_maintenance"], 12.0)
        self.assertEqual(row["production_state_hours"], 1)
        self.assertEqual(row["setup_state_hours"], 0)
        self.assertEqual(row["maintenance_state_hours"], 0)
        self.assertEqual(row["productive_hours"], 1.0)
        self.assertEqual(row["nonproductive_hours"], 1.0)
        self.assertEqual(row["utilization_proxy"], 0.5)
        self.assertAlmostEqual(row["scrap_rate"], 2.0 / 22.0)
        self.assertEqual(row["top_driver"], "High non-productive share")

    def test_opportunity_score_and_ranking_are_deterministic(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-100",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 200.0,
                    "production_minutes": 30.0,
                    "idle_minutes": 30.0,
                    "good_qty": 10.0,
                    "scrap_qty": 5.0,
                    "hours_since_last_maintenance": 100.0,
                },
                {
                    "canonical_machine_id": "024-100",
                    "hour_ts": "2025-06-01T01:00:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 50.0,
                    "setup_minutes": 60.0,
                    "hours_since_last_maintenance": 100.0,
                },
                {
                    "canonical_machine_id": "024-200",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 50.0,
                    "scrap_qty": 0.0,
                    "hours_since_last_maintenance": 10.0,
                },
                {
                    "canonical_machine_id": "024-300",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 150.0,
                    "production_minutes": 60.0,
                    "good_qty": 30.0,
                    "scrap_qty": 1.0,
                    "hours_since_last_maintenance": 50.0,
                },
                {
                    "canonical_machine_id": "024-300",
                    "hour_ts": "2025-06-01T01:00:00",
                    "machine_state": "idle",
                    "energy_total_kwh": 25.0,
                    "idle_minutes": 60.0,
                    "hours_since_last_maintenance": 50.0,
                },
            ]
        )

        first_summary = self.reader.build_machine_summary("June 2025")
        second_summary = self.reader.build_machine_summary("June 2025")

        self.assertEqual(
            first_summary["machine_id"].tolist(),
            second_summary["machine_id"].tolist(),
        )
        self.assertEqual(
            first_summary["opportunity_score"].tolist(),
            second_summary["opportunity_score"].tolist(),
        )
        self.assertEqual(first_summary.iloc[0]["machine_id"], "024-100")
        self.assertEqual(first_summary.iloc[-1]["machine_id"], "024-200")
        self.assertEqual(first_summary.iloc[0]["opportunity_flag"], "High")

    def test_empty_month_returns_empty_summary(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-999",
                    "hour_ts": "2025-05-01T00:00:00",
                    "energy_total_kwh": 5.0,
                }
            ]
        )

        summary_df = self.reader.build_machine_summary("June 2025")

        self.assertTrue(summary_df.empty)
        self.assertEqual(list(summary_df.columns), CANONICAL_OPTIMIZATION_SUMMARY_COLUMNS)

    def test_schedule_summary_uses_canonical_hourly_aggregates(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 40.0,
                    "production_minutes": 60.0,
                    "good_qty": 20.0,
                },
                {
                    "canonical_machine_id": "024-011",
                    "hour_ts": "2025-06-01T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 24.0,
                    "production_minutes": 60.0,
                    "good_qty": 12.0,
                },
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T16:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 15.0,
                    "production_minutes": 60.0,
                    "good_qty": 30.0,
                },
                {
                    "canonical_machine_id": "024-011",
                    "hour_ts": "2025-06-01T16:00:00",
                    "machine_state": "idle",
                    "energy_total_kwh": 5.0,
                    "idle_minutes": 60.0,
                    "good_qty": 0.0,
                },
            ]
        )

        schedule_df = self.reader.build_schedule_summary("June 2025")

        self.assertEqual(list(schedule_df.columns), CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS)
        self.assertEqual(schedule_df.iloc[0]["hour_of_day"], 16)
        self.assertEqual(schedule_df.iloc[0]["shift_label"], "Evening")
        self.assertEqual(schedule_df.iloc[0]["eligible_rows"], 1)
        self.assertEqual(schedule_df.iloc[0]["distinct_machines"], 2)
        self.assertAlmostEqual(schedule_df.iloc[0]["avg_kwh_per_good_unit"], 0.5)
        self.assertEqual(schedule_df.iloc[0]["top_driver"], "Low kWh per good unit")
        self.assertGreater(schedule_df.iloc[0]["schedule_score"], schedule_df.iloc[1]["schedule_score"])

    def test_team_insights_rank_named_team_leaders_only(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-01T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 30.0,
                    "production_minutes": 60.0,
                    "good_qty": 20.0,
                    "scrap_qty": 0.0,
                    "team_leader": "Leader A",
                    "hours_since_last_maintenance": 20.0,
                },
                {
                    "canonical_machine_id": "024-021",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 20.0,
                    "production_minutes": 60.0,
                    "good_qty": 20.0,
                    "scrap_qty": 0.0,
                    "team_leader": "Leader A",
                    "hours_since_last_maintenance": 24.0,
                },
                {
                    "canonical_machine_id": "024-030",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 60.0,
                    "production_minutes": 60.0,
                    "good_qty": 20.0,
                    "scrap_qty": 5.0,
                    "team_leader": "Leader B",
                    "hours_since_last_maintenance": 80.0,
                },
                {
                    "canonical_machine_id": "024-031",
                    "hour_ts": "2025-06-01T11:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 10.0,
                    "production_minutes": 60.0,
                    "good_qty": 0.0,
                    "scrap_qty": 0.0,
                    "team_leader": "",
                    "hours_since_last_maintenance": 50.0,
                },
            ]
        )

        team_df = self.reader.build_team_insights("June 2025")

        self.assertEqual(list(team_df.columns), CANONICAL_OPTIMIZATION_TEAM_COLUMNS)
        self.assertEqual(team_df.iloc[0]["team_leader"], "Leader A")
        self.assertEqual(team_df.iloc[0]["distinct_machines"], 2)
        self.assertEqual(team_df.iloc[0]["rows_with_team"], 2)
        self.assertAlmostEqual(team_df.iloc[0]["avg_kwh_per_good_unit"], 1.25)
        self.assertEqual(team_df.iloc[0]["team_band"], "Strong")
        self.assertEqual(team_df.iloc[0]["top_driver"], "Low kWh per good unit")
        self.assertEqual(team_df.iloc[-1]["team_leader"], "Leader B")

    def test_team_insights_returns_empty_when_no_named_team_rows_exist(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-040",
                    "hour_ts": "2025-06-01T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 25.0,
                    "production_minutes": 60.0,
                    "good_qty": 10.0,
                    "team_leader": None,
                }
            ]
        )

        team_df = self.reader.build_team_insights("June 2025")

        self.assertTrue(team_df.empty)
        self.assertEqual(list(team_df.columns), CANONICAL_OPTIMIZATION_TEAM_COLUMNS)

    def test_reader_source_contains_no_legacy_or_demo_fallback(self):
        source_text = Path(optimization_reader_module.__file__).read_text(encoding="utf-8").lower()

        self.assertNotIn("unified_view", source_text)
        self.assertNotIn("demo", source_text)


if __name__ == "__main__":
    unittest.main()
