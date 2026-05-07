from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_factory_deployment_readiness.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("factory_readiness_check", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_required_fixture(root: Path) -> None:
    module = _load_script_module()
    for relative_path in module.REQUIRED_FILES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")
    (root / "etl_outputs").mkdir(parents=True, exist_ok=True)
    (root / "etl_outputs" / ".gitkeep").write_text("", encoding="utf-8")
    (root / "etl_outputs" / "ETL_OUTPUTS_GUIDE.md").write_text("fixture\n", encoding="utf-8")


def _tracked_files_provider(_repo_root: Path, pathspec: str | None) -> list[str]:
    tracked = {
        "etl_outputs": [
            "etl_outputs/.gitkeep",
            "etl_outputs/ETL_OUTPUTS_GUIDE.md",
        ],
        "manufacturing_data.db": [],
    }
    return list(tracked.get(pathspec or "", []))


class FactoryDeploymentReadinessCheckTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_script_module()

    def test_reports_required_docs_present_in_temporary_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_required_fixture(root)

            report = self.module.build_readiness_report(
                root,
                tracked_files_provider=_tracked_files_provider,
                include_policy_imports=False,
            )

            self.assertTrue(report["success"])
            required_check = _find_check(report, "required_files_present")
            self.assertTrue(required_check["passed"])
            self.assertEqual(required_check["details"]["missing"], [])

    def test_detects_missing_required_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_required_fixture(root)
            (root / "docs" / "operations" / "FACTORY_DEPLOYMENT_RUNBOOK.md").unlink()

            report = self.module.build_readiness_report(
                root,
                tracked_files_provider=_tracked_files_provider,
                include_policy_imports=False,
            )

            self.assertFalse(report["success"])
            required_check = _find_check(report, "required_files_present")
            self.assertFalse(required_check["passed"])
            self.assertIn(
                "docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md",
                required_check["details"]["missing"],
            )

    def test_detects_repo_local_db_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_required_fixture(root)
            (root / "manufacturing_data.db").write_text("not a real db\n", encoding="utf-8")

            report = self.module.build_readiness_report(
                root,
                tracked_files_provider=_tracked_files_provider,
                include_policy_imports=False,
            )

            self.assertFalse(report["success"])
            db_check = _find_check(report, "no_repo_local_db_files")
            self.assertFalse(db_check["passed"])
            self.assertIn("manufacturing_data.db", db_check["details"]["paths"])

    def test_detects_local_env_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_required_fixture(root)
            (root / ".conda311").mkdir()

            report = self.module.build_readiness_report(
                root,
                tracked_files_provider=_tracked_files_provider,
                include_policy_imports=False,
            )

            self.assertFalse(report["success"])
            env_check = _find_check(report, "no_local_env_or_upload_dirs")
            self.assertFalse(env_check["passed"])
            self.assertIn(".conda311", env_check["details"]["paths"])

    def test_default_carry_forward_mode_is_disabled_without_streamlit(self):
        report = self.module.build_readiness_report(REPO_ROOT)

        carry_forward_check = _find_check(report, "carry_forward_default_disabled")
        self.assertTrue(carry_forward_check["passed"])
        self.assertEqual(carry_forward_check["details"]["default_constant"], "disabled")
        self.assertEqual(carry_forward_check["details"]["default_config_mode"], "disabled")

    def test_runtime_modes_include_expected_values(self):
        report = self.module.build_readiness_report(REPO_ROOT)

        runtime_check = _find_check(report, "supported_runtime_modes_present")
        self.assertTrue(runtime_check["passed"])
        self.assertEqual(runtime_check["details"]["missing"], [])
        self.assertIn("standard", runtime_check["details"]["modes"])
        self.assertIn("demo_readonly", runtime_check["details"]["modes"])
        self.assertIn("pilot_review", runtime_check["details"]["modes"])

    def test_helper_does_not_create_db_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_required_fixture(root)

            self.module.build_readiness_report(
                root,
                tracked_files_provider=_tracked_files_provider,
                include_policy_imports=False,
            )

            db_files = list(root.rglob("*.db"))
            self.assertEqual(db_files, [])


def _find_check(report: dict[str, object], name: str) -> dict[str, object]:
    for check in report["checks"]:
        if check["name"] == name:
            return check
    raise AssertionError(f"missing check: {name}")


if __name__ == "__main__":
    unittest.main()
