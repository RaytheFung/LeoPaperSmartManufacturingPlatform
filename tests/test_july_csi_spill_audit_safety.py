import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.audit_july_csi_spill_rows import build_audit, classify_csi_row_scope


class JulyCsiSpillAuditSafetyTests(unittest.TestCase):
    def test_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_csi_spill_audit.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            build_audit(repo_db)

        self.assertFalse(repo_db.exists())

    def test_refuses_missing_db_path_clearly(self):
        missing_db = Path(tempfile.gettempdir()) / "missing_csi_spill_audit.db"
        if missing_db.exists():
            missing_db.unlink()

        with self.assertRaisesRegex(FileNotFoundError, "DB path does not exist"):
            build_audit(missing_db)

    def test_classification_helper_identifies_canonical_and_spill_rows(self):
        canonical = classify_csi_row_scope(
            start_time="2025-07-31 23:50:00",
            end_time="2025-08-01 00:10:00",
            setup_end=None,
            shift_date=None,
        )
        spill = classify_csi_row_scope(
            start_time="2025-08-01 00:02:01",
            end_time="2025-08-01 08:00:00",
            setup_end="2025-08-01 00:00:00",
            shift_date="2025-07-31",
        )

        self.assertEqual(canonical["classification"], "canonical_target_month")
        self.assertTrue(canonical["canonical_in_target"])
        self.assertEqual(spill["classification"], "spill_outside_canonical_scope")
        self.assertFalse(spill["canonical_in_target"])
        self.assertTrue(spill["extraction_intersects_target"])

    def test_build_audit_on_tiny_temp_db_without_repo_db_creation(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "tiny_csi_spill.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute(
                    """
                    CREATE TABLE etl_csi_data (
                        month_year TEXT,
                        machine_id TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        setup_end TEXT,
                        material TEXT,
                        order_id TEXT,
                        good_qty REAL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE raw_csi_event (
                        source_row_hash TEXT,
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
                        shift_date TEXT,
                        good_qty REAL
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO etl_csi_data VALUES
                    ('July 2025', 'D-001', '2025-07-31 23:00:00', '2025-08-01 01:00:00', NULL, 'M1', 'J1', 10),
                    ('July 2025', 'D-002', '2025-08-01 00:05:00', '2025-08-01 02:00:00', '2025-08-01 00:04:00', 'M2', 'J2', 20)
                    """
                )
                conn.execute(
                    """
                    INSERT INTO raw_csi_event VALUES
                    ('h1', 'D-001', '2025-07-31 23:00:00', '2025-08-01 01:00:00', NULL, 'J1', 'M1', 10, '{}')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO csi_job_event VALUES
                    ('h1', '2025-07-31 23:00:00', '2025-08-01 01:00:00', NULL, NULL, 10)
                    """
                )
                conn.commit()
            finally:
                conn.close()

            audit = build_audit(temp_db)

        reconciliation = audit["row_count_reconciliation"]
        self.assertEqual(reconciliation["etl_csi_data_month_year_july"]["row_count"], 2)
        self.assertEqual(reconciliation["raw_csi_event_canonical_july"]["row_count"], 1)
        self.assertEqual(reconciliation["csi_job_event_canonical_july"]["row_count"], 1)
        self.assertEqual(
            reconciliation["etl_csi_data_spill_rows_outside_canonical_july"]["row_count"],
            1,
        )
        self.assertEqual(repo_db.exists(), before_repo_db_exists)


if __name__ == "__main__":
    unittest.main()
