import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.data_contracts import load_source_manifest
from core.november_december_carry_forward_preflight import (
    build_november_december_csi_carry_forward_preflight,
)


class NovemberDecemberCarryForwardPreflightTests(unittest.TestCase):
    def test_candidate_selection_works_on_tiny_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, duplicate_candidate=False, include_target_overlap=False)

            preflight = build_november_december_csi_carry_forward_preflight(
                data_root=root,
                manifest=manifest,
            )

        identity = preflight["candidate_identity_evidence"]
        self.assertEqual(identity["candidate_count"], 2)
        self.assertEqual(identity["distinct_machine_count"], 2)
        self.assertEqual(identity["distinct_order_count"], 2)
        self.assertEqual(identity["good_qty_sum"], 30.0)
        self.assertEqual(identity["canonical_month_distribution"], {"2025-12": 2})
        self.assertEqual(identity["duplicate_stable_identity_group_count"], 0)

    def test_duplicate_stable_identity_groups_are_detected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, duplicate_candidate=True, include_target_overlap=False)

            preflight = build_november_december_csi_carry_forward_preflight(
                data_root=root,
                manifest=manifest,
            )

        identity = preflight["candidate_identity_evidence"]
        self.assertEqual(identity["candidate_count"], 3)
        self.assertEqual(identity["duplicate_stable_identity_group_count"], 1)
        self.assertEqual(identity["duplicate_stable_identity_row_count"], 2)

    def test_overlap_check_can_report_zero_and_nonzero_overlap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, duplicate_candidate=False, include_target_overlap=False)

            zero_preflight = build_november_december_csi_carry_forward_preflight(
                data_root=root,
                manifest=manifest,
            )

            self._write_sources(root, duplicate_candidate=False, include_target_overlap=True)
            overlap_preflight = build_november_december_csi_carry_forward_preflight(
                data_root=root,
                manifest=manifest,
            )

        zero_overlap = zero_preflight["current_december_overlap_check"]["workbook_level_overlap"]
        nonzero_overlap = overlap_preflight["current_december_overlap_check"]["workbook_level_overlap"]
        self.assertEqual(zero_overlap["status"], "zero_overlap")
        self.assertEqual(zero_overlap["candidate_overlap_count"], 0)
        self.assertEqual(nonzero_overlap["status"], "overlap_found")
        self.assertEqual(nonzero_overlap["candidate_overlap_count"], 1)

    def test_helper_refuses_repo_local_db_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, duplicate_candidate=False, include_target_overlap=False)
            repo_db = Path(__file__).resolve().parents[1] / "blocked_b10_2.db"

            with self.assertRaisesRegex(ValueError, "inside repo"):
                build_november_december_csi_carry_forward_preflight(
                    data_root=root,
                    manifest=manifest,
                    source_package_db_path=repo_db,
                )

        self.assertFalse(repo_db.exists())

    def test_helper_does_not_create_db_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, duplicate_candidate=False, include_target_overlap=False)
            before_db_files = set(root.glob("*.db"))

            build_november_december_csi_carry_forward_preflight(
                data_root=root,
                manifest=manifest,
            )

            after_db_files = set(root.glob("*.db"))

        self.assertEqual(before_db_files, after_db_files)

    def test_unknown_target_month_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "Only December 2025"):
            build_november_december_csi_carry_forward_preflight(target_month="January 2026")

    def test_optional_db_overlap_reports_nonzero_overlap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, duplicate_candidate=False, include_target_overlap=False)
            db_path = root / "current.db"
            self._create_current_db_with_overlap(db_path)

            preflight = build_november_december_csi_carry_forward_preflight(
                data_root=root,
                manifest=manifest,
                current_package_db_path=db_path,
            )

        bronze_overlap = preflight["current_december_overlap_check"]["bronze_db_overlap"]
        self.assertEqual(bronze_overlap["status"], "overlap_found")
        self.assertEqual(bronze_overlap["raw_overlap_candidate_count"], 1)
        self.assertEqual(bronze_overlap["silver_overlap_candidate_count"], 1)

    def _manifest_for_fixtures(self) -> dict:
        manifest = copy.deepcopy(load_source_manifest())
        for month_key, filename in {
            "2025-11": "CSI(July2025 to Feb2026)/november.xlsx",
            "2025-12": "CSI(July2025 to Feb2026)/december.xlsx",
        }.items():
            spec = manifest["month_source_files"][month_key]
            spec["csi_file"] = filename
            spec["energy_files"] = [f"energy-{month_key}.xlsx"]
            spec["mes_file"] = f"mes-{month_key}.xlsx"
        return manifest

    def _write_sources(self, root: Path, *, duplicate_candidate: bool, include_target_overlap: bool) -> None:
        november_rows = [
            self._source_row("D-001", "J1", "M1", 10, "2025-12-01 00:05:00", "2025-12-01 01:00:00"),
            self._source_row("D-002", "J2", "M2", 20, "2025-12-01 02:05:00", "2025-12-01 03:00:00"),
            self._source_row("D-003", "J3", "M3", 30, "2025-11-15 08:00:00", "2025-11-15 09:00:00"),
        ]
        if duplicate_candidate:
            november_rows.append(dict(november_rows[0]))

        december_rows = [
            self._source_row("D-009", "J9", "M9", 90, "2025-12-02 08:00:00", "2025-12-02 09:00:00")
        ]
        if include_target_overlap:
            december_rows.append(dict(november_rows[0]))

        self._write_excel(root / "CSI(July2025 to Feb2026)/november.xlsx", pd.DataFrame(november_rows))
        self._write_excel(root / "CSI(July2025 to Feb2026)/december.xlsx", pd.DataFrame(december_rows))
        for relative_path in (
            "energy-2025-11.xlsx",
            "energy-2025-12.xlsx",
            "mes-2025-11.xlsx",
            "mes-2025-12.xlsx",
        ):
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"placeholder")

    def _source_row(
        self,
        machine: str,
        order: str,
        material: str,
        good_qty: int,
        start_time: str,
        end_time: str,
    ) -> dict:
        return {
            "班次內日期": start_time[:10],
            "機台編號": machine,
            "作业": order,
            "物料": material,
            "工程開始時間": start_time,
            "準備結束時間": start_time,
            "工程結束時間": end_time,
            "正品數量": good_qty,
        }

    def _write_excel(self, path: Path, df: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, index=False)

    def _create_current_db_with_overlap(self, db_path: Path) -> None:
        conn = sqlite3.connect(db_path)
        try:
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
                INSERT INTO raw_csi_event VALUES
                ('h1', 'december-source.xls', 'D-001', '2025-12-01 00:05:00', '2025-12-01 01:00:00', '2025-12-01 00:05:00', 'J1', 'M1', 10, '{}')
                """
            )
            conn.execute(
                """
                INSERT INTO csi_job_event VALUES
                ('h1', 'D-001', '2025-12-01 00:05:00', '2025-12-01 01:00:00', '2025-12-01 00:05:00', NULL, 'J1', 'M1', 10)
                """
            )
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
