import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import core.canonical_ml_reader as canonical_ml_module
from core.canonical_ml_reader import (
    CANONICAL_ML_INPUT_COLUMNS,
    CANONICAL_ML_PREDICTION_COLUMNS,
    CanonicalMLReader,
)
from core.gold_fact_builder import GoldFactBuilder


class PredictorStub:
    def __init__(self, responses=None, loaded_model=True, loaded_preprocessor=True):
        self.responses = responses or {}
        self.loaded_model = loaded_model
        self.loaded_preprocessor = loaded_preprocessor
        self.feature_defaults = {
            "team_size": 2.0,
            "cumulative_maintenance_count": 7.0,
        }

    def predict_efficiency(self, **kwargs):
        machine_id = kwargs["machine_id"]
        return self.responses.get(
            machine_id,
            {
                "efficiency": 3.2,
                "confidence": 0.82,
                "feature_impacts": {"hours_since_last_maintenance": "48 hours since maintenance"},
                "source": "model",
            },
        )


class CanonicalMLReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "canonical_ml_reader.db"
        GoldFactBuilder(self.db_path)
        self.reader = CanonicalMLReader(self.db_path)

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
            "energy_source_row_hashes_json": json.dumps(["energy-hash"]),
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
                    "good_qty": 10.0,
                    "hours_since_last_maintenance": 24.0,
                },
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-05-01T00:00:00",
                    "good_qty": 8.0,
                    "hours_since_last_maintenance": 12.0,
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

    def test_build_month_input_dataframe_derives_finishing_task_family_without_default(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T09:00:00",
                    "material_code": "MAT-001",
                    "task_name": "UV(染)",
                    "good_qty": 50.0,
                    "team_leader": None,
                    "team_size": None,
                    "manpower": 3.0,
                    "hours_since_last_maintenance": 48.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 2,
                    "cumulative_maintenance_count": 7,
                    "source_flags": json.dumps(
                        {
                            "maintenance_distinct_work_order_count_30d": 99,
                            "maintenance_last_work_order_type": "Corrective",
                        },
                        sort_keys=True,
                    ),
                }
            ]
        )

        input_df = self.reader.build_month_input_dataframe(
            "June 2025",
            predictor=PredictorStub(),
        )

        row = input_df.iloc[0]
        self.assertEqual(list(input_df.columns), CANONICAL_ML_INPUT_COLUMNS)
        self.assertEqual(row["machine_id"], "024-010")
        self.assertEqual(row["task_difficulty"], "Easy")
        self.assertEqual(row["production_qty"], 50.0)
        self.assertEqual(row["team_size"], 3.0)
        self.assertEqual(row["last_maintenance_type"], "PM")
        self.assertEqual(row["maintenance_intensity_30d"], 2.0)
        self.assertEqual(row["cumulative_maintenance_count"], 7.0)
        self.assertEqual(row["eligible_for_inference"], 1)
        self.assertIn("team_size_from_manpower", row["adapter_notes"])
        self.assertIn("team_leader_unknown", row["adapter_notes"])
        self.assertNotIn("task_difficulty_unmapped", row["adapter_notes"])

    def test_build_month_input_dataframe_blocks_unmapped_task_name(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-099",
                    "hour_ts": "2025-06-01T10:00:00",
                    "material_code": "MAT-999",
                    "task_name": "未知工序",
                    "good_qty": 20.0,
                    "team_leader": "Leader A",
                    "team_size": 3.0,
                    "hours_since_last_maintenance": 24.0,
                    "last_maintenance_work_order_type": "PM",
                }
            ]
        )

        input_df = self.reader.build_month_input_dataframe(
            "June 2025",
            predictor=PredictorStub(),
        )

        row = input_df.iloc[0]
        self.assertEqual(row["blocked_reason"], "unmapped_task_name")
        self.assertEqual(row["eligible_for_inference"], 0)
        self.assertIn("task_difficulty_unmapped", row["adapter_notes"])

    def test_blocked_behavior_when_required_canonical_fields_are_missing(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-011",
                    "hour_ts": "2025-06-01T09:00:00",
                    "material_code": "MAT-001",
                    "task_name": "印色",
                    "good_qty": 0.0,
                    "hours_since_last_maintenance": 48.0,
                },
                {
                    "canonical_machine_id": "024-012",
                    "hour_ts": "2025-06-01T10:00:00",
                    "material_code": "MAT-002",
                    "task_name": "印色",
                    "good_qty": 20.0,
                    "hours_since_last_maintenance": None,
                },
            ]
        )

        input_df = self.reader.build_month_input_dataframe("June 2025", predictor=PredictorStub())

        self.assertEqual(input_df.iloc[0]["blocked_reason"], "missing_positive_good_qty")
        self.assertEqual(input_df.iloc[1]["blocked_reason"], "missing_hours_since_last_maintenance")
        self.assertEqual(int(input_df["eligible_for_inference"].sum()), 0)

    def test_build_prediction_candidates_keeps_latest_eligible_row_per_machine(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-01T08:00:00",
                    "material_code": "MAT-001",
                    "task_name": "印色",
                    "good_qty": 10.0,
                    "hours_since_last_maintenance": 12.0,
                },
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-01T09:00:00",
                    "material_code": "MAT-001",
                    "task_name": "印色",
                    "good_qty": 11.0,
                    "hours_since_last_maintenance": 13.0,
                },
            ]
        )

        input_df = self.reader.build_month_input_dataframe("June 2025", predictor=PredictorStub())
        candidate_df = self.reader.build_prediction_candidates(input_df)

        self.assertEqual(len(candidate_df), 1)
        self.assertEqual(candidate_df.iloc[0]["hour_ts"], "2025-06-01T09:00:00")

    def test_build_prediction_dataframe_blocks_non_model_sources(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-030",
                    "hour_ts": "2025-06-01T08:00:00",
                    "material_code": "MAT-001",
                    "task_name": "印色",
                    "good_qty": 10.0,
                    "hours_since_last_maintenance": 12.0,
                },
                {
                    "canonical_machine_id": "024-031",
                    "hour_ts": "2025-06-01T09:00:00",
                    "material_code": "MAT-002",
                    "task_name": "光油",
                    "good_qty": 11.0,
                    "hours_since_last_maintenance": 13.0,
                },
            ]
        )

        input_df = self.reader.build_month_input_dataframe("June 2025", predictor=PredictorStub())
        candidate_df = self.reader.build_prediction_candidates(input_df)
        prediction_df, blocked_df = self.reader.build_prediction_dataframe(
            candidate_df,
            predictor=PredictorStub(
                responses={
                    "024-030": {
                        "efficiency": 3.1,
                        "confidence": 0.9,
                        "feature_impacts": {"production_qty": "Current load 10 units vs typical 7"},
                        "source": "model",
                    },
                    "024-031": {
                        "efficiency": 4.2,
                        "confidence": 0.5,
                        "feature_impacts": {},
                        "source": "fallback",
                    },
                }
            ),
        )

        self.assertEqual(list(prediction_df.columns), CANONICAL_ML_PREDICTION_COLUMNS)
        self.assertEqual(len(prediction_df), 1)
        self.assertEqual(prediction_df.iloc[0]["machine_id"], "024-030")
        self.assertEqual(prediction_df.iloc[0]["top_driver"], "production_qty: Current load 10 units vs typical 7")
        self.assertEqual(len(blocked_df), 1)
        self.assertEqual(blocked_df.iloc[0]["machine_id"], "024-031")
        self.assertEqual(blocked_df.iloc[0]["blocked_reason"], "predictor_returned_non_model_source")

    def test_empty_month_returns_empty_inputs(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-999",
                    "hour_ts": "2025-05-01T00:00:00",
                    "good_qty": 5.0,
                    "hours_since_last_maintenance": 10.0,
                }
            ]
        )

        input_df = self.reader.build_month_input_dataframe("June 2025", predictor=PredictorStub())
        candidate_df = self.reader.build_prediction_candidates(input_df)

        self.assertTrue(input_df.empty)
        self.assertEqual(list(input_df.columns), CANONICAL_ML_INPUT_COLUMNS)
        self.assertTrue(candidate_df.empty)

    def test_helper_source_contains_no_legacy_unified_view_or_demo_fallback(self):
        source_text = Path(canonical_ml_module.__file__).read_text(encoding="utf-8").lower()

        self.assertNotIn("unified_view", source_text)
        self.assertNotIn("demo", source_text)


if __name__ == "__main__":
    unittest.main()
