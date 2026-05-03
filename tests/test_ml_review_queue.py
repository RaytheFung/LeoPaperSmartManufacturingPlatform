import unittest

import pandas as pd

from core.canonical_ml_reader import (
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
)
from core.ml_review_queue import (
    build_blocked_reason_summary,
    build_inference_coverage_summary,
    build_model_review_queue,
    collect_blocked_rows,
)


class ReviewQueuePredictorStub:
    def predict_efficiency(self, **kwargs):
        hours_since_maintenance = float(kwargs["hours_since_maintenance"])
        team_size = float(kwargs["team_size"])
        efficiency = 0.050 + (hours_since_maintenance / 10000.0) - (team_size * 0.001)
        return {
            "efficiency": efficiency,
            "confidence": 0.81,
            "feature_impacts": {
                "production_qty": f"Current load {kwargs['production_qty']:.0f} units vs peer reference"
            },
            "source": "model",
        }


class MLReviewQueueTests(unittest.TestCase):
    def test_build_inference_coverage_summary_reports_counts_and_shares(self):
        input_df = pd.DataFrame(
            [
                {"eligible_for_inference": 1, "adapter_notes": ""},
                {"eligible_for_inference": 1, "adapter_notes": "team_size_from_manpower"},
                {
                    "eligible_for_inference": 1,
                    "adapter_notes": "team_size_from_preprocessor_default; team_leader_unknown",
                },
                {"eligible_for_inference": 0, "adapter_notes": "task_difficulty_unmapped"},
            ]
        )

        summary_df = build_inference_coverage_summary(input_df)

        self.assertEqual(
            summary_df["coverage_bucket"].tolist(),
            ["Direct canonical", "Adapted", "Defaulted", "Blocked"],
        )
        self.assertEqual(summary_df["rows"].tolist(), [1, 1, 1, 1])
        self.assertTrue((summary_df["share"] == 0.25).all())

    def test_build_model_review_queue_prefers_family_and_task_peer_median(self):
        predictor = ReviewQueuePredictorStub()
        candidate_df = pd.DataFrame(
            [
                _candidate_row("024-150", "2025-06-30 10:00:00", task_difficulty="Medium", production_qty=100.0),
                _candidate_row("024-151", "2025-06-30 10:00:00", task_difficulty="Medium", production_qty=90.0),
                _candidate_row("024-152", "2025-06-30 10:00:00", task_difficulty="Medium", production_qty=80.0),
                _candidate_row("024-153", "2025-06-30 10:00:00", task_difficulty="Medium", production_qty=70.0),
                _candidate_row("035-001", "2025-06-30 10:00:00", task_difficulty="Hard", production_qty=60.0),
            ]
        )
        prediction_df = pd.DataFrame(
            [
                _prediction_row("024-150", "2025-06-30 10:00:00", 1.2, 0.9, "production_qty: current load is elevated"),
                _prediction_row("024-151", "2025-06-30 10:00:00", 0.6, 0.8, "production_qty: peer 1"),
                _prediction_row("024-152", "2025-06-30 10:00:00", 0.8, 0.8, "production_qty: peer 2"),
                _prediction_row("024-153", "2025-06-30 10:00:00", 1.0, 0.8, "production_qty: peer 3"),
                _prediction_row("035-001", "2025-06-30 10:00:00", 0.7, 0.8, "task_difficulty: out-of-family"),
            ]
        )

        queue_df = build_model_review_queue(candidate_df, prediction_df, predictor=predictor)
        target_row = queue_df.loc[queue_df["machine_id"] == "024-150"].iloc[0]

        self.assertEqual(target_row["baseline_basis"], "Family + task-difficulty peer median")
        self.assertEqual(target_row["baseline_peer_count"], 3)
        self.assertAlmostEqual(target_row["comparable_baseline"], 0.8)
        self.assertAlmostEqual(target_row["severity_gap"], 0.4)
        self.assertAlmostEqual(target_row["estimated_excess_kwh"], 40.0)
        self.assertAlmostEqual(target_row["review_priority_score"], 36.0)
        self.assertTrue(target_row["preview_available"])

    def test_build_model_review_queue_falls_back_to_selected_month_median_and_support_weight(self):
        predictor = ReviewQueuePredictorStub()
        candidate_df = pd.DataFrame(
            [
                _candidate_row(
                    "166-002",
                    "2025-06-30 11:00:00",
                    task_difficulty="Hard",
                    production_qty=50.0,
                    adapter_notes="team_size_from_preprocessor_default",
                ),
                _candidate_row("024-081", "2025-06-30 11:00:00", task_difficulty="Easy", production_qty=30.0),
            ]
        )
        prediction_df = pd.DataFrame(
            [
                _prediction_row("166-002", "2025-06-30 11:00:00", 1.5, 0.8, "maintenance: long recency"),
                _prediction_row("024-081", "2025-06-30 11:00:00", 0.9, 0.8, "production_qty: lower load"),
            ]
        )

        queue_df = build_model_review_queue(candidate_df, prediction_df, predictor=predictor)
        target_row = queue_df.loc[queue_df["machine_id"] == "166-002"].iloc[0]

        self.assertEqual(target_row["support_path"], "Defaulted row")
        self.assertAlmostEqual(target_row["support_weight"], 0.65)
        self.assertEqual(target_row["baseline_basis"], "Selected-month median fallback")
        self.assertAlmostEqual(target_row["comparable_baseline"], 1.2)
        self.assertAlmostEqual(target_row["severity_gap"], 0.3)
        self.assertAlmostEqual(target_row["estimated_excess_kwh"], 15.0)
        self.assertAlmostEqual(target_row["review_priority_score"], 7.8)

    def test_collect_blocked_rows_and_summary_keep_unique_reasons(self):
        input_df = pd.DataFrame(
            [
                {
                    "machine_id": "024-010",
                    "datetime": pd.Timestamp("2025-06-01 00:00:00"),
                    "hour_ts": "2025-06-01T00:00:00",
                    "eligible_for_inference": 0,
                    "blocked_reason": MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
                    "adapter_notes": "",
                },
                {
                    "machine_id": "024-010",
                    "datetime": pd.Timestamp("2025-06-01 00:00:00"),
                    "hour_ts": "2025-06-01T00:00:00",
                    "eligible_for_inference": 0,
                    "blocked_reason": MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
                    "adapter_notes": "",
                },
                {
                    "machine_id": "024-011",
                    "datetime": pd.Timestamp("2025-06-01 00:30:00"),
                    "hour_ts": "2025-06-01T00:30:00",
                    "eligible_for_inference": 0,
                    "blocked_reason": MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
                    "adapter_notes": "",
                },
            ]
        )
        blocked_prediction_df = pd.DataFrame(
            [
                {
                    "machine_id": "024-099",
                    "datetime": pd.Timestamp("2025-06-01 01:00:00"),
                    "hour_ts": "2025-06-01T01:00:00",
                    "blocked_reason": "predictor_returned_non_model_source",
                    "adapter_notes": "",
                }
            ]
        )

        blocked_df = collect_blocked_rows(input_df, blocked_prediction_df)
        summary_df = build_blocked_reason_summary(blocked_df)

        self.assertEqual(len(blocked_df), 3)
        self.assertEqual(
            summary_df["blocked_reason"].tolist(),
            [
                MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
                MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
                "predictor_returned_non_model_source",
            ],
        )
        self.assertEqual(summary_df["row_count"].tolist(), [1, 1, 1])
        self.assertEqual(
            summary_df["blocked_reason_label"].tolist(),
            [
                "Production-state rows with pure-production zero good_qty",
                "Production-state rows with contradictory stop / idle minutes",
                "Predictor returned non-model source",
            ],
        )


def _candidate_row(
    machine_id: str,
    timestamp: str,
    *,
    task_difficulty: str,
    production_qty: float,
    adapter_notes: str = "",
) -> dict[str, object]:
    return {
        "machine_id": machine_id,
        "datetime": pd.Timestamp(timestamp),
        "team_leader": "Leader A",
        "material_code": "MAT-001",
        "hours_since_last_maintenance": 120.0,
        "task_difficulty": task_difficulty,
        "production_qty": production_qty,
        "team_size": 3.0,
        "hour_of_day": 10,
        "is_weekend": 0,
        "month": 6,
        "last_maintenance_type": "PM",
        "maintenance_intensity_30d": 2.0,
        "cumulative_maintenance_count": 8.0,
        "adapter_notes": adapter_notes,
    }


def _prediction_row(
    machine_id: str,
    timestamp: str,
    predicted_efficiency: float,
    confidence: float,
    top_driver: str,
) -> dict[str, object]:
    return {
        "machine_id": machine_id,
        "datetime": pd.Timestamp(timestamp),
        "predicted_efficiency": predicted_efficiency,
        "confidence": confidence,
        "top_driver": top_driver,
    }


if __name__ == "__main__":
    unittest.main()
