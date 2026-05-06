import sqlite3
import sys
import unittest
from pathlib import Path

from core.csi_carry_forward_audit_schema import create_carry_forward_audit_schema
from core.csi_carry_forward_audit_workflow import (
    build_backup_rollback_requirements,
    build_live_migration_abort_gates,
    build_migration_preflight_checklist,
    build_sample_audit_run_payload,
    build_sample_candidate_payload,
    build_sample_gold_delta_payload,
    get_audit_retention_policy,
    get_reviewer_status_values,
    insert_audit_run,
    insert_candidate,
    insert_gold_delta,
    validate_audit_workflow_counts,
    validate_reviewer_status,
)


class CsiCarryForwardAuditWorkflowTests(unittest.TestCase):
    def test_reviewer_statuses_validate(self):
        self.assertEqual(
            get_reviewer_status_values(),
            (
                "draft",
                "pending_review",
                "accepted",
                "rejected",
                "superseded",
                "rollback_required",
            ),
        )
        self.assertEqual(validate_reviewer_status(" Accepted "), "accepted")

    def test_unknown_reviewer_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported reviewer status"):
            validate_reviewer_status("auto_promote")

    def test_retention_policy_returns_required_non_deletion_rules(self):
        policy = get_audit_retention_policy()
        rules_text = " ".join(policy["rules"]).lower()

        self.assertFalse(policy["automatic_cleanup"])
        self.assertIn("permanently", rules_text)
        self.assertIn("do not delete candidate-level provenance", rules_text)
        self.assertIn("supersede rather than mutate", rules_text)
        self.assertIn("no automatic cleanup", rules_text)

    def test_sample_audit_candidate_and_gold_delta_inserts_succeed_in_memory(self):
        conn = sqlite3.connect(":memory:")
        try:
            create_carry_forward_audit_schema(conn)
            audit_payload = build_sample_audit_run_payload(reviewer_status="accepted")
            insert_audit_run(conn, audit_payload)
            insert_candidate(
                conn,
                build_sample_candidate_payload(
                    audit_run_id=audit_payload["audit_run_id"],
                    candidate_index=1,
                    decision="include",
                ),
            )
            insert_candidate(
                conn,
                build_sample_candidate_payload(
                    audit_run_id=audit_payload["audit_run_id"],
                    candidate_index=2,
                    decision="skip",
                ),
            )
            insert_gold_delta(conn, build_sample_gold_delta_payload(audit_run_id=audit_payload["audit_run_id"]))

            validation = validate_audit_workflow_counts(conn, audit_payload["audit_run_id"])

            self.assertTrue(validation["valid"])
            self.assertEqual(validation["actual"]["candidate_count"], 2)
            self.assertEqual(validation["actual"]["include_count"], 1)
            self.assertEqual(validation["actual"]["skip_count"], 1)
            self.assertEqual(validation["gold_delta_count"], 1)
            self.assertEqual(validation["reviewer_status"], "accepted")
        finally:
            conn.close()

    def test_workflow_count_validation_detects_mismatch(self):
        conn = sqlite3.connect(":memory:")
        try:
            create_carry_forward_audit_schema(conn)
            audit_payload = build_sample_audit_run_payload(candidate_count=2, include_count=2, skip_count=0)
            insert_audit_run(conn, audit_payload)
            insert_candidate(
                conn,
                build_sample_candidate_payload(
                    audit_run_id=audit_payload["audit_run_id"],
                    candidate_index=1,
                    decision="include",
                ),
            )

            validation = validate_audit_workflow_counts(conn, audit_payload["audit_run_id"])

            self.assertFalse(validation["valid"])
            self.assertIn("candidate_count", validation["mismatches"])
            self.assertIn("include_count", validation["mismatches"])
        finally:
            conn.close()

    def test_migration_checklist_contains_required_items(self):
        item_ids = _ids(build_migration_preflight_checklist())

        self.assertIn("db_backup_path_required", item_ids)
        self.assertIn("backup_checksum_required", item_ids)
        self.assertIn("dry_run_sql_diff_required", item_ids)
        self.assertIn("rollback_procedure_required", item_ids)
        self.assertIn("reviewer_approval_required", item_ids)

    def test_abort_gates_contain_required_blockers(self):
        item_ids = _ids(build_live_migration_abort_gates())

        self.assertIn("unsafe_db_path", item_ids)
        self.assertIn("duplicate_source_hash_groups", item_ids)
        self.assertIn("unresolved_candidate_decisions", item_ids)
        self.assertIn("reviewer_status_not_accepted", item_ids)

    def test_backup_rollback_requirements_are_structured(self):
        item_ids = _ids(build_backup_rollback_requirements())

        self.assertIn("backup_before_migration", item_ids)
        self.assertIn("backup_checksum", item_ids)
        self.assertIn("restore_procedure", item_ids)
        self.assertIn("post_restore_validation", item_ids)

    def test_no_db_file_is_created_in_repo(self):
        repo_root = Path(__file__).resolve().parents[1]
        before = _repo_db_files(repo_root)

        conn = sqlite3.connect(":memory:")
        try:
            create_carry_forward_audit_schema(conn)
            audit_payload = build_sample_audit_run_payload()
            insert_audit_run(conn, audit_payload)
            insert_candidate(conn, build_sample_candidate_payload(audit_run_id=audit_payload["audit_run_id"]))
            insert_gold_delta(conn, build_sample_gold_delta_payload(audit_run_id=audit_payload["audit_run_id"]))
        finally:
            conn.close()

        after = _repo_db_files(repo_root)
        self.assertEqual(before, after)

    def test_module_imports_without_pandas_or_streamlit(self):
        sys.modules.pop("core.csi_carry_forward_audit_workflow", None)
        sys.modules.pop("pandas", None)
        sys.modules.pop("streamlit", None)

        __import__("core.csi_carry_forward_audit_workflow")

        self.assertNotIn("pandas", sys.modules)
        self.assertNotIn("streamlit", sys.modules)

    def test_no_destructive_table_removal_phrase_appears_in_generated_outputs(self):
        rendered = " ".join(
            [
                str(build_migration_preflight_checklist()),
                str(build_live_migration_abort_gates()),
                str(build_backup_rollback_requirements()),
            ]
        ).lower()

        self.assertNotIn("drop" + " table", rendered)


def _ids(items):
    return {item["id"] for item in items}


def _repo_db_files(repo_root: Path) -> set[Path]:
    return {
        path.relative_to(repo_root)
        for suffix in ("*.db", "*.sqlite", "*.sqlite3")
        for path in repo_root.glob(f"**/{suffix}")
        if ".git" not in path.parts
    }


if __name__ == "__main__":
    unittest.main()
