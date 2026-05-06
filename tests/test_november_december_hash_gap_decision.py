import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.data_contracts import load_source_manifest
from core.november_december_hash_gap_decision import (
    build_november_december_hash_gap_decision,
    normalize_timestamp_for_gap_match,
)


class NovemberDecemberHashGapDecisionTests(unittest.TestCase):
    def test_refuses_repo_local_db_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root)
            repo_db = Path(__file__).resolve().parents[1] / "blocked_hash_gap.db"

            with self.assertRaisesRegex(ValueError, "inside repo"):
                build_november_december_hash_gap_decision(
                    db_path=repo_db,
                    data_root=root,
                    manifest=manifest,
                )

        self.assertFalse(repo_db.exists())

    def test_refuses_original_runtime_repo_db_path(self):
        original_runtime_db = (
            Path(__file__).resolve().parents[1].parent
            / "LeoPaperSmartManufacturingPlatform"
            / "manufacturing_data.db"
        )

        with self.assertRaisesRegex(ValueError, "original runtime repo"):
            build_november_december_hash_gap_decision(db_path=original_runtime_db)

    def test_tiny_fixture_can_classify_hash_resolved(self):
        decision = self._build_decision("hash_resolved")

        self.assertEqual(decision["source_hash_gap_reproduction"]["source_hash_gap_count"], 1)
        self.assertEqual(decision["alternative_matching_attempts"]["null_equivalent_identity_hash_resolved_count"], 1)
        self.assertEqual(decision["include_skip_block_plan"]["block_count"], 0)

    def test_tiny_fixture_can_classify_stable_identity_fallback_safe(self):
        decision = self._build_decision("fallback_safe")

        self.assertEqual(decision["alternative_matching_attempts"]["stable_identity_fallback_safe_count"], 1)
        self.assertEqual(
            decision["fallback_policy_decision"]["fallback_policy"],
            "approved_for_narrow_maintenance_null_quantity_rows",
        )
        self.assertTrue(decision["b10_5_execution_safety_decision"]["safe_for_b10_5_temp_reconciliation"])

    def test_tiny_fixture_can_classify_existing_duplicate_skip(self):
        decision = self._build_decision("skip_duplicate")

        self.assertEqual(decision["alternative_matching_attempts"]["skip_due_existing_duplicate_count"], 1)
        self.assertEqual(decision["include_skip_block_plan"]["skip_count"], 1)
        self.assertEqual(
            decision["fallback_policy_decision"]["fallback_policy"],
            "not_required_with_duplicate_skips",
        )
        self.assertTrue(decision["b10_5_execution_safety_decision"]["safe_for_b10_5_temp_reconciliation"])

    def test_tiny_fixture_blocks_ambiguous_unresolved_candidate(self):
        decision = self._build_decision("ambiguous")

        self.assertEqual(decision["alternative_matching_attempts"]["block_unresolved_count"], 1)
        self.assertFalse(decision["b10_5_execution_safety_decision"]["safe_for_b10_5_temp_reconciliation"])

    def test_timestamp_normalization_helper_is_deterministic(self):
        self.assertEqual(
            normalize_timestamp_for_gap_match("2025-12-01 06:29:57.000"),
            "2025-12-01 06:29:57",
        )
        self.assertEqual(normalize_timestamp_for_gap_match(None), "")

    def test_helper_does_not_create_db_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root)
            db_path = root / "fixture.db"
            self._write_db(db_path, "hash_resolved")
            before = set(root.glob("*.db"))

            build_november_december_hash_gap_decision(
                db_path=db_path,
                data_root=root,
                manifest=manifest,
            )

            after = set(root.glob("*.db"))

        self.assertEqual(before, after)

    def _build_decision(self, mode: str) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_for_fixtures()
            self._write_sources(root)
            db_path = root / "fixture.db"
            self._write_db(db_path, mode)

            return build_november_december_hash_gap_decision(
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

    def _write_sources(self, root: Path) -> None:
        november_rows = [
            self._source_row("D-001", "日保養", None, None, "2025-12-01 06:29:57", "2025-12-01 07:21:25"),
            self._source_row("D-002", "J2", "M2", 20, "2025-12-01 02:05:00", "2025-12-01 03:00:00"),
        ]
        december_rows = [
            self._source_row("D-009", "J9", "M9", 90, "2025-12-02 08:00:00", "2025-12-02 09:00:00")
        ]
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

    def _write_db(self, db_path: Path, mode: str) -> None:
        conn = sqlite3.connect(db_path)
        try:
            self._create_tables(conn)
            self._insert_raw(
                conn,
                "hash-j2",
                "CSI(July2025 to Feb2026)/november.xlsx",
                "D-002",
                "J2",
                "M2",
                20,
                "2025-12-01 02:05:00",
                "2025-12-01 03:00:00",
            )
            if mode == "hash_resolved":
                self._insert_raw(
                    conn,
                    "hash-maint",
                    "CSI(July2025 to Feb2026)/november.xlsx",
                    "D-001",
                    "日保養",
                    None,
                    None,
                    "2025-12-01 06:29:57",
                    "2025-12-01 07:21:25",
                )
            elif mode == "skip_duplicate":
                self._insert_raw(
                    conn,
                    "target-hash-maint",
                    "CSI(July2025 to Feb2026)/december.xlsx",
                    "D-001",
                    "日保養",
                    None,
                    None,
                    "2025-12-01 06:29:57",
                    "2025-12-01 07:21:25",
                )
            elif mode == "ambiguous":
                self._insert_raw(
                    conn,
                    None,
                    "CSI(July2025 to Feb2026)/december.xlsx",
                    "D-001",
                    "日保養",
                    None,
                    None,
                    "2025-12-01 06:29:57",
                    "2025-12-01 07:21:25",
                )
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
        material: str | None,
        good_qty: int | None,
        start_time: str,
        end_time: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO raw_csi_event VALUES
            (?, ?, ?, ?, ?, NULL, ?, ?, ?, '{}')
            """,
            (source_hash, source_file, machine, start_time, end_time, order, material, good_qty),
        )

    def _source_row(
        self,
        machine: str,
        order: str,
        material: str | None,
        good_qty: int | None,
        start_time: str,
        end_time: str,
    ) -> dict:
        return {
            "班次內日期": start_time[:10],
            "機台編號": machine,
            "作业": order,
            "物料": material,
            "工程開始時間": start_time,
            "準備結束時間": None,
            "工程結束時間": end_time,
            "正品數量": good_qty,
        }

    def _write_excel(self, path: Path, df: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, index=False)


if __name__ == "__main__":
    unittest.main()
