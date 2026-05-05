import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_august_2025_temp_backfill_rehearsal import (
    inspect_august_source_hash_duplicates,
    isolate_august_baseline_partitions,
    run_august_temp_backfill_rehearsal,
    summarize_august_temp_db,
)


class AugustTempBackfillRehearsalSafetyTests(unittest.TestCase):
    def test_rehearsal_refuses_repo_local_db_path(self):
        repo_db = Path(__file__).resolve().parents[1] / "blocked_august_rehearsal.db"

        with self.assertRaisesRegex(ValueError, "inside repo"):
            run_august_temp_backfill_rehearsal(temp_db_path=repo_db, data_root=Path("/tmp"))

        self.assertFalse(repo_db.exists())

    def test_rehearsal_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            run_august_temp_backfill_rehearsal(temp_db_path=original_runtime_db, data_root=Path("/tmp"))

    def test_rehearsal_refuses_non_august_month(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "safe_august_temp.db"
            temp_db.write_bytes(b"placeholder")

            with self.assertRaisesRegex(ValueError, "non-August"):
                run_august_temp_backfill_rehearsal(
                    temp_db_path=temp_db,
                    data_root=Path(temp_dir),
                    month="July 2025",
                )

    def test_august_isolation_prune_deletes_only_august_scoped_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "august_isolation_temp.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute("CREATE TABLE etl_energy_data (month_year TEXT, value INTEGER)")
                conn.execute("INSERT INTO etl_energy_data VALUES ('August 2025', 1)")
                conn.execute("INSERT INTO etl_energy_data VALUES ('July 2025', 2)")
                conn.execute("CREATE TABLE raw_energy_hourly (raw_timestamp TEXT, source_row_hash TEXT)")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-08-01T00:00:00', 'aug')")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-07-01T00:00:00', 'july')")
                conn.execute("CREATE TABLE three_way_matches (machine_id TEXT, last_confirmed_date TEXT)")
                conn.execute("INSERT INTO three_way_matches VALUES ('024-001', 'August 2025')")
                conn.commit()
            finally:
                conn.close()

            evidence = isolate_august_baseline_partitions(temp_db)

            conn = sqlite3.connect(temp_db)
            try:
                energy_rows = conn.execute("SELECT month_year, value FROM etl_energy_data").fetchall()
                raw_rows = conn.execute("SELECT raw_timestamp, source_row_hash FROM raw_energy_hourly").fetchall()
                global_rows = conn.execute("SELECT machine_id, last_confirmed_date FROM three_way_matches").fetchall()
            finally:
                conn.close()

        self.assertEqual(energy_rows, [("July 2025", 2)])
        self.assertEqual(raw_rows, [("2025-07-01T00:00:00", "july")])
        self.assertEqual(global_rows, [("024-001", "August 2025")])
        self.assertEqual(evidence["tables_pruned"]["etl_energy_data"]["deleted_rows"], 1)
        self.assertEqual(evidence["tables_pruned"]["raw_energy_hourly"]["deleted_rows"], 1)
        self.assertIn("three_way_matches", evidence["tables_skipped"])

    def test_august_isolation_skips_rule_when_required_columns_are_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "august_missing_columns_temp.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute("CREATE TABLE raw_energy_hourly (not_timestamp TEXT)")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-08-01')")
                conn.commit()
            finally:
                conn.close()

            evidence = isolate_august_baseline_partitions(temp_db)

            conn = sqlite3.connect(temp_db)
            try:
                row_count = conn.execute("SELECT COUNT(*) FROM raw_energy_hourly").fetchone()[0]
            finally:
                conn.close()

        self.assertEqual(row_count, 1)
        self.assertIn("raw_energy_hourly", evidence["tables_skipped"])
        self.assertIn("Required columns are missing", evidence["tables_skipped"]["raw_energy_hourly"]["reason"])

    def test_august_helpers_do_not_create_repo_db(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "august_summary_temp.db"
            conn = sqlite3.connect(temp_db)
            try:
                conn.execute("CREATE TABLE etl_runs (month_processed TEXT)")
                conn.execute("INSERT INTO etl_runs VALUES ('August 2025')")
                conn.execute("CREATE TABLE raw_energy_hourly (raw_timestamp TEXT, source_row_hash TEXT)")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-08-01T00:00:00', 'h1')")
                conn.execute("INSERT INTO raw_energy_hourly VALUES ('2025-08-01T01:00:00', 'h1')")
                conn.commit()
            finally:
                conn.close()

            summary = summarize_august_temp_db(temp_db)
            duplicates = inspect_august_source_hash_duplicates(temp_db)

        self.assertTrue(summary["etl_runs"]["present"])
        self.assertEqual(summary["etl_runs"]["august_row_count"]["row_count"], 1)
        self.assertEqual(duplicates["raw_energy_hourly"]["august_duplicate_hash_group_count"], 1)
        self.assertEqual(repo_db.exists(), before_repo_db_exists)

    def test_runner_can_be_exercised_without_repo_db_creation_when_dependencies_are_mocked(self):
        repo_db = Path(__file__).resolve().parents[1] / "manufacturing_data.db"
        before_repo_db_exists = repo_db.exists()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            temp_db = temp_root / "august_mock_run.db"
            original_db = temp_root / "original_runtime.db"
            sqlite3.connect(temp_db).close()
            original_db.write_bytes(b"original")

            with patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.isolate_august_baseline_partitions",
                return_value={"tables_inspected": {}, "tables_pruned": {}, "tables_skipped": {}},
            ), patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.summarize_august_temp_db",
                return_value={},
            ), patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.inspect_august_source_hash_duplicates",
                return_value={},
            ), patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.build_traceability_audit",
                return_value={
                    "traceability_result": {
                        "raw_august_unmatched_spill_row_count": 0,
                        "silver_august_unmatched_spill_row_count": 0,
                    }
                },
            ), patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.build_historical_backfill_preflight_plan",
                return_value={"expected_source_files": {}},
            ), patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.build_source_discovery_compare_diagnostics",
                return_value={"success": True, "rows": []},
            ), patch(
                "scripts.run_august_2025_temp_backfill_rehearsal.ETLPipelineModule"
            ) as pipeline_cls:
                pipeline = pipeline_cls.return_value
                pipeline.resolve_historical_month_sources.return_value = {
                    "source_discovery_mode": "auto_manifest",
                    "backfill_readiness": "ready_with_flags",
                    "energy_files": [],
                    "csi_file": None,
                    "mes_file": None,
                }
                pipeline.run_historical_canonical_backfill.return_value = {"status": "success"}
                pipeline.save_etl_results = lambda *args, **kwargs: None

                evidence = run_august_temp_backfill_rehearsal(
                    temp_db_path=temp_db,
                    data_root=temp_root,
                    original_db_path=original_db,
                )

        self.assertEqual(evidence["status"], "success")
        self.assertFalse(evidence["safety_evidence"]["temp_db_inside_github_safe_repo"])
        self.assertTrue(evidence["safety_evidence"]["original_runtime_db_unchanged_by_size_mtime"])
        self.assertEqual(repo_db.exists(), before_repo_db_exists)


if __name__ == "__main__":
    unittest.main()
