import unittest

import pandas as pd

from modules.optimization_module import (
    _apply_opportunity_filters,
    _build_machine_summary_cards,
    _build_machine_drilldown_snapshot,
    _build_opportunity_worklist,
    _build_preview_comparison_table,
    build_schedule_tab_payload,
    build_team_insights_tab_payload,
)


class OptimizationReaderStub:
    def __init__(self, schedule_df=None, team_df=None):
        self.schedule_df = schedule_df if schedule_df is not None else pd.DataFrame()
        self.team_df = team_df if team_df is not None else pd.DataFrame()

    def build_schedule_summary(self, month_year):
        return self.schedule_df.copy()

    def build_team_insights(self, month_year):
        return self.team_df.copy()


class OptimizationModuleHelperTests(unittest.TestCase):
    def test_schedule_payload_blocks_honestly_when_canonical_summary_is_empty(self):
        payload = build_schedule_tab_payload(OptimizationReaderStub(), "January 2025")

        self.assertTrue(payload["blocked"])
        self.assertIn("No canonical scheduling summary is available", payload["message"])
        self.assertTrue(payload["schedule_df"].empty)

    def test_schedule_payload_passes_through_dataframe_when_available(self):
        schedule_df = pd.DataFrame(
            [
                {
                    "hour_of_day": 16,
                    "shift_label": "Evening",
                    "schedule_score": 0.8,
                }
            ]
        )

        payload = build_schedule_tab_payload(
            OptimizationReaderStub(schedule_df=schedule_df),
            "January 2025",
        )

        self.assertFalse(payload["blocked"])
        self.assertIsNone(payload["message"])
        self.assertEqual(payload["schedule_df"].iloc[0]["hour_of_day"], 16)

    def test_team_payload_blocks_honestly_when_canonical_summary_is_empty(self):
        payload = build_team_insights_tab_payload(OptimizationReaderStub(), "January 2025")

        self.assertTrue(payload["blocked"])
        self.assertIn("No canonical team insights are available", payload["message"])
        self.assertTrue(payload["team_df"].empty)

    def test_team_payload_passes_through_dataframe_when_available(self):
        team_df = pd.DataFrame(
            [
                {
                    "team_leader": "Leader A",
                    "team_effectiveness_score": 0.9,
                }
            ]
        )

        payload = build_team_insights_tab_payload(
            OptimizationReaderStub(team_df=team_df),
            "January 2025",
        )

        self.assertFalse(payload["blocked"])
        self.assertIsNone(payload["message"])
        self.assertEqual(payload["team_df"].iloc[0]["team_leader"], "Leader A")

    def test_apply_opportunity_filters_respects_family_and_support_thresholds(self):
        summary_df = pd.DataFrame(
            [
                {
                    "machine_id": "024-081",
                    "machine_family": "024",
                    "eligible_rows": 12,
                    "total_good_qty": 800.0,
                },
                {
                    "machine_id": "026-001",
                    "machine_family": "026",
                    "eligible_rows": 4,
                    "total_good_qty": 600.0,
                },
                {
                    "machine_id": "024-099",
                    "machine_family": "024",
                    "eligible_rows": 2,
                    "total_good_qty": 50.0,
                },
            ]
        )

        filtered_df = _apply_opportunity_filters(
            summary_df,
            machine_family="024",
            min_eligible_rows=5,
            min_total_good_qty=100.0,
        )

        self.assertEqual(filtered_df["machine_id"].tolist(), ["024-081"])

    def test_build_machine_drilldown_snapshot_includes_required_fields(self):
        snapshot = _build_machine_drilldown_snapshot(
            pd.Series(
                {
                    "machine_id": "024-081",
                    "machine_family": "024",
                    "opportunity_score": 0.78,
                    "top_driver": "High non-productive share",
                    "eligible_rows": 12,
                    "total_good_qty": 800.0,
                    "productive_hours": 20.0,
                    "nonproductive_hours": 5.0,
                    "avg_kwh_per_good_unit": 1.23,
                    "scrap_rate": 0.05,
                    "avg_hours_since_last_maintenance": 72.0,
                }
            )
        )

        self.assertEqual(snapshot["machine_id"], "024-081")
        self.assertEqual(snapshot["machine_family"], "024")
        self.assertEqual(snapshot["eligible_rows"], 12)
        self.assertEqual(snapshot["top_driver"], "High non-productive share")
        self.assertAlmostEqual(snapshot["weighted_kwh_per_good_unit"], 1.23)
        self.assertAlmostEqual(snapshot["scrap_rate"], 0.05)
        self.assertAlmostEqual(snapshot["avg_hours_since_last_maintenance"], 72.0)
        self.assertIn("024-081", snapshot["recommended_action"])

    def test_build_opportunity_worklist_merges_priority_and_action_columns(self):
        worklist_df = _build_opportunity_worklist(
            pd.DataFrame(
                [
                    {
                        "machine_id": "024-081",
                        "machine_family": "024",
                        "opportunity_flag": "High",
                        "opportunity_score": 0.81234,
                        "top_driver": "High non-productive share",
                        "eligible_rows": 12,
                        "total_good_qty": 800.0,
                        "avg_kwh_per_good_unit": 1.23456,
                    }
                ]
            )
        )

        self.assertEqual(
            worklist_df.columns.tolist(),
            [
                "Machine",
                "Family",
                "Priority",
                "Opportunity Score",
                "Top Driver",
                "Recommended Action",
                "Eligible Rows",
                "Total Good Qty",
                "Weighted kWh / Good Unit",
            ],
        )
        self.assertEqual(worklist_df.iloc[0]["Priority"], "High")
        self.assertIn("024-081", worklist_df.iloc[0]["Recommended Action"])
        self.assertEqual(worklist_df.iloc[0]["Opportunity Score"], 0.8123)
        self.assertEqual(worklist_df.iloc[0]["Weighted kWh / Good Unit"], 1.2346)

    def test_build_machine_summary_cards_returns_compact_review_payload(self):
        cards = _build_machine_summary_cards(
            {
                "machine_id": "024-081",
                "machine_family": "024",
                "opportunity_score": 0.78,
                "top_driver": "High non-productive share",
                "eligible_rows": 12,
                "total_good_qty": 800.0,
                "weighted_kwh_per_good_unit": 1.23,
                "scrap_rate": 0.05,
                "avg_hours_since_last_maintenance": 72.0,
            }
        )

        self.assertEqual(len(cards), 7)
        self.assertEqual(cards[0]["label"], "Machine")
        self.assertEqual(cards[0]["primary"], "024-081")
        self.assertEqual(cards[1]["label"], "Opportunity Score")
        self.assertEqual(cards[2]["primary"], "12")
        self.assertEqual(cards[4]["label"], "Weighted kWh / Good Unit")
        self.assertEqual(cards[6]["label"], "Avg Hours Since Maintenance")

    def test_build_preview_comparison_table_surfaces_baseline_and_best_supported_scenario(self):
        comparison_df = _build_preview_comparison_table(
            {
                "blocked": False,
                "baseline": {
                    "predicted_efficiency": 1.25,
                    "confidence": 0.82,
                    "top_driver": "Maintenance recency",
                },
                "best_supported_scenario": {
                    "scenario_name": "Maintenance Refresh",
                    "predicted_efficiency": 1.11,
                    "delta_vs_baseline": -0.14,
                    "confidence": 0.79,
                    "estimated_kwh_change": -4.2,
                    "interpretation": "Lower predicted kWh / unit than baseline.",
                },
            }
        )

        self.assertEqual(comparison_df["Comparison Point"].tolist(), ["Baseline", "Maintenance Refresh"])
        self.assertEqual(comparison_df.iloc[0]["Delta vs Baseline"], 0.0)
        self.assertEqual(comparison_df.iloc[1]["Comparable kWh Change"], -4.2)


if __name__ == "__main__":
    unittest.main()
