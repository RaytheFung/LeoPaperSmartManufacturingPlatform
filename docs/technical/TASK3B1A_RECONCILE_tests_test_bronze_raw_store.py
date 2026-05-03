import sqlite3
import tempfile
import unittest
import json
from pathlib import Path

import pandas as pd

from core.bronze_raw_store import BronzeRawStore


class BronzeRawStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "bronze_test.db"
        self.store = BronzeRawStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_tables_creates_all_bronze_tables(self):
        conn = sqlite3.connect(self.db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        self.assertTrue({
            "raw_energy_hourly",
            "raw_csi_event",
            "raw_mes_report",
            "raw_maintenance_txn",
        }.issubset(tables))

    def test_write_rows_persists_bronze_metadata_for_all_source_systems(self):
        energy_df = pd.DataFrame([
            {
                "source_file": "data/energy_sample.xlsx",
                "machine": "印刷机024-018主機+IR",
                "datetime": pd.Timestamp("2025-06-01 01:00:00"),
                "electricity_kwh": 12.5,
                "electricity_cost": 30.2,
                "canonical_machine_id": "024-018",
                "matched_on": "energy_alias_example",
                "matched_value": "印刷机024-018主機+IR",
                "exception_applied": False,
                "source_system": "energy",
                "scope_status": "production_joinable",
                "join_status": "production_joinable",
            }
        ])
        csi_df = pd.DataFrame([
            {
                "source_file": "data/csi_sample.xlsx",
                "機台編號": "D-024-018",
                "工程開始時間": pd.Timestamp("2025-06-01 08:00:00"),
                "工程結束時間": pd.Timestamp("2025-06-01 10:00:00"),
                "準備結束時間": pd.Timestamp("2025-06-01 07:50:00"),
                "作业": "JOB-1",
                "物料": "MAT-1",
                "正品數量": 100,
                "廢品數量": 3,
                "canonical_machine_id": "024-018",
                "matched_on": "csi_machine_id",
                "matched_value": "D-024-018",
                "exception_applied": False,
                "source_system": "csi",
                "scope_status": "production_joinable",
                "join_status": "production_joinable",
            }
        ])
        mes_df = pd.DataFrame([
            {
                "source_file": "data/mes_sample.xlsx",
                "資源": "1035-00017",
                "任務": "印刷",
                "訂單號": "ORDER-1",
                "物料編碼": "MAT-2",
                "計劃數量": 200,
                "計劃開始": pd.Timestamp("2025-06-01 09:00:00"),
                "計劃結束": pd.Timestamp("2025-06-01 12:00:00"),
                "canonical_machine_id": "035-017",
                "matched_on": "mes_secondary_alias",
                "matched_value": "1035-00017",
                "exception_applied": True,
                "source_system": "mes",
                "scope_status": "production_joinable",
                "join_status": "production_joinable",
            }
        ])
        maintenance_df = pd.DataFrame([
            {
                "source_file": "2025 DataSet(JAN to JUN)/Maintenance/sample.xlsx",
                "交易日期": pd.Timestamp("2025-06-02 14:00:00"),
                "工單": "WO-1",
                "工單類型": "PM",
                "交易類型": "發出",
                "資產": "1264-00003",
                "資產老編號": "342-002",
                "物料編碼": "PART-1",
                "數量": 2,
                "normalized_id": "342-002",
                "canonical_machine_id": "1264-00003",
                "matched_on": "maintenance_asset_id",
                "matched_value": "1264-00003",
                "exception_applied": False,
                "source_system": "maintenance",
                "scope_status": "production_joinable",
                "join_status": "production_joinable",
            }
        ])

        self.store.write_energy_rows(energy_df)
        self.store.write_csi_rows(csi_df)
        self.store.write_mes_rows(mes_df)
        self.store.write_maintenance_rows(maintenance_df)

        conn = sqlite3.connect(self.db_path)
        energy_row = conn.execute(
            "SELECT source_system, source_file, canonical_machine_id, matched_on, matched_value, exception_applied, scope_status, join_status FROM raw_energy_hourly"
        ).fetchone()
        csi_row = conn.execute(
            "SELECT raw_machine_id_or_label, raw_order_id, canonical_machine_id FROM raw_csi_event"
        ).fetchone()
        mes_row = conn.execute(
            "SELECT raw_machine_id_or_label, canonical_machine_id, exception_applied FROM raw_mes_report"
        ).fetchone()
        maintenance_row = conn.execute(
            "SELECT raw_machine_id_or_label, raw_asset_old_id, canonical_machine_id FROM raw_maintenance_txn"
        ).fetchone()
        hash_count = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT source_row_hash FROM raw_energy_hourly
                UNION ALL
                SELECT source_row_hash FROM raw_csi_event
                UNION ALL
                SELECT source_row_hash FROM raw_mes_report
                UNION ALL
                SELECT source_row_hash FROM raw_maintenance_txn
            )
            """
        ).fetchone()[0]
        conn.close()

        self.assertEqual(
            energy_row,
            ("energy", "data/energy_sample.xlsx", "024-018", "energy_alias_example", "印刷机024-018主機+IR", 0, "production_joinable", "production_joinable"),
        )
        self.assertEqual(csi_row, ("D-024-018", "JOB-1", "024-018"))
        self.assertEqual(mes_row, ("1035-00017", "035-017", 1))
        self.assertEqual(maintenance_row, ("1264-00003", "342-002", "1264-00003"))
        self.assertEqual(hash_count, 4)

    def test_source_row_hash_ignores_derived_mapping_metadata(self):
        base_row = {
            "source_file": "data/energy_sample.xlsx",
            "machine": "印刷机024-018主機+IR",
            "datetime": pd.Timestamp("2025-06-01 01:00:00"),
            "electricity_kwh": 12.5,
            "electricity_cost": 30.2,
            "canonical_machine_id": "024-018",
            "matched_on": "energy_alias_example",
            "matched_value": "印刷机024-018主機+IR",
            "exception_applied": False,
            "source_system": "energy",
            "scope_status": "production_joinable",
            "join_status": "production_joinable",
        }
        updated_metadata_row = {
            **base_row,
            "canonical_machine_id": "024-999",
            "matched_on": "manual_override",
            "matched_value": "OVERRIDE",
            "exception_applied": True,
            "scope_status": "review_required",
            "join_status": "exception_joinable",
        }

        built_base = self.store._build_energy_row(pd.Series(base_row))
        built_updated = self.store._build_energy_row(pd.Series(updated_metadata_row))

        self.assertEqual(
            built_base["source_row_hash"],
            built_updated["source_row_hash"],
        )
        self.assertNotEqual(
            built_base["raw_payload_json"],
            built_updated["raw_payload_json"],
        )

    def test_upsert_updates_existing_bronze_row_without_duplicate(self):
        original_df = pd.DataFrame([
            {
                "source_file": "data/energy_sample.xlsx",
                "machine": "印刷机024-018主機+IR",
                "datetime": pd.Timestamp("2025-06-01 01:00:00"),
                "electricity_kwh": 12.5,
                "electricity_cost": 30.2,
                "canonical_machine_id": "024-018",
                "matched_on": "energy_alias_example",
                "matched_value": "印刷机024-018主機+IR",
                "exception_applied": False,
                "source_system": "energy",
                "scope_status": "production_joinable",
                "join_status": "production_joinable",
            }
        ])
        updated_df = pd.DataFrame([
            {
                "source_file": "data/energy_sample.xlsx",
                "machine": "印刷机024-018主機+IR",
                "datetime": pd.Timestamp("2025-06-01 01:00:00"),
                "electricity_kwh": 12.5,
                "electricity_cost": 30.2,
                "canonical_machine_id": "024-999",
                "matched_on": "manual_override",
                "matched_value": "OVERRIDE",
                "exception_applied": True,
                "source_system": "energy",
                "scope_status": "review_required",
                "join_status": "exception_joinable",
            }
        ])

        self.store.write_energy_rows(original_df)
        self.store.write_energy_rows(updated_df)

        conn = sqlite3.connect(self.db_path)
        row_count = conn.execute(
            "SELECT COUNT(*) FROM raw_energy_hourly"
        ).fetchone()[0]
        persisted_row = conn.execute(
            """
            SELECT canonical_machine_id, matched_on, matched_value,
                   exception_applied, scope_status, join_status
            FROM raw_energy_hourly
            """
        ).fetchone()
        conn.close()

        self.assertEqual(row_count, 1)
        self.assertEqual(
            persisted_row,
            ("024-999", "manual_override", "OVERRIDE", 1, "review_required", "exception_joinable"),
        )

    def test_mes_row_prefers_real_raw_fields_over_fallback_fields(self):
        mes_row = pd.Series(
            {
                "source_file": "data/mes_sample.xlsx",
                "資源": "1035-00017",
                "resource": "fallback-resource",
                "任務": "印刷",
                "task": "fallback-task",
                "訂單號": "ORDER-1",
                "order_number": "ORDER-FALLBACK",
                "物料編碼": "MAT-2",
                "material_code": "MAT-FALLBACK",
                "計劃數量": 200,
                "planned_qty": 999,
                "計劃開始": pd.Timestamp("2025-06-01 09:00:00"),
                "planned_start": "2025-01-01T00:00:00",
                "計劃結束": pd.Timestamp("2025-06-01 12:00:00"),
                "planned_end": "2025-01-01T01:00:00",
            }
        )

        built_row = self.store._build_mes_row(mes_row)
        payload = json.loads(built_row["raw_payload_json"])

        self.assertEqual(built_row["raw_machine_id_or_label"], "1035-00017")
        self.assertEqual(built_row["raw_task"], "印刷")
        self.assertEqual(built_row["raw_order_number"], "ORDER-1")
        self.assertEqual(built_row["raw_material_code"], "MAT-2")
        self.assertEqual(built_row["raw_planned_qty"], 200.0)
        self.assertEqual(built_row["raw_planned_start"], "2025-06-01T09:00:00")
        self.assertEqual(built_row["raw_planned_end"], "2025-06-01T12:00:00")
        self.assertEqual(payload["資源"], "1035-00017")
        self.assertEqual(payload["resource"], "fallback-resource")

    def test_mes_row_uses_explicit_fallbacks_when_raw_fields_absent(self):
        mes_row = pd.Series(
            {
                "source_file": "data/mes_sample.xlsx",
                "resource": "1035-00018",
                "task": "塗布",
                "order_number": "ORDER-2",
                "material_code": "MAT-3",
                "planned_qty": 150,
                "planned_start": "2025-06-02T09:00:00",
                "planned_end": "2025-06-02T11:00:00",
            }
        )

        built_row = self.store._build_mes_row(mes_row)
        payload = json.loads(built_row["raw_payload_json"])

        self.assertEqual(built_row["raw_machine_id_or_label"], "1035-00018")
        self.assertEqual(built_row["raw_task"], "塗布")
        self.assertEqual(built_row["raw_order_number"], "ORDER-2")
        self.assertEqual(built_row["raw_material_code"], "MAT-3")
        self.assertEqual(built_row["raw_planned_qty"], 150.0)
        self.assertEqual(built_row["raw_planned_start"], "2025-06-02T09:00:00")
        self.assertEqual(built_row["raw_planned_end"], "2025-06-02T11:00:00")
        self.assertEqual(payload["resource"], "1035-00018")


if __name__ == "__main__":
    unittest.main()
