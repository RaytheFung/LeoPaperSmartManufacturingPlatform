import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from core.experimental_scheduling import (
    build_scheduling_export_artifacts,
    build_real_seeded_queue,
    load_real_input_queue,
    run_constraint_aware_scheduling,
)


class PredictorStub:
    def predict_efficiency(self, **kwargs):
        machine_id = str(kwargs.get("machine_id"))
        if machine_id.endswith("003"):
            return {
                "efficiency": 0.018,
                "confidence": 0.82,
                "feature_impacts": {"hours_since_last_maintenance": "recent"},
                "source": "model",
            }
        if machine_id.endswith("002"):
            return {
                "efficiency": 0.021,
                "confidence": 0.80,
                "feature_impacts": {"production_qty": "moderate"},
                "source": "model",
            }
        return {
            "efficiency": 0.024,
            "confidence": 0.78,
            "feature_impacts": {"task_complexity": "high"},
            "source": "model",
        }


class ExperimentalSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "experimental_schedule.db"
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
                "machine_state": "setup_changeover",
                "material_code": "MAT-A",
                "task_name": "印刷",
                "good_qty": 280.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 16.0,
                "energy_total_cost": 32.0,
                "setup_minutes": 60.0,
                "production_minutes": 0.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader A",
                "team_size": 2.0,
                "hours_since_last_maintenance": 18.0,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 4.0,
            },
            {
                "canonical_machine_id": "024-001",
                "hour_ts": "2025-06-01T09:00:00",
                "machine_state": "production",
                "material_code": "MAT-A",
                "task_name": "印刷",
                "good_qty": 320.0,
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
                "hours_since_last_maintenance": 19.0,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 4.0,
            },
            {
                "canonical_machine_id": "024-002",
                "hour_ts": "2025-06-02T08:00:00",
                "machine_state": "setup_changeover",
                "material_code": "MAT-B",
                "task_name": "印刷+光油",
                "good_qty": 300.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 18.0,
                "energy_total_cost": 36.0,
                "setup_minutes": 60.0,
                "production_minutes": 0.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader B",
                "team_size": 3.0,
                "hours_since_last_maintenance": 42.0,
                "last_maintenance_work_order_type": "CM",
                "maintenance_distinct_work_order_count_30d": 2.0,
                "cumulative_maintenance_count": 5.0,
            },
            {
                "canonical_machine_id": "024-002",
                "hour_ts": "2025-06-02T09:00:00",
                "machine_state": "production",
                "material_code": "MAT-B",
                "task_name": "印刷+光油",
                "good_qty": 360.0,
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
                "hours_since_last_maintenance": 43.0,
                "last_maintenance_work_order_type": "CM",
                "maintenance_distinct_work_order_count_30d": 2.0,
                "cumulative_maintenance_count": 5.0,
            },
            {
                "canonical_machine_id": "024-003",
                "hour_ts": "2025-06-03T08:00:00",
                "machine_state": "setup_changeover",
                "material_code": "MAT-C",
                "task_name": "光油",
                "good_qty": 340.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 17.0,
                "energy_total_cost": 34.0,
                "setup_minutes": 60.0,
                "production_minutes": 0.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader C",
                "team_size": 2.0,
                "hours_since_last_maintenance": 70.0,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 3.0,
            },
            {
                "canonical_machine_id": "024-003",
                "hour_ts": "2025-06-03T09:00:00",
                "machine_state": "production",
                "material_code": "MAT-C",
                "task_name": "光油",
                "good_qty": 380.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 13.0,
                "energy_total_cost": 26.0,
                "setup_minutes": 0.0,
                "production_minutes": 60.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader C",
                "team_size": 2.0,
                "hours_since_last_maintenance": 71.0,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 3.0,
            },
            {
                "canonical_machine_id": "035-001",
                "hour_ts": "2025-06-04T08:00:00",
                "machine_state": "production",
                "material_code": "MAT-Z",
                "task_name": "UV",
                "good_qty": 500.0,
                "scrap_qty": 0.0,
                "energy_total_kwh": 22.0,
                "energy_total_cost": 44.0,
                "setup_minutes": 0.0,
                "production_minutes": 60.0,
                "planned_stop_minutes": 0.0,
                "unplanned_stop_minutes": 0.0,
                "idle_minutes": 0.0,
                "team_leader": "Leader Z",
                "team_size": 4.0,
                "hours_since_last_maintenance": 12.0,
                "last_maintenance_work_order_type": "PM",
                "maintenance_distinct_work_order_count_30d": 1.0,
                "cumulative_maintenance_count": 2.0,
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
                "transaction_date": "2025-05-20 08:00:00",
                "material_code": "MAT-A",
                "month_year": "May 2025",
                "machine_id": "024-001",
                "canonical_machine_id": "024-001",
                "is_three_way_match": 1,
            },
            {
                "work_order": "WO-002",
                "work_order_type": "CM",
                "transaction_date": "2025-05-25 08:00:00",
                "material_code": "MAT-B",
                "month_year": "May 2025",
                "machine_id": "024-002",
                "canonical_machine_id": "024-002",
                "is_three_way_match": 1,
            },
            {
                "work_order": "WO-003",
                "work_order_type": "PM",
                "transaction_date": "2025-05-28 08:00:00",
                "material_code": "MAT-C",
                "month_year": "May 2025",
                "machine_id": "024-003",
                "canonical_machine_id": "024-003",
                "is_three_way_match": 1,
            },
        ]
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(rows).to_sql("maintenance_records", conn, if_exists="append", index=False)
        conn.close()

    def _hash_db(self) -> str:
        return hashlib.sha1(self.db_path.read_bytes()).hexdigest()

    def test_real_seeded_queue_is_deterministic(self):
        first_payload = build_real_seeded_queue("June 2025", queue_size=3, db_path=self.db_path)
        second_payload = build_real_seeded_queue("June 2025", queue_size=3, db_path=self.db_path)

        self.assertFalse(first_payload["blocked"])
        self.assertFalse(second_payload["blocked"])
        self.assertTrue(first_payload["queue_df"].equals(second_payload["queue_df"]))
        self.assertEqual(
            first_payload["seed_summary"]["deterministic_seed"],
            second_payload["seed_summary"]["deterministic_seed"],
        )

    def test_constraint_aware_schedule_produces_assignments_and_baseline(self):
        payload = run_constraint_aware_scheduling(
            "June 2025",
            queue_size=3,
            max_jobs_per_machine=1,
            predictor=PredictorStub(),
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        self.assertEqual(len(payload["queue_df"]), 3)
        self.assertEqual(len(payload["optimized_schedule_df"]), 3)
        self.assertFalse(payload["feasible_assignment_df"].empty)
        self.assertIn("Composite score", payload["baseline_comparison_df"]["Metric"].tolist())

    def test_schedule_keeps_machine_family_compatibility(self):
        payload = run_constraint_aware_scheduling(
            "June 2025",
            queue_size=3,
            max_jobs_per_machine=1,
            predictor=PredictorStub(),
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        assigned_machine_ids = payload["optimized_schedule_df"]["machine_id"].tolist()
        self.assertTrue(all(machine_id.startswith("024-") for machine_id in assigned_machine_ids))
        self.assertFalse(any(machine_id == "035-001" for machine_id in assigned_machine_ids))

    def test_real_input_queue_upload_validates_and_normalizes(self):
        upload_df = pd.DataFrame(
            [
                {
                    "Preferred Machine Family": "024",
                    "Material Code": "MAT-A",
                    "Task Name": "印刷",
                    "Quantity": 250,
                    "Urgency Label": "High",
                },
                {
                    "Preferred Machine Family": "024",
                    "Material Code": "MAT-B",
                    "Task Name": "印刷+光油",
                    "Quantity": 300,
                    "Urgency Label": "Medium",
                },
            ]
        )
        payload = load_real_input_queue(
            upload_df.to_csv(index=False).encode("utf-8"),
            file_name="pending_queue.csv",
            month_year="June 2025",
        )

        self.assertFalse(payload["blocked"])
        self.assertEqual(payload["input_summary"]["accepted_rows"], 2)
        self.assertEqual(payload["queue_df"]["source_mode"].unique().tolist(), ["real_input_queue_upload"])
        self.assertEqual(payload["queue_df"]["provenance_label"].unique().tolist(), ["Real-input pilot queue"])

    def test_scheduling_export_artifacts_include_manifest_and_csv_frames(self):
        payload = run_constraint_aware_scheduling(
            "June 2025",
            queue_size=3,
            max_jobs_per_machine=1,
            predictor=PredictorStub(),
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        export_artifacts = build_scheduling_export_artifacts(
            payload,
            runtime_mode="pilot_review",
            anchor_month="June 2025",
        )

        self.assertIn("optimized_schedule.csv", export_artifacts["export_frames"])
        self.assertIn("candidate_scores.csv", export_artifacts["export_frames"])
        self.assertIn('"runtime_mode": "pilot_review"', export_artifacts["manifest_json"])
        self.assertIn('"prototype": "constraint_aware_scheduling_prototype"', export_artifacts["manifest_json"])

    def test_schedule_helper_does_not_write_live_db(self):
        before_hash = self._hash_db()
        payload = run_constraint_aware_scheduling(
            "June 2025",
            queue_size=3,
            max_jobs_per_machine=1,
            predictor=PredictorStub(),
            db_path=self.db_path,
        )
        after_hash = self._hash_db()

        self.assertFalse(payload["blocked"])
        self.assertEqual(before_hash, after_hash)

    @patch("core.experimental_scheduling.build_active_saved_predictor")
    def test_default_predictor_uses_explicit_active_saved_artifact_binding(self, build_active_saved_predictor):
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

        payload = run_constraint_aware_scheduling(
            "June 2025",
            queue_size=3,
            max_jobs_per_machine=1,
            db_path=self.db_path,
        )

        self.assertFalse(payload["blocked"])
        build_active_saved_predictor.assert_called_once()
        self.assertEqual(payload["active_artifact_binding"]["task_tag"], "Task 14F")
        self.assertEqual(payload["active_artifact_binding"]["artifact_version_id"], "20260419_181842")
        self.assertTrue(payload["active_artifact_binding"]["predictor_instantiated_from_active_paths"])


if __name__ == "__main__":
    unittest.main()
