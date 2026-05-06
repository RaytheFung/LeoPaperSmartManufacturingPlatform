import sqlite3
import sys
import unittest
from pathlib import Path

from core.csi_carry_forward_audit_schema import (
    EXPECTED_SCHEMA_COLUMNS,
    build_audit_run_id,
    build_candidate_id,
    create_carry_forward_audit_schema,
    get_carry_forward_audit_schema_statements,
    validate_carry_forward_audit_schema,
)


class CsiCarryForwardAuditSchemaTests(unittest.TestCase):
    def test_schema_statement_list_contains_expected_tables(self):
        ddl = "\n".join(get_carry_forward_audit_schema_statements())

        self.assertIn("CREATE TABLE IF NOT EXISTS csi_carry_forward_audit_runs", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS csi_carry_forward_candidates", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS csi_carry_forward_gold_deltas", ddl)

    def test_in_memory_schema_creation_succeeds(self):
        conn = sqlite3.connect(":memory:")
        try:
            result = create_carry_forward_audit_schema(conn)

            self.assertTrue(result["valid"])
            self.assertEqual(result["statement_count"], 3)
            self.assertEqual(
                _table_names(conn),
                {
                    "csi_carry_forward_audit_runs",
                    "csi_carry_forward_candidates",
                    "csi_carry_forward_gold_deltas",
                },
            )
        finally:
            conn.close()

    def test_dry_run_validates_without_mutating_supplied_connection(self):
        conn = sqlite3.connect(":memory:")
        try:
            result = create_carry_forward_audit_schema(conn, dry_run=True)

            self.assertTrue(result["valid"])
            self.assertEqual(_table_names(conn), set())
        finally:
            conn.close()

    def test_validate_function_confirms_required_tables_and_columns(self):
        conn = sqlite3.connect(":memory:")
        try:
            create_carry_forward_audit_schema(conn)

            validation = validate_carry_forward_audit_schema(conn)

            self.assertTrue(validation["valid"])
            for table_name, expected_columns in EXPECTED_SCHEMA_COLUMNS.items():
                self.assertTrue(validation["tables"][table_name]["exists"])
                self.assertEqual(validation["tables"][table_name]["missing_columns"], [])
                for column in expected_columns:
                    self.assertIn(column, validation["tables"][table_name]["actual_columns"])
        finally:
            conn.close()

    def test_candidate_id_is_stable_and_deterministic(self):
        stable_identity = (
            "PM1",
            "2025-11-30 23:00:00",
            "2025-12-01 01:00:00",
            "ORD-1",
            "MAT-1",
            "100.0",
        )

        first = build_candidate_id(stable_identity, source_row_hash="abc123")
        second = build_candidate_id(list(stable_identity), source_row_hash="abc123")
        changed = build_candidate_id(stable_identity, source_row_hash="different")

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertTrue(first.startswith("cfcand_"))

    def test_audit_run_id_is_stable_and_deterministic_with_suffix(self):
        first = build_audit_run_id("November 2025", "December 2025", suffix="dry run")
        second = build_audit_run_id(" November 2025 ", "December 2025", suffix="dry-run")

        self.assertEqual(first, second)
        self.assertEqual(first, "cfaudit_november_2025_to_december_2025_dry_run")

    def test_no_drop_table_appears_in_ddl(self):
        ddl = "\n".join(get_carry_forward_audit_schema_statements()).lower()

        self.assertNotIn("drop table", ddl)

    def test_no_db_file_is_created_in_repo(self):
        repo_root = Path(__file__).resolve().parents[1]
        before = _repo_db_files(repo_root)

        conn = sqlite3.connect(":memory:")
        try:
            create_carry_forward_audit_schema(conn)
        finally:
            conn.close()

        after = _repo_db_files(repo_root)
        self.assertEqual(before, after)

    def test_module_imports_without_pandas_or_streamlit(self):
        sys.modules.pop("core.csi_carry_forward_audit_schema", None)
        sys.modules.pop("pandas", None)
        sys.modules.pop("streamlit", None)

        __import__("core.csi_carry_forward_audit_schema")

        self.assertNotIn("pandas", sys.modules)
        self.assertNotIn("streamlit", sys.modules)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {str(row[0]) for row in rows}


def _repo_db_files(repo_root: Path) -> set[Path]:
    return {
        path.relative_to(repo_root)
        for suffix in ("*.db", "*.sqlite", "*.sqlite3")
        for path in repo_root.glob(f"**/{suffix}")
        if ".git" not in path.parts
    }


if __name__ == "__main__":
    unittest.main()
