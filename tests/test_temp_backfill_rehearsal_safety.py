import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.run_july_2025_temp_backfill_rehearsal import (
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


if __name__ == "__main__":
    unittest.main()
