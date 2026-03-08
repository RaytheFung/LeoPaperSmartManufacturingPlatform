import unittest

import pandas as pd

from core.etl.mapper import MachineMapper
from core.etl.reporter import ETLReporter, ReportContext


class MachineMapperPatternTests(unittest.TestCase):
    def test_extract_machine_pattern_normalizes_common_formats(self):
        cases = [
            ("D-024-001主機", "024-001", "主機"),
            ("1024-00012 UV", "024-012", "UV"),
            ("024 - 567", "024-567", None),
            ("Unknown Machine", None, None),
        ]
        for machine_name, expected_pattern, expected_component in cases:
            with self.subTest(machine_name=machine_name):
                pattern, component = MachineMapper.extract_machine_pattern(machine_name)
                self.assertEqual(pattern, expected_pattern)
                self.assertEqual(component, expected_component)


class ETLReporterMetricsTests(unittest.TestCase):
    def setUp(self):
        energy_aggregated = pd.DataFrame(
            {
                "total_kwh": [100.0],
                "avg_kwh": [10.0],
                "min_kwh": [5.0],
                "max_kwh": [12.0],
                "records": [10],
                "components": [["主機"]],
                "original_names": [["D-024-001主機"]],
                "date_range": [{"start": pd.Timestamp("2025-01-01"), "end": pd.Timestamp("2025-01-10")}],
                "unique_components": [1],
                "machine_id": ["024-001"],
            }
        ).set_index("machine_id")

        csi_df = pd.DataFrame(
            {
                "機台編號": ["CSI-001"],
                "正品數量": [100],
                "廢品數量": [5],
            }
        )
        mes_df = pd.DataFrame(
            {
                "資源": ["MES-001"],
                "計劃生產數量": [150],
                "實際完成數量": [120],
            }
        )
        mapping_result = {
            "three_way_matches": [
                {
                    "machine_id": "024-001",
                    "csi": "CSI-001",
                    "mes": "MES-001",
                    "components": 1,
                    "total_kwh": 100.0,
                    "pattern": "024 series",
                    "energy_samples": ["D-024-001主機"],
                }
            ],
            "mapping_stats": {},
        }
        partial_matches = {
            "energy_csi_only": [],
            "energy_mes_only": [],
            "csi_mes_only": [],
            "energy_only": [],
            "csi_only": [],
            "mes_only": [],
        }

        context = ReportContext(
            energy_aggregated=energy_aggregated,
            csi_df=csi_df,
            mes_df=mes_df,
            mapping_result=mapping_result,
            partial_matches=partial_matches,
        )
        self.reporter = ETLReporter(context)

    def test_calculate_integrated_metrics_produces_expected_fields(self):
        metrics = self.reporter.calculate_integrated_metrics()
        self.assertSetEqual(
            set(metrics.columns),
            {
                "machine_id",
                "energy_id",
                "csi_id",
                "mes_id",
                "total_kwh",
                "good_products",
                "defect_products",
                "defect_rate",
                "planned_quantity",
                "actual_quantity",
                "plan_achievement",
                "kwh_per_unit",
                "components",
            },
        )
        row = metrics.iloc[0]
        self.assertAlmostEqual(row["defect_rate"], (5 / 105) * 100, places=5)
        self.assertAlmostEqual(row["plan_achievement"], (120 / 150) * 100, places=5)
        self.assertAlmostEqual(row["kwh_per_unit"], 1.0)


class MachineMapperIntegrationTests(unittest.TestCase):
    def test_create_mapping_generates_three_way_and_partial_stats(self):
        energy_df = pd.DataFrame(
            {
                "machine": ["D-024-001主機", "D-024-001馬達", "135-0002 UV"],
                "datetime": [
                    pd.Timestamp("2025-01-01 00:00:00"),
                    pd.Timestamp("2025-01-01 01:00:00"),
                    pd.Timestamp("2025-01-01 02:00:00"),
                ],
                "electricity_kwh": [20.0, 10.0, 5.0],
                "electricity_cost": [200.0, 100.0, 50.0],
            }
        )
        csi_df = pd.DataFrame(
            {
                "機台編號": ["024-001 主機", "CSI-ONLY"],
                "正品數量": [80, 0],
                "廢品數量": [5, 0],
            }
        )
        mes_df = pd.DataFrame(
            {
                "資源": ["024-001 IR", "MES-ONLY"],
                "計劃生產數量": [100, 50],
                "實際完成數量": [90, 25],
            }
        )

        mapper = MachineMapper(energy_df, csi_df, mes_df)
        aggregated = mapper.aggregate_energy()
        self.assertAlmostEqual(aggregated.loc["024-001", "total_kwh"], 30.0)
        self.assertEqual(aggregated.loc["024-001", "records"], 2)
        self.assertAlmostEqual(aggregated.loc["135-0002", "total_kwh"], 5.0)

        result = mapper.create_mapping()
        self.assertEqual(result.mapping_stats["three_way_matches"], 1)
        self.assertEqual(result.three_way_matches[0]["machine_id"], "024-001")
        self.assertEqual(result.energy_to_csi["024-001"], "024-001 主機")
        self.assertEqual(result.energy_to_mes["024-001"], "024-001 IR")
        self.assertEqual(result.csi_to_mes["024-001 主機"], "024-001 IR")

        self.assertIn("135-0002", result.partial_matches["energy_only"])
        self.assertIn("CSI-ONLY", result.partial_matches["csi_only"])
        self.assertIn("MES-ONLY", result.partial_matches["mes_only"])


if __name__ == "__main__":
    unittest.main()
