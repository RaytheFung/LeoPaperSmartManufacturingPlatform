import unittest
from datetime import datetime

import numpy as np
import pandas as pd

from modules.euvg_module import EnhancedUnifiedViewGenerator, TeamSynergyAnalyzer


class EUVGAllocationTests(unittest.TestCase):
    def setUp(self):
        self.generator = EnhancedUnifiedViewGenerator(production_floor=0.5)

    def _make_csi_row(self, start, end, quantity):
        return pd.Series(
            {
                "開始時間": start,
                "結束時間": end,
                "正品數量": quantity,
            }
        )

    def test_allocate_production_hourly_respects_production_floor(self):
        row = self._make_csi_row(
            datetime(2025, 1, 1, 8, 15),
            datetime(2025, 1, 1, 8, 45),
            0.3,
        )
        allocations = self.generator.allocate_production_hourly(row)
        self.assertTrue(allocations, "Expected at least one allocation entry")
        for allocation in allocations:
            self.assertEqual(
                allocation["production_qty"],
                0,
                "Quantities below production floor should be zeroed",
            )
            self.assertEqual(
                allocation["proportion"], 0, "Zeroed quantities should have zero proportion"
            )

    def test_allocate_production_hourly_preserves_total_quantity(self):
        total_qty = 120
        row = self._make_csi_row(
            datetime(2025, 1, 1, 9, 0),
            datetime(2025, 1, 1, 13, 0),
            total_qty,
        )
        allocations = self.generator.allocate_production_hourly(row)
        allocated_qty = sum(a["production_qty"] for a in allocations)
        self.assertAlmostEqual(allocated_qty, total_qty, delta=0.01)
        self.assertTrue(all(a["production_qty"] >= 0 for a in allocations))


class TeamSynergyAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = TeamSynergyAnalyzer()

    def test_analyze_team_performance_ranks_by_efficiency(self):
        sample = pd.DataFrame(
            {
                "team_composition": ["Alice + Bob", "Alice + Bob", "Carol"],
                "production_qty": [100, 150, 80],
                "energy_kwh": [250, 360, 200],
                "kwh_per_unit": [2.5, 2.4, 2.5],
                "task_type": ["印刷", "印刷", "光油"],
            }
        )

        summary = self.analyzer.analyze_team_performance(sample)
        rankings = summary["team_rankings"]

        self.assertGreaterEqual(len(rankings), 2)
        top_team = rankings[0]
        bottom_team = rankings[-1]

        self.assertLessEqual(
            top_team["avg_kwh_per_unit"],
            bottom_team["avg_kwh_per_unit"],
            "Rankings should be sorted by average kWh/unit ascending",
        )
        expected_efficiency = (250 + 360) / (100 + 150)
        self.assertAlmostEqual(top_team["avg_kwh_per_unit"], expected_efficiency, places=3)
        self.assertEqual(top_team["primary_task"], "印刷")


if __name__ == "__main__":
    unittest.main()
