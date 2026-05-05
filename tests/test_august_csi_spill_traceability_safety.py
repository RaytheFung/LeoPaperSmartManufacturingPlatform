import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.audit_august_csi_spill_traceability import build_csi_identity_key, build_traceability_audit


class AugustCsiSpillTraceabilitySafetyTests(unittest.TestCase):
    def test_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_august_traceability.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            build_traceability_audit(repo_db)

        self.assertFalse(repo_db.exists())

    def test_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            build_traceability_audit(original_runtime_db)

    def test_refuses_missing_db_path_clearly(self):
        missing_db = Path(tempfile.gettempdir()) / "missing_august_traceability.db"
        if missing_db.exists():
            missing_db.unlink()

        with self.assertRaisesRegex(FileNotFoundError, "DB path does not exist"):
            build_traceability_audit(missing_db)

    def test_identity_key_normalizes_numeric_good_qty(self):
        self.assertEqual(
            build_csi_identity_key(
                machine_id=" D-001 ",
                start_time="2025-08-01 00:00:00",
                end_time="2025-08-01 01:00:00",
                prep_end_time=None,
                order_id="J1",
                material="M1",
                good_qty=10.0,
            ),
            ("D-001", "2025-08-01 00:00:00", "2025-08-01 01:00:00", "", "J1", "M1", "10"),
        )

    def test_traceability_helper_on_tiny_temp_db_without_repo_db_creation(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "tiny_august_traceability.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute(
                    """
                    CREATE TABLE etl_csi_data (
                        id INTEGER PRIMARY KEY,
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
                conn.execute(
                    """
                    CREATE TABLE csi_job_event (
                        source_row_hash TEXT,
                        raw_machine_id_or_label TEXT,
                        prod_start_ts TEXT,
                        prod_end_ts TEXT,
                        prep_end_ts TEXT,
                        shift_date TEXT,
                        order_id TEXT,
                        material_code TEXT,
                        good_qty REAL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE fact_machine_hour (
                        hour_ts TEXT,
                        good_qty REAL
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO etl_csi_data
                    (month_year, machine_id, start_time, end_time, setup_end, material, order_id, good_qty)
                    VALUES
                    ('July 2025', 'D-001', '2025-08-01 00:05:00', '2025-08-01 02:00:00', '2025-08-01 00:04:00', 'M1', 'J1', 10),
                    ('July 2025', 'D-002', '2025-08-01 01:05:00', '2025-08-01 03:00:00', '2025-08-01 01:04:00', 'M2', 'J2', 20)
                    """
                )
                conn.execute(
                    """
                    INSERT INTO raw_csi_event VALUES
                    ('h1', 'july-source.xls', 'D-001', '2025-08-01 00:05:00', '2025-08-01 02:00:00', '2025-08-01 00:04:00', 'J1', 'M1', 10, '{}'),
                    ('h2', 'july-source.xls', 'D-002', '2025-08-01 01:05:00', '2025-08-01 03:00:00', '2025-08-01 01:04:00', 'J2', 'M2', 20, '{}')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO csi_job_event VALUES
                    ('h1', 'D-001', '2025-08-01 00:05:00', '2025-08-01 02:00:00', '2025-08-01 00:04:00', NULL, 'J1', 'M1', 10)
                    """
                )
                conn.commit()
            finally:
                conn.close()

            audit = build_traceability_audit(temp_db)

        self.assertEqual(audit["spill_identity_summary"]["spill_row_count"], 2)
        self.assertEqual(audit["traceability_result"]["raw_august_matched_spill_row_count"], 2)
        self.assertEqual(audit["traceability_result"]["raw_august_unmatched_spill_row_count"], 0)
        self.assertEqual(audit["traceability_result"]["silver_august_matched_spill_row_count"], 1)
        self.assertEqual(audit["traceability_result"]["silver_august_unmatched_spill_row_count"], 1)
        self.assertEqual(repo_db.exists(), before_repo_db_exists)


if __name__ == "__main__":
    unittest.main()
