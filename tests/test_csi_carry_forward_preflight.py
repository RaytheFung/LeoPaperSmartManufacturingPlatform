import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.csi_carry_forward_preflight import build_csi_carry_forward_preflight


class CsiCarryForwardPreflightTests(unittest.TestCase):
    def test_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_csi_carry_forward.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            build_csi_carry_forward_preflight(db_path=repo_db)

        self.assertFalse(repo_db.exists())

    def test_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            build_csi_carry_forward_preflight(db_path=original_runtime_db)

    def test_missing_db_path_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "db_path is required"):
            build_csi_carry_forward_preflight()

    def test_tiny_fixture_identifies_previous_package_rows_for_target_month(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_candidate_fixture(candidate_db)

            plan = build_csi_carry_forward_preflight(db_path=candidate_db)

        self.assertEqual(plan["target_month"], "August 2025")
        self.assertEqual(plan["previous_package_month"], "July 2025")
        self.assertEqual(plan["canonical_month_key"], "2025-08")
        self.assertTrue(plan["carry_forward_required"])
        self.assertEqual(plan["candidate_count"], 2)
        self.assertEqual(
            plan["candidate_identity_fields"],
            ["machine_id", "start_time", "end_time", "prep_end_time", "order_id", "material", "good_qty"],
        )

    def test_helper_produces_candidate_identity_and_hash_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_candidate_fixture(candidate_db)

            plan = build_csi_carry_forward_preflight(db_path=candidate_db)

        identity_summary = plan["candidate_identity_summary"]
        hash_evidence = plan["source_row_hash_evidence"]
        self.assertEqual(identity_summary["distinct_machine_count"], 2)
        self.assertEqual(identity_summary["distinct_order_count"], 2)
        self.assertEqual(identity_summary["good_qty_sum"], 30.0)
        self.assertEqual(hash_evidence["previous_package_raw_identity_matched_candidate_count"], 2)
        self.assertEqual(hash_evidence["previous_package_silver_matched_candidate_count"], 1)
        self.assertEqual(hash_evidence["distinct_source_row_hash_count"], 2)
        self.assertTrue(plan["source_row_hash_available"])

    def test_helper_does_not_create_repo_db_files(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_db = Path(temp_dir) / "candidate.db"
            self._create_candidate_fixture(candidate_db)
            build_csi_carry_forward_preflight(db_path=candidate_db)

        self.assertEqual(repo_db.exists(), before_repo_db_exists)

    def test_august_current_package_overlap_can_report_zero_overlap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_db = Path(temp_dir) / "candidate.db"
            current_db = Path(temp_dir) / "current.db"
            self._create_candidate_fixture(candidate_db)
            self._create_current_package_fixture(current_db)

            plan = build_csi_carry_forward_preflight(
                db_path=candidate_db,
                current_package_db_path=current_db,
            )

        overlap = plan["current_package_overlap_summary"]
        self.assertEqual(overlap["status"], "zero_overlap")
        self.assertEqual(overlap["raw_overlap_candidate_count"], 0)
        self.assertEqual(overlap["silver_overlap_candidate_count"], 0)
        self.assertEqual(plan["duplicate_risk_summary"]["risk_level"], "controlled_zero_overlap_in_current_package")

    def _create_candidate_fixture(self, db_path: Path) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self._create_base_tables(conn)
            conn.execute(
                """
                INSERT INTO etl_csi_data
                (month_year, machine_id, start_time, end_time, setup_end, material, order_id, good_qty)
                VALUES
                ('July 2025', 'D-001', '2025-08-01 00:05:00', '2025-08-01 02:00:00', '2025-08-01 00:04:00', 'M1', 'J1', 10),
                ('July 2025', 'D-002', '2025-08-01 01:05:00', '2025-08-01 03:00:00', '2025-08-01 01:04:00', 'M2', 'J2', 20),
                ('July 2025', 'D-003', '2025-07-31 23:05:00', '2025-08-01 01:00:00', NULL, 'M3', 'J3', 30)
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

    def _create_current_package_fixture(self, db_path: Path) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self._create_base_tables(conn)
            conn.execute(
                """
                INSERT INTO raw_csi_event VALUES
                ('h3', 'august-source.xls', 'D-009', '2025-08-01 08:00:00', '2025-08-01 09:00:00', '2025-08-01 07:55:00', 'J9', 'M9', 90, '{}')
                """
            )
            conn.execute(
                """
                INSERT INTO csi_job_event VALUES
                ('h3', 'D-009', '2025-08-01 08:00:00', '2025-08-01 09:00:00', '2025-08-01 07:55:00', NULL, 'J9', 'M9', 90)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _create_base_tables(self, conn: sqlite3.Connection) -> None:
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


if __name__ == "__main__":
    unittest.main()
