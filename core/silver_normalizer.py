"""Silver normalization helpers built on top of the Bronze raw tables.

Silver stays source-specific by design. The next merge stage should use:
- an aggregated machine-hour projection derived from `energy_meter_hour` as the
  canonical `canonical_machine_id x hour_ts` Gold backbone
- `csi_job_event` for production and setup-window evidence
- `mes_report_event` for manpower / report context and fallback prep signals
- `maintenance_txn_event` for recency / count / context, not exact downtime labels
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

import pandas as pd

from core.machine_alias_registry import MachineAliasRegistry, get_default_machine_alias_registry
from core.runtime_paths import get_database_path
from core.source_family_registry import get_source_family_contract


_ENERGY_SUMMARY_TOKEN = "合計用量"
_ENERGY_MACHINE_ID_RE = re.compile(r"(?:D-)?\d{3,4}\s*-\s*\d{3,5}")
_ENERGY_SENTINEL_ANOMALY_LABEL = "1024-10032/024-147印刷機UV"
_ENERGY_SENTINEL_ANOMALY_START = pd.Timestamp("2025-08-17 08:00:00")
_ENERGY_SENTINEL_ANOMALY_END = pd.Timestamp("2025-08-17 17:00:00")
_ENERGY_SENTINEL_ANOMALY_VALUE = 99999999.9999
_ENERGY_PARTIAL_METER_RULES = {
    ("2025-10", "印刷机024-094"): "localized_partial_meter_month",
    ("2025-10", "印刷機1024-10006（UV）"): "localized_partial_meter_month",
    ("2025-10", "印刷機1024-10006（主機）"): "localized_partial_meter_month",
    ("2025-10", "印刷機1024-10006（馬達）"): "localized_partial_meter_month",
    ("2025-10", "印刷機024-082風泵用電(測量)"): "localized_partial_meter_month",
    ("2025-11", "印刷機1024-10009（IR+UV）"): "localized_partial_meter_month",
    ("2026-01", "印刷機024-010"): "localized_partial_meter_month",
    ("2026-01", "印刷機024-075 UV"): "localized_partial_meter_month",
    ("2026-01", "印刷機024-075主機"): "localized_partial_meter_month",
    ("2026-01", "印刷機024-080主機"): "localized_partial_meter_month",
    ("2026-02", "印刷機024-080 UV"): "localized_partial_meter_month",
}


def get_gold_merge_readiness_contract() -> dict[str, str]:
    return {
        "energy_backbone": (
            "Gold must aggregate meter-level energy_meter_hour rows into a machine-hour "
            "projection keyed by canonical_machine_id x hour_ts"
        ),
        "csi_role": "csi_job_event defines production and setup-window evidence",
        "mes_role": "mes_report_event enriches manpower, report context, and fallback prep signals",
        "maintenance_role": "maintenance_txn_event provides recency, count, and context instead of exact downtime labels",
    }


def get_silver_bronze_traceability_contract() -> dict[str, dict[str, str]]:
    return {
        "energy_meter_hour": {"bronze_table": "raw_energy_hourly", "join_key": "source_row_hash"},
        "csi_job_event": {"bronze_table": "raw_csi_event", "join_key": "source_row_hash"},
        "mes_report_event": {"bronze_table": "raw_mes_report", "join_key": "source_row_hash"},
        "maintenance_txn_event": {"bronze_table": "raw_maintenance_txn", "join_key": "source_row_hash"},
    }


class SilverNormalizer:
    def __init__(
        self,
        db_path: str | Path | None = None,
        registry: MachineAliasRegistry | None = None,
    ):
        self.db_path = str(db_path or get_database_path())
        self.registry = registry or get_default_machine_alias_registry()
        self.ensure_tables()

    def ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS energy_meter_hour (
                source_row_hash TEXT PRIMARY KEY,
                canonical_machine_id TEXT,
                meter_label TEXT,
                meter_component TEXT,
                meter_is_aggregate INTEGER,
                hour_ts TEXT,
                kwh REAL,
                cost REAL,
                source_file TEXT,
                parse_confidence TEXT,
                raw_machine_id_or_label TEXT,
                quality_status TEXT,
                quality_flags_json TEXT
            )
            """
        )
        self._ensure_table_columns(
            cursor,
            "energy_meter_hour",
            {
                "quality_status": "TEXT",
                "quality_flags_json": "TEXT",
            },
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS csi_job_event (
                source_row_hash TEXT PRIMARY KEY,
                canonical_machine_id TEXT,
                shift_date TEXT,
                shift_name TEXT,
                csi_area TEXT,
                order_id TEXT,
                suffix TEXT,
                operation TEXT,
                material_code TEXT,
                task_name TEXT,
                prod_start_ts TEXT,
                prep_end_ts TEXT,
                prod_end_ts TEXT,
                good_qty REAL,
                scrap_qty REAL,
                cumulative_qty REAL,
                actual_run_minutes REAL,
                actual_prod_minutes REAL,
                actual_speed_per_hour REAL,
                actual_changeover_minutes REAL,
                planned_stop_minutes REAL,
                unplanned_stop_minutes REAL,
                stop_reason TEXT,
                stop_count INTEGER,
                team_leader TEXT,
                team_members_raw TEXT,
                source_file TEXT,
                raw_machine_id_or_label TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mes_report_event (
                source_row_hash TEXT PRIMARY KEY,
                canonical_machine_id TEXT,
                report_ts TEXT,
                order_id TEXT,
                suffix TEXT,
                operation TEXT,
                task_name TEXT,
                material_code TEXT,
                required_qty REAL,
                reported_qty REAL,
                cumulative_qty REAL,
                report_type TEXT,
                equipment_total_hours REAL,
                prep_hours REAL,
                equipment_prod_hours REAL,
                manpower REAL,
                shift_name TEXT,
                resource_id_raw TEXT,
                csi_upload_status TEXT,
                status_changed_ts TEXT,
                record_created_ts TEXT,
                source_file TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_txn_event (
                source_row_hash TEXT PRIMARY KEY,
                canonical_machine_id TEXT,
                txn_ts TEXT,
                work_order_id TEXT,
                work_order_desc TEXT,
                work_order_type TEXT,
                txn_type TEXT,
                item_code TEXT,
                item_desc TEXT,
                quantity REAL,
                asset_id TEXT,
                asset_legacy_id TEXT,
                asset_parent_id TEXT,
                asset_desc TEXT,
                maint_team TEXT,
                maint_department TEXT,
                source_file TEXT
            )
            """
        )

        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_table_columns(cursor, table_name: str, columns: dict[str, str]) -> None:
        existing_columns = {
            row[1]
            for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def normalize_energy_to_silver(self) -> pd.DataFrame:
        contract = get_source_family_contract("energy_hourly_report_v1")
        if contract.status != "supported":
            raise ValueError("Hourly energy source family is not enabled for Silver normalization")

        bronze_df = self._read_bronze_table("raw_energy_hourly")
        silver_rows = self._normalize_energy_rows(bronze_df)

        self._replace_table("energy_meter_hour", silver_rows)
        return pd.DataFrame(silver_rows)

    def normalize_csi_to_silver(self) -> pd.DataFrame:
        contract = get_source_family_contract("csi_monthly_xlsx_v1")
        if contract.status != "supported":
            raise ValueError("CSI xlsx source family is not enabled for Silver normalization")

        bronze_df = self._read_bronze_table("raw_csi_event")
        silver_rows = self._normalize_csi_rows(bronze_df)

        self._replace_table("csi_job_event", silver_rows)
        return pd.DataFrame(silver_rows)

    def normalize_mes_to_silver(self) -> pd.DataFrame:
        contract = get_source_family_contract("mes_monthly_report_v1")
        if contract.status != "supported":
            raise ValueError("MES source family is not enabled for Silver normalization")

        bronze_df = self._read_bronze_table("raw_mes_report")
        silver_rows = self._normalize_mes_rows(bronze_df)

        self._replace_table("mes_report_event", silver_rows)
        return pd.DataFrame(silver_rows)

    def normalize_maintenance_to_silver(self) -> pd.DataFrame:
        contract = get_source_family_contract("maintenance_transaction_v1")
        if contract.status != "supported":
            raise ValueError("Maintenance source family is not enabled for Silver normalization")

        bronze_df = self._read_bronze_table("raw_maintenance_txn")
        silver_rows = self._normalize_maintenance_rows(bronze_df)

        self._replace_table("maintenance_txn_event", silver_rows)
        return pd.DataFrame(silver_rows)

    def _normalize_energy_rows(self, bronze_df: pd.DataFrame) -> list[dict[str, object]]:
        if bronze_df.empty:
            return []

        working_df = bronze_df.copy()
        working_df["raw_label_clean"] = working_df["raw_machine_id_or_label"].map(self._clean_text)
        working_df = working_df[
            ~working_df["raw_label_clean"].map(self._is_energy_summary_label).fillna(False)
        ].copy()
        if working_df.empty:
            return []

        parsed_ts = pd.to_datetime(working_df["raw_timestamp"], errors="coerce")
        valid_timestamp_mask = (
            parsed_ts.notna()
            & (parsed_ts.dt.minute == 0)
            & (parsed_ts.dt.second == 0)
            & (parsed_ts.dt.microsecond == 0)
            & (parsed_ts.dt.nanosecond == 0)
        )
        working_df = working_df.loc[valid_timestamp_mask].copy()
        if working_df.empty:
            return []
        parsed_ts = parsed_ts.loc[working_df.index]

        working_df["hour_ts_clean"] = parsed_ts.dt.strftime("%Y-%m-%dT%H:%M:%S")
        working_df["month_key_clean"] = parsed_ts.dt.strftime("%Y-%m")
        working_df["raw_kwh_num"] = pd.to_numeric(working_df["raw_kwh"], errors="coerce")
        working_df["raw_cost_num"] = pd.to_numeric(working_df["raw_cost"], errors="coerce")

        sentinel_mask = (
            (working_df["raw_label_clean"] == _ENERGY_SENTINEL_ANOMALY_LABEL)
            & (working_df["raw_kwh_num"] == _ENERGY_SENTINEL_ANOMALY_VALUE)
            & (working_df["raw_cost_num"] == _ENERGY_SENTINEL_ANOMALY_VALUE)
            & (parsed_ts >= _ENERGY_SENTINEL_ANOMALY_START)
            & (parsed_ts <= _ENERGY_SENTINEL_ANOMALY_END)
        )
        working_df = working_df.loc[~sentinel_mask].copy()
        if working_df.empty:
            return []

        working_df["quality_status"] = "ok"
        working_df["quality_flags_json"] = None
        partial_flags = pd.Series(
            (
                _ENERGY_PARTIAL_METER_RULES.get((month_key, raw_label))
                for month_key, raw_label in zip(
                    working_df["month_key_clean"],
                    working_df["raw_label_clean"],
                )
            ),
            index=working_df.index,
        )
        flagged_mask = partial_flags.notna()
        if flagged_mask.any():
            working_df.loc[flagged_mask, "quality_status"] = "flagged_partial"
            working_df.loc[flagged_mask, "quality_flags_json"] = [
                json.dumps(
                    {
                        quality_flag: True,
                        "flagged_month": month_key,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                for month_key, quality_flag in zip(
                    working_df.loc[flagged_mask, "month_key_clean"],
                    partial_flags.loc[flagged_mask],
                )
            ]

        silver_rows = []
        parse_cache = {
            raw_label: self._parse_energy_meter(raw_label)
            for raw_label in working_df["raw_label_clean"].drop_duplicates().tolist()
        }
        canonical_cache: dict[tuple[str, str | None], str | None] = {}
        working_df["bronze_canonical_clean"] = working_df["canonical_machine_id"].map(self._clean_text)
        unique_canonical_pairs = working_df[
            ["raw_label_clean", "bronze_canonical_clean"]
        ].drop_duplicates()
        for raw_label, bronze_canonical in unique_canonical_pairs.itertuples(index=False, name=None):
            canonical_cache[(raw_label, bronze_canonical)] = self._resolve_canonical_machine_id(
                raw_value=raw_label,
                source_system="energy",
                bronze_canonical=bronze_canonical,
            )

        for row in working_df.itertuples(index=False):
            raw_label = row.raw_label_clean
            energy_parse = parse_cache[raw_label]
            canonical_machine_id = canonical_cache[(raw_label, row.bronze_canonical_clean)]
            silver_rows.append(
                {
                    "source_row_hash": row.source_row_hash,
                    "canonical_machine_id": canonical_machine_id,
                    "meter_label": energy_parse["meter_label"],
                    "meter_component": energy_parse["meter_component"],
                    "meter_is_aggregate": energy_parse["meter_is_aggregate"],
                    "hour_ts": row.hour_ts_clean,
                    "kwh": self._float_or_none(row.raw_kwh_num),
                    "cost": self._float_or_none(row.raw_cost_num),
                    "source_file": self._clean_text(row.source_file),
                    "parse_confidence": self._energy_parse_confidence(
                        energy_parse["meter_component"],
                        canonical_machine_id,
                    ),
                    "raw_machine_id_or_label": raw_label,
                    "quality_status": row.quality_status,
                    "quality_flags_json": row.quality_flags_json,
                }
            )
        return silver_rows

    def _normalize_csi_rows(self, bronze_df: pd.DataFrame) -> list[dict[str, object]]:
        if bronze_df.empty:
            return []
        if "raw_payload_json" not in bronze_df.columns:
            return self._normalize_csi_rows_fast(bronze_df)

        silver_rows = []
        canonical_cache: dict[tuple[object, str | None], str | None] = {}
        for row in bronze_df.itertuples(index=False):
            payload = self._load_payload(self._row_value(row, "raw_payload_json"))
            raw_machine = self._payload_or_row(payload, row, "機台編號", "raw_machine_id_or_label")
            team_members = [
                self._clean_text(self._payload_or_row(payload, row, "機長姓名2")),
                self._clean_text(self._payload_or_row(payload, row, "機組人員姓名1")),
                self._clean_text(self._payload_or_row(payload, row, "機組人員姓名2")),
                self._clean_text(self._payload_or_row(payload, row, "機組人員姓名3")),
                self._clean_text(self._payload_or_row(payload, row, "機組人員姓名4")),
            ]
            bronze_canonical = self._clean_text(self._row_value(row, "canonical_machine_id"))
            canonical_key = (raw_machine, bronze_canonical)
            if canonical_key not in canonical_cache:
                canonical_cache[canonical_key] = self._resolve_canonical_machine_id(
                    raw_value=raw_machine,
                    source_system="csi",
                    bronze_canonical=bronze_canonical,
                )
            silver_rows.append(
                {
                    "source_row_hash": self._row_value(row, "source_row_hash"),
                    "canonical_machine_id": canonical_cache[canonical_key],
                    "shift_date": self._stringify_date(self._payload_or_row(payload, row, "班次內日期")),
                    "shift_name": self._clean_text(self._payload_or_row(payload, row, "班次")),
                    "csi_area": self._clean_text(self._payload_or_row(payload, row, "區域")),
                    "order_id": self._clean_text(self._payload_or_row(payload, row, "作业", "raw_order_id")),
                    "suffix": self._clean_text(self._payload_or_row(payload, row, "作业后缀")),
                    "operation": self._clean_text(self._payload_or_row(payload, row, "操作")),
                    "material_code": self._clean_text(self._payload_or_row(payload, row, "物料", "raw_material")),
                    "task_name": self._clean_text(self._payload_or_row(payload, row, "任務")),
                    "prod_start_ts": self._stringify_datetime(self._payload_or_row(payload, row, "工程開始時間", "raw_start_time")),
                    "prep_end_ts": self._stringify_datetime(self._payload_or_row(payload, row, "準備結束時間", "raw_prep_end_time")),
                    "prod_end_ts": self._stringify_datetime(self._payload_or_row(payload, row, "工程結束時間", "raw_end_time")),
                    "good_qty": self._float_or_none(self._payload_or_row(payload, row, "正品數量", "raw_good_qty")),
                    "scrap_qty": self._float_or_none(self._payload_or_row(payload, row, "廢品數量", "raw_scrap_qty")),
                    "cumulative_qty": self._float_or_none(self._payload_or_row(payload, row, "纍計數量")),
                    "actual_run_minutes": self._float_or_none(self._payload_or_row(payload, row, "心電圖整體運作時間")),
                    "actual_prod_minutes": self._float_or_none(self._payload_or_row(payload, row, "實際生產時間")),
                    "actual_speed_per_hour": self._float_or_none(self._payload_or_row(payload, row, "實際速度_本_時")),
                    "actual_changeover_minutes": self._float_or_none(self._payload_or_row(payload, row, "心電圖實際轉版時間")),
                    "planned_stop_minutes": self._float_or_none(self._payload_or_row(payload, row, "實際計劃停機時間")),
                    "unplanned_stop_minutes": self._float_or_none(self._payload_or_row(payload, row, "實際無計劃停機時間")),
                    "stop_reason": self._clean_text(self._payload_or_row(payload, row, "停機原因")),
                    "stop_count": self._int_or_none(self._payload_or_row(payload, row, "運作中途總停機次數")),
                    "team_leader": self._clean_text(self._payload_or_row(payload, row, "機長姓名1")),
                    "team_members_raw": self._json_list([member for member in team_members if member]),
                    "source_file": self._clean_text(self._row_value(row, "source_file")),
                    "raw_machine_id_or_label": self._clean_text(raw_machine),
                }
            )
        return silver_rows

    def _normalize_mes_rows(self, bronze_df: pd.DataFrame) -> list[dict[str, object]]:
        if bronze_df.empty:
            return []
        if "raw_payload_json" not in bronze_df.columns:
            return self._normalize_mes_rows_fast(bronze_df)

        silver_rows = []
        canonical_cache: dict[tuple[object, str | None], str | None] = {}
        for row in bronze_df.itertuples(index=False):
            payload = self._load_payload(self._row_value(row, "raw_payload_json"))
            resource_id_raw = self._payload_or_row(payload, row, "資源", "resource", "raw_machine_id_or_label")
            bronze_canonical = self._clean_text(self._row_value(row, "canonical_machine_id"))
            canonical_key = (resource_id_raw, bronze_canonical)
            if canonical_key not in canonical_cache:
                canonical_cache[canonical_key] = self._resolve_canonical_machine_id(
                    raw_value=resource_id_raw,
                    source_system="mes",
                    bronze_canonical=bronze_canonical,
                )
            silver_rows.append(
                {
                    "source_row_hash": self._row_value(row, "source_row_hash"),
                    "canonical_machine_id": canonical_cache[canonical_key],
                    "report_ts": self._stringify_datetime(self._payload_or_row(payload, row, "報工時間")),
                    "order_id": self._clean_text(self._payload_or_row(payload, row, "作業")),
                    "suffix": self._clean_text(self._payload_or_row(payload, row, "後綴")),
                    "operation": self._clean_text(self._payload_or_row(payload, row, "操作")),
                    "task_name": self._clean_text(self._payload_or_row(payload, row, "任務", "raw_task")),
                    "material_code": self._clean_text(self._payload_or_row(payload, row, "物料", "raw_material_code")),
                    "required_qty": self._float_or_none(self._payload_or_row(payload, row, "要求生產數量")),
                    "reported_qty": self._float_or_none(self._payload_or_row(payload, row, "生產數量")),
                    "cumulative_qty": self._float_or_none(self._payload_or_row(payload, row, "累計生產數量")),
                    "report_type": self._clean_text(self._payload_or_row(payload, row, "報工類型")),
                    "equipment_total_hours": self._float_or_none(self._payload_or_row(payload, row, "設備總用時")),
                    "prep_hours": self._float_or_none(self._payload_or_row(payload, row, "準備時間")),
                    "equipment_prod_hours": self._float_or_none(self._payload_or_row(payload, row, "設備生產時間")),
                    "manpower": self._float_or_none(self._payload_or_row(payload, row, "人數")),
                    "shift_name": self._clean_text(self._payload_or_row(payload, row, "班次")),
                    "resource_id_raw": self._clean_text(resource_id_raw),
                    "csi_upload_status": self._clean_text(self._payload_or_row(payload, row, "上傳CSI狀態")),
                    "status_changed_ts": self._stringify_datetime(self._payload_or_row(payload, row, "狀態變更時間")),
                    "record_created_ts": self._stringify_datetime(self._payload_or_row(payload, row, "記錄新增時間")),
                    "source_file": self._clean_text(self._row_value(row, "source_file")),
                }
            )
        return silver_rows

    def _normalize_maintenance_rows(self, bronze_df: pd.DataFrame) -> list[dict[str, object]]:
        if bronze_df.empty:
            return []

        silver_rows = []
        canonical_cache: dict[tuple[object, str | None], str | None] = {}
        fallback_cache: dict[tuple[object, str | None], str | None] = {}
        for row in bronze_df.itertuples(index=False):
            payload = self._load_payload(self._row_value(row, "raw_payload_json"))
            asset_id = self._payload_or_row(payload, row, "資產", "raw_asset_id")
            asset_legacy_id = self._payload_or_row(payload, row, "資產老編號", "raw_asset_old_id")
            bronze_canonical = self._clean_text(self._row_value(row, "canonical_machine_id"))
            canonical_key = (asset_id, bronze_canonical)
            if canonical_key not in canonical_cache:
                canonical_cache[canonical_key] = self._resolve_canonical_machine_id(
                    raw_value=asset_id,
                    source_system="maintenance",
                    bronze_canonical=bronze_canonical,
                )
            canonical_machine_id = canonical_cache[canonical_key]
            if canonical_machine_id is None:
                fallback_key = (asset_legacy_id, None)
                if fallback_key not in fallback_cache:
                    fallback_cache[fallback_key] = self._resolve_canonical_machine_id(
                        raw_value=asset_legacy_id,
                        source_system="maintenance",
                        bronze_canonical=None,
                    )
                canonical_machine_id = fallback_cache[fallback_key]

            silver_rows.append(
                {
                    "source_row_hash": self._row_value(row, "source_row_hash"),
                    "canonical_machine_id": canonical_machine_id,
                    "txn_ts": self._stringify_datetime(self._payload_or_row(payload, row, "交易日期", "raw_transaction_date")),
                    "work_order_id": self._clean_text(self._payload_or_row(payload, row, "工單", "raw_work_order")),
                    "work_order_desc": self._clean_text(self._payload_or_row(payload, row, "工單描述", "工單說明")),
                    "work_order_type": self._clean_text(self._payload_or_row(payload, row, "工單類型", "raw_work_order_type")),
                    "txn_type": self._clean_text(self._payload_or_row(payload, row, "交易類型", "raw_transaction_type")),
                    "item_code": self._clean_text(self._payload_or_row(payload, row, "物料編碼", "raw_material_code")),
                    "item_desc": self._clean_text(self._payload_or_row(payload, row, "物料描述")),
                    "quantity": self._float_or_none(self._payload_or_row(payload, row, "數量", "raw_quantity")),
                    "asset_id": self._clean_text(asset_id),
                    "asset_legacy_id": self._clean_text(asset_legacy_id),
                    "asset_parent_id": self._clean_text(self._payload_or_row(payload, row, "資產父級")),
                    "asset_desc": self._clean_text(self._payload_or_row(payload, row, "資產描述")),
                    "maint_team": self._clean_text(self._payload_or_row(payload, row, "維修班組")),
                    "maint_department": self._clean_text(self._payload_or_row(payload, row, "維修部門")),
                    "source_file": self._clean_text(self._row_value(row, "source_file")),
                }
            )
        return silver_rows

    def _normalize_csi_rows_fast(self, bronze_df: pd.DataFrame) -> list[dict[str, object]]:
        working_df = bronze_df.copy()
        working_df["raw_machine_clean"] = working_df["機台編號"].where(
            working_df["機台編號"].map(self._has_value),
            working_df["raw_machine_id_or_label"],
        ).map(self._clean_text)
        working_df["bronze_canonical_clean"] = working_df["canonical_machine_id"].map(self._clean_text)
        working_df["shift_date_clean"] = self._stringify_date_series(working_df["班次內日期"])
        working_df["shift_name_clean"] = working_df["班次"].map(self._clean_text)
        working_df["csi_area_clean"] = working_df["區域"].map(self._clean_text)
        working_df["order_id_clean"] = working_df["作业"].where(
            working_df["作业"].map(self._has_value),
            working_df["raw_order_id"],
        ).map(self._clean_text)
        working_df["suffix_clean"] = working_df["作业后缀"].map(self._clean_text)
        working_df["operation_clean"] = working_df["操作"].map(self._clean_text)
        working_df["material_code_clean"] = working_df["物料"].where(
            working_df["物料"].map(self._has_value),
            working_df["raw_material"],
        ).map(self._clean_text)
        working_df["task_name_clean"] = working_df["任務"].map(self._clean_text)
        working_df["prod_start_ts_clean"] = self._stringify_datetime_series(
            working_df["工程開始時間"].where(
                working_df["工程開始時間"].map(self._has_value),
                working_df["raw_start_time"],
            )
        )
        working_df["prep_end_ts_clean"] = self._stringify_datetime_series(
            working_df["準備結束時間"].where(
                working_df["準備結束時間"].map(self._has_value),
                working_df["raw_prep_end_time"],
            )
        )
        working_df["prod_end_ts_clean"] = self._stringify_datetime_series(
            working_df["工程結束時間"].where(
                working_df["工程結束時間"].map(self._has_value),
                working_df["raw_end_time"],
            )
        )
        working_df["good_qty_num"] = pd.to_numeric(
            working_df["正品數量"].where(
                working_df["正品數量"].map(self._has_value),
                working_df["raw_good_qty"],
            ),
            errors="coerce",
        )
        working_df["scrap_qty_num"] = pd.to_numeric(
            working_df["廢品數量"].where(
                working_df["廢品數量"].map(self._has_value),
                working_df["raw_scrap_qty"],
            ),
            errors="coerce",
        )
        working_df["cumulative_qty_num"] = pd.to_numeric(working_df["纍計數量"], errors="coerce")
        working_df["actual_run_minutes_num"] = pd.to_numeric(working_df["心電圖整體運作時間"], errors="coerce")
        working_df["actual_prod_minutes_num"] = pd.to_numeric(working_df["實際生產時間"], errors="coerce")
        working_df["actual_speed_per_hour_num"] = pd.to_numeric(working_df["實際速度_本_時"], errors="coerce")
        working_df["actual_changeover_minutes_num"] = pd.to_numeric(
            working_df["心電圖實際轉版時間"],
            errors="coerce",
        )
        working_df["planned_stop_minutes_num"] = pd.to_numeric(
            working_df["實際計劃停機時間"],
            errors="coerce",
        )
        working_df["unplanned_stop_minutes_num"] = pd.to_numeric(
            working_df["實際無計劃停機時間"],
            errors="coerce",
        )
        working_df["stop_reason_clean"] = working_df["停機原因"].map(self._clean_text)
        working_df["stop_count_num"] = pd.to_numeric(working_df["運作中途總停機次數"], errors="coerce")
        working_df["team_leader_clean"] = working_df["機長姓名1"].map(self._clean_text)
        working_df["team_leader_2_clean"] = working_df["機長姓名2"].map(self._clean_text)
        working_df["team_member_1_clean"] = working_df["機組人員姓名1"].map(self._clean_text)
        working_df["team_member_2_clean"] = working_df["機組人員姓名2"].map(self._clean_text)
        working_df["team_member_3_clean"] = working_df["機組人員姓名3"].map(self._clean_text)
        working_df["team_member_4_clean"] = working_df["機組人員姓名4"].map(self._clean_text)
        working_df["source_file_clean"] = working_df["source_file"].map(self._clean_text)

        canonical_cache: dict[tuple[str | None, str | None], str | None] = {}
        for raw_machine, bronze_canonical in working_df[
            ["raw_machine_clean", "bronze_canonical_clean"]
        ].drop_duplicates().itertuples(index=False, name=None):
            canonical_cache[(raw_machine, bronze_canonical)] = self._resolve_canonical_machine_id(
                raw_value=raw_machine,
                source_system="csi",
                bronze_canonical=bronze_canonical,
            )

        silver_rows = []
        for row in working_df.itertuples(index=False):
            team_members = [
                row.team_leader_2_clean,
                row.team_member_1_clean,
                row.team_member_2_clean,
                row.team_member_3_clean,
                row.team_member_4_clean,
            ]
            silver_rows.append(
                {
                    "source_row_hash": row.source_row_hash,
                    "canonical_machine_id": canonical_cache[(row.raw_machine_clean, row.bronze_canonical_clean)],
                    "shift_date": row.shift_date_clean,
                    "shift_name": row.shift_name_clean,
                    "csi_area": row.csi_area_clean,
                    "order_id": row.order_id_clean,
                    "suffix": row.suffix_clean,
                    "operation": row.operation_clean,
                    "material_code": row.material_code_clean,
                    "task_name": row.task_name_clean,
                    "prod_start_ts": row.prod_start_ts_clean,
                    "prep_end_ts": row.prep_end_ts_clean,
                    "prod_end_ts": row.prod_end_ts_clean,
                    "good_qty": self._float_or_none(row.good_qty_num),
                    "scrap_qty": self._float_or_none(row.scrap_qty_num),
                    "cumulative_qty": self._float_or_none(row.cumulative_qty_num),
                    "actual_run_minutes": self._float_or_none(row.actual_run_minutes_num),
                    "actual_prod_minutes": self._float_or_none(row.actual_prod_minutes_num),
                    "actual_speed_per_hour": self._float_or_none(row.actual_speed_per_hour_num),
                    "actual_changeover_minutes": self._float_or_none(row.actual_changeover_minutes_num),
                    "planned_stop_minutes": self._float_or_none(row.planned_stop_minutes_num),
                    "unplanned_stop_minutes": self._float_or_none(row.unplanned_stop_minutes_num),
                    "stop_reason": row.stop_reason_clean,
                    "stop_count": self._int_or_none(row.stop_count_num),
                    "team_leader": row.team_leader_clean,
                    "team_members_raw": self._json_list([member for member in team_members if member]),
                    "source_file": row.source_file_clean,
                    "raw_machine_id_or_label": row.raw_machine_clean,
                }
            )
        return silver_rows

    def _normalize_mes_rows_fast(self, bronze_df: pd.DataFrame) -> list[dict[str, object]]:
        working_df = bronze_df.copy()
        working_df["resource_id_raw_clean"] = working_df["資源"].where(
            working_df["資源"].map(self._has_value),
            working_df["raw_machine_id_or_label"],
        ).map(self._clean_text)
        working_df["bronze_canonical_clean"] = working_df["canonical_machine_id"].map(self._clean_text)
        working_df["report_ts_clean"] = self._stringify_datetime_series(working_df["報工時間"])
        working_df["order_id_clean"] = working_df["作業"].map(self._clean_text)
        working_df["suffix_clean"] = working_df["後綴"].map(self._clean_text)
        working_df["operation_clean"] = working_df["操作"].map(self._clean_text)
        working_df["task_name_clean"] = working_df["任務"].where(
            working_df["任務"].map(self._has_value),
            working_df["raw_task"],
        ).map(self._clean_text)
        working_df["material_code_clean"] = working_df["物料"].where(
            working_df["物料"].map(self._has_value),
            working_df["raw_material_code"],
        ).map(self._clean_text)
        working_df["required_qty_num"] = pd.to_numeric(working_df["要求生產數量"], errors="coerce")
        working_df["reported_qty_num"] = pd.to_numeric(working_df["生產數量"], errors="coerce")
        working_df["cumulative_qty_num"] = pd.to_numeric(working_df["累計生產數量"], errors="coerce")
        working_df["report_type_clean"] = working_df["報工類型"].map(self._clean_text)
        working_df["equipment_total_hours_num"] = pd.to_numeric(working_df["設備總用時"], errors="coerce")
        working_df["prep_hours_num"] = pd.to_numeric(working_df["準備時間"], errors="coerce")
        working_df["equipment_prod_hours_num"] = pd.to_numeric(working_df["設備生產時間"], errors="coerce")
        working_df["manpower_num"] = pd.to_numeric(working_df["人數"], errors="coerce")
        working_df["shift_name_clean"] = working_df["班次"].map(self._clean_text)
        working_df["csi_upload_status_clean"] = working_df["上傳CSI狀態"].map(self._clean_text)
        working_df["status_changed_ts_clean"] = self._stringify_datetime_series(working_df["狀態變更時間"])
        working_df["record_created_ts_clean"] = self._stringify_datetime_series(working_df["記錄新增時間"])
        working_df["source_file_clean"] = working_df["source_file"].map(self._clean_text)

        canonical_cache: dict[tuple[str | None, str | None], str | None] = {}
        for resource_id_raw, bronze_canonical in working_df[
            ["resource_id_raw_clean", "bronze_canonical_clean"]
        ].drop_duplicates().itertuples(index=False, name=None):
            canonical_cache[(resource_id_raw, bronze_canonical)] = self._resolve_canonical_machine_id(
                raw_value=resource_id_raw,
                source_system="mes",
                bronze_canonical=bronze_canonical,
            )

        silver_rows = []
        for row in working_df.itertuples(index=False):
            silver_rows.append(
                {
                    "source_row_hash": row.source_row_hash,
                    "canonical_machine_id": canonical_cache[(row.resource_id_raw_clean, row.bronze_canonical_clean)],
                    "report_ts": row.report_ts_clean,
                    "order_id": row.order_id_clean,
                    "suffix": row.suffix_clean,
                    "operation": row.operation_clean,
                    "task_name": row.task_name_clean,
                    "material_code": row.material_code_clean,
                    "required_qty": self._float_or_none(row.required_qty_num),
                    "reported_qty": self._float_or_none(row.reported_qty_num),
                    "cumulative_qty": self._float_or_none(row.cumulative_qty_num),
                    "report_type": row.report_type_clean,
                    "equipment_total_hours": self._float_or_none(row.equipment_total_hours_num),
                    "prep_hours": self._float_or_none(row.prep_hours_num),
                    "equipment_prod_hours": self._float_or_none(row.equipment_prod_hours_num),
                    "manpower": self._float_or_none(row.manpower_num),
                    "shift_name": row.shift_name_clean,
                    "resource_id_raw": row.resource_id_raw_clean,
                    "csi_upload_status": row.csi_upload_status_clean,
                    "status_changed_ts": row.status_changed_ts_clean,
                    "record_created_ts": row.record_created_ts_clean,
                    "source_file": row.source_file_clean,
                }
            )
        return silver_rows

    def normalize_all(self) -> dict[str, pd.DataFrame]:
        return {
            "energy_meter_hour": self.normalize_energy_to_silver(),
            "csi_job_event": self.normalize_csi_to_silver(),
            "mes_report_event": self.normalize_mes_to_silver(),
            "maintenance_txn_event": self.normalize_maintenance_to_silver(),
        }

    def _read_bronze_table(self, table_name: str) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        finally:
            conn.close()

    def _replace_table(self, table_name: str, rows: Iterable[dict[str, object]]) -> None:
        rows = list(rows)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name}")
        if rows:
            columns = list(rows[0].keys())
            placeholders = ", ".join("?" for _ in columns)
            column_list = ", ".join(columns)
            cursor.executemany(
                f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})",
                [tuple(row[column] for column in columns) for row in rows],
            )
        conn.commit()
        conn.close()

    def _resolve_canonical_machine_id(
        self,
        raw_value: object,
        source_system: str,
        bronze_canonical: object,
    ) -> str | None:
        cleaned_bronze = self._clean_text(bronze_canonical)
        if cleaned_bronze:
            return cleaned_bronze

        resolution = self.registry.resolve_canonical_machine_id(raw_value, source_system=source_system)
        return self._clean_text(resolution.get("canonical_machine_id"))

    @classmethod
    def _load_payload(cls, raw_payload_json: object) -> dict[str, object]:
        cleaned_payload = cls._clean_text(raw_payload_json)
        if not cleaned_payload:
            return {}
        try:
            parsed = json.loads(cleaned_payload)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @classmethod
    def _row_value(cls, row: object, key: str) -> object:
        if isinstance(row, dict):
            return row.get(key)
        return getattr(row, key, None)

    @classmethod
    def _payload_or_row(cls, payload: dict[str, object], row: object, *keys: str) -> object:
        for key in keys:
            if key in payload and cls._has_value(payload.get(key)):
                return payload.get(key)
            row_value = cls._row_value(row, key)
            if cls._has_value(row_value):
                return row_value
        return None

    @classmethod
    def _stringify_date_series(cls, values: pd.Series) -> pd.Series:
        parsed = pd.to_datetime(values, errors="coerce")
        result = pd.Series(index=values.index, dtype=object)
        valid_mask = parsed.notna()
        if valid_mask.any():
            result.loc[valid_mask] = parsed.loc[valid_mask].dt.strftime("%Y-%m-%d")
        if (~valid_mask).any():
            result.loc[~valid_mask] = values.loc[~valid_mask].map(cls._clean_text)
        return result

    @classmethod
    def _stringify_datetime_series(cls, values: pd.Series) -> pd.Series:
        parsed = pd.to_datetime(values, errors="coerce")
        result = pd.Series(index=values.index, dtype=object)
        valid_mask = parsed.notna()
        if valid_mask.any():
            result.loc[valid_mask] = parsed.loc[valid_mask].map(lambda value: value.isoformat())
        if (~valid_mask).any():
            result.loc[~valid_mask] = values.loc[~valid_mask].map(cls._clean_text)
        return result

    @staticmethod
    def _normalize_energy_label(raw_label: object) -> str:
        normalized = unicodedata.normalize("NFKC", str(raw_label or ""))
        normalized = normalized.replace("\u3000", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @classmethod
    def _is_energy_summary_label(cls, raw_label: object) -> bool:
        return _ENERGY_SUMMARY_TOKEN in cls._normalize_energy_label(raw_label)

    @classmethod
    def _parse_energy_meter(cls, raw_label: object) -> dict[str, object]:
        label = cls._normalize_energy_label(raw_label)
        meter_label = re.sub(rf"{_ENERGY_SUMMARY_TOKEN}$", "", label).strip()
        upper_label = meter_label.upper()

        components = []
        if "主機" in meter_label or " MAIN" in f" {upper_label}":
            components.append("main")
        if "UV" in upper_label:
            components.append("uv")
        if "IR" in upper_label:
            components.append("ir")
        if "馬達" in meter_label or "MOTOR" in upper_label:
            components.append("motor")

        unique_components = list(dict.fromkeys(components))
        if len(unique_components) > 1:
            meter_component = "combo"
        elif len(unique_components) == 1:
            meter_component = unique_components[0]
        elif _ENERGY_MACHINE_ID_RE.search(meter_label):
            meter_component = "aggregate_total"
        else:
            meter_component = "unknown"

        return {
            "meter_label": meter_label,
            "meter_component": meter_component,
            "meter_is_aggregate": int(meter_component in {"aggregate_total", "combo"}),
        }

    @staticmethod
    def _energy_parse_confidence(meter_component: str, canonical_machine_id: str | None) -> str:
        if meter_component == "unknown" or canonical_machine_id is None:
            return "low"
        if meter_component == "aggregate_total":
            return "medium"
        return "high"

    @classmethod
    def _parse_energy_hour_timestamp(cls, value: object) -> str | None:
        if not cls._has_value(value):
            return None

        if isinstance(value, pd.Timestamp):
            parsed = value
        elif isinstance(value, datetime):
            parsed = pd.Timestamp(value)
        else:
            parsed = pd.to_datetime(str(value).strip(), errors="coerce")

        if pd.isna(parsed):
            return None
        if any((parsed.minute, parsed.second, parsed.microsecond, parsed.nanosecond)):
            return None
        return parsed.isoformat()

    @classmethod
    def _build_energy_quality_assessment(
        cls,
        *,
        raw_label: str | None,
        hour_ts: str,
        raw_kwh: float | None,
        raw_cost: float | None,
    ) -> dict[str, object]:
        parsed_hour = pd.to_datetime(hour_ts, errors="coerce")
        if (
            raw_label == _ENERGY_SENTINEL_ANOMALY_LABEL
            and raw_kwh == _ENERGY_SENTINEL_ANOMALY_VALUE
            and raw_cost == _ENERGY_SENTINEL_ANOMALY_VALUE
            and pd.notna(parsed_hour)
            and _ENERGY_SENTINEL_ANOMALY_START <= parsed_hour <= _ENERGY_SENTINEL_ANOMALY_END
        ):
            return {
                "exclude_from_canonical": True,
                "quality_status": "excluded_invalid",
                "quality_flags_json": json.dumps(
                    {"sentinel_anomaly_aug_2025": True},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }

        month_key = parsed_hour.strftime("%Y-%m") if pd.notna(parsed_hour) else None
        quality_flag = _ENERGY_PARTIAL_METER_RULES.get((month_key, raw_label or ""))
        if quality_flag:
            return {
                "exclude_from_canonical": False,
                "quality_status": "flagged_partial",
                "quality_flags_json": json.dumps(
                    {
                        quality_flag: True,
                        "flagged_month": month_key,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }

        return {
            "exclude_from_canonical": False,
            "quality_status": "ok",
            "quality_flags_json": None,
        }

    @classmethod
    def _clean_text(cls, value: object) -> str | None:
        if not cls._has_value(value):
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _has_value(value: object) -> bool:
        if value is None:
            return False
        try:
            if pd.isna(value):
                return False
        except TypeError:
            pass
        if isinstance(value, str):
            return value.strip() != ""
        return True

    @classmethod
    def _float_or_none(cls, value: object) -> float | None:
        if not cls._has_value(value):
            return None
        return float(value)

    @classmethod
    def _int_or_none(cls, value: object) -> int | None:
        if not cls._has_value(value):
            return None
        return int(float(value))

    @classmethod
    def _stringify_date(cls, value: object) -> str | None:
        if not cls._has_value(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()

        parsed = pd.to_datetime(str(value).strip(), errors="coerce")
        if pd.isna(parsed):
            return cls._clean_text(value)
        return parsed.date().isoformat()

    @classmethod
    def _stringify_datetime(cls, value: object) -> str | None:
        if not cls._has_value(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()

        cleaned = str(value).strip()
        parsed = pd.to_datetime(cleaned, errors="coerce")
        if pd.isna(parsed):
            return cleaned
        return parsed.isoformat()

    @staticmethod
    def _json_list(values: list[str]) -> str:
        return json.dumps(values, ensure_ascii=False, sort_keys=False)
