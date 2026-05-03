import unittest

import pandas as pd

from core.intervention_preview import (
    build_intervention_preview_table,
    build_machine_intervention_preview,
    build_seed_row_intervention_preview,
    candidate_support_label,
)


class PreviewPredictorStub:
    def __init__(self, source="model"):
        self.source = source
        self.calls = []

    def predict_efficiency(self, **kwargs):
        self.calls.append(kwargs)
        hours_since_maintenance = float(kwargs["hours_since_maintenance"])
        team_size = float(kwargs["team_size"])
        efficiency = 0.050 + (hours_since_maintenance / 10000.0) - (team_size * 0.0015)
        return {
            "efficiency": efficiency,
            "confidence": 0.84,
            "feature_impacts": {
                "hours_since_last_maintenance": f"{hours_since_maintenance:.1f} hours since maintenance"
            },
            "source": self.source,
        }


class InterventionPreviewTests(unittest.TestCase):
    def test_candidate_support_label_distinguishes_direct_adapted_and_defaulted_rows(self):
        self.assertEqual(candidate_support_label(pd.Series({"adapter_notes": ""})), "Direct canonical row")
        self.assertEqual(
            candidate_support_label(pd.Series({"adapter_notes": "team_size_from_manpower"})),
            "Adapted row",
        )
        self.assertEqual(
            candidate_support_label(pd.Series({"adapter_notes": "team_size_from_preprocessor_default"})),
            "Defaulted row",
        )

    def test_build_seed_row_intervention_preview_returns_supported_templates_and_best_case(self):
        predictor = PreviewPredictorStub()
        seed_row = pd.Series(
            {
                "machine_id": "024-081",
                "datetime": pd.Timestamp("2025-06-10 09:00:00"),
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
                "adapter_notes": "team_size_from_manpower",
            }
        )
        baseline_row = pd.Series(
            {
                "machine_id": "024-081",
                "datetime": pd.Timestamp("2025-06-10 09:00:00"),
                "predicted_efficiency": 0.0560,
                "confidence": 0.80,
                "top_driver": "hours_since_last_maintenance: 120.0 hours since maintenance",
            }
        )

        preview = build_seed_row_intervention_preview(
            seed_row,
            predictor,
            baseline_row=baseline_row,
        )

        self.assertFalse(preview["blocked"])
        self.assertEqual(preview["support_path"], "Adapted row")
        self.assertEqual(preview["baseline"]["predicted_efficiency"], 0.0560)
        self.assertEqual(len(preview["scenarios"]), 3)
        self.assertTrue(all(row["status"] == "supported" for row in preview["scenarios"]))
        self.assertEqual(preview["best_supported_scenario"]["scenario_name"], "Combined Support")

        scenario_table = build_intervention_preview_table(preview)
        self.assertEqual(
            scenario_table["Scenario"].tolist(),
            ["Maintenance Refresh", "Crew Support +1", "Combined Support"],
        )
        self.assertTrue((scenario_table["Status"] == "Supported").all())

    def test_build_seed_row_intervention_preview_keeps_unsupported_templates_visible(self):
        predictor = PreviewPredictorStub()
        seed_row = pd.Series(
            {
                "machine_id": "024-090",
                "datetime": pd.Timestamp("2025-06-12 10:00:00"),
                "team_leader": "Leader B",
                "material_code": "MAT-090",
                "hours_since_last_maintenance": 0.0,
                "task_difficulty": "Easy",
                "production_qty": 200.0,
                "team_size": 3.0,
                "hour_of_day": 10,
                "is_weekend": 0,
                "month": 6,
                "last_maintenance_type": "PM",
                "maintenance_intensity_30d": 1.0,
                "cumulative_maintenance_count": 4.0,
                "adapter_notes": "",
            }
        )

        preview = build_seed_row_intervention_preview(seed_row, predictor)

        self.assertFalse(preview["blocked"])
        scenario_status = {row["scenario_name"]: row["status"] for row in preview["scenarios"]}
        self.assertEqual(scenario_status["Maintenance Refresh"], "unsupported")
        self.assertEqual(scenario_status["Crew Support +1"], "supported")
        self.assertEqual(scenario_status["Combined Support"], "unsupported")

        scenario_table = build_intervention_preview_table(preview)
        unsupported_rows = scenario_table[scenario_table["Status"] == "Unsupported"]
        self.assertEqual(len(unsupported_rows), 2)
        self.assertIn("lowest supported maintenance-recency bound", unsupported_rows.iloc[0]["Blocked Reason"])

    def test_build_machine_intervention_preview_blocks_honestly_when_machine_is_missing(self):
        predictor = PreviewPredictorStub()
        candidate_df = pd.DataFrame(
            [
                {
                    "machine_id": "024-081",
                    "datetime": pd.Timestamp("2025-06-10 09:00:00"),
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
                    "adapter_notes": "",
                }
            ]
        )
        prediction_df = pd.DataFrame(
            [
                {
                    "machine_id": "024-081",
                    "datetime": pd.Timestamp("2025-06-10 09:00:00"),
                    "predicted_efficiency": 0.0560,
                    "confidence": 0.80,
                    "top_driver": "hours_since_last_maintenance: 120.0 hours since maintenance",
                }
            ]
        )

        preview = build_machine_intervention_preview(
            candidate_df,
            prediction_df,
            predictor,
            "999-999",
        )

        self.assertTrue(preview["blocked"])
        self.assertIn("no eligible canonical machine-hour seed row", preview["reason"].lower())

    def test_build_seed_row_intervention_preview_blocks_when_predictor_returns_non_model(self):
        predictor = PreviewPredictorStub(source="fallback")
        seed_row = pd.Series(
            {
                "machine_id": "024-081",
                "datetime": pd.Timestamp("2025-06-10 09:00:00"),
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
                "adapter_notes": "",
            }
        )

        preview = build_seed_row_intervention_preview(seed_row, predictor)

        self.assertTrue(preview["blocked"])
        self.assertIn("baseline preview is unavailable", preview["reason"].lower())


if __name__ == "__main__":
    unittest.main()
