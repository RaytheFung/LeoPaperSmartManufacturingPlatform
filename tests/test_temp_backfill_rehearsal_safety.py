import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.run_july_2025_temp_backfill_rehearsal import (
    isolate_july_baseline_partitions,
    main,
    run_july_temp_backfill_rehearsal,
    summarize_temp_db,
)


class TempBackfillRehearsalSafetyTests(unittest.TestCase):
    def test_rehearsal_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_rehearsal.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            run_july_temp_backfill_rehearsal(
                temp_db_path=repo_db,
                data_root=Path("/tmp"),
            )

        self.assertFalse(repo_db.exists())

    def test_rehearsal_refuses_non_july_month(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "safe_temp.db"
            temp_db.write_bytes(b"placeholder")

            with self.assertRaisesRegex(ValueError, "non-July"):
                run_july_temp_backfill_rehearsal(
                    temp_db_path=temp_db,
                    data_root=Path(temp_dir),
                    month="August 2025",
                )

    def test_summarize_temp_db_reads_temp_path_without_repo_db_creation(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "summary_temp.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute("CREATE TABLE etl_runs (month_processed TEXT)")
                conn.execute("INSERT INTO etl_runs VALUES ('July 2025')")
                conn.commit()
            finally:
                conn.close()

            summary = summarize_temp_db(temp_db)

        self.assertTrue(summary["etl_runs"]["present"])
        self.assertEqual(summary["etl_runs"]["july_row_count"], 1)
        self.assertEqual(repo_db.exists(), before_repo_db_exists)

    def test_summarize_temp_db_refuses_repo_local_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_summary.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            summarize_temp_db(repo_db)

        self.assertFalse(repo_db.exists())

    def test_isolation_prune_deletes_only_july_scoped_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "isolation_temp.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute("CREATE TABLE etl_energy_data (month_year TEXT, value INTEGER)")
                conn.execute("INSERT INTO etl_energy_data VALUES ('July 2025', 1)")
                conn.execute("INSERT INTO etl_energy_data VALUES ('August 2025', 2)")
                conn.execute("CREATE TABLE raw_energy_hourly (raw_timestamp TEXT, source_row_hash TEXT)")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-07-01T00:00:00', 'july')")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-08-01T00:00:00', 'aug')")
                conn.execute("CREATE TABLE three_way_matches (machine_id TEXT, last_confirmed_date TEXT)")
                conn.execute("INSERT INTO three_way_matches VALUES ('024-001', 'July 2025')")
                conn.commit()
            finally:
                conn.close()

            evidence = isolate_july_baseline_partitions(temp_db)

            conn = sqlite3.connect(temp_db)
            try:
                energy_rows = conn.execute("SELECT month_year, value FROM etl_energy_data").fetchall()
                raw_rows = conn.execute("SELECT raw_timestamp, source_row_hash FROM raw_energy_hourly").fetchall()
                global_rows = conn.execute("SELECT machine_id, last_confirmed_date FROM three_way_matches").fetchall()
            finally:
                conn.close()

        self.assertEqual(energy_rows, [("August 2025", 2)])
        self.assertEqual(raw_rows, [("2025-08-01T00:00:00", "aug")])
        self.assertEqual(global_rows, [("024-001", "July 2025")])
        self.assertEqual(evidence["tables_pruned"]["etl_energy_data"]["deleted_rows"], 1)
        self.assertEqual(evidence["tables_pruned"]["etl_energy_data"]["pre_total_row_count"], 2)
        self.assertEqual(evidence["tables_pruned"]["etl_energy_data"]["post_total_row_count"], 1)
        self.assertIn("three_way_matches", evidence["tables_skipped"])
        self.assertEqual(evidence["tables_skipped"]["three_way_matches"]["pre_total_row_count"], 1)
        self.assertEqual(evidence["tables_skipped"]["three_way_matches"]["post_total_row_count"], 1)

    def test_isolation_prune_refuses_repo_local_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_isolation.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            isolate_july_baseline_partitions(repo_db)

        self.assertFalse(repo_db.exists())

    def test_rehearsal_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            run_july_temp_backfill_rehearsal(
                temp_db_path=original_runtime_db,
                data_root=Path("/tmp"),
            )

    def test_isolation_cli_requires_explicit_temp_db_path(self):
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["--isolate-july-baseline", "--data-root", "/tmp"])

        self.assertEqual(exit_code, 1)
        self.assertIn("requires explicit --temp-db-path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
