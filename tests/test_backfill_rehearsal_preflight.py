import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.backfill_rehearsal_preflight import build_historical_backfill_preflight_plan
from modules.etl_module import ETLPipelineModule, EXTENSION_MONTH_SOURCE_MAPPINGS


class BackfillRehearsalPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_root = Path(self.temp_dir.name)
        self._create_extension_placeholder_sources()

    def test_july_2025_plan_builds_with_placeholder_sources(self):
        plan = build_historical_backfill_preflight_plan(data_root=self.data_root)

        self.assertEqual(plan["target_month"], "July 2025")
        self.assertTrue(plan["accepted_for_rehearsal"])
        self.assertFalse(plan["blocked"])
        self.assertEqual(plan["default_resolver_mode"], "auto")
        self.assertEqual(plan["source_payload_equivalence_status"], "match")
        self.assertEqual(plan["expected_source_families"], {"energy": "complete", "csi": "complete", "mes": "complete"})

    def test_plan_declares_temp_db_and_write_boundaries(self):
        plan = build_historical_backfill_preflight_plan(data_root=self.data_root)

        self.assertTrue(plan["temp_db_required"])
        self.assertFalse(plan["live_db_write_allowed"])
        self.assertFalse(plan["repo_db_write_allowed"])
        self.assertFalse(plan["raw_file_staging_allowed"])
        self.assertFalse(plan["generated_output_staging_allowed"])
        self.assertFalse(plan["model_artifact_change_allowed"])

    def test_plan_includes_expected_source_files_and_future_steps(self):
        plan = build_historical_backfill_preflight_plan(data_root=self.data_root)

        self.assertTrue(plan["expected_source_files"]["energy_files"])
        self.assertTrue(plan["expected_source_files"]["csi_file"].endswith("CSI印刷心電圖報表2025年7月.xls"))
        self.assertTrue(plan["expected_source_files"]["mes_file"].endswith("2026年2月28日.xlsx"))
        self.assertGreaterEqual(len(plan["planned_execution_steps"]), 5)
        self.assertIn("temp DB copy only", plan["planned_write_surfaces"])

    def test_plan_includes_abort_criteria_and_required_post_run_evidence(self):
        plan = build_historical_backfill_preflight_plan(data_root=self.data_root)

        self.assertTrue(any("DB path is not temp-only" in item for item in plan["abort_criteria"]))
        self.assertTrue(any("fact_machine_hour" in item for item in plan["required_post_run_evidence"]))
        self.assertTrue(plan["proof_gaps"])

    def test_plan_does_not_create_db_files(self):
        before_db_files = set(self.data_root.glob("*.db"))

        build_historical_backfill_preflight_plan(data_root=self.data_root)

        after_db_files = set(self.data_root.glob("*.db"))
        self.assertEqual(after_db_files, before_db_files)

    def test_plan_does_not_invoke_etl_backfill_or_materialization(self):
        with patch("modules.etl_module.EnhancedSmartManufacturingETL") as etl_cls, patch(
            "modules.etl_module.CanonicalMaterializer"
        ) as materializer_cls, patch.object(
            ETLPipelineModule,
            "run_historical_canonical_backfill",
            side_effect=AssertionError("historical backfill must not run"),
        ), patch.object(
            ETLPipelineModule,
            "save_etl_results",
            side_effect=AssertionError("ETL persistence must not run"),
        ):
            etl_cls.side_effect = AssertionError("ETL extraction must not run")
            materializer_cls.side_effect = AssertionError("canonical materialization must not run")

            plan = build_historical_backfill_preflight_plan(data_root=self.data_root)

        self.assertEqual(plan["target_month"], "July 2025")
        self.assertEqual(plan["source_payload_equivalence_status"], "match")

    def test_march_2026_returns_blocked_plan(self):
        plan = build_historical_backfill_preflight_plan("March 2026", data_root=self.data_root)

        self.assertEqual(plan["target_month"], "March 2026")
        self.assertFalse(plan["accepted_for_rehearsal"])
        self.assertTrue(plan["blocked"])
        self.assertEqual(plan["source_payload_equivalence_status"], "blocked")
        self.assertEqual(plan["planned_write_surfaces"], [])

    def test_unknown_month_raises_clear_value_error(self):
        with self.assertRaisesRegex(ValueError, "No manifest source file map is defined for 2026-04"):
            build_historical_backfill_preflight_plan("April 2026", data_root=self.data_root)

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


if __name__ == "__main__":
    unittest.main()
