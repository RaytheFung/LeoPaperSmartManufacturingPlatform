import tempfile
import unittest
from pathlib import Path

import pandas as pd

from modules.etl_module import (
    ETLPipelineModule,
    EXTENSION_MONTH_SOURCE_MAPPINGS,
    _build_extension_source_availability_dataframe,
    _scope_source_dataframe_to_month,
)


class Task13SourceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.extension_root = Path(self.temp_dir.name)

        created_paths = set()
        for spec in EXTENSION_MONTH_SOURCE_MAPPINGS.values():
            for relative_path in spec["energy_files"]:
                created_paths.add(relative_path)
            if spec.get("csi_file"):
                created_paths.add(spec["csi_file"])
            if spec.get("mes_file"):
                created_paths.add(spec["mes_file"])

        for relative_path in created_paths:
            full_path = self.extension_root / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(b"placeholder")

    def test_extension_availability_matrix_distinguishes_ready_partial_and_blocked_months(self):
        availability_df = _build_extension_source_availability_dataframe(self.extension_root)
        indexed = availability_df.set_index("Month")

        self.assertEqual(indexed.loc["July 2025", "Backfill Readiness"], "Ready")
        self.assertEqual(indexed.loc["August 2025", "Backfill Readiness"], "Ready with Flags")
        self.assertEqual(indexed.loc["March 2026", "Backfill Readiness"], "Blocked")
        self.assertIn("July 2025 CSI is accepted", indexed.loc["July 2025", "Notes"])

    def test_extension_source_resolution_returns_real_july_mapping(self):
        pipeline = ETLPipelineModule(db_path=self.extension_root / "task13.db")

        source_files = pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
        )

        self.assertEqual(source_files["backfill_readiness"], "ready")
        self.assertTrue(source_files["csi_file"].endswith(".xls"))
        self.assertIn("能耗、費用報表__2025.7.xlsx", source_files["energy_files"][0])
        self.assertTrue(source_files["mes_file"].endswith("2026年2月28日.xlsx"))

    def test_extension_source_resolution_blocks_march_2026(self):
        pipeline = ETLPipelineModule(db_path=self.extension_root / "task13.db")

        with self.assertRaisesRegex(ValueError, "blocked"):
            pipeline.resolve_historical_month_sources(
                "March 2026",
                data_root=self.extension_root,
            )

    def test_mes_month_scoping_uses_report_time_only(self):
        mes_df = pd.DataFrame(
            [
                {
                    "資源": "1024-00075",
                    "報工時間": pd.Timestamp("2026-02-28 23:50:00"),
                    "狀態變更時間": pd.Timestamp("2026-03-01 00:05:00"),
                    "記錄新增時間": pd.Timestamp("2026-03-01 00:06:00"),
                }
            ]
        )

        feb_df = _scope_source_dataframe_to_month(mes_df, "mes", "February 2026")
        march_df = _scope_source_dataframe_to_month(mes_df, "mes", "March 2026")

        self.assertEqual(len(feb_df), 1)
        self.assertTrue(march_df.empty)


if __name__ == "__main__":
    unittest.main()
