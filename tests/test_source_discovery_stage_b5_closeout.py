import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.etl_module import (
    ETLPipelineModule,
    EXTENSION_MONTH_SOURCE_MAPPINGS,
    build_source_discovery_default_policy_audit,
    build_source_discovery_diagnostic_snapshot,
)


class SourceDiscoveryStageB5CloseoutTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_root = Path(self.temp_dir.name)
        self._create_extension_placeholder_sources()
        self._create_initial_placeholder_sources()

    def test_closeout_snapshots_are_read_only_and_preserve_policy_boundaries(self):
        before_db_files = set(self.data_root.glob("*.db"))

        with patch("modules.etl_module.EnhancedSmartManufacturingETL") as etl_cls, patch(
            "modules.etl_module.CanonicalMaterializer"
        ) as materializer_cls, patch.object(
            ETLPipelineModule,
            "run_historical_canonical_backfill",
            side_effect=AssertionError("historical backfill must not run"),
        ):
            etl_cls.side_effect = AssertionError("ETL extraction must not run")
            materializer_cls.side_effect = AssertionError("canonical materialization must not run")

            policy_audit = build_source_discovery_default_policy_audit(data_root=self.data_root)
            compare_snapshot = build_source_discovery_diagnostic_snapshot(data_root=self.data_root)

        after_db_files = set(self.data_root.glob("*.db"))
        self.assertEqual(after_db_files, before_db_files)
        self.assertTrue(policy_audit["success"])
        self.assertTrue(compare_snapshot["success"])
        self.assertEqual(policy_audit["default_policy"], "auto")
        self.assertEqual(policy_audit["extension_default"], "manifest")
        self.assertEqual(policy_audit["initial_jan_jun_default"], "legacy")
        self.assertEqual(policy_audit["manual_upload_behavior"], "unchanged")

        manifest_rows = [
            row for row in policy_audit["rows"]
            if row["expected_policy"] == "manifest"
        ]
        legacy_rows = [
            row for row in policy_audit["rows"]
            if row["expected_policy"] == "legacy"
        ]
        march_policy_row = next(row for row in policy_audit["rows"] if row["month_label"] == "March 2026")
        march_compare_row = next(row for row in compare_snapshot["rows"] if row["Month"] == "March 2026")

        self.assertEqual(len(manifest_rows), 8)
        self.assertTrue(all(row["default_source_discovery_mode"] == "auto_manifest" for row in manifest_rows))
        self.assertEqual(len(legacy_rows), 6)
        self.assertTrue(all(row["default_source_discovery_mode"] == "legacy" for row in legacy_rows))
        self.assertEqual(march_policy_row["default_status"], "blocked")
        self.assertEqual(march_policy_row["compare_status"], "expected_blocked")
        self.assertTrue(march_compare_row["Expected Blocked"])
        self.assertTrue(march_compare_row["OK"])

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

    def _create_initial_placeholder_sources(self):
        energy_dir = self.data_root / "Energy Usage 1hr Interval"
        csi_dir = self.data_root / "CSI Monthly"
        mes_dir = self.data_root / "MES Monthly"
        for directory in (energy_dir, csi_dir, mes_dir):
            directory.mkdir(parents=True, exist_ok=True)

        for mapping in ETLPipelineModule.HISTORICAL_MONTH_FILE_MAPPINGS.values():
            for file_name in mapping["energy"]:
                (energy_dir / file_name).write_bytes(b"energy")
            (csi_dir / mapping["csi"]).write_bytes(b"csi")
            (mes_dir / mapping["mes"]).write_bytes(b"mes")


if __name__ == "__main__":
    unittest.main()
