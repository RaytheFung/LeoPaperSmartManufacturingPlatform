import sys
import tempfile
import unittest
from pathlib import Path

from core.csi_carry_forward_config import (
    CarryForwardConfig,
    CarryForwardMode,
    assert_explicit_target_month,
    assert_no_live_db_mode,
    assert_supported_boundary,
    build_default_carry_forward_config,
    is_carry_forward_enabled,
    require_disabled_by_default,
    validate_carry_forward_mode,
    validate_temp_db_path,
)


class CsiCarryForwardConfigTests(unittest.TestCase):
    def test_default_config_mode_is_disabled(self):
        config = build_default_carry_forward_config()

        self.assertEqual(config.mode, CarryForwardMode.DISABLED)
        require_disabled_by_default(config)

    def test_disabled_mode_is_not_enabled(self):
        self.assertFalse(is_carry_forward_enabled(build_default_carry_forward_config()))
        self.assertFalse(is_carry_forward_enabled({"carry_forward_mode": "disabled"}))

    def test_preflight_and_temp_reconcile_validate_without_live_db_permission(self):
        preflight = CarryForwardConfig(
            mode=CarryForwardMode.PREFLIGHT_ONLY,
            source_package_month="July 2025",
            target_canonical_month="August 2025",
        )
        temp_path = Path(tempfile.gettempdir()) / "b11_2_config_guardrail.sqlite"
        temp_reconcile = CarryForwardConfig(
            mode=CarryForwardMode.TEMP_RECONCILE,
            source_package_month="November 2025",
            target_canonical_month="December 2025",
            target_db_path=temp_path,
        )

        self.assertTrue(is_carry_forward_enabled(preflight))
        self.assertTrue(is_carry_forward_enabled(temp_reconcile))
        self.assertFalse(preflight.allow_live_db)
        self.assertFalse(temp_reconcile.allow_live_db)
        self.assertFalse(temp_path.exists())

    def test_unknown_mode_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported carry-forward mode"):
            validate_carry_forward_mode("auto_live")

    def test_live_db_mode_is_rejected_if_attempted(self):
        with self.assertRaisesRegex(ValueError, "live DB mode"):
            assert_no_live_db_mode("live_db")
        with self.assertRaisesRegex(ValueError, "live DB mode"):
            CarryForwardConfig(allow_live_db=True)

    def test_missing_target_month_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "target month"):
            assert_explicit_target_month("")
        with self.assertRaisesRegex(ValueError, "target month"):
            CarryForwardConfig(
                mode=CarryForwardMode.PREFLIGHT_ONLY,
                source_package_month="July 2025",
            )

    def test_supported_proven_boundaries_pass(self):
        self.assertEqual(assert_supported_boundary("July 2025", "August 2025"), ("July 2025", "August 2025"))
        self.assertEqual(
            assert_supported_boundary("November 2025", "December 2025"),
            ("November 2025", "December 2025"),
        )

    def test_unsupported_boundary_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported CSI carry-forward boundary"):
            assert_supported_boundary("October 2025", "November 2025")

    def test_repo_local_db_path_rejected(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_b11_2.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            validate_temp_db_path(repo_db)

        self.assertFalse(repo_db.exists())

    def test_original_runtime_db_path_rejected(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            validate_temp_db_path(original_runtime_db)

    def test_temp_db_path_under_tmp_accepted(self):
        temp_db = Path(tempfile.gettempdir()) / "b11_2_allowed_temp.db"

        self.assertEqual(validate_temp_db_path(temp_db), temp_db.resolve(strict=False))
        self.assertFalse(temp_db.exists())

    def test_helper_does_not_create_db_files(self):
        temp_db = Path(tempfile.gettempdir()) / "b11_2_non_created.sqlite3"
        if temp_db.exists():
            temp_db.unlink()

        validate_temp_db_path(temp_db)

        self.assertFalse(temp_db.exists())

    def test_no_streamlit_import_is_required(self):
        sys.modules.pop("core.csi_carry_forward_config", None)
        sys.modules.pop("streamlit", None)

        __import__("core.csi_carry_forward_config")

        self.assertNotIn("streamlit", sys.modules)


if __name__ == "__main__":
    unittest.main()
