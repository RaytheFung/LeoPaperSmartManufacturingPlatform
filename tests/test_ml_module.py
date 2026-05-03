import inspect
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import modules.ml_module as ml_module
from core.gold_fact_builder import GoldFactBuilder


class WhatIfPredictorStub:
    def __init__(self, response=None):
        self.response = response or {
            "efficiency": 1.75,
            "confidence": 0.91,
            "feature_impacts": {"production_qty": "Scenario output is sensitive to production scale"},
            "source": "model",
        }
        self.calls = []

    def predict_efficiency(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class MLModuleHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ml_module.db"
        self.model_path = Path(self.temp_dir.name) / "models" / "production_efficiency_model.pkl"
        self.preprocessor_path = (
            Path(self.temp_dir.name) / "models" / "production_preprocessor.pkl"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _insert_fact_rows(self, rows):
        GoldFactBuilder(self.db_path)
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

    def _build_training_rows(self):
        rows = []
        for index in range(6):
            rows.append(
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": f"2025-06-01T0{index}:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 30.0 + index * 2.0,
                    "good_qty": 12.0 + index,
                    "team_leader": "Leader A",
                    "team_size": None if index % 2 == 0 else 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-001",
                    "task_name": "印刷" if index % 2 == 0 else "印刷+光油",
                    "hours_since_last_maintenance": 24.0 + index,
                    "days_since_last_maintenance": (24.0 + index) / 24.0,
                    "last_maintenance_work_order_type": "PM",
                    "source_flags": json.dumps(
                        {
                            "maintenance_distinct_work_order_count_30d": 2,
                            "maintenance_last_work_order_type": "PM",
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            )
            rows.append(
                {
                    "canonical_machine_id": "024-002",
                    "hour_ts": f"2025-06-02T0{index}:00:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 24.0 + index * 1.5,
                    "good_qty": 14.0 + index,
                    "team_leader": "Leader B",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": "MAT-002",
                    "task_name": "光油",
                    "hours_since_last_maintenance": 48.0 + index * 2.0,
                    "days_since_last_maintenance": (48.0 + index * 2.0) / 24.0,
                    "last_maintenance_work_order_type": None,
                    "source_flags": json.dumps(
                        {
                            "maintenance_distinct_work_order_count_30d": 1,
                            "maintenance_last_work_order_type": "Corrective",
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            )
        return rows

    def _build_multi_month_training_rows(self):
        rows = []
        month_starts = ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"]
        for month_offset, month_start in enumerate(month_starts):
            for hour_offset in range(3):
                rows.append(
                    {
                        "canonical_machine_id": "024-001",
                        "hour_ts": f"{month_start}T0{hour_offset}:00:00",
                        "machine_state": "production",
                        "energy_total_kwh": 18.0 + month_offset * 2.0 + hour_offset,
                        "good_qty": 9.0 + month_offset + hour_offset,
                        "team_leader": "Leader A",
                        "team_size": 3.0,
                        "manpower": 3.0,
                        "material_code": "MAT-001",
                        "task_name": "印刷",
                        "hours_since_last_maintenance": 24.0 + month_offset * 10.0 + hour_offset,
                        "days_since_last_maintenance": (24.0 + month_offset * 10.0 + hour_offset) / 24.0,
                        "last_maintenance_work_order_type": "PM",
                        "maintenance_distinct_work_order_count_30d": 1 + month_offset,
                        "cumulative_maintenance_count": 2 + month_offset,
                    }
                )
                rows.append(
                    {
                        "canonical_machine_id": "024-002",
                        "hour_ts": f"{month_start}T1{hour_offset}:00:00",
                        "machine_state": "setup_changeover",
                        "energy_total_kwh": 16.0 + month_offset * 1.5 + hour_offset,
                        "good_qty": 8.0 + month_offset + hour_offset,
                        "team_leader": "Leader B",
                        "team_size": 2.0,
                        "manpower": 2.0,
                        "material_code": "MAT-002",
                        "task_name": "光油",
                        "hours_since_last_maintenance": 48.0 + month_offset * 8.0 + hour_offset,
                        "days_since_last_maintenance": (48.0 + month_offset * 8.0 + hour_offset) / 24.0,
                        "last_maintenance_work_order_type": "Corrective",
                        "maintenance_distinct_work_order_count_30d": 2 + month_offset,
                        "cumulative_maintenance_count": 3 + month_offset,
                    }
                )
        return rows

    def test_get_canonical_retraining_status_reports_blocker_when_fact_missing(self):
        status = ml_module._get_canonical_retraining_status(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
        )

        self.assertEqual(status["db_path"], str(self.db_path))
        self.assertFalse(status["fact_machine_hour_reachable"])
        self.assertFalse(status["trainer_prerequisites_met"])
        self.assertIn("fact_machine_hour does not exist", status["blocker_reason"])

    def test_trigger_canonical_retraining_returns_structured_summary(self):
        self._insert_fact_rows(self._build_multi_month_training_rows())

        result = ml_module._trigger_canonical_retraining(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
        )

        self.assertEqual(result["training_source"], "fact_machine_hour")
        self.assertEqual(result["db_path"], str(self.db_path))
        self.assertEqual(result["rows_loaded"], 24)
        self.assertEqual(result["rows_after_filtering"], 24)
        self.assertEqual(result["distinct_machines_after_filtering"], 2)
        self.assertEqual(
            result["month_coverage"],
            ["January 2025", "February 2025", "March 2025", "April 2025"],
        )
        self.assertEqual(result["train_months"], ["January 2025", "February 2025"])
        self.assertEqual(result["eval_months"], ["March 2025", "April 2025"])
        self.assertTrue(result["artifact_status"]["model_exists"])
        self.assertTrue(result["artifact_status"]["preprocessor_exists"])
        self.assertTrue(result["artifact_status"]["model_loadable"])
        self.assertTrue(result["artifact_status"]["preprocessor_loadable"])
        self.assertEqual(result["artifact_status"]["model_provenance_state"], "present")
        self.assertEqual(result["artifact_status"]["preprocessor_provenance_state"], "present")
        self.assertTrue(result["promotion_success"])
        self.assertTrue(result["promotion_gate"]["passed"])
        self.assertTrue(result["predictor_smoke"]["passed"])
        self.assertEqual(result["predictor_smoke"]["prediction_source"], "model")
        self.assertTrue(Path(result["candidate_paths"]["model_path"]).exists())
        self.assertTrue(Path(result["candidate_paths"]["preprocessor_path"]).exists())
        self.assertIn("r2_score", result["evaluation_metrics"])
        self.assertIn("mae", result["evaluation_metrics"])
        self.assertIn("rmse", result["evaluation_metrics"])
        self.assertEqual(result["training_provenance"]["source_table"], "fact_machine_hour")
        self.assertEqual(result["training_provenance"]["task_tag"], "canonical_retraining_candidate")

    def test_status_reports_latest_metadata_after_canonical_retraining(self):
        self._insert_fact_rows(self._build_multi_month_training_rows())

        ml_module._trigger_canonical_retraining(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
        )
        status = ml_module._get_canonical_retraining_status(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
        )

        self.assertTrue(status["fact_machine_hour_reachable"])
        self.assertTrue(status["trainer_prerequisites_met"])
        self.assertTrue(status["artifact_status"]["model_exists"])
        self.assertTrue(status["artifact_status"]["preprocessor_exists"])
        self.assertTrue(status["artifact_status"]["model_loadable"])
        self.assertTrue(status["artifact_status"]["preprocessor_loadable"])
        self.assertEqual(status["artifact_status"]["model_provenance_state"], "present")
        self.assertEqual(status["artifact_status"]["preprocessor_provenance_state"], "present")
        self.assertIsNotNone(status["last_training_metadata"])
        self.assertEqual(status["load_summary"]["rows_after_filtering"], 24)
        self.assertEqual(
            status["month_coverage"],
            ["January 2025", "February 2025", "March 2025", "April 2025"],
        )
        self.assertEqual(
            status["team_size_fallback_summary"]["rows_using_team_size_from_preprocessor_default"],
            0,
        )
        self.assertEqual(
            status["team_size_fallback_summary"]["rows_using_team_size_from_manpower"],
            0,
        )
        self.assertEqual(status["train_months"], ["January 2025", "February 2025"])
        self.assertEqual(status["eval_months"], ["March 2025", "April 2025"])

    def test_ml_module_source_contains_no_demo_or_simulated_training_path(self):
        source = inspect.getsource(ml_module).lower()
        self.assertNotIn("demo training", source)
        self.assertNotIn("simulated training", source)


class MLWhatIfHelperTests(unittest.TestCase):
    def test_run_what_if_prediction_uses_real_seed_row_and_applies_overrides(self):
        predictor = WhatIfPredictorStub()
        seed_row = pd.Series(
            {
                "machine_id": "024-081",
                "team_leader": "Leader A",
                "material_code": "MAT-001",
                "hours_since_last_maintenance": 120.0,
                "task_difficulty": "Medium",
                "production_qty": 500.0,
                "team_size": 4.0,
                "hour_of_day": 9,
                "is_weekend": 0,
                "month": 6,
                "last_maintenance_type": "PM",
                "maintenance_intensity_30d": 2.0,
                "cumulative_maintenance_count": 8.0,
            }
        )

        result = ml_module._run_what_if_prediction(
            seed_row,
            {
                "team_size": 5.0,
                "hours_since_last_maintenance": 140.0,
                "production_qty": 560.0,
                "task_difficulty": "Hard",
            },
            predictor,
        )

        self.assertFalse(result["blocked"])
        self.assertEqual(result["prediction"]["source"], "model")
        self.assertEqual(len(predictor.calls), 1)
        self.assertEqual(predictor.calls[0]["machine_id"], "024-081")
        self.assertEqual(predictor.calls[0]["team_size"], 5.0)
        self.assertEqual(predictor.calls[0]["hours_since_maintenance"], 140.0)
        self.assertEqual(predictor.calls[0]["production_qty"], 560.0)
        self.assertEqual(predictor.calls[0]["task_difficulty"], "Hard")

    def test_run_what_if_prediction_blocks_non_model_results(self):
        predictor = WhatIfPredictorStub(
            response={
                "efficiency": 1.75,
                "confidence": 0.5,
                "feature_impacts": {},
                "source": "fallback",
            }
        )
        seed_row = pd.Series(
            {
                "machine_id": "024-081",
                "team_leader": "Leader A",
                "material_code": "MAT-001",
                "hours_since_last_maintenance": 120.0,
                "task_difficulty": "Medium",
                "production_qty": 500.0,
                "team_size": 4.0,
                "hour_of_day": 9,
                "is_weekend": 0,
                "month": 6,
                "last_maintenance_type": "PM",
                "maintenance_intensity_30d": 2.0,
                "cumulative_maintenance_count": 8.0,
            }
        )

        result = ml_module._run_what_if_prediction(seed_row, {}, predictor)

        self.assertTrue(result["blocked"])
        self.assertIn("did not return a saved-model result", result["reason"])

    def test_blocked_reason_snapshot_prefers_readable_labels(self):
        blocked_summary_df = pd.DataFrame(
            [
                {
                    "blocked_reason": "missing_positive_good_qty_production_state_likely_state_label_contradiction",
                    "blocked_reason_label": "Production-state rows with contradictory stop / idle minutes",
                    "row_count": 9,
                    "share": 0.60,
                },
                {
                    "blocked_reason": "missing_positive_good_qty_production_state_likely_quantity_overlay_gap",
                    "blocked_reason_label": "Production-state rows with pure-production zero good_qty",
                    "row_count": 6,
                    "share": 0.40,
                },
            ]
        )

        snapshot_text = ml_module._blocked_reason_snapshot_text(blocked_summary_df)

        self.assertIn("Production-state rows with contradictory stop / idle minutes", snapshot_text)
        self.assertIn("Production-state rows with pure-production zero good_qty", snapshot_text)
        self.assertNotIn(
            "missing_positive_good_qty_production_state_likely_state_label_contradiction",
            snapshot_text,
        )

    def test_candidate_support_label_distinguishes_direct_adapted_and_defaulted_rows(self):
        self.assertEqual(
            ml_module._candidate_support_label(pd.Series({"adapter_notes": ""})),
            "Direct canonical row",
        )
        self.assertEqual(
            ml_module._candidate_support_label(pd.Series({"adapter_notes": "team_size_from_manpower"})),
            "Adapted row",
        )
        self.assertEqual(
            ml_module._candidate_support_label(
                pd.Series({"adapter_notes": "team_size_from_preprocessor_default"})
            ),
            "Defaulted row",
        )


if __name__ == "__main__":
    unittest.main()
