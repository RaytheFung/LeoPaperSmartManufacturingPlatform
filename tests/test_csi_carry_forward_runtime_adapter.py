import sys
import tempfile
import unittest
from pathlib import Path

from core.csi_carry_forward_config import CarryForwardConfig, CarryForwardMode
from core.csi_carry_forward_runtime_adapter import (
    build_carry_forward_runtime_preflight,
    maybe_build_preflight_only_result,
    summarize_carry_forward_runtime_policy,
)
from modules.etl_module import ETLPipelineModule


class CsiCarryForwardRuntimeAdapterTests(unittest.TestCase):
    def test_disabled_mode_returns_noop_without_touching_helpers(self):
        def fail_builder(**kwargs):
            raise AssertionError("disabled mode must not call helper")

        result = maybe_build_preflight_only_result(
            CarryForwardConfig(),
            None,
            None,
            preflight_builder=fail_builder,
        )

        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["enabled"])
        self.assertFalse(result["helper_called"])
        self.assertFalse(result["writes_db"])

    def test_preflight_only_rejects_missing_target_or_source_month(self):
        with self.assertRaisesRegex(ValueError, "target month"):
            build_carry_forward_runtime_preflight(
                CarryForwardMode.PREFLIGHT_ONLY,
                source_package_month="July 2025",
            )
        with self.assertRaisesRegex(ValueError, "source package month"):
            build_carry_forward_runtime_preflight(
                CarryForwardMode.PREFLIGHT_ONLY,
                target_canonical_month="August 2025",
            )

    def test_preflight_only_accepts_july_august_allowlisted_boundary(self):
        result = maybe_build_preflight_only_result(
            CarryForwardConfig(
                mode=CarryForwardMode.PREFLIGHT_ONLY,
                source_package_month="July 2025",
                target_canonical_month="August 2025",
            ),
            "July 2025",
            "August 2025",
        )

        self.assertEqual(result["status"], "preflight_only")
        self.assertEqual(result["source_package_month"], "July 2025")
        self.assertEqual(result["target_canonical_month"], "August 2025")
        self.assertFalse(result["helper_called"])
        self.assertFalse(result["writes_db"])

    def test_preflight_only_accepts_november_december_with_injected_readonly_builder(self):
        calls = []

        def fake_builder(**kwargs):
            calls.append(kwargs)
            return {"candidate_count": 142, "writes_db": False, "runs_etl": False}

        result = maybe_build_preflight_only_result(
            CarryForwardConfig(
                mode=CarryForwardMode.PREFLIGHT_ONLY,
                source_package_month="November 2025",
                target_canonical_month="December 2025",
            ),
            "November 2025",
            "December 2025",
            preflight_builder=fake_builder,
        )

        self.assertEqual(result["status"], "preflight_only")
        self.assertTrue(result["helper_called"])
        self.assertEqual(result["preflight"]["candidate_count"], 142)
        self.assertEqual(calls[0]["source_package_month"], "November 2025")

    def test_preflight_only_rejects_unsupported_boundary(self):
        with self.assertRaisesRegex(ValueError, "Unsupported CSI carry-forward boundary"):
            build_carry_forward_runtime_preflight(
                CarryForwardMode.PREFLIGHT_ONLY,
                source_package_month="October 2025",
                target_canonical_month="November 2025",
            )

    def test_temp_reconcile_returns_guarded_plan_and_does_not_execute(self):
        temp_db = Path(tempfile.gettempdir()) / "b11_3_guarded_temp.db"
        if temp_db.exists():
            temp_db.unlink()

        result = build_carry_forward_runtime_preflight(
            CarryForwardMode.TEMP_RECONCILE,
            source_package_month="November 2025",
            target_canonical_month="December 2025",
            db_path=temp_db,
        )

        self.assertEqual(result["status"], "guarded_not_executed")
        self.assertFalse(result["runs_reconciliation"])
        self.assertFalse(result["writes_db"])
        self.assertFalse(result["helper_called"])
        self.assertFalse(temp_db.exists())

    def test_temp_reconcile_rejects_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_b11_3.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            build_carry_forward_runtime_preflight(
                CarryForwardMode.TEMP_RECONCILE,
                source_package_month="July 2025",
                target_canonical_month="August 2025",
                db_path=repo_db,
            )

        self.assertFalse(repo_db.exists())

    def test_temp_reconcile_rejects_original_runtime_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            build_carry_forward_runtime_preflight(
                CarryForwardMode.TEMP_RECONCILE,
                source_package_month="July 2025",
                target_canonical_month="August 2025",
                db_path=original_runtime_db,
            )

    def test_adapter_requires_no_streamlit_import(self):
        sys.modules.pop("core.csi_carry_forward_runtime_adapter", None)
        sys.modules.pop("streamlit", None)

        __import__("core.csi_carry_forward_runtime_adapter")

        self.assertNotIn("streamlit", sys.modules)

    def test_adapter_does_not_create_db_files(self):
        temp_db = Path(tempfile.gettempdir()) / "b11_3_not_created.sqlite"
        if temp_db.exists():
            temp_db.unlink()

        build_carry_forward_runtime_preflight(
            CarryForwardMode.TEMP_RECONCILE,
            source_package_month="November 2025",
            target_canonical_month="December 2025",
            db_path=temp_db,
        )

        self.assertFalse(temp_db.exists())

    def test_active_etl_default_behavior_remains_unchanged_by_importing_adapter(self):
        __import__("core.csi_carry_forward_runtime_adapter")

        defaults = ETLPipelineModule.resolve_historical_month_sources.__kwdefaults__

        self.assertEqual(defaults["discovery_mode"], "auto")

    def test_policy_summary_reports_no_active_runtime_wiring(self):
        summary = summarize_carry_forward_runtime_policy(
            {
                "carry_forward_mode": "disabled",
            }
        )

        self.assertFalse(summary["active_runtime_wiring"])
        self.assertFalse(summary["runs_etl"])
        self.assertFalse(summary["writes_db"])


if __name__ == "__main__":
    unittest.main()
