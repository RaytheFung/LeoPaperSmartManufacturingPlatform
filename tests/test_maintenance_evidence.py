import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.maintenance_evidence import (
    MaintenanceEvidenceReader,
    parse_maintenance_month_label,
    sort_maintenance_month_labels,
)


class MaintenanceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "maintenance_evidence.db"
        self._create_tables()
        self._insert_seed_rows()
        self.reader = MaintenanceEvidenceReader(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order TEXT,
                work_order_type TEXT,
                transaction_date TEXT,
                material_code TEXT,
                month_year TEXT,
                machine_id TEXT,
                is_three_way_match INTEGER
            )
            """
        )
        conn.execute("CREATE TABLE three_way_matches (machine_id TEXT)")
        conn.execute(
            """
            CREATE TABLE maintenance_ml_features (
                machine_id TEXT,
                date TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _insert_seed_rows(self):
        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(
            [
                {"machine_id": "166-002"},
                {"machine_id": "024-001"},
                {"machine_id": "024-999"},
            ]
        ).to_sql("three_way_matches", conn, if_exists="append", index=False)
        pd.DataFrame(
            [
                {
                    "work_order": "WO-001",
                    "work_order_type": "PM",
                    "transaction_date": "2025-01-05 08:00:00",
                    "material_code": "MAT-001",
                    "month_year": "January 2025",
                    "machine_id": "166-002",
                    "is_three_way_match": 1,
                },
                {
                    "work_order": "WO-002",
                    "work_order_type": "CM",
                    "transaction_date": "2025-02-01 10:00:00",
                    "material_code": "MAT-002",
                    "month_year": "February 2025",
                    "machine_id": "166-002",
                    "is_three_way_match": 1,
                },
                {
                    "work_order": "WO-003",
                    "work_order_type": "PM",
                    "transaction_date": "2025-03-01 09:30:00",
                    "material_code": "MAT-003",
                    "month_year": "March 2025",
                    "machine_id": "166-002",
                    "is_three_way_match": 1,
                },
                {
                    "work_order": "WO-004",
                    "work_order_type": "AM",
                    "transaction_date": "2025-03-10 12:00:00",
                    "material_code": "MAT-004",
                    "month_year": "March 2025",
                    "machine_id": "166-002",
                    "is_three_way_match": 1,
                },
                {
                    "work_order": "WO-005",
                    "work_order_type": "PM",
                    "transaction_date": "2025-02-15 15:00:00",
                    "material_code": "MAT-005",
                    "month_year": "February 2025",
                    "machine_id": "024-001",
                    "is_three_way_match": 1,
                },
                {
                    "work_order": "WO-006",
                    "work_order_type": "CM",
                    "transaction_date": "2025-04-01 11:00:00",
                    "material_code": "MAT-006",
                    "month_year": "April 2025",
                    "machine_id": "UNM-001",
                    "is_three_way_match": 0,
                },
            ]
        ).to_sql("maintenance_records", conn, if_exists="append", index=False)
        pd.DataFrame(
            [
                {"machine_id": "166-002", "date": "2025-03-10"},
                {"machine_id": "024-001", "date": "2025-02-15"},
            ]
        ).to_sql("maintenance_ml_features", conn, if_exists="append", index=False)
        conn.commit()
        conn.close()

    def test_parse_maintenance_month_label_accepts_full_month_year(self):
        parsed = parse_maintenance_month_label("March 2025")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.strftime("%Y-%m-%d"), "2025-03-01")

    def test_sort_maintenance_month_labels_orders_values_chronologically(self):
        months = [
            "April 2025",
            "January 2025",
            "March 2025",
            "February 2025",
        ]

        self.assertEqual(
            sort_maintenance_month_labels(months),
            ["January 2025", "February 2025", "March 2025", "April 2025"],
        )

    def test_build_coverage_snapshot_reports_storage_and_match_counts(self):
        snapshot = self.reader.build_coverage_snapshot()

        self.assertTrue(snapshot["maintenance_records_available"])
        self.assertEqual(snapshot["records_stored"], 6)
        self.assertEqual(snapshot["matched_records_stored"], 5)
        self.assertEqual(snapshot["integrated_machine_count"], 2)
        self.assertEqual(snapshot["total_three_way_matches"], 3)
        self.assertAlmostEqual(snapshot["integration_coverage_ratio"], 2 / 3)
        self.assertEqual(
            snapshot["months_covered"],
            ["January 2025", "February 2025", "March 2025", "April 2025"],
        )
        self.assertEqual(snapshot["latest_maintenance_datetime_label"], "2025-04-01 11:00")
        self.assertEqual(snapshot["legacy_risk_rows"], 2)

    def test_build_machine_evidence_keeps_all_time_and_recent_window_contracts_separate(self):
        evidence = self.reader.build_machine_evidence(
            "166-002",
            recent_window_limit=3,
            as_of=pd.Timestamp("2025-03-15 12:00:00"),
        )

        self.assertTrue(evidence["machine_has_history"])
        self.assertEqual(evidence["all_time_event_count"], 4)
        self.assertEqual(evidence["recent_window_event_count"], 3)
        self.assertTrue(evidence["history_window_limited"])
        self.assertEqual(evidence["latest_work_order_type"], "AM")
        self.assertEqual(evidence["latest_maintenance_datetime_label"], "2025-03-10 12:00")
        self.assertEqual(evidence["days_since_last_maintenance"], 5)
        self.assertEqual(evidence["months_covered_count"], 3)
        self.assertEqual(
            evidence["months_covered"],
            ["January 2025", "February 2025", "March 2025"],
        )
        self.assertAlmostEqual(evidence["pm_ratio_all_time"], 0.5)
        self.assertAlmostEqual(evidence["pm_ratio_recent_window"], 1 / 3)
        self.assertEqual(
            evidence["recent_history_df"]["work_order"].tolist(),
            ["WO-004", "WO-003", "WO-002"],
        )

    def test_build_machine_context_payload_returns_compact_cross_module_fields(self):
        payload = self.reader.build_machine_context_payload(
            "166-002",
            recent_window_limit=3,
            as_of=pd.Timestamp("2025-03-15 12:00:00"),
        )

        self.assertTrue(payload["available"])
        self.assertEqual(payload["machine_id"], "166-002")
        self.assertEqual(payload["days_since_last_maintenance"], 5)
        self.assertEqual(payload["total_events"], 4)
        self.assertEqual(payload["recent_events_shown"], 3)
        self.assertEqual(payload["latest_work_order_type"], "AM")
        self.assertTrue(payload["history_window_limited"])

    def test_build_machine_context_payload_blocks_honestly_when_machine_is_missing(self):
        payload = self.reader.build_machine_context_payload("999-999")

        self.assertFalse(payload["available"])
        self.assertIn("No matched maintenance evidence is stored", payload["reason"])


if __name__ == "__main__":
    unittest.main()
