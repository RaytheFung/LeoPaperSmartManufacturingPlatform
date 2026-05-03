import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.canonical_gold_reader import (
    CANONICAL_GOLD_EXPORT_COLUMNS,
    CanonicalGoldReader,
)
from core.gold_fact_builder import GoldFactBuilder


class CanonicalGoldReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "canonical_reader_test.db"
        GoldFactBuilder(self.db_path)
        self.reader = CanonicalGoldReader(self.db_path)

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
            "source_flags": json.dumps({}, sort_keys=True),
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

    def test_get_available_months_reads_fact_machine_hour_without_legacy_unified_view(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T00:00:00",
                    "energy_total_kwh": 10.0,
                },
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-05-01T00:00:00",
                    "energy_total_kwh": 9.0,
                },
            ]
        )

        conn = sqlite3.connect(self.db_path)
        legacy_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'unified_view'"
        ).fetchone()
        conn.close()

        months = self.reader.get_available_months()

        self.assertIsNone(legacy_table)
        self.assertEqual(months, ["June 2025", "May 2025"])

    def test_read_month_page_dataframe_derives_safe_kwh_and_preserves_zero_vs_null(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "state_confidence": "high",
                    "energy_total_kwh": 100.0,
                    "good_qty": 10.0,
                    "scrap_qty": 2.0,
                    "team_leader": "Alice",
                },
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T01:00:00",
                    "machine_state": "idle",
                    "state_confidence": "high",
                    "energy_total_kwh": 40.0,
                    "good_qty": 0.0,
                    "scrap_qty": 0.0,
                },
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T02:00:00",
                    "machine_state": None,
                    "state_confidence": None,
                    "energy_total_kwh": 15.0,
                    "good_qty": None,
                    "scrap_qty": None,
                },
            ]
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")

        self.assertEqual(len(page_df), 3)
        self.assertEqual(page_df.iloc[0]["production_qty"], 10.0)
        self.assertEqual(page_df.iloc[0]["kwh_per_good_unit"], 10.0)
        self.assertEqual(page_df.iloc[1]["production_qty"], 0.0)
        self.assertTrue(pd.isna(page_df.iloc[1]["kwh_per_good_unit"]))
        self.assertEqual(page_df.iloc[1]["scrap_qty"], 0.0)
        self.assertTrue(pd.isna(page_df.iloc[2]["production_qty"]))
        self.assertTrue(pd.isna(page_df.iloc[2]["scrap_qty"]))
        self.assertEqual(page_df.iloc[2]["state_bucket"], "unknown")

    def test_maintenance_in_hour_derives_from_source_flags_or_machine_state(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-02T00:00:00",
                    "source_flags": json.dumps({"maintenance_txn_in_hour": True}, sort_keys=True),
                },
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-02T01:00:00",
                    "machine_state": "maintenance",
                    "source_flags": json.dumps({}, sort_keys=True),
                },
            ]
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")

        self.assertEqual(page_df.iloc[0]["maintenance_in_hour"], 1)
        self.assertEqual(page_df.iloc[1]["maintenance_in_hour"], 1)
        self.assertEqual(page_df.iloc[1]["state_label"], "Maintenance")

    def test_build_export_dataframe_has_deterministic_column_order(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-011",
                    "hour_ts": "2025-06-03T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 25.0,
                    "good_qty": 5.0,
                }
            ]
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")
        export_df = self.reader.build_export_dataframe(page_df)

        self.assertEqual(list(export_df.columns), CANONICAL_GOLD_EXPORT_COLUMNS)

    def test_build_month_metrics_uses_weighted_efficiency_ratio(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-04T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "good_qty": 100.0,
                },
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-04T01:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 90.0,
                    "good_qty": 10.0,
                },
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-04T02:00:00",
                    "machine_state": "idle",
                    "energy_total_kwh": 20.0,
                    "good_qty": 0.0,
                },
            ]
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")
        metrics = self.reader.build_month_metrics(page_df)

        self.assertAlmostEqual(metrics["weighted_kwh_per_good_unit"], 190.0 / 110.0)
        self.assertAlmostEqual(metrics["efficiency_energy_kwh"], 190.0)
        self.assertAlmostEqual(metrics["efficiency_good_qty"], 110.0)
        self.assertAlmostEqual(metrics["total_energy_total_kwh"], 210.0)
        self.assertAlmostEqual(metrics["total_good_qty"], 110.0)

    def test_build_state_summary_includes_energy_totals_for_chart_contract(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-021",
                    "hour_ts": "2025-06-04T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "good_qty": 100.0,
                },
                {
                    "canonical_machine_id": "024-022",
                    "hour_ts": "2025-06-04T01:00:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 90.0,
                    "good_qty": 10.0,
                },
                {
                    "canonical_machine_id": "024-023",
                    "hour_ts": "2025-06-04T02:00:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 10.0,
                    "good_qty": 0.0,
                },
            ]
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")
        state_summary = self.reader.build_state_summary(page_df)

        self.assertEqual(list(state_summary.columns), ["state_bucket", "state_label", "row_count", "energy_kwh", "energy_share"])
        self.assertAlmostEqual(state_summary["energy_kwh"].sum(), 200.0)
        self.assertAlmostEqual(state_summary["energy_share"].sum(), 1.0)
        self.assertAlmostEqual(
            state_summary.loc[state_summary["state_label"] == "Production", "energy_kwh"].iloc[0],
            100.0,
        )
        self.assertAlmostEqual(
            state_summary.loc[state_summary["state_label"] == "Production", "energy_share"].iloc[0],
            0.5,
        )
        self.assertEqual(
            int(state_summary.loc[state_summary["state_label"] == "Setup Changeover", "row_count"].iloc[0]),
            2,
        )

    def test_empty_month_returns_empty_dataframe(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-099",
                    "hour_ts": "2025-05-01T00:00:00",
                    "energy_total_kwh": 5.0,
                }
            ]
        )

        page_df = self.reader.read_month_page_dataframe("June 2025")

        self.assertTrue(page_df.empty)
        self.assertEqual(list(page_df.columns), CANONICAL_GOLD_EXPORT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
