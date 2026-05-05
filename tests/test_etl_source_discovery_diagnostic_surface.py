import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.etl_module import (
    EXTENSION_MONTH_SOURCE_MAPPINGS,
    build_source_discovery_diagnostic_snapshot,
)
from scripts.compare_source_discovery_modes import EXTENSION_MONTH_LABELS


class ETLSourceDiscoveryDiagnosticSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.extension_root = Path(self.temp_dir.name)
        self._create_placeholder_sources()

    def test_snapshot_covers_all_extension_months(self):
        snapshot = build_source_discovery_diagnostic_snapshot(data_root=self.extension_root)

        self.assertEqual(snapshot["month_count"], len(EXTENSION_MONTH_LABELS))
        self.assertEqual([row["Month"] for row in snapshot["rows"]], EXTENSION_MONTH_LABELS)
        self.assertEqual(snapshot["accepted_month_count"], 8)
        self.assertEqual(snapshot["expected_blocked_month_count"], 1)

    def test_snapshot_reports_accepted_months_as_matching_without_differences(self):
        snapshot = build_source_discovery_diagnostic_snapshot(data_root=self.extension_root)

        accepted_rows = [row for row in snapshot["rows"] if not row["Expected Blocked"]]
        self.assertTrue(accepted_rows)
        for row in accepted_rows:
            self.assertTrue(row["Matches"], row)
            self.assertEqual(row["Legacy Status"], "Resolved")
            self.assertEqual(row["Manifest Status"], "Resolved")
            self.assertEqual(row["Difference Count"], 0)
            self.assertEqual(row["Error Count"], 0)
            self.assertTrue(row["OK"], row)

    def test_snapshot_keeps_march_2026_as_expected_blocked_boundary(self):
        snapshot = build_source_discovery_diagnostic_snapshot(data_root=self.extension_root)

        march_row = next(row for row in snapshot["rows"] if row["Month"] == "March 2026")
        self.assertTrue(march_row["Expected Blocked"])
        self.assertFalse(march_row["Matches"])
        self.assertEqual(march_row["Backfill Readiness"], "Blocked")
        self.assertEqual(march_row["Legacy Status"], "Blocked")
        self.assertEqual(march_row["Manifest Status"], "Blocked")
        self.assertTrue(march_row["OK"])

    def test_snapshot_helper_does_not_create_db_file(self):
        before_db_files = set(self.extension_root.glob("*.db"))

        build_source_discovery_diagnostic_snapshot(data_root=self.extension_root)

        after_db_files = set(self.extension_root.glob("*.db"))
        self.assertEqual(after_db_files, before_db_files)

    def test_snapshot_helper_does_not_use_streamlit_runtime(self):
        with patch("modules.etl_module.st", _ExplodingStreamlit()):
            snapshot = build_source_discovery_diagnostic_snapshot(data_root=self.extension_root)

        self.assertTrue(snapshot["success"])

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


class _ExplodingStreamlit:
    def __getattr__(self, name):
        raise AssertionError(f"Streamlit runtime was accessed through st.{name}")


if __name__ == "__main__":
    unittest.main()
