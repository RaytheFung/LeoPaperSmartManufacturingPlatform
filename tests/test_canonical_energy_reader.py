import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.canonical_energy_reader import (
    CANONICAL_ENERGY_EXPORT_COLUMNS,
    CanonicalEnergyReader,
)
from core.gold_fact_builder import GoldFactBuilder


class CanonicalEnergyReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "canonical_energy_reader.db"
        GoldFactBuilder(self.db_path)
        self.reader = CanonicalEnergyReader(self.db_path)

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

    def test_month_dataframe_reads_fact_machine_hour_without_unified_view(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T00:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 10.0,
                    "production_minutes": 60.0,
                    "good_qty": 5.0,
                },
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-05-01T00:00:00",
                    "machine_state": "idle",
                    "energy_total_kwh": 8.0,
                    "idle_minutes": 60.0,
                    "good_qty": 0.0,
                },
            ]
        )

        conn = sqlite3.connect(self.db_path)
        legacy_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'unified_view'"
        ).fetchone()
        conn.close()

        months = self.reader.get_available_months()
        energy_df = self.reader.read_month_energy_dataframe("June 2025")

        self.assertIsNone(legacy_table)
        self.assertEqual(months, ["June 2025", "May 2025"])
        self.assertEqual(list(energy_df.columns), CANONICAL_ENERGY_EXPORT_COLUMNS)
        self.assertEqual(len(energy_df), 1)
        self.assertEqual(energy_df.iloc[0]["machine_id"], "024-001")

    def test_energy_attribution_prefers_minute_share_then_row_state_fallback(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 120.0,
                    "production_minutes": 30.0,
                    "idle_minutes": 30.0,
                    "good_qty": 40.0,
                },
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": "maintenance",
                    "energy_total_kwh": 20.0,
                    "good_qty": 0.0,
                },
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "energy_only",
                    "energy_total_kwh": 15.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")

        first_row = energy_df.iloc[0]
        self.assertEqual(first_row["energy_attribution_method"], "minute_share")
        self.assertAlmostEqual(first_row["production_energy_kwh"], 60.0)
        self.assertAlmostEqual(first_row["idle_energy_kwh"], 60.0)
        self.assertAlmostEqual(first_row["unallocated_energy_kwh"], 0.0)
        self.assertAlmostEqual(first_row["kwh_per_good_unit"], 3.0)

        second_row = energy_df.iloc[1]
        self.assertEqual(second_row["energy_attribution_method"], "machine_state_fallback")
        self.assertAlmostEqual(second_row["maintenance_energy_kwh"], 20.0)

        third_row = energy_df.iloc[2]
        self.assertEqual(third_row["energy_attribution_method"], "unallocated")
        self.assertAlmostEqual(third_row["unallocated_energy_kwh"], 15.0)

    def test_breakdown_and_maintenance_curve_are_built_from_canonical_rows(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-01T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 50.0,
                    "hours_since_last_maintenance": 50.0,
                },
                {
                    "canonical_machine_id": "024-021",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 90.0,
                    "production_minutes": 60.0,
                    "good_qty": 45.0,
                    "hours_since_last_maintenance": 100.0,
                },
                {
                    "canonical_machine_id": "024-022",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "idle",
                    "energy_total_kwh": 20.0,
                    "idle_minutes": 60.0,
                    "good_qty": 0.0,
                    "hours_since_last_maintenance": 300.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")
        breakdown_df = self.reader.build_energy_breakdown(energy_df)
        curve_df = self.reader.build_maintenance_efficiency_curve(
            month_year="June 2025",
            min_bucket_count=1,
        )

        self.assertEqual(breakdown_df.iloc[0]["energy_bucket"], "Production")
        self.assertAlmostEqual(
            breakdown_df.loc[breakdown_df["energy_bucket"] == "Production", "energy_kwh"].iloc[0],
            190.0,
        )
        self.assertAlmostEqual(
            breakdown_df.loc[breakdown_df["energy_bucket"] == "Idle", "energy_kwh"].iloc[0],
            20.0,
        )
        self.assertEqual(curve_df.iloc[0]["bucket"], "0-200h")
        self.assertAlmostEqual(curve_df.iloc[0]["weighted_kwh_per_good_unit"], 2.0)
        self.assertEqual(int(curve_df.iloc[0]["row_count"]), 2)

    def test_month_summary_uses_weighted_ratio_not_row_mean(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-030",
                    "hour_ts": "2025-06-02T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 100.0,
                },
                {
                    "canonical_machine_id": "024-030",
                    "hour_ts": "2025-06-02T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 90.0,
                    "production_minutes": 60.0,
                    "good_qty": 10.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")
        summary = self.reader.build_month_summary(energy_df)

        self.assertAlmostEqual(summary["weighted_kwh_per_good_unit"], 190.0 / 110.0)
        self.assertAlmostEqual(summary["efficiency_energy_kwh"], 190.0)
        self.assertAlmostEqual(summary["efficiency_good_qty"], 110.0)
        self.assertNotAlmostEqual(summary["weighted_kwh_per_good_unit"], 5.0)

    def test_machine_ranking_uses_weighted_ratio_per_machine(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-040",
                    "hour_ts": "2025-06-03T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 10.0,
                    "production_minutes": 60.0,
                    "good_qty": 1.0,
                },
                {
                    "canonical_machine_id": "024-040",
                    "hour_ts": "2025-06-03T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 100.0,
                },
                {
                    "canonical_machine_id": "024-041",
                    "hour_ts": "2025-06-03T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 75.0,
                    "production_minutes": 60.0,
                    "good_qty": 50.0,
                },
                {
                    "canonical_machine_id": "024-041",
                    "hour_ts": "2025-06-03T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 75.0,
                    "production_minutes": 60.0,
                    "good_qty": 50.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")
        ranking_df = self.reader.build_machine_efficiency_ranking(energy_df)

        self.assertEqual(ranking_df.iloc[0]["machine_id"], "024-040")
        self.assertAlmostEqual(ranking_df.iloc[0]["weighted_kwh_per_good_unit"], 110.0 / 101.0)
        self.assertEqual(int(ranking_df.iloc[0]["row_count"]), 2)
        self.assertAlmostEqual(ranking_df.iloc[1]["weighted_kwh_per_good_unit"], 1.5)

    def test_machine_energy_summary_preserves_energy_and_support_columns(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-040",
                    "hour_ts": "2025-06-03T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 10.0,
                    "production_minutes": 60.0,
                    "good_qty": 1.0,
                },
                {
                    "canonical_machine_id": "024-040",
                    "hour_ts": "2025-06-03T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 100.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")
        summary_df = self.reader.build_machine_energy_summary(energy_df)

        self.assertEqual(list(summary_df.columns), ["machine_id", "weighted_kwh_per_good_unit", "row_count", "total_good_qty", "total_energy_kwh"])
        self.assertEqual(summary_df.iloc[0]["machine_id"], "024-040")
        self.assertAlmostEqual(summary_df.iloc[0]["weighted_kwh_per_good_unit"], 110.0 / 101.0)
        self.assertEqual(int(summary_df.iloc[0]["row_count"]), 2)
        self.assertAlmostEqual(summary_df.iloc[0]["total_energy_kwh"], 110.0)

    def test_maintenance_curve_uses_weighted_ratio_per_bucket(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-050",
                    "hour_ts": "2025-06-04T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 100.0,
                    "production_minutes": 60.0,
                    "good_qty": 100.0,
                    "hours_since_last_maintenance": 50.0,
                },
                {
                    "canonical_machine_id": "024-051",
                    "hour_ts": "2025-06-04T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 90.0,
                    "production_minutes": 60.0,
                    "good_qty": 10.0,
                    "hours_since_last_maintenance": 100.0,
                },
            ]
        )

        curve_df = self.reader.build_maintenance_efficiency_curve(
            month_year="June 2025",
            min_bucket_count=1,
        )

        self.assertEqual(curve_df.iloc[0]["bucket"], "0-200h")
        self.assertAlmostEqual(curve_df.iloc[0]["weighted_kwh_per_good_unit"], 190.0 / 110.0)
        self.assertEqual(int(curve_df.iloc[0]["row_count"]), 2)
        self.assertNotAlmostEqual(curve_df.iloc[0]["weighted_kwh_per_good_unit"], 5.0)

    def test_maintenance_curve_final_bucket_label_matches_capped_4000h_edge(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-060",
                    "hour_ts": "2025-06-05T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 40.0,
                    "production_minutes": 60.0,
                    "good_qty": 20.0,
                    "hours_since_last_maintenance": 2500.0,
                },
                {
                    "canonical_machine_id": "024-061",
                    "hour_ts": "2025-06-05T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 30.0,
                    "production_minutes": 60.0,
                    "good_qty": 10.0,
                    "hours_since_last_maintenance": 4500.0,
                },
            ]
        )

        curve_df = self.reader.build_maintenance_efficiency_curve(
            month_year="June 2025",
            min_bucket_count=1,
        )

        self.assertEqual(list(curve_df["bucket"]), ["2000-4000h"])
        self.assertAlmostEqual(curve_df.iloc[0]["weighted_kwh_per_good_unit"], 2.0)
        self.assertEqual(int(curve_df.iloc[0]["row_count"]), 1)

    def test_attribution_trust_summary_reports_energy_share_by_method(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-070",
                    "hour_ts": "2025-06-06T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 60.0,
                    "production_minutes": 30.0,
                    "idle_minutes": 30.0,
                    "good_qty": 10.0,
                },
                {
                    "canonical_machine_id": "024-070",
                    "hour_ts": "2025-06-06T09:00:00",
                    "machine_state": "maintenance",
                    "energy_total_kwh": 30.0,
                    "good_qty": 0.0,
                },
                {
                    "canonical_machine_id": "024-070",
                    "hour_ts": "2025-06-06T10:00:00",
                    "machine_state": "energy_only",
                    "energy_total_kwh": 10.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")
        trust_df = self.reader.build_attribution_trust_summary(energy_df)

        self.assertEqual(
            trust_df.loc[trust_df["attribution_method"] == "minute_share", "attribution_label"].iloc[0],
            "Minute-share attribution",
        )
        self.assertIn(
            "minute shares",
            trust_df.loc[trust_df["attribution_method"] == "minute_share", "meaning"].iloc[0].lower(),
        )
        self.assertAlmostEqual(
            trust_df.loc[trust_df["attribution_method"] == "minute_share", "energy_share"].iloc[0],
            0.6,
        )
        self.assertAlmostEqual(
            trust_df.loc[trust_df["attribution_method"] == "unallocated", "energy_share"].iloc[0],
            0.1,
        )

    def test_attribution_coverage_summary_makes_coverage_and_residual_explicit(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-080",
                    "hour_ts": "2025-06-07T08:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 60.0,
                    "production_minutes": 30.0,
                    "idle_minutes": 30.0,
                    "good_qty": 10.0,
                },
                {
                    "canonical_machine_id": "024-080",
                    "hour_ts": "2025-06-07T09:00:00",
                    "machine_state": "maintenance",
                    "energy_total_kwh": 30.0,
                    "good_qty": 0.0,
                },
                {
                    "canonical_machine_id": "024-080",
                    "hour_ts": "2025-06-07T10:00:00",
                    "machine_state": "energy_only",
                    "energy_total_kwh": 10.0,
                },
                {
                    "canonical_machine_id": "024-080",
                    "hour_ts": "2025-06-07T11:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 0.0,
                    "good_qty": 2.0,
                },
            ]
        )

        energy_df = self.reader.read_month_energy_dataframe("June 2025")
        coverage = self.reader.build_attribution_coverage_summary(energy_df)

        self.assertAlmostEqual(coverage["total_energy_kwh"], 100.0)
        self.assertAlmostEqual(coverage["attributed_energy_kwh"], 90.0)
        self.assertAlmostEqual(coverage["residual_energy_kwh"], 10.0)
        self.assertAlmostEqual(coverage["attributed_energy_share"], 0.9)
        self.assertAlmostEqual(coverage["residual_energy_share"], 0.1)
        self.assertEqual(coverage["positive_energy_rows"], 3)
        self.assertEqual(coverage["attributed_positive_energy_rows"], 2)
        self.assertEqual(coverage["residual_positive_energy_rows"], 1)
        self.assertAlmostEqual(coverage["attributed_positive_energy_row_share"], 2.0 / 3.0)
        self.assertEqual(coverage["no_energy_rows"], 1)

    def test_daily_energy_anomalies_flags_high_outlier_days(self):
        daily_energy_df = pd.DataFrame(
            [
                {"date": pd.Timestamp("2025-06-01"), "Production": 100.0, "Idle": 0.0},
                {"date": pd.Timestamp("2025-06-02"), "Production": 110.0, "Idle": 0.0},
                {"date": pd.Timestamp("2025-06-03"), "Production": 105.0, "Idle": 0.0},
                {"date": pd.Timestamp("2025-06-04"), "Production": 420.0, "Idle": 0.0},
                {"date": pd.Timestamp("2025-06-05"), "Production": 98.0, "Idle": 0.0},
            ]
        )

        anomaly_df = self.reader.build_daily_energy_anomalies(daily_energy_df)

        self.assertEqual(len(anomaly_df), 1)
        self.assertEqual(anomaly_df.iloc[0]["date"], pd.Timestamp("2025-06-04"))
        self.assertEqual(anomaly_df.iloc[0]["direction"], "High")


if __name__ == "__main__":
    unittest.main()
