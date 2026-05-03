import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from core.runtime_mode import DEMO_READONLY_RUNTIME_MODE, STANDARD_RUNTIME_MODE
from modules.experimental_intelligence_lab_module import build_experimental_lab_route_snapshot


class PredictorStub:
    loaded_model = True
    loaded_preprocessor = True

    def predict_efficiency(self, **kwargs):
        machine_id = str(kwargs.get("machine_id"))
        if machine_id.endswith("003"):
            return {
                "efficiency": 0.018,
                "confidence": 0.82,
                "feature_impacts": {},
                "source": "model",
            }
        return {
            "efficiency": 0.021,
            "confidence": 0.80,
            "feature_impacts": {},
            "source": "model",
        }


class ExperimentalIntelligenceLabRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "experimental_route.db"
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
                machine_state TEXT,
                material_code TEXT,
                task_name TEXT,
                good_qty REAL,
                scrap_qty REAL,
                energy_total_kwh REAL,
                energy_total_cost REAL,
                setup_minutes REAL,
                production_minutes REAL,
                planned_stop_minutes REAL,
                unplanned_stop_minutes REAL,
                idle_minutes REAL,
                team_leader TEXT,
                team_size REAL,
                hours_since_last_maintenance REAL,
                days_since_last_maintenance REAL,
                last_maintenance_work_order_type TEXT,
                maintenance_distinct_work_order_count_30d REAL,
                cumulative_maintenance_count REAL
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
        rows = [
            {
                "canonical_machine_id": "024-001",
                "hour_ts": "2025-06-01T08:00:00",
                "machine_state": "production",
                "material_code": "MAT-A",
                "task_name": "印刷",
                "good_qty": 260.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 12.0,
                "energy_total_cost": 24.0,
                "setup_minutes": 0.0,
                "production_minutes": 60.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader A",
                "team_size": 2.0,
                "hours_since_last_maintenance": 18.0,
                "days_since_last_maintenance": 0.75,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 4.0,
            },
            {
                "canonical_machine_id": "024-002",
                "hour_ts": "2025-06-02T08:00:00",
                "machine_state": "production",
                "material_code": "MAT-B",
                "task_name": "印刷+光油",
                "good_qty": 320.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 15.0,
                "energy_total_cost": 30.0,
                "setup_minutes": 0.0,
                "production_minutes": 60.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader B",
                "team_size": 3.0,
                "hours_since_last_maintenance": 42.0,
                "days_since_last_maintenance": 1.75,
                "last_maintenance_work_order_type": "CM",
                "maintenance_distinct_work_order_count_30d": 2.0,
                "cumulative_maintenance_count": 5.0,
            },
            {
                "canonical_machine_id": "024-003",
                "hour_ts": "2025-06-03T08:00:00",
                "machine_state": "production",
                "material_code": "MAT-C",
                "task_name": "光油",
                "good_qty": 340.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 17.0,
                "energy_total_cost": 34.0,
                "setup_minutes": 0.0,
                "production_minutes": 60.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader C",
                "team_size": 2.0,
                "hours_since_last_maintenance": 70.0,
                "days_since_last_maintenance": 2.9,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 3.0,
            },
        ]
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(rows).to_sql("fact_machine_hour", conn, if_exists="append", index=False)
        conn.close()

    def _insert_maintenance_rows(self):
        rows = [
            {
                "work_order": "WO-001",
                "work_order_type": "PM",
                "transaction_date": "2025-05-28 08:00:00",
                "material_code": "MAT-A",
                "month_year": "May 2025",
                "machine_id": "024-001",
                "canonical_machine_id": "024-001",
                "is_three_way_match": 1,
            },
            {
                "work_order": "WO-002",
                "work_order_type": "CM",
                "transaction_date": "2025-06-04 08:00:00",
                "material_code": "MAT-B",
                "month_year": "June 2025",
                "machine_id": "024-002",
                "canonical_machine_id": "024-002",
                "is_three_way_match": 1,
            },
            {
                "work_order": "WO-003",
                "work_order_type": "PM",
                "transaction_date": "2025-06-05 08:00:00",
                "material_code": "MAT-C",
                "month_year": "June 2025",
                "machine_id": "024-003",
                "canonical_machine_id": "024-003",
                "is_three_way_match": 1,
            },
        ]
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(rows).to_sql("maintenance_records", conn, if_exists="append", index=False)
        conn.close()

    @patch("core.experimental_scheduling.build_active_saved_predictor")
    def test_route_snapshot_reports_flagship_copy_and_live_binding(self, build_active_saved_predictor):
        build_active_saved_predictor.return_value = (
            PredictorStub(),
            {
                "model_path": "/repo/models/production_efficiency_model.pkl",
                "preprocessor_path": "/repo/models/production_preprocessor.pkl",
                "model_provenance_path": "/repo/models/production_efficiency_model.provenance.json",
                "preprocessor_provenance_path": "/repo/models/production_preprocessor.provenance.json",
                "task_tag": "Task 14F",
                "artifact_version_id": "20260419_181842",
                "selected_model": "random_forest",
                "predictor_instantiated_from_active_paths": True,
                "model_loaded": True,
                "preprocessor_loaded": True,
            },
        )

        snapshot = build_experimental_lab_route_snapshot(
            "June 2025",
            runtime_mode=STANDARD_RUNTIME_MODE,
            db_path=self.db_path,
            queue_size=3,
            max_jobs_per_machine=1,
            horizon_days=7,
        )

        module_source = (
            Path(__file__).resolve().parents[1]
            / "modules"
            / "experimental_intelligence_lab_module.py"
        ).read_text(encoding="utf-8")

        self.assertTrue(snapshot["route_exposed"])
        self.assertEqual(snapshot["selected_month"], "June 2025")
        self.assertFalse(snapshot["scheduling"]["blocked"])
        self.assertEqual(snapshot["scheduling"]["queue_provenance"], "Real-seeded synthetic queue")
        self.assertFalse(snapshot["maintenance"]["blocked"])
        self.assertIn(snapshot["maintenance"]["prototype_mode"], {"Weak-label model", "Fallback evidence score"})
        self.assertEqual(snapshot["active_artifact_binding"]["task_tag"], "Task 14F")
        self.assertEqual(snapshot["active_artifact_binding"]["artifact_version_id"], "20260419_181842")
        self.assertEqual(snapshot["active_artifact_binding"]["selected_model"], "random_forest")
        self.assertNotIn("Task 4L", module_source)
        self.assertIn("Internal-landing experimental flagship lane", module_source)

    def test_route_snapshot_hides_lane_in_demo_readonly_mode(self):
        snapshot = build_experimental_lab_route_snapshot(
            "June 2025",
            runtime_mode=DEMO_READONLY_RUNTIME_MODE,
            db_path=self.db_path,
        )

        self.assertFalse(snapshot["route_exposed"])
        self.assertIsNone(snapshot["scheduling"])
        self.assertIsNone(snapshot["maintenance"])


if __name__ == "__main__":
    unittest.main()
