import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.data_contracts import load_source_manifest
from core.november_december_overlap_proof import build_november_december_overlap_proof


class NovemberDecemberOverlapProofTests(unittest.TestCase):
    def test_helper_refuses_repo_local_db_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, overlap_mode="none")
            repo_db = Path(__file__).resolve().parents[1] / "blocked_overlap_proof.db"

            with self.assertRaisesRegex(ValueError, "inside repo"):
                build_november_december_overlap_proof(
                    db_path=repo_db,
                    data_root=root,
                    manifest=manifest,
                )

        self.assertFalse(repo_db.exists())

    def test_helper_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            build_november_december_overlap_proof(db_path=original_runtime_db)

    def test_tiny_fixture_classifies_true_duplicate_by_source_row_hash(self):
        proof = self._build_fixture_proof(overlap_mode="true_duplicate")

        self.assertEqual(proof["seven_overlap_classification"]["summary"], {"true_duplicate_already_present": 1})
        self.assertEqual(proof["include_skip_unresolved_plan"]["skip_count"], 1)
        self.assertEqual(proof["include_skip_unresolved_plan"]["unresolved_count"], 0)

    def test_tiny_fixture_classifies_same_identity_different_hash(self):
        proof = self._build_fixture_proof(overlap_mode="different_hash")

        self.assertEqual(
            proof["seven_overlap_classification"]["summary"],
            {"same_identity_but_different_provenance_hash": 1},
        )
        self.assertEqual(proof["include_skip_unresolved_plan"]["unresolved_count"], 1)
        self.assertFalse(proof["b10_4_execution_safety_decision"]["safe_for_b10_4_temp_reconciliation"])

    def test_tiny_fixture_classifies_absent_candidate_as_include(self):
        proof = self._build_fixture_proof(overlap_mode="none")

        self.assertEqual(proof["workbook_level_overlap_reproduction"]["overlap_count"], 0)
        self.assertEqual(proof["include_skip_unresolved_plan"]["include_count"], 2)
        self.assertEqual(proof["include_skip_unresolved_plan"]["skip_count"], 0)
        self.assertEqual(proof["include_skip_unresolved_plan"]["unresolved_count"], 0)

    def test_unresolved_ambiguity_is_blocked(self):
        proof = self._build_fixture_proof(overlap_mode="unresolved")

        self.assertEqual(proof["seven_overlap_classification"]["summary"], {"unresolved": 1})
        self.assertEqual(proof["include_skip_unresolved_plan"]["unresolved_count"], 1)
        self.assertFalse(proof["b10_4_execution_safety_decision"]["safe_for_b10_4_temp_reconciliation"])

    def test_helper_does_not_create_db_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, overlap_mode="none")
            db_path = root / "fixture.db"
            self._write_db(db_path, mode="none")
            before = set(root.glob("*.db"))

            build_november_december_overlap_proof(
                db_path=db_path,
                data_root=root,
                manifest=manifest,
            )

            after = set(root.glob("*.db"))

        self.assertEqual(before, after)

    def _build_fixture_proof(self, *, overlap_mode: str) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root, overlap_mode=overlap_mode)
            db_path = root / "fixture.db"
            self._write_db(db_path, mode=overlap_mode)

            return build_november_december_overlap_proof(
                db_path=db_path,
                data_root=root,
                manifest=manifest,
            )

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

    def _write_sources(self, root: Path, *, overlap_mode: str) -> None:
        candidate_1 = self._source_row("D-001", "J1", "M1", 10, "2025-12-01 00:05:00", "2025-12-01 01:00:00")
        candidate_2 = self._source_row("D-002", "J2", "M2", 20, "2025-12-01 02:05:00", "2025-12-01 03:00:00")
        november_rows = [
            candidate_1,
            candidate_2,
            self._source_row("D-003", "J3", "M3", 30, "2025-11-15 08:00:00", "2025-11-15 09:00:00"),
        ]
        december_rows = [
            self._source_row("D-009", "J9", "M9", 90, "2025-12-02 08:00:00", "2025-12-02 09:00:00")
        ]
        if overlap_mode in {"true_duplicate", "different_hash", "unresolved"}:
            december_rows.append(dict(candidate_1))

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

    def _write_db(self, db_path: Path, *, mode: str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self._create_tables(conn)
            self._insert_raw(conn, "source-h1", "CSI(July2025 to Feb2026)/november.xlsx", "D-001", "J1", "M1", 10)
            self._insert_raw(conn, "source-h2", "CSI(July2025 to Feb2026)/november.xlsx", "D-002", "J2", "M2", 20)
            if mode == "true_duplicate":
                self._insert_raw(conn, "source-h1", "CSI(July2025 to Feb2026)/december.xlsx", "D-001", "J1", "M1", 10)
                self._insert_silver(conn, "source-h1", "CSI(July2025 to Feb2026)/december.xlsx", "D-001", "J1", "M1", 10)
            elif mode == "different_hash":
                self._insert_raw(conn, "target-h1", "CSI(July2025 to Feb2026)/december.xlsx", "D-001", "J1", "M1", 10)
                self._insert_silver(conn, "target-h1", "CSI(July2025 to Feb2026)/december.xlsx", "D-001", "J1", "M1", 10)
            elif mode == "unresolved":
                self._insert_raw(conn, None, "CSI(July2025 to Feb2026)/december.xlsx", "D-001", "J1", "M1", 10)
                self._insert_silver(conn, None, "CSI(July2025 to Feb2026)/december.xlsx", "D-001", "J1", "M1", 10)
            conn.commit()
        finally:
            conn.close()

    def _create_tables(self, conn: sqlite3.Connection) -> None:
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
                source_file TEXT,
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

    def _insert_raw(
        self,
        conn: sqlite3.Connection,
        source_hash: str | None,
        source_file: str,
        machine: str,
        order: str,
        material: str,
        good_qty: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO raw_csi_event VALUES
            (?, ?, ?, '2025-12-01 00:05:00', '2025-12-01 01:00:00', '2025-12-01 00:05:00', ?, ?, ?, '{}')
            """,
            (source_hash, source_file, machine, order, material, good_qty),
        )

    def _insert_silver(
        self,
        conn: sqlite3.Connection,
        source_hash: str | None,
        source_file: str,
        machine: str,
        order: str,
        material: str,
        good_qty: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO csi_job_event VALUES
            (?, ?, ?, '2025-12-01 00:05:00', '2025-12-01 01:00:00', '2025-12-01 00:05:00', NULL, ?, ?, ?)
            """,
            (source_hash, source_file, machine, order, material, good_qty),
        )

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


if __name__ == "__main__":
    unittest.main()
