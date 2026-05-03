import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.bronze_raw_store import BronzeRawStore
from core.silver_normalizer import (
    SilverNormalizer,
    get_gold_merge_readiness_contract,
    get_silver_bronze_traceability_contract,
)
from core.source_family_registry import (
    get_registered_source_families,
    get_source_family_contract,
)


class SourceFamilyRegistryTests(unittest.TestCase):
    def test_registered_source_family_statuses_match_task_contract(self):
        contracts = get_registered_source_families()

        self.assertEqual(contracts["energy_hourly_report_v1"].status, "supported")
        self.assertEqual(contracts["energy_daily_report_v1"].status, "supplementary_only")
        self.assertEqual(contracts["energy_tariff_aggregate_v1"].status, "separate_family")
        self.assertEqual(contracts["csi_monthly_xlsx_v1"].status, "supported")
        self.assertEqual(contracts["csi_monthly_xls_variant_v1"].status, "registered_variant")
        self.assertEqual(contracts["mes_monthly_report_v1"].status, "supported")
        self.assertEqual(contracts["maintenance_transaction_v1"].status, "supported")
        self.assertEqual(
            get_source_family_contract("csi_monthly_xls_variant_v1").reader_dependency,
            "xlrd",
        )


class SilverNormalizerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "silver_test.db"
        self.bronze_store = BronzeRawStore(self.db_path)
        self.normalizer = SilverNormalizer(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_energy_normalization_excludes_summary_rows_and_parses_components(self):
        energy_df = pd.DataFrame(
            [
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018",
                    "datetime": pd.Timestamp("2025-06-01 01:00:00"),
                    "electricity_kwh": 10.5,
                    "electricity_cost": 2.1,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018主機+IR",
                    "datetime": pd.Timestamp("2025-06-01 02:00:00"),
                    "electricity_kwh": 9.0,
                    "electricity_cost": 1.8,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018 UV",
                    "datetime": pd.Timestamp("2025-06-01 03:00:00"),
                    "electricity_kwh": 8.0,
                    "electricity_cost": 1.6,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷機024-119(IR)",
                    "datetime": pd.Timestamp("2025-06-01 04:00:00"),
                    "electricity_kwh": 7.0,
                    "electricity_cost": 1.4,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷機024-131(馬達)",
                    "datetime": pd.Timestamp("2025-06-01 05:00:00"),
                    "electricity_kwh": 6.0,
                    "electricity_cost": 1.2,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018合計用量",
                    "datetime": pd.Timestamp("2025-06-01 06:00:00"),
                    "electricity_kwh": 99.0,
                    "electricity_cost": 19.8,
                },
            ]
        )

        self.bronze_store.write_energy_rows(energy_df)
        silver_df = self.normalizer.normalize_energy_to_silver()

        self.assertEqual(len(silver_df), 5)
        components = dict(zip(silver_df["meter_label"], silver_df["meter_component"]))
        self.assertEqual(components["印刷机024-018"], "aggregate_total")
        self.assertEqual(components["印刷机024-018主機+IR"], "combo")
        self.assertEqual(components["印刷机024-018 UV"], "uv")
        self.assertEqual(components["印刷機024-119(IR)"], "ir")
        self.assertEqual(components["印刷機024-131(馬達)"], "motor")

        aggregate_flags = dict(zip(silver_df["meter_label"], silver_df["meter_is_aggregate"]))
        self.assertEqual(aggregate_flags["印刷机024-018"], 1)
        self.assertEqual(aggregate_flags["印刷机024-018主機+IR"], 1)
        self.assertEqual(aggregate_flags["印刷机024-018 UV"], 0)

    def test_energy_dual_id_label_parsing_and_resolution_is_stable(self):
        energy_df = pd.DataFrame(
            [
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "1024-10032/024-147印刷機主機",
                    "datetime": pd.Timestamp("2025-06-01 01:00:00"),
                    "electricity_kwh": 11.0,
                    "electricity_cost": 2.2,
                }
            ]
        )

        self.bronze_store.write_energy_rows(energy_df)
        silver_df = self.normalizer.normalize_energy_to_silver()
        row = silver_df.iloc[0]

        self.assertEqual(row["canonical_machine_id"], "024-147")
        self.assertEqual(row["meter_component"], "main")
        self.assertEqual(row["meter_label"], "1024-10032/024-147印刷機主機")
        self.assertEqual(row["parse_confidence"], "high")

    def test_energy_normalization_excludes_invalid_hour_timestamps(self):
        energy_df = pd.DataFrame(
            [
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018",
                    "datetime": "not-a-timestamp",
                    "electricity_kwh": 10.5,
                    "electricity_cost": 2.1,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018 UV",
                    "datetime": "2025-06-01 01:30:00",
                    "electricity_kwh": 8.0,
                    "electricity_cost": 1.6,
                },
                {
                    "source_file": "data/june_energy.xlsx",
                    "machine": "印刷机024-018主機+IR",
                    "datetime": "2025-06-01 02:00:00",
                    "electricity_kwh": 9.0,
                    "electricity_cost": 1.8,
                },
            ]
        )

        self.bronze_store.write_energy_rows(energy_df)
        silver_df = self.normalizer.normalize_energy_to_silver()

        self.assertEqual(len(silver_df), 1)
        self.assertEqual(silver_df.iloc[0]["hour_ts"], "2025-06-01T02:00:00")

    def test_energy_normalization_excludes_task13_august_sentinel_anomaly_rows(self):
        energy_df = pd.DataFrame(
            [
                {
                    "source_file": "data/aug_energy.xlsx",
                    "machine": "1024-10032/024-147印刷機UV",
                    "datetime": pd.Timestamp("2025-08-17 08:00:00"),
                    "electricity_kwh": 99999999.9999,
                    "electricity_cost": 99999999.9999,
                },
                {
                    "source_file": "data/aug_energy.xlsx",
                    "machine": "1024-10032/024-147印刷機UV",
                    "datetime": pd.Timestamp("2025-08-17 18:00:00"),
                    "electricity_kwh": 12.0,
                    "electricity_cost": 3.0,
                },
            ]
        )

        self.bronze_store.write_energy_rows(energy_df)
        silver_df = self.normalizer.normalize_energy_to_silver()

        self.assertEqual(len(silver_df), 1)
        self.assertEqual(silver_df.iloc[0]["hour_ts"], "2025-08-17T18:00:00")
        self.assertEqual(silver_df.iloc[0]["quality_status"], "ok")

    def test_energy_normalization_flags_task13_partial_meter_months(self):
        energy_df = pd.DataFrame(
            [
                {
                    "source_file": "data/feb_energy.xlsx",
                    "machine": "印刷機024-080 UV",
                    "datetime": pd.Timestamp("2026-02-02 09:00:00"),
                    "electricity_kwh": 1.0,
                    "electricity_cost": 0.2,
                }
            ]
        )

        self.bronze_store.write_energy_rows(energy_df)
        silver_df = self.normalizer.normalize_energy_to_silver()
        row = silver_df.iloc[0]

        self.assertEqual(row["canonical_machine_id"], "024-080")
        self.assertEqual(row["quality_status"], "flagged_partial")
        self.assertTrue(json.loads(row["quality_flags_json"])["localized_partial_meter_month"])

    def test_csi_normalization_maps_june_contract_and_preserves_maintenance_like_rows(self):
        csi_df = pd.DataFrame(
            [
                {
                    "source_file": "data/june_csi.xlsx",
                    "班次內日期": "2025-06-09",
                    "班次": "日班",
                    "區域": "八期印刷",
                    "機台編號": "D-024-018",
                    "作业": "J250015565",
                    "作业后缀": 1,
                    "操作": 10,
                    "物料": "PH0002201236-03-01",
                    "任務": "印刷啤",
                    "工程開始時間": pd.Timestamp("2025-06-09 08:35:00"),
                    "準備結束時間": "2025-06-09 08:50:00 ",
                    "工程結束時間": pd.Timestamp("2025-06-09 19:50:00"),
                    "正品數量": 150000,
                    "廢品數量": 0,
                    "纍計數量": 150000,
                    "心電圖整體運作時間": 675,
                    "實際生產時間": 540,
                    "實際速度_本_時": 16666.67,
                    "心電圖實際轉版時間": 15,
                    "實際計劃停機時間": 120,
                    "實際無計劃停機時間": 0,
                    "停機原因": "A2-有計劃停機維修;A3-自主保養;",
                    "運作中途總停機次數": 2,
                    "機長姓名1": "張展鵬",
                    "機長姓名2": "李四",
                    "機組人員姓名1": "陳家雄",
                    "機組人員姓名2": "王五",
                    "機組人員姓名3": None,
                    "機組人員姓名4": None,
                    "額外欄位": "ignore-me",
                }
            ]
        )

        self.bronze_store.write_csi_rows(csi_df)
        silver_df = self.normalizer.normalize_csi_to_silver()
        row = silver_df.iloc[0]

        self.assertEqual(row["canonical_machine_id"], "024-018")
        self.assertEqual(row["shift_date"], "2025-06-09")
        self.assertEqual(row["shift_name"], "日班")
        self.assertEqual(row["csi_area"], "八期印刷")
        self.assertEqual(row["order_id"], "J250015565")
        self.assertEqual(row["suffix"], "1")
        self.assertEqual(row["operation"], "10")
        self.assertEqual(row["material_code"], "PH0002201236-03-01")
        self.assertEqual(row["task_name"], "印刷啤")
        self.assertEqual(row["prod_start_ts"], "2025-06-09T08:35:00")
        self.assertEqual(row["prep_end_ts"], "2025-06-09T08:50:00")
        self.assertEqual(row["prod_end_ts"], "2025-06-09T19:50:00")
        self.assertEqual(row["good_qty"], 150000.0)
        self.assertEqual(row["actual_changeover_minutes"], 15.0)
        self.assertIn("維修", row["stop_reason"])
        self.assertEqual(row["team_leader"], "張展鵬")
        self.assertEqual(json.loads(row["team_members_raw"]), ["李四", "陳家雄", "王五"])

    def test_team_leader_is_the_explicit_csi_leader_field(self):
        csi_df = pd.DataFrame(
            [
                {
                    "source_file": "data/june_csi.xlsx",
                    "班次內日期": "2025-06-09",
                    "班次": "日班",
                    "區域": "八期印刷",
                    "機台編號": "D-024-018",
                    "作业": "J250015565",
                    "任務": "印刷啤",
                    "工程開始時間": pd.Timestamp("2025-06-09 08:35:00"),
                    "準備結束時間": pd.Timestamp("2025-06-09 08:50:00"),
                    "工程結束時間": pd.Timestamp("2025-06-09 19:50:00"),
                    "機長姓名1": "張展鵬",
                }
            ]
        )

        self.bronze_store.write_csi_rows(csi_df)
        self.normalizer.normalize_csi_to_silver()

        conn = sqlite3.connect(self.db_path)
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(csi_job_event)").fetchall()
        }
        team_leader = conn.execute(
            "SELECT team_leader FROM csi_job_event"
        ).fetchone()[0]
        conn.close()

        self.assertIn("team_leader", columns)
        self.assertNotIn("engineer_leader", columns)
        self.assertEqual(team_leader, "張展鵬")

    def test_csi_normalization_preserves_blank_vs_zero_time_fields_and_turnover_column(self):
        csi_df = pd.DataFrame(
            [
                {
                    "source_file": "data/feb_csi.xls",
                    "班次內日期": "2026-02-25",
                    "班次": "日班",
                    "區域": "八期印刷",
                    "機台編號": "D-024-075",
                    "作业": "JOB-BLANK",
                    "物料": "MAT-BLANK",
                    "任務": "印色",
                    "工程開始時間": pd.Timestamp("2026-02-25 08:00:00"),
                    "準備結束時間": pd.Timestamp("2026-02-25 08:15:00"),
                    "工程結束時間": pd.Timestamp("2026-02-25 09:00:00"),
                    "實際生產時間": None,
                    "實際計劃停機時間": None,
                    "實際無計劃停機時間": None,
                    "心電圖轉版次數": 2,
                },
                {
                    "source_file": "data/feb_csi.xls",
                    "班次內日期": "2026-02-25",
                    "班次": "日班",
                    "區域": "八期印刷",
                    "機台編號": "D-024-080",
                    "作业": "JOB-ZERO",
                    "物料": "MAT-ZERO",
                    "任務": "印色",
                    "工程開始時間": pd.Timestamp("2026-02-25 09:00:00"),
                    "準備結束時間": pd.Timestamp("2026-02-25 09:05:00"),
                    "工程結束時間": pd.Timestamp("2026-02-25 10:00:00"),
                    "實際生產時間": 0,
                    "實際計劃停機時間": 0,
                    "實際無計劃停機時間": 0,
                    "心電圖轉版次數": 1,
                },
            ]
        )

        self.bronze_store.write_csi_rows(csi_df)
        silver_df = self.normalizer.normalize_csi_to_silver().sort_values("order_id").reset_index(drop=True)

        self.assertTrue(pd.isna(silver_df.iloc[0]["actual_prod_minutes"]))
        self.assertTrue(pd.isna(silver_df.iloc[0]["planned_stop_minutes"]))
        self.assertTrue(pd.isna(silver_df.iloc[0]["unplanned_stop_minutes"]))
        self.assertEqual(silver_df.iloc[1]["actual_prod_minutes"], 0.0)
        self.assertEqual(silver_df.iloc[1]["planned_stop_minutes"], 0.0)
        self.assertEqual(silver_df.iloc[1]["unplanned_stop_minutes"], 0.0)

    def test_mes_normalization_uses_real_june_schema_payload(self):
        mes_df = pd.DataFrame(
            [
                {
                    "source_file": "data/june_mes.xlsx",
                    "工序": "印刷",
                    "作業": "J250002960",
                    "後綴": 1,
                    "操作": 20,
                    "任務": "UV(染)",
                    "物料": "PB0002500031-05-01",
                    "報工時間": pd.Timestamp("2025-06-02 22:16:05.323000"),
                    "要求生產數量": 5252,
                    "生產數量": 5340,
                    "累計生產數量": 5340,
                    "報工類型": "ALL",
                    "設備總用時": 1.313,
                    "準備時間": 0.102,
                    "設備生產時間": 1.211,
                    "人數": 2,
                    "班次": "夜班",
                    "資源": "1035-00017",
                    "上傳CSI狀態": "NotControlPiont",
                    "狀態變更時間": pd.Timestamp("2025-06-02 22:21:51.953000"),
                    "記錄新增時間": pd.Timestamp("2025-06-02 22:16:08.933000"),
                }
            ]
        )

        self.bronze_store.write_mes_rows(mes_df)
        silver_df = self.normalizer.normalize_mes_to_silver()
        row = silver_df.iloc[0]

        self.assertEqual(row["canonical_machine_id"], "035-017")
        self.assertEqual(row["order_id"], "J250002960")
        self.assertEqual(row["suffix"], "1")
        self.assertEqual(row["operation"], "20")
        self.assertEqual(row["task_name"], "UV(染)")
        self.assertEqual(row["material_code"], "PB0002500031-05-01")
        self.assertEqual(row["required_qty"], 5252.0)
        self.assertEqual(row["reported_qty"], 5340.0)
        self.assertEqual(row["report_type"], "ALL")
        self.assertEqual(row["resource_id_raw"], "1035-00017")

    def test_maintenance_normalization_resolves_asset_and_legacy_paths(self):
        maintenance_df = pd.DataFrame(
            [
                {
                    "source_file": "data/maintenance.xlsx",
                    "交易日期": pd.Timestamp("2025-07-31 17:56:44.637000"),
                    "工單": "1802100675",
                    "工單描述": "水雞電眼",
                    "工單類型": "PM",
                    "交易類型": "發出",
                    "物料編碼": "JGAB00010079",
                    "物料描述": "萬向軸",
                    "數量": -1,
                    "資產": "1024-00094",
                    "資產父級": None,
                    "資產老編號": "024-094",
                    "資產描述": "柯式印刷機(四色)",
                    "維修班組": "M61",
                    "維修部門": "印刷部",
                },
                {
                    "source_file": "data/maintenance.xlsx",
                    "交易日期": pd.Timestamp("2025-07-31 19:45:36.900000"),
                    "工單": "1802100676",
                    "工單描述": "退回測試",
                    "工單類型": "PM",
                    "交易類型": "退回",
                    "物料編碼": "JGAB00010080",
                    "物料描述": "測試料",
                    "數量": 1,
                    "資產": None,
                    "資產父級": None,
                    "資產老編號": "024-094",
                    "資產描述": "柯式印刷機(四色)",
                    "維修班組": "M61",
                    "維修部門": "印刷部",
                },
            ]
        )

        self.bronze_store.write_maintenance_rows(maintenance_df)
        silver_df = self.normalizer.normalize_maintenance_to_silver()

        self.assertEqual(len(silver_df), 2)
        self.assertTrue((silver_df["canonical_machine_id"] == "024-094").all())
        self.assertEqual(set(silver_df["txn_type"]), {"發出", "退回"})
        self.assertEqual(set(silver_df["work_order_type"]), {"PM"})

    def test_gold_merge_readiness_contract_is_documented(self):
        contract = get_gold_merge_readiness_contract()

        self.assertIn("aggregate meter-level energy_meter_hour rows", contract["energy_backbone"])
        self.assertIn("canonical_machine_id x hour_ts", contract["energy_backbone"])
        self.assertIn("production and setup-window", contract["csi_role"])
        self.assertIn("manpower", contract["mes_role"])
        self.assertIn("recency", contract["maintenance_role"])

    def test_traceability_contract_uses_source_row_hash_for_bronze_rejoin(self):
        contract = get_silver_bronze_traceability_contract()

        self.assertEqual(
            contract["energy_meter_hour"],
            {"bronze_table": "raw_energy_hourly", "join_key": "source_row_hash"},
        )
        self.assertEqual(
            contract["csi_job_event"],
            {"bronze_table": "raw_csi_event", "join_key": "source_row_hash"},
        )
        self.assertEqual(
            contract["mes_report_event"],
            {"bronze_table": "raw_mes_report", "join_key": "source_row_hash"},
        )
        self.assertEqual(
            contract["maintenance_txn_event"],
            {"bronze_table": "raw_maintenance_txn", "join_key": "source_row_hash"},
        )

    def test_silver_tables_are_created(self):
        conn = sqlite3.connect(self.db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        self.assertTrue(
            {
                "energy_meter_hour",
                "csi_job_event",
                "mes_report_event",
                "maintenance_txn_event",
            }.issubset(tables)
        )


if __name__ == "__main__":
    unittest.main()
