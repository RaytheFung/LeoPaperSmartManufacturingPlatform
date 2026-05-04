import copy
import tempfile
import unittest
from pathlib import Path

from core.data_contracts import get_accepted_canonical_months, load_source_manifest
from core.source_manifest_discovery import (
    build_manifest_source_availability_dataframe,
    compare_manifest_to_legacy_extension_mapping,
    get_manifest_month_source_files,
    month_key_to_label,
    month_label_to_key,
    resolve_manifest_month_sources,
)
from modules.etl_module import (
    ETLPipelineModule,
    EXTENSION_MONTH_SOURCE_MAPPINGS,
    _build_extension_source_availability_dataframe,
)


class SourceManifestDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_source_manifest()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.extension_root = Path(self.temp_dir.name)
        self._create_placeholder_sources()

    def test_manifest_backed_extension_months_match_accepted_canonical_scope(self):
        month_map = self.manifest["month_source_files"]
        accepted_manifest_keys = {
            month_key
            for month_key, spec in month_map.items()
            if spec["canonical_scope_status"] == "accepted"
        }
        extended_scope = next(
            scope
            for scope in self.manifest["source_scopes"]
            if scope["scope_id"] == "2025_jul_2026_feb_collected"
        )

        self.assertEqual(sorted(accepted_manifest_keys), extended_scope["accepted_months"])
        self.assertTrue(accepted_manifest_keys.issubset(set(get_accepted_canonical_months(self.manifest))))
        self.assertEqual(month_label_to_key("July 2025"), "2025-07")
        self.assertEqual(month_key_to_label("2026-02"), "February 2026")

    def test_march_2026_remains_blocked_out_of_scope(self):
        march_spec = get_manifest_month_source_files("March 2026", self.manifest)

        self.assertEqual(march_spec["canonical_scope_status"], "blocked_out_of_scope")
        self.assertEqual(march_spec["backfill_readiness"], "blocked")
        self.assertNotIn("2026-03", get_accepted_canonical_months(self.manifest))
        with self.assertRaisesRegex(ValueError, "blocks March 2026"):
            resolve_manifest_month_sources("March 2026", self.extension_root, self.manifest)

    def test_july_2025_resolution_matches_legacy_output_shape_and_suffixes(self):
        pipeline = ETLPipelineModule(db_path=self.extension_root / "stage_b2.db")
        legacy_sources = pipeline.resolve_historical_month_sources(
            "July 2025",
            data_root=self.extension_root,
        )
        manifest_sources = resolve_manifest_month_sources(
            "2025-07",
            data_root=self.extension_root,
            manifest=self.manifest,
        )

        for key in (
            "dataset_root",
            "energy_files",
            "csi_file",
            "mes_file",
            "family_status",
            "notes",
            "backfill_readiness",
        ):
            self.assertIn(key, manifest_sources)
            self.assertIn(key, legacy_sources)
        self.assertEqual(manifest_sources["backfill_readiness"], legacy_sources["backfill_readiness"])
        self.assertTrue(manifest_sources["csi_file"].endswith(".xls"))
        self.assertIn("能耗、費用報表__2025.7.xlsx", manifest_sources["energy_files"][0])
        self.assertTrue(manifest_sources["mes_file"].endswith("2026年2月28日.xlsx"))

    def test_manifest_availability_readiness_matches_legacy_for_required_months(self):
        legacy_df = _build_extension_source_availability_dataframe(self.extension_root).set_index("Month")
        manifest_df = build_manifest_source_availability_dataframe(
            self.extension_root,
            self.manifest,
        ).set_index("Month")

        for month_label in ("July 2025", "August 2025", "February 2026", "March 2026"):
            self.assertEqual(
                manifest_df.loc[month_label, "Backfill Readiness"],
                legacy_df.loc[month_label, "Backfill Readiness"],
            )

    def test_manifest_config_does_not_require_absolute_paths(self):
        for spec in self.manifest["month_source_files"].values():
            for relative_path in spec["energy_files"]:
                self.assertFalse(Path(relative_path).is_absolute())
            if spec.get("csi_file"):
                self.assertFalse(Path(spec["csi_file"]).is_absolute())
            if spec.get("mes_file"):
                self.assertFalse(Path(spec["mes_file"]).is_absolute())

        relative_sources = resolve_manifest_month_sources("July 2025", manifest=self.manifest)
        self.assertFalse(Path(relative_sources["energy_files"][0]).is_absolute())

    def test_missing_file_checks_run_against_temporary_placeholder_directories(self):
        missing_root = self.extension_root / "missing"

        with self.assertRaisesRegex(ValueError, "files are missing"):
            resolve_manifest_month_sources("July 2025", missing_root, self.manifest)

        availability_df = build_manifest_source_availability_dataframe(missing_root, self.manifest)
        july_row = availability_df.set_index("Month").loc["July 2025"]
        self.assertEqual(july_row["Backfill Readiness"], "Blocked")
        self.assertIn("能耗、費用報表__2025.7.xlsx", july_row["Missing Files"])

    def test_malformed_source_file_map_raises_value_error(self):
        malformed = copy.deepcopy(self.manifest)
        malformed["month_source_files"]["2025-07"]["energy_files"] = ["/tmp/source.xlsx"]

        with self.assertRaisesRegex(ValueError, "absolute"):
            get_manifest_month_source_files("July 2025", malformed)

        malformed = copy.deepcopy(self.manifest)
        malformed["month_source_files"]["2025-07"].pop("family_status")
        with self.assertRaisesRegex(ValueError, "family_status"):
            get_manifest_month_source_files("July 2025", malformed)

    def test_manifest_comparison_reports_legacy_equivalence(self):
        comparison = compare_manifest_to_legacy_extension_mapping(self.manifest)

        self.assertTrue(comparison["matches"])
        self.assertEqual(
            comparison["checked_months"],
            list(EXTENSION_MONTH_SOURCE_MAPPINGS),
        )
        self.assertEqual(comparison["differences"], [])

    def _create_placeholder_sources(self):
        created_paths = set()
        for spec in self.manifest["month_source_files"].values():
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
