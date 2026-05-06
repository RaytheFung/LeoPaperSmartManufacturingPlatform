import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.run_august_2025_csi_carry_forward_reconciliation import (
    reconcile_csi_carry_forward_candidates,
    run_august_csi_carry_forward_reconciliation,
)


class CsiCarryForwardReconciliationSafetyTests(unittest.TestCase):
    def test_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_carry_forward_reconciliation.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            reconcile_csi_carry_forward_candidates(
                target_db_path=repo_db,
                candidate_source_db_path=Path(tempfile.gettempdir()) / "missing_candidates.db",
            )

        self.assertFalse(repo_db.exists())

    def test_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            reconcile_csi_carry_forward_candidates(
                target_db_path=original_runtime_db,
                candidate_source_db_path=Path(tempfile.gettempdir()) / "missing_candidates.db",
            )

    def test_refuses_non_august_target_month(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            candidate_db = Path(temp_dir) / "candidate.db"
            original_db = Path(temp_dir) / "original.db"
            baseline_db = Path(temp_dir) / "baseline.db"
            original_db.write_bytes(b"placeholder")
            self._create_candidate_source_fixture(candidate_db)
            self._create_target_fixture(baseline_db)

            with self.assertRaisesRegex(ValueError, "non-August"):
                run_august_csi_carry_forward_reconciliation(
                    target_db_path=target_db,
                    candidate_source_db_path=candidate_db,
                    baseline_db_path=baseline_db,
                    original_db_path=original_db,
                    month="September 2025",
                    dry_run=True,
                )

    def test_tiny_fixture_reconciles_candidate_without_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_target_fixture(target_db)
            self._create_candidate_source_fixture(candidate_db)

            evidence = reconcile_csi_carry_forward_candidates(
                target_db_path=target_db,
                candidate_source_db_path=candidate_db,
            )

            self.assertEqual(evidence["candidate_count"], 2)
            self.assertEqual(evidence["raw_rows_inserted"], 2)
            self.assertEqual(evidence["skipped_existing_identity_count"], 0)
            self.assertEqual(self._raw_row_count(target_db), 3)

    def test_reconciliation_does_not_copy_source_raw_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_target_fixture(target_db, include_id_column=True)
            self._create_candidate_source_fixture(candidate_db, include_id_column=True)

            evidence = reconcile_csi_carry_forward_candidates(
                target_db_path=target_db,
                candidate_source_db_path=candidate_db,
            )

            self.assertEqual(evidence["raw_rows_inserted"], 2)
            self.assertEqual(self._raw_row_count(target_db), 3)

    def test_duplicate_prevention_skips_existing_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_target_fixture(target_db, include_existing_candidate=True)
            self._create_candidate_source_fixture(candidate_db)

            evidence = reconcile_csi_carry_forward_candidates(
                target_db_path=target_db,
                candidate_source_db_path=candidate_db,
            )

            self.assertEqual(evidence["candidate_count"], 2)
            self.assertEqual(evidence["raw_rows_inserted"], 1)
            self.assertEqual(evidence["skipped_existing_identity_count"], 1)
            self.assertEqual(self._raw_row_count(target_db), 3)

    def test_helper_does_not_create_db_inside_repo(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_target_fixture(target_db)
            self._create_candidate_source_fixture(candidate_db)
            reconcile_csi_carry_forward_candidates(
                target_db_path=target_db,
                candidate_source_db_path=candidate_db,
            )

        self.assertEqual(repo_db.exists(), before_repo_db_exists)

    def test_dry_run_does_not_mutate_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_db = Path(temp_dir) / "target.db"
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_target_fixture(target_db)
            self._create_candidate_source_fixture(candidate_db)
            before_count = self._raw_row_count(target_db)

            evidence = reconcile_csi_carry_forward_candidates(
                target_db_path=target_db,
                candidate_source_db_path=candidate_db,
                dry_run=True,
            )

            self.assertTrue(evidence["dry_run"])
            self.assertEqual(evidence["raw_rows_inserted"], 0)
            self.assertEqual(evidence["raw_rows_planned"], 2)
            self.assertEqual(self._raw_row_count(target_db), before_count)

    def _create_candidate_source_fixture(self, db_path: Path, include_id_column: bool = False) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self._create_common_tables(conn, include_id_column=include_id_column)
            conn.execute(
                """
                INSERT INTO etl_csi_data
                (month_year, machine_id, start_time, end_time, setup_end, order_id, material, good_qty)
                VALUES
                ('July 2025', 'D-001', '2025-08-01 00:00:00', '2025-08-01 01:00:00', '2025-08-01 00:00:00', 'J1', 'M1', 10),
                ('July 2025', 'D-002', '2025-08-01 02:00:00', '2025-08-01 03:00:00', '2025-08-01 02:00:00', 'J2', 'M2', 20)
                """
            )
            conn.execute(
                """
                INSERT INTO raw_csi_event
                (source_row_hash, source_file, raw_machine_id_or_label, raw_start_time, raw_end_time,
                 raw_prep_end_time, raw_order_id, raw_material, raw_good_qty, raw_payload_json)
                VALUES
                ('h1', 'source_data/july.xls', 'D-001', '2025-08-01 00:00:00', '2025-08-01 01:00:00', '2025-08-01 00:00:00', 'J1', 'M1', 10, '{}'),
                ('h2', 'source_data/july.xls', 'D-002', '2025-08-01 02:00:00', '2025-08-01 03:00:00', '2025-08-01 02:00:00', 'J2', 'M2', 20, '{}')
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _create_target_fixture(
        self,
        db_path: Path,
        include_existing_candidate: bool = False,
        include_id_column: bool = False,
    ) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self._create_common_tables(conn, include_id_column=include_id_column)
            conn.execute(
                """
                INSERT INTO raw_csi_event
                (source_row_hash, source_file, raw_machine_id_or_label, raw_start_time, raw_end_time,
                 raw_prep_end_time, raw_order_id, raw_material, raw_good_qty, raw_payload_json)
                VALUES
                ('current-hash', 'source_data/august.xls', 'D-009', '2025-08-01 08:00:00', '2025-08-01 09:00:00', '2025-08-01 08:00:00', 'J9', 'M9', 90, '{}')
                """
            )
            if include_existing_candidate:
                conn.execute(
                    """
                    INSERT INTO raw_csi_event
                    (source_row_hash, source_file, raw_machine_id_or_label, raw_start_time, raw_end_time,
                     raw_prep_end_time, raw_order_id, raw_material, raw_good_qty, raw_payload_json)
                    VALUES
                    ('existing-different-hash', 'source_data/august.xls', 'D-001', '2025-08-01 00:00:00', '2025-08-01 01:00:00', '2025-08-01 00:00:00', 'J1', 'M1', 10, '{}')
                    """
                )
            conn.commit()
        finally:
            conn.close()

    def _create_common_tables(self, conn: sqlite3.Connection, include_id_column: bool = False) -> None:
        raw_id_column = "id INTEGER PRIMARY KEY AUTOINCREMENT," if include_id_column else ""
        source_hash_column = "source_row_hash TEXT," if include_id_column else "source_row_hash TEXT PRIMARY KEY,"
        conn.execute(
            """
            CREATE TABLE etl_csi_data (
                month_year TEXT,
                machine_id TEXT,
                start_time TEXT,
                end_time TEXT,
                setup_end TEXT,
                order_id TEXT,
                material TEXT,
                good_qty REAL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE raw_csi_event (
                {raw_id_column}
                {source_hash_column}
                source_file TEXT,
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

    def _raw_row_count(self, db_path: Path) -> int:
        conn = sqlite3.connect(db_path)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM raw_csi_event").fetchone()[0])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
