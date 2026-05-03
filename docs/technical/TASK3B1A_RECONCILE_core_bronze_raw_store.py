"""Bronze raw table storage helpers for canonical raw-source preservation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from core.runtime_paths import get_database_path, get_repo_root


_DERIVED_HASH_EXCLUDED_FIELDS = {
    "canonical_machine_id",
    "matched_on",
    "matched_value",
    "exception_applied",
    "scope_status",
    "join_status",
    "source_system",
    "normalized_id",
    "machine_id",
    "is_three_way_match",
}


class BronzeRawStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_database_path())
        self.ensure_tables()

    def ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_energy_hourly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_row_hash TEXT NOT NULL UNIQUE,
                ingested_at TEXT NOT NULL,
                raw_machine_id_or_label TEXT,
                canonical_machine_id TEXT,
                matched_on TEXT,
                matched_value TEXT,
                exception_applied INTEGER,
                scope_status TEXT,
                join_status TEXT,
                raw_timestamp TEXT,
                raw_kwh REAL,
                raw_cost REAL,
                raw_payload_json TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_csi_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_row_hash TEXT NOT NULL UNIQUE,
                ingested_at TEXT NOT NULL,
                raw_machine_id_or_label TEXT,
                canonical_machine_id TEXT,
                matched_on TEXT,
                matched_value TEXT,
                exception_applied INTEGER,
                scope_status TEXT,
                join_status TEXT,
                raw_start_time TEXT,
                raw_end_time TEXT,
                raw_prep_end_time TEXT,
                raw_order_id TEXT,
                raw_material TEXT,
                raw_good_qty REAL,
                raw_scrap_qty REAL,
                raw_payload_json TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_mes_report (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_row_hash TEXT NOT NULL UNIQUE,
                ingested_at TEXT NOT NULL,
                raw_machine_id_or_label TEXT,
                canonical_machine_id TEXT,
                matched_on TEXT,
                matched_value TEXT,
                exception_applied INTEGER,
                scope_status TEXT,
                join_status TEXT,
                raw_task TEXT,
                raw_order_number TEXT,
                raw_material_code TEXT,
                raw_planned_qty REAL,
                raw_planned_start TEXT,
                raw_planned_end TEXT,
                raw_payload_json TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_maintenance_txn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_row_hash TEXT NOT NULL UNIQUE,
                ingested_at TEXT NOT NULL,
                raw_machine_id_or_label TEXT,
                canonical_machine_id TEXT,
                matched_on TEXT,
                matched_value TEXT,
                exception_applied INTEGER,
                scope_status TEXT,
                join_status TEXT,
                raw_transaction_date TEXT,
                raw_work_order TEXT,
                raw_work_order_type TEXT,
                raw_transaction_type TEXT,
                raw_asset_id TEXT,
                raw_asset_old_id TEXT,
                raw_material_code TEXT,
                raw_quantity REAL,
                raw_payload_json TEXT
            )
            """
        )

        conn.commit()
        conn.close()

    def write_energy_rows(self, df: pd.DataFrame) -> None:
        row_dicts = [
            self._build_energy_row(row)
            for _, row in df.iterrows()
        ]
        self._upsert_rows("raw_energy_hourly", row_dicts)

    def write_csi_rows(self, df: pd.DataFrame) -> None:
        row_dicts = [
            self._build_csi_row(row)
            for _, row in df.iterrows()
        ]
        self._upsert_rows("raw_csi_event", row_dicts)

    def write_mes_rows(self, df: pd.DataFrame) -> None:
        row_dicts = [
            self._build_mes_row(row)
            for _, row in df.iterrows()
        ]
        self._upsert_rows("raw_mes_report", row_dicts)

    def write_maintenance_rows(self, df: pd.DataFrame) -> None:
        row_dicts = [
            self._build_maintenance_row(row)
            for _, row in df.iterrows()
        ]
        self._upsert_rows("raw_maintenance_txn", row_dicts)

    def _upsert_rows(self, table_name: str, row_dicts: Iterable[dict[str, object]]) -> None:
        rows = list(row_dicts)
        if not rows:
            return

        columns = list(rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)
        update_clause = ", ".join(
            f"{column}=excluded.{column}"
            for column in columns
            if column != "source_row_hash"
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            f"""
            INSERT INTO {table_name} ({column_list})
            VALUES ({placeholders})
            ON CONFLICT(source_row_hash) DO UPDATE SET
            {update_clause}
            """,
            [tuple(row[column] for column in columns) for row in rows],
        )
        conn.commit()
        conn.close()

    def _build_energy_row(self, row: pd.Series) -> dict[str, object]:
        payload_json = self._row_payload_json(row)
        return {
            "source_system": "energy",
            "source_file": self._normalize_source_file(row.get("source_file")),
            "source_row_hash": self._build_source_row_hash("energy", row),
            "ingested_at": self._ingested_at(),
            "raw_machine_id_or_label": self._clean_value(row.get("machine")),
            "canonical_machine_id": self._clean_value(row.get("canonical_machine_id")),
            "matched_on": self._clean_value(row.get("matched_on")),
            "matched_value": self._clean_value(row.get("matched_value")),
            "exception_applied": int(bool(row.get("exception_applied", False))),
            "scope_status": self._clean_value(row.get("scope_status")),
            "join_status": self._clean_value(row.get("join_status")),
            "raw_timestamp": self._stringify_value(row.get("datetime")),
            "raw_kwh": self._float_or_none(row.get("electricity_kwh")),
            "raw_cost": self._float_or_none(row.get("electricity_cost")),
            "raw_payload_json": payload_json,
        }

    def _build_csi_row(self, row: pd.Series) -> dict[str, object]:
        payload_json = self._row_payload_json(row)
        return {
            "source_system": "csi",
            "source_file": self._normalize_source_file(row.get("source_file")),
            "source_row_hash": self._build_source_row_hash("csi", row),
            "ingested_at": self._ingested_at(),
            "raw_machine_id_or_label": self._clean_value(row.get("機台編號")),
            "canonical_machine_id": self._clean_value(row.get("canonical_machine_id")),
            "matched_on": self._clean_value(row.get("matched_on")),
            "matched_value": self._clean_value(row.get("matched_value")),
            "exception_applied": int(bool(row.get("exception_applied", False))),
            "scope_status": self._clean_value(row.get("scope_status")),
            "join_status": self._clean_value(row.get("join_status")),
            "raw_start_time": self._stringify_value(row.get("工程開始時間")),
            "raw_end_time": self._stringify_value(row.get("工程結束時間")),
            "raw_prep_end_time": self._stringify_value(row.get("準備結束時間")),
            "raw_order_id": self._clean_value(row.get("作业")),
            "raw_material": self._clean_value(row.get("物料")),
            "raw_good_qty": self._float_or_none(row.get("正品數量")),
            "raw_scrap_qty": self._float_or_none(row.get("廢品數量")),
            "raw_payload_json": payload_json,
        }

    def _build_mes_row(self, row: pd.Series) -> dict[str, object]:
        payload_json = self._row_payload_json(row)
        return {
            "source_system": "mes",
            "source_file": self._normalize_source_file(row.get("source_file")),
            "source_row_hash": self._build_source_row_hash("mes", row),
            "ingested_at": self._ingested_at(),
            "raw_machine_id_or_label": self._first_present(row, "資源", "resource"),
            "canonical_machine_id": self._clean_value(row.get("canonical_machine_id")),
            "matched_on": self._clean_value(row.get("matched_on")),
            "matched_value": self._clean_value(row.get("matched_value")),
            "exception_applied": int(bool(row.get("exception_applied", False))),
            "scope_status": self._clean_value(row.get("scope_status")),
            "join_status": self._clean_value(row.get("join_status")),
            "raw_task": self._first_present(row, "任務", "task"),
            "raw_order_number": self._first_present(row, "訂單號", "order_number"),
            "raw_material_code": self._first_present(row, "物料編碼", "material_code"),
            "raw_planned_qty": self._first_present_float(row, "計劃數量", "planned_qty", "計劃生產數量"),
            "raw_planned_start": self._first_present_string(row, "計劃開始", "planned_start"),
            "raw_planned_end": self._first_present_string(row, "計劃結束", "planned_end"),
            "raw_payload_json": payload_json,
        }

    def _build_maintenance_row(self, row: pd.Series) -> dict[str, object]:
        payload_json = self._row_payload_json(row)
        raw_machine_id_or_label = (
            self._clean_value(row.get("資產"))
            or self._clean_value(row.get("資產老編號"))
            or self._clean_value(row.get("normalized_id"))
        )
        return {
            "source_system": "maintenance",
            "source_file": self._normalize_source_file(row.get("source_file")),
            "source_row_hash": self._build_source_row_hash("maintenance", row),
            "ingested_at": self._ingested_at(),
            "raw_machine_id_or_label": raw_machine_id_or_label,
            "canonical_machine_id": self._clean_value(row.get("canonical_machine_id")),
            "matched_on": self._clean_value(row.get("matched_on")),
            "matched_value": self._clean_value(row.get("matched_value")),
            "exception_applied": int(bool(row.get("exception_applied", False))),
            "scope_status": self._clean_value(row.get("scope_status")),
            "join_status": self._clean_value(row.get("join_status")),
            "raw_transaction_date": self._stringify_value(row.get("交易日期")),
            "raw_work_order": self._clean_value(row.get("工單")),
            "raw_work_order_type": self._clean_value(row.get("工單類型")),
            "raw_transaction_type": self._clean_value(row.get("交易類型")),
            "raw_asset_id": self._clean_value(row.get("資產")),
            "raw_asset_old_id": self._clean_value(row.get("資產老編號")),
            "raw_material_code": self._clean_value(row.get("物料編碼")),
            "raw_quantity": self._float_or_none(row.get("數量")),
            "raw_payload_json": payload_json,
        }

    @staticmethod
    def _clean_value(value: object) -> str | None:
        if value is None:
            return None
        if pd.isna(value):
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @classmethod
    def _float_or_none(cls, value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @classmethod
    def _stringify_value(cls, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        return str(value)

    def _normalize_source_file(self, source_file: object) -> str:
        cleaned = self._clean_value(source_file)
        if not cleaned:
            return ""

        repo_root = get_repo_root().resolve()
        path = Path(cleaned)

        try:
            resolved = path.resolve() if path.is_absolute() else (repo_root / path).resolve()
            return str(resolved.relative_to(repo_root))
        except Exception:
            return cleaned

    def _build_source_row_hash(self, source_system: str, row: pd.Series) -> str:
        source_file = self._normalize_source_file(row.get("source_file"))
        raw_truth = {
            str(key): self._json_value(value)
            for key, value in row.to_dict().items()
            if key not in _DERIVED_HASH_EXCLUDED_FIELDS and key != "source_file"
        }
        hash_input = {
            "source_system": source_system,
            "source_file": source_file,
            "raw_truth": raw_truth,
        }
        return hashlib.sha256(
            json.dumps(hash_input, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _ingested_at() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row_payload_json(self, row: pd.Series) -> str:
        payload = {
            str(key): self._json_value(value)
            for key, value in row.to_dict().items()
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @classmethod
    def _first_present(cls, row: pd.Series, *column_names: str) -> str | None:
        for column_name in column_names:
            value = cls._clean_value(row.get(column_name))
            if value is not None:
                return value
        return None

    @classmethod
    def _first_present_float(cls, row: pd.Series, *column_names: str) -> float | None:
        for column_name in column_names:
            value = row.get(column_name)
            if value is not None and not pd.isna(value):
                return float(value)
        return None

    @classmethod
    def _first_present_string(cls, row: pd.Series, *column_names: str) -> str | None:
        for column_name in column_names:
            value = row.get(column_name)
            if value is not None and not pd.isna(value):
                if isinstance(value, pd.Timestamp):
                    return value.isoformat()
                return str(value)
        return None

    @classmethod
    def _json_value(cls, value: object) -> object:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        return value
