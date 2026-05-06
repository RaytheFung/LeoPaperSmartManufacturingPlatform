import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from core.csi_carry_forward_audit_schema import create_carry_forward_audit_schema
from scripts.rehearse_csi_carry_forward_audit_workflow import (
    ORIGINAL_RUNTIME_REPO_ROOT,
    REPO_ROOT,
    run_csi_carry_forward_audit_workflow_rehearsal,
    validate_restored_audit_db,
    validate_temp_only_db_path,
    verify_backup_checksum,
)


class CsiCarryForwardAuditWorkflowRehearsalTests(unittest.TestCase):
    def test_rehearsal_refuses_repo_local_db_path(self):
        repo_db = REPO_ROOT / "blocked_b12_3_audit_rehearsal.db"

        with self.assertRaisesRegex(ValueError, "temp root|GitHub-safe repo"):
            validate_temp_only_db_path(repo_db)

        self.assertFalse(repo_db.exists())

    def test_rehearsal_refuses_original_runtime_db_path(self):
        original_runtime_db = ORIGINAL_RUNTIME_REPO_ROOT / "manufacturing_data.db"

        with self.assertRaisesRegex(ValueError, "temp root|original runtime repo"):
            validate_temp_only_db_path(original_runtime_db)

    def test_rehearsal_creates_schema_and_sample_records_in_tempfile_db(self):
        with tempfile.TemporaryDirectory(prefix="b12_3_audit_rehearsal_", dir="/tmp") as tmpdir:
            root = Path(tmpdir)
            evidence = run_csi_carry_forward_audit_workflow_rehearsal(
                temp_db_path=root / "audit.db",
                backup_db_path=root / "audit.backup.db",
                restore_db_path=root / "audit.restored.db",
            )

            self.assertEqual(evidence["status"], "success")
            self.assertTrue(evidence["audit_schema_applied"]["valid"])
            self.assertTrue(evidence["workflow_count_validation"]["valid"])
            self.assertEqual(evidence["sample_audit_records"]["candidate_records_inserted"], 3)
            self.assertEqual(evidence["sample_audit_records"]["include_decisions"], 2)
            self.assertEqual(evidence["sample_audit_records"]["skip_decisions"], 1)
            self.assertFalse(evidence["temp_db_boundary"]["writes_live_db"])

    def test_backup_checksum_validation_works_on_tempfile_db(self):
        with tempfile.TemporaryDirectory(prefix="b12_3_backup_check_", dir="/tmp") as tmpdir:
            root = Path(tmpdir)
            source = root / "source.db"
            backup = root / "source.backup.db"
            with sqlite3.connect(source) as conn:
                create_carry_forward_audit_schema(conn)
            shutil.copy2(source, backup)

            result = verify_backup_checksum(source, backup)

            self.assertTrue(result["matches"])
            self.assertEqual(result["source_checksum"], result["backup_checksum"])

    def test_rollback_restore_validation_works_on_tempfile_db(self):
        with tempfile.TemporaryDirectory(prefix="b12_3_restore_check_", dir="/tmp") as tmpdir:
            root = Path(tmpdir)
            evidence = run_csi_carry_forward_audit_workflow_rehearsal(
                temp_db_path=root / "audit.db",
                backup_db_path=root / "audit.backup.db",
                restore_db_path=root / "audit.restored.db",
            )

            restored = validate_restored_audit_db(
                root / "audit.restored.db",
                evidence["sample_audit_records"]["audit_run_id"],
            )

            self.assertTrue(restored["schema_valid"])
            self.assertTrue(restored["workflow_counts_valid"])

    def test_no_db_file_is_created_inside_repo(self):
        before = _repo_db_files(REPO_ROOT)
        with tempfile.TemporaryDirectory(prefix="b12_3_no_repo_db_", dir="/tmp") as tmpdir:
            root = Path(tmpdir)
            run_csi_carry_forward_audit_workflow_rehearsal(
                temp_db_path=root / "audit.db",
                backup_db_path=root / "audit.backup.db",
                restore_db_path=root / "audit.restored.db",
            )
        after = _repo_db_files(REPO_ROOT)

        self.assertEqual(before, after)

    def test_no_destructive_table_removal_phrase_appears(self):
        script_path = REPO_ROOT / "scripts" / "rehearse_csi_carry_forward_audit_workflow.py"
        text = script_path.read_text(encoding="utf-8").lower()

        self.assertNotIn("drop" + " table", text)

    def test_module_imports_without_pandas_or_streamlit(self):
        sys.modules.pop("scripts.rehearse_csi_carry_forward_audit_workflow", None)
        sys.modules.pop("pandas", None)
        sys.modules.pop("streamlit", None)

        __import__("scripts.rehearse_csi_carry_forward_audit_workflow")

        self.assertNotIn("pandas", sys.modules)
        self.assertNotIn("streamlit", sys.modules)


def _repo_db_files(repo_root: Path) -> set[Path]:
    return {
        path.relative_to(repo_root)
        for suffix in ("*.db", "*.sqlite", "*.sqlite3")
        for path in repo_root.glob(f"**/{suffix}")
        if ".git" not in path.parts
    }


if __name__ == "__main__":
    unittest.main()
