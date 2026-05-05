import tempfile
import unittest
from pathlib import Path

from modules.etl_module import ETLPipelineModule, EXTENSION_MONTH_SOURCE_MAPPINGS


class SourceDiscoveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.extension_root = Path(self.temp_dir.name)
        self._create_placeholder_sources()
        self.pipeline = ETLPipelineModule(db_path=self.extension_root / "stage_b3.db")

    def test_default_resolution_uses_auto_manifest_for_july_2025(self):
        source_files = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
        )

        self.assertEqual(source_files["source_discovery_mode"], "auto_manifest")
        self.assertEqual(source_files["backfill_readiness"], "ready")
        self.assertTrue(source_files["csi_file"].endswith(".xls"))
        self.assertIn("能耗、費用報表__2025.7.xlsx", source_files["energy_files"][0])
        self.assertTrue(source_files["mes_file"].endswith("2026年2月28日.xlsx"))

    def test_explicit_legacy_mode_still_resolves_july_2025(self):
        legacy_sources = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
            discovery_mode="legacy",
        )

        self.assertNotIn("source_discovery_mode", legacy_sources)
        self.assertEqual(legacy_sources["backfill_readiness"], "ready")
        self.assertTrue(legacy_sources["csi_file"].endswith(".xls"))
        self.assertIn("能耗、費用報表__2025.7.xlsx", legacy_sources["energy_files"][0])

    def test_manifest_mode_returns_equivalent_july_source_files(self):
        legacy_sources = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
        )
        manifest_sources = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
            discovery_mode="manifest",
        )

        self.assertEqual(manifest_sources["source_discovery_mode"], "manifest")
        self.assertEqual(manifest_sources["energy_files"], legacy_sources["energy_files"])
        self.assertEqual(manifest_sources["csi_file"], legacy_sources["csi_file"])
        self.assertEqual(manifest_sources["mes_file"], legacy_sources["mes_file"])
        self.assertEqual(manifest_sources["family_status"], legacy_sources["family_status"])
        self.assertEqual(manifest_sources["backfill_readiness"], legacy_sources["backfill_readiness"])

    def test_manifest_mode_blocks_march_2026(self):
        with self.assertRaisesRegex(ValueError, "blocks March 2026"):
            self.pipeline.resolve_historical_month_sources(
                "March 2026",
                data_root=self.extension_root,
                discovery_mode="manifest",
            )

    def test_compare_mode_returns_legacy_payload_with_matching_july_equivalence(self):
        source_files = self.pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
            discovery_mode="compare",
        )

        self.assertEqual(source_files["source_discovery_mode"], "compare")
        self.assertEqual(source_files["backfill_readiness"], "ready")
        self.assertTrue(source_files["manifest_equivalence"]["matches"])
        self.assertEqual(source_files["manifest_equivalence"]["differences"], [])
        self.assertIn("能耗、費用報表__2025.7.xlsx", source_files["energy_files"][0])

    def test_compare_mode_reports_march_2026_blocked_status_honestly(self):
        source_files = self.pipeline.resolve_historical_month_sources(
            "March 2026",
            data_root=self.extension_root,
            discovery_mode="compare",
        )

        equivalence = source_files["manifest_equivalence"]
        self.assertEqual(source_files["source_discovery_mode"], "compare")
        self.assertEqual(source_files["backfill_readiness"], "blocked")
        self.assertFalse(equivalence["matches"])
        self.assertTrue(equivalence["both_blocked"])
        self.assertIn("blocked", equivalence["legacy_error"]["message"])
        self.assertIn("blocks March 2026", equivalence["manifest_error"]["message"])

    def test_invalid_discovery_mode_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported source discovery mode"):
            self.pipeline.resolve_historical_month_sources(
                "July 2025",
                data_root=self.extension_root,
                discovery_mode="unknown",
            )

    def _create_placeholder_sources(self):
        created_paths = set()
        for spec in EXTENSION_MONTH_SOURCE_MAPPINGS.values():
            created_paths.update(spec["energy_files"])
            if spec.get("csi_file"):
                created_paths.add(spec["csi_file"])
            if spec.get("mes_file"):
                created_paths.add(spec["mes_file"])

        for relative_path in created_paths:
            full_path = self.extension_root / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(b"placeholder")


if __name__ == "__main__":
    unittest.main()
