import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.run_november_december_csi_carry_forward_reconciliation import (
    apply_approved_carry_forward_plan,
    run_november_december_csi_carry_forward_reconciliation,
    validate_approved_plan_counts,
)


class NovemberDecemberCarryForwardReconciliationSafetyTests(unittest.TestCase):
    def test_script_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_b10_5_reconciliation.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            apply_approved_carry_forward_plan(
                target_db_path=repo_db,
                approved_plan=self._approved_plan([]),
            )

        self.assertFalse(repo_db.exists())

    def test_script_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            apply_approved_carry_forward_plan(
                target_db_path=original_runtime_db,
                approved_plan=self._approved_plan([]),
            )

    def test_script_refuses_unsupported_boundary(self):
        with self.assertRaisesRegex(ValueError, "Only November 2025 -> December 2025"):
            run_november_december_csi_carry_forward_reconciliation(
                target_db_path=Path(tempfile.gettempdir()) / "unused_b10_5.db",
                source_package_month="October 2025",
                target_month="November 2025",
                dry_run=True,
            )

    def test_execution_blocks_if_include_skip_block_counts_differ(self):
        with self.assertRaisesRegex(ValueError, "include_count expected 135 got 1"):
            validate_approved_plan_counts(self._approved_plan([self._raw_row("h1", "D-001", "J1")]))

    def test_execution_skips_duplicate_identities(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            self._create_target_db(target_db, existing_skip=True)
            include_row = self._raw_row("include-hash", "D-002", "J2")
            evidence = apply_approved_carry_forward_plan(
                target_db_path=target_db,
                approved_plan=self._approved_plan([include_row], skip_count=1),
                expected_include_count=1,
                expected_skip_count=1,
            )

            self.assertEqual(evidence["raw_rows_inserted"], 1)
            self.assertEqual(evidence["skipped_existing_duplicate_count"], 1)
            self.assertEqual(self._raw_row_count(target_db), 2)

    def test_execution_blocks_unresolved_candidates(self):
        plan = self._approved_plan([self._raw_row("h1", "D-001", "J1")], block_count=1)

        with self.assertRaisesRegex(ValueError, "block_count expected 0 got 1"):
            validate_approved_plan_counts(
                plan,
                expected_include_count=1,
                expected_skip_count=0,
                expected_block_count=0,
            )

    def test_helper_does_not_create_db_inside_repo(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            self._create_target_db(target_db)
            include_row = self._raw_row("include-hash", "D-002", "J2")
            apply_approved_carry_forward_plan(
                target_db_path=target_db,
                approved_plan=self._approved_plan([include_row]),
                expected_include_count=1,
                expected_skip_count=0,
            )

        self.assertEqual(repo_db.exists(), before_repo_db_exists)

    def _approved_plan(
        self,
        include_rows: list[dict],
        *,
        skip_count: int = 0,
        block_count: int = 0,
    ) -> dict:
        return {
            "candidate_count": len(include_rows) + skip_count + block_count,
            "include_count": len(include_rows),
            "skip_count": skip_count,
            "block_count": block_count,
            "hash_proven_include_count": len(include_rows),
            "hash_resolved_include_count": 0,
            "stable_identity_fallback_include_count": 0,
            "duplicate_include_identity_group_count": 0,
            "include_raw_rows": include_rows,
            "include_source_hashes": [
                row["source_row_hash"] for row in include_rows if row.get("source_row_hash")
            ],
        }

    def _create_target_db(self, db_path: Path, *, existing_skip: bool = False) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                CREATE TABLE raw_csi_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_system TEXT,
                    source_file TEXT,
                    source_row_hash TEXT,
                    ingested_at TEXT,
                    raw_machine_id_or_label TEXT,
                    raw_start_time TEXT,
                    raw_end_time TEXT,
                    raw_prep_end_time TEXT,
                    raw_order_id TEXT,
                    raw_material TEXT,
                    raw_good_qty REAL,
                    raw_payload_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE csi_job_event (
                    source_row_hash TEXT,
                    prod_start_ts TEXT,
                    prod_end_ts TEXT,
                    prep_end_ts TEXT,
                    shift_date TEXT
                )
                """
            )
            if existing_skip:
                row = self._raw_row("skip-hash", "D-001", "J1")
                conn.execute(
                    """
                    INSERT INTO raw_csi_event
                    (source_system, source_file, source_row_hash, ingested_at, raw_machine_id_or_label,
                     raw_start_time, raw_end_time, raw_prep_end_time, raw_order_id, raw_material,
                     raw_good_qty, raw_payload_json)
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(
                        row[column]
                        for column in (
                            "source_system",
                            "source_file",
                            "source_row_hash",
                            "ingested_at",
                            "raw_machine_id_or_label",
                            "raw_start_time",
                            "raw_end_time",
                            "raw_prep_end_time",
                            "raw_order_id",
                            "raw_material",
                            "raw_good_qty",
                            "raw_payload_json",
                        )
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def _raw_row(self, source_hash: str, machine: str, order: str) -> dict:
        return {
            "source_system": "csi",
            "source_file": "source_data/november.xls",
            "source_row_hash": source_hash,
            "ingested_at": "2026-01-01T00:00:00+00:00",
            "raw_machine_id_or_label": machine,
            "raw_start_time": "2025-12-01 00:00:00",
            "raw_end_time": "2025-12-01 01:00:00",
            "raw_prep_end_time": "",
            "raw_order_id": order,
            "raw_material": "M1",
            "raw_good_qty": 10,
            "raw_payload_json": "{}",
        }

    def _raw_row_count(self, db_path: Path) -> int:
        conn = sqlite3.connect(db_path)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM raw_csi_event").fetchone()[0])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
