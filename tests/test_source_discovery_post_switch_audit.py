import tempfile
import unittest
from pathlib import Path

from modules.etl_module import (
    ETLPipelineModule,
    EXTENSION_MONTH_SOURCE_MAPPINGS,
    build_source_discovery_default_policy_audit,
)


class SourceDiscoveryPostSwitchAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_root = Path(self.temp_dir.name)
        self._create_extension_placeholder_sources()
        self._create_initial_placeholder_sources()

    def test_audit_reports_active_auto_policy(self):
        audit = build_source_discovery_default_policy_audit(data_root=self.data_root)

        self.assertEqual(audit["default_policy"], "auto")
        self.assertEqual(audit["extension_default"], "manifest")
        self.assertEqual(audit["initial_jan_jun_default"], "legacy")
        self.assertEqual(audit["manual_upload_behavior"], "unchanged")
        self.assertTrue(audit["success"])

    def test_accepted_extension_months_default_to_auto_manifest_and_are_ok(self):
        audit = build_source_discovery_default_policy_audit(data_root=self.data_root)
        accepted_rows = [
            row for row in audit["rows"]
            if row["expected_policy"] == "manifest"
        ]

        self.assertEqual(len(accepted_rows), 8)
        self.assertEqual(audit["accepted_extension_months"][0], "July 2025")
        self.assertEqual(audit["accepted_extension_months"][-1], "February 2026")
        for row in accepted_rows:
            self.assertEqual(row["default_status"], "resolved", row)
            self.assertEqual(row["default_source_discovery_mode"], "auto_manifest", row)
            self.assertEqual(row["compare_status"], "match", row)
            self.assertTrue(row["ok"], row)

    def test_jan_jun_months_remain_legacy_by_default(self):
        audit = build_source_discovery_default_policy_audit(data_root=self.data_root)
        initial_rows = [
            row for row in audit["rows"]
            if row["expected_policy"] == "legacy"
        ]

        self.assertEqual(len(initial_rows), 6)
        self.assertEqual(initial_rows[0]["month_label"], "January 2025")
        self.assertEqual(initial_rows[-1]["month_label"], "June 2025")
        for row in initial_rows:
            self.assertEqual(row["default_status"], "resolved", row)
            self.assertEqual(row["default_source_discovery_mode"], "legacy", row)
            self.assertEqual(row["explicit_legacy_status"], "resolved", row)
            self.assertEqual(row["compare_status"], "not_applicable_initial_legacy", row)
            self.assertTrue(row["ok"], row)

    def test_march_2026_is_expected_blocked_and_ok(self):
        audit = build_source_discovery_default_policy_audit(data_root=self.data_root)
        march_row = next(row for row in audit["rows"] if row["month_label"] == "March 2026")

        self.assertEqual(audit["blocked_months"], ["March 2026"])
        self.assertEqual(march_row["expected_policy"], "blocked")
        self.assertEqual(march_row["default_status"], "blocked")
        self.assertEqual(march_row["explicit_legacy_status"], "blocked")
        self.assertEqual(march_row["compare_status"], "expected_blocked")
        self.assertTrue(march_row["ok"])

    def test_audit_helper_does_not_create_db_file(self):
        before_db_files = set(self.data_root.glob("*.db"))

        build_source_discovery_default_policy_audit(data_root=self.data_root)

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
