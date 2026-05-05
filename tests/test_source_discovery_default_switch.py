import tempfile
import unittest
from pathlib import Path

from modules.etl_module import ETLPipelineModule, EXTENSION_MONTH_SOURCE_MAPPINGS


class SourceDiscoveryDefaultSwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_root = Path(self.temp_dir.name)
        self.pipeline = ETLPipelineModule(
            db_path=self.data_root / "source_discovery_default_switch.db",
            initialize_schema=False,
        )
        self._create_extension_placeholder_sources()
        self._create_initial_month_placeholder_sources("January")

    def test_default_july_2025_uses_auto_manifest_policy(self):
        source_files = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.data_root,
        )

        self.assertEqual(source_files["source_discovery_mode"], "auto_manifest")
        self.assertEqual(source_files["backfill_readiness"], "ready")
        self.assertTrue(source_files["dataset_root"].endswith(str(self.data_root)))
        self.assertIn("能耗、費用報表__2025.7.xlsx", source_files["energy_files"][0])
        self.assertTrue(source_files["csi_file"].endswith("CSI印刷心電圖報表2025年7月.xls"))
        self.assertTrue(source_files["mes_file"].endswith("2026年2月28日.xlsx"))

    def test_explicit_legacy_july_2025_still_works(self):
        legacy_sources = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.data_root,
            discovery_mode="legacy",
        )

        self.assertNotIn("source_discovery_mode", legacy_sources)
        self.assertEqual(legacy_sources["backfill_readiness"], "ready")
        self.assertIn("能耗、費用報表__2025.7.xlsx", legacy_sources["energy_files"][0])
        self.assertTrue(legacy_sources["csi_file"].endswith("CSI印刷心電圖報表2025年7月.xls"))

    def test_explicit_compare_july_2025_still_reports_match(self):
        compare_sources = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.data_root,
            discovery_mode="compare",
        )

        self.assertEqual(compare_sources["source_discovery_mode"], "compare")
        self.assertTrue(compare_sources["manifest_equivalence"]["matches"])
        self.assertEqual(compare_sources["manifest_equivalence"]["differences"], [])

    def test_default_march_2026_remains_blocked(self):
        with self.assertRaisesRegex(ValueError, "blocked"):
            self.pipeline.resolve_historical_month_sources(
                "March 2026",
                data_root=self.data_root,
            )

    def test_explicit_manifest_march_2026_remains_blocked(self):
        with self.assertRaisesRegex(ValueError, "blocks March 2026"):
            self.pipeline.resolve_historical_month_sources(
                "March 2026",
                data_root=self.data_root,
                discovery_mode="manifest",
            )

    def test_default_january_2025_still_uses_legacy_initial_mapping(self):
        source_files = self.pipeline.resolve_historical_month_sources(
            "January 2025",
            data_root=self.data_root,
        )

        self.assertNotIn("source_discovery_mode", source_files)
        self.assertEqual(source_files["dataset_root"], str(self.data_root))
        self.assertIn("Energy Usage 1hr Interval", source_files["energy_files"][0])
        self.assertTrue(source_files["csi_file"].endswith("CSI印刷心電圖報表Jan.xlsx"))
        self.assertTrue(source_files["mes_file"].endswith("MES生產數據Jan(Printer).xlsx"))

    def test_invalid_mode_still_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported source discovery mode"):
            self.pipeline.resolve_historical_month_sources(
                "July 2025",
                data_root=self.data_root,
                discovery_mode="unknown",
            )

    def test_unknown_month_still_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "No historical source mapping"):
            self.pipeline.resolve_historical_month_sources(
                "April 2026",
                data_root=self.data_root,
            )

    def test_source_discovery_only_default_switch_does_not_create_db_file(self):
        before_db_files = set(self.data_root.glob("*.db"))

        self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.data_root,
        )
        self.pipeline.resolve_historical_month_sources(
            "January 2025",
            data_root=self.data_root,
        )

        after_db_files = set(self.data_root.glob("*.db"))
        self.assertEqual(after_db_files, before_db_files)

    def _create_extension_placeholder_sources(self):
        created_paths = set()
        for spec in EXTENSION_MONTH_SOURCE_MAPPINGS.values():
            created_paths.update(spec["energy_files"])
            if spec.get("csi_file"):
                created_paths.add(spec["csi_file"])
            if spec.get("mes_file"):
                created_paths.add(spec["mes_file"])

        for relative_path in created_paths:
            full_path = self.data_root / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(b"placeholder")

    def _create_initial_month_placeholder_sources(self, month_name):
        mapping = ETLPipelineModule.HISTORICAL_MONTH_FILE_MAPPINGS[month_name]
        energy_dir = self.data_root / "Energy Usage 1hr Interval"
        csi_dir = self.data_root / "CSI Monthly"
        mes_dir = self.data_root / "MES Monthly"
        for directory in (energy_dir, csi_dir, mes_dir):
            directory.mkdir(parents=True, exist_ok=True)
        for file_name in mapping["energy"]:
            (energy_dir / file_name).write_bytes(b"energy")
        (csi_dir / mapping["csi"]).write_bytes(b"csi")
        (mes_dir / mapping["mes"]).write_bytes(b"mes")


if __name__ == "__main__":
    unittest.main()
