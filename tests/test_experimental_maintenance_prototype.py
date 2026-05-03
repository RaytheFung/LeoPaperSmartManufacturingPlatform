import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.experimental_maintenance_prototype import (
    build_predictive_maintenance_export_artifacts,
    build_predictive_maintenance_prototype,
)


class ExperimentalMaintenancePrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "experimental_maintenance.db"
        self._create_tables()
        self._insert_fact_rows()
        self._insert_maintenance_rows()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE fact_machine_hour (
                canonical_machine_id TEXT,
                hour_ts TEXT,
                good_qty REAL,
                energy_total_kwh REAL,
                idle_minutes REAL,
                setup_minutes REAL,
                planned_stop_minutes REAL,
                unplanned_stop_minutes REAL,
                production_minutes REAL,
                hours_since_last_maintenance REAL,
                days_since_last_maintenance REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order TEXT,
                work_order_type TEXT,
                transaction_date TEXT,
                material_code TEXT,
                month_year TEXT,
                machine_id TEXT,
                canonical_machine_id TEXT,
                is_three_way_match INTEGER
            )
            """
        )
        conn.commit()
        conn.close()

    def _insert_fact_rows(self):
        rows = []
        for day in range(1, 11):
            rows.append(
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": f"2025-01-{day:02d}T08:00:00",
                    "good_qty": 200.0 + day * 10.0,
                    "energy_total_kwh": 10.0 + day,
                    "idle_minutes": 5.0,
                    "setup_minutes": 10.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 0.0,
                    "production_minutes": 45.0,
                    "hours_since_last_maintenance": 12.0 + day * 6.0,
                    "days_since_last_maintenance": (12.0 + day * 6.0) / 24.0,
                }
            )
            rows.append(
                {
                    "canonical_machine_id": "024-002",
                    "hour_ts": f"2025-01-{day:02d}T08:00:00",
                    "good_qty": 180.0 + day * 8.0,
                    "energy_total_kwh": 9.0 + day,
                    "idle_minutes": 15.0,
                    "setup_minutes": 5.0,
                    "planned_stop_minutes": 0.0,
                    "unplanned_stop_minutes": 5.0,
                    "production_minutes": 35.0,
                    "hours_since_last_maintenance": 40.0 + day * 5.0,
                    "days_since_last_maintenance": (40.0 + day * 5.0) / 24.0,
                }
            )
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(rows).to_sql("fact_machine_hour", conn, if_exists="append", index=False)
        conn.close()

    def _insert_maintenance_rows(self):
        rows = [
            {
                "work_order": "WO-001",
                "work_order_type": "PM",
                "transaction_date": "2025-01-06 09:00:00",
                "material_code": "MAT-A",
                "month_year": "January 2025",
                "machine_id": "024-001",
                "canonical_machine_id": "024-001",
                "is_three_way_match": 1,
            },
            {
                "work_order": "WO-002",
                "work_order_type": "CM",
                "transaction_date": "2025-01-12 09:00:00",
                "material_code": "MAT-A",
                "month_year": "January 2025",
                "machine_id": "024-001",
                "canonical_machine_id": "024-001",
                "is_three_way_match": 1,
            },
            {
                "work_order": "WO-003",
                "work_order_type": "PM",
                "transaction_date": "2025-01-08 09:00:00",
                "material_code": "MAT-B",
                "month_year": "January 2025",
                "machine_id": "024-002",
                "canonical_machine_id": "024-002",
                "is_three_way_match": 1,
            },
        ]
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(rows).to_sql("maintenance_records", conn, if_exists="append", index=False)
        conn.close()

    def _hash_db(self) -> str:
        return hashlib.sha1(self.db_path.read_bytes()).hexdigest()

    def test_label_construction_uses_actual_future_horizon_events(self):
        payload = build_predictive_maintenance_prototype(
            "January 2025",
            horizon_days=7,
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        snapshot_df = payload["snapshot_df"]
        target_row = snapshot_df[
            (snapshot_df["machine_id"] == "024-001")
            & (snapshot_df["snapshot_date"] == pd.Timestamp("2025-01-05"))
        ].iloc[0]
        self.assertEqual(int(target_row["label_available"]), 1)
        self.assertEqual(int(target_row["label"]), 1)

    def test_sparse_dataset_triggers_fallback_mode(self):
        payload = build_predictive_maintenance_prototype(
            "January 2025",
            horizon_days=7,
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        self.assertEqual(payload["prototype_mode"], "Fallback evidence score")
        self.assertFalse(payload["risk_table_df"].empty)

    def test_payload_reports_maintenance_event_horizon_end(self):
        payload = build_predictive_maintenance_prototype(
            "January 2025",
            horizon_days=7,
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        self.assertEqual(payload["maintenance_event_horizon_end"], "2025-01-12")
        self.assertIn("2025-01-12", payload["prototype_note"])

    def test_export_artifacts_include_manifest_and_frames(self):
        payload = build_predictive_maintenance_prototype(
            "January 2025",
            horizon_days=7,
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        export_artifacts = build_predictive_maintenance_export_artifacts(
            payload,
            runtime_mode="pilot_review",
            anchor_month="January 2025",
        )

        self.assertIn("maintenance_risk_table.csv", export_artifacts["export_frames"])
        self.assertIn("maintenance_evidence_factors.csv", export_artifacts["export_frames"])
        self.assertIn('"runtime_mode": "pilot_review"', export_artifacts["manifest_json"])
        self.assertIn('"prototype": "predictive_maintenance_prototype"', export_artifacts["manifest_json"])

    def test_helper_is_read_only(self):
        before_hash = self._hash_db()
        payload = build_predictive_maintenance_prototype(
            "January 2025",
            horizon_days=7,
            db_path=self.db_path,
        )
        after_hash = self._hash_db()

        self.assertFalse(payload["blocked"])
        self.assertEqual(before_hash, after_hash)


if __name__ == "__main__":
    unittest.main()
