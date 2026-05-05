import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from modules.etl_module import EXTENSION_MONTH_SOURCE_MAPPINGS
from scripts.compare_source_discovery_modes import (
    build_source_discovery_compare_diagnostics,
    main,
)


class SourceDiscoveryCompareDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.extension_root = Path(self.temp_dir.name)
        self._create_placeholder_sources()

    def test_diagnostic_helper_returns_match_for_july_2025(self):
        diagnostics = build_source_discovery_compare_diagnostics(
            ["July 2025"],
            data_root=self.extension_root,
        )

        self.assertTrue(diagnostics["success"])
        row = diagnostics["rows"][0]
        self.assertEqual(row["month_label"], "July 2025")
        self.assertTrue(row["matches"])
        self.assertEqual(row["differences"], [])
        self.assertEqual(row["legacy_status"], "resolved")
        self.assertEqual(row["manifest_status"], "resolved")

    def test_diagnostic_helper_returns_expected_blocked_for_march_2026(self):
        diagnostics = build_source_discovery_compare_diagnostics(
            ["March 2026"],
            data_root=self.extension_root,
        )

        self.assertTrue(diagnostics["success"])
        row = diagnostics["rows"][0]
        self.assertTrue(row["expected_blocked"])
        self.assertEqual(row["backfill_readiness"], "blocked")
        self.assertEqual(row["legacy_status"], "blocked")
        self.assertEqual(row["manifest_status"], "blocked")

    def test_main_exits_success_with_placeholder_sources_and_march_blocked(self):
        with redirect_stdout(StringIO()):
            exit_code = main(["--data-root", str(self.extension_root)])

        self.assertEqual(exit_code, 0)

    def test_diagnostic_reports_manifest_mismatch_from_mocked_pipeline(self):
        diagnostics = build_source_discovery_compare_diagnostics(
            ["July 2025"],
            data_root=self.extension_root,
            pipeline=_MismatchPipeline(),
        )

        self.assertFalse(diagnostics["success"])
        row = diagnostics["rows"][0]
        self.assertFalse(row["matches"])
        self.assertEqual(row["differences"][0]["field"], "csi_file")

    def test_diagnostic_does_not_create_db_file(self):
        before_db_files = set(self.extension_root.glob("*.db"))

        build_source_discovery_compare_diagnostics(
            ["July 2025", "March 2026"],
            data_root=self.extension_root,
        )

        after_db_files = set(self.extension_root.glob("*.db"))
        self.assertEqual(after_db_files, before_db_files)

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


class _MismatchPipeline:
    def resolve_historical_month_sources(self, _month_label, data_root=None, *, discovery_mode):
        self.last_data_root = data_root
        self.last_discovery_mode = discovery_mode
        return {
            "backfill_readiness": "ready",
            "manifest_equivalence": {
                "matches": False,
                "differences": [
                    {
                        "field": "csi_file",
                        "legacy": "legacy.xls",
                        "manifest": "manifest.xls",
                    }
                ],
            },
        }


if __name__ == "__main__":
    unittest.main()
