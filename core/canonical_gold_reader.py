from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from core.runtime_paths import get_database_path


CANONICAL_GOLD_REQUIRED_COLUMNS = [
    "canonical_machine_id",
    "hour_ts",
    "machine_state",
    "state_confidence",
    "energy_total_kwh",
    "order_id",
    "material_code",
    "task_name",
    "setup_minutes",
    "production_minutes",
    "planned_stop_minutes",
    "unplanned_stop_minutes",
    "maintenance_minutes",
    "idle_minutes",
    "good_qty",
    "scrap_qty",
    "team_leader",
    "manpower",
    "hours_since_last_maintenance",
    "days_since_last_maintenance",
    "source_flags",
    "attribution_method",
]

CANONICAL_GOLD_EXPORT_COLUMNS = [
    "month_year",
    "datetime",
    "hour_ts",
    "canonical_machine_id",
    "machine_id",
    "machine_state",
    "state_label",
    "state_confidence",
    "state_bucket",
    "energy_total_kwh",
    "order_id",
    "material_code",
    "task_name",
    "setup_minutes",
    "production_minutes",
    "planned_stop_minutes",
    "unplanned_stop_minutes",
    "maintenance_minutes",
    "idle_minutes",
    "good_qty",
    "scrap_qty",
    "production_qty",
    "kwh_per_good_unit",
    "team_leader",
    "manpower",
    "hours_since_last_maintenance",
    "days_since_last_maintenance",
    "maintenance_in_hour",
    "attribution_method",
]

CANONICAL_GOLD_SAMPLE_COLUMNS = [
    "datetime",
    "machine_id",
    "machine_state",
    "energy_total_kwh",
    "good_qty",
    "scrap_qty",
    "kwh_per_good_unit",
    "team_leader",
    "material_code",
    "order_id",
]


class CanonicalGoldReader:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_database_path())

    def fact_machine_hour_exists(self) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'fact_machine_hour'
                """
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_available_months(self) -> list[str]:
        if not self.fact_machine_hour_exists():
            return []

        conn = sqlite3.connect(self.db_path)
        try:
            month_keys = pd.read_sql_query(
                """
                SELECT DISTINCT substr(hour_ts, 1, 7) AS month_key
                FROM fact_machine_hour
                WHERE hour_ts IS NOT NULL
                  AND trim(hour_ts) != ''
                ORDER BY month_key DESC
                """,
                conn,
            )
        finally:
            conn.close()

        months = []
        for value in month_keys["month_key"].tolist():
            label = self._month_key_to_label(value)
            if label is not None:
                months.append(label)
        return months

    def read_month_page_dataframe(self, month_year: str) -> pd.DataFrame:
        if not self.fact_machine_hour_exists():
            return pd.DataFrame(columns=CANONICAL_GOLD_EXPORT_COLUMNS)

        bounds = self._month_label_to_bounds(month_year)
        if bounds is None:
            return pd.DataFrame(columns=CANONICAL_GOLD_EXPORT_COLUMNS)
        start_ts, end_ts = bounds

        conn = sqlite3.connect(self.db_path)
        try:
            fact_df = pd.read_sql_query(
                """
                SELECT *
                FROM fact_machine_hour
                WHERE hour_ts >= ?
                  AND hour_ts < ?
                ORDER BY hour_ts, canonical_machine_id
                """,
                conn,
                params=(start_ts, end_ts),
            )
        finally:
            conn.close()

        if fact_df.empty:
            return pd.DataFrame(columns=CANONICAL_GOLD_EXPORT_COLUMNS)

        missing_columns = [
            column for column in CANONICAL_GOLD_REQUIRED_COLUMNS if column not in fact_df.columns
        ]
        if missing_columns:
            raise ValueError(
                "fact_machine_hour is missing required canonical columns: "
                + ", ".join(missing_columns)
            )

        return self._build_page_dataframe(fact_df)

    def build_month_metrics(self, page_df: pd.DataFrame) -> dict[str, float | int | None]:
        efficiency_df = self._select_efficiency_rows(page_df)
        efficiency_energy_kwh = self._sum_or_none(efficiency_df["energy_total_kwh"])
        efficiency_good_qty = self._sum_or_none(efficiency_df["good_qty"])
        return {
            "gold_rows_loaded_for_page": int(len(page_df)),
            "distinct_machines": int(page_df["canonical_machine_id"].nunique()),
            "rows_with_null_machine_state": int(page_df["machine_state"].isna().sum()),
            "total_energy_total_kwh": self._sum_or_none(page_df["energy_total_kwh"]),
            "total_good_qty": self._sum_or_none(page_df["good_qty"]),
            "total_scrap_qty": self._sum_or_none(page_df["scrap_qty"]),
            "efficiency_energy_kwh": efficiency_energy_kwh,
            "efficiency_good_qty": efficiency_good_qty,
            "weighted_kwh_per_good_unit": self._safe_divide(
                efficiency_energy_kwh,
                efficiency_good_qty,
            ),
        }

    def build_state_summary(self, page_df: pd.DataFrame) -> pd.DataFrame:
        if page_df.empty:
            return pd.DataFrame(
                columns=["state_bucket", "state_label", "row_count", "energy_kwh", "energy_share"]
            )

        summary = (
            page_df.groupby(["state_bucket", "state_label"], dropna=False)
            .agg(
                row_count=("machine_id", "size"),
                energy_kwh=("energy_total_kwh", "sum"),
            )
            .reset_index()
        )
        total_energy = float(summary["energy_kwh"].fillna(0.0).sum())
        summary["energy_share"] = summary["energy_kwh"].fillna(0.0) / total_energy if total_energy > 0 else 0.0
        summary = summary.sort_values(
            ["energy_kwh", "row_count", "state_label"],
            ascending=[False, False, True],
        )
        summary["energy_kwh"] = summary["energy_kwh"].fillna(0.0)
        summary = summary[
            ["state_bucket", "state_label", "row_count", "energy_kwh", "energy_share"]
        ].copy()
        summary = summary.reset_index(drop=True)
        return summary

    def build_export_dataframe(self, page_df: pd.DataFrame) -> pd.DataFrame:
        if page_df.empty:
            return pd.DataFrame(columns=CANONICAL_GOLD_EXPORT_COLUMNS)
        return page_df.loc[:, CANONICAL_GOLD_EXPORT_COLUMNS].copy()

    @classmethod
    def _build_page_dataframe(cls, fact_df: pd.DataFrame) -> pd.DataFrame:
        page_df = fact_df.copy()
        page_df["datetime"] = pd.to_datetime(page_df["hour_ts"], errors="coerce")
        page_df["month_year"] = page_df["datetime"].dt.strftime("%B %Y")
        page_df["machine_id"] = page_df["canonical_machine_id"]
        page_df["production_qty"] = page_df["good_qty"]
        page_df["kwh_per_good_unit"] = page_df.apply(cls._derive_kwh_per_good_unit, axis=1)
        page_df["maintenance_in_hour"] = page_df.apply(cls._derive_maintenance_in_hour, axis=1)
        page_df["state_bucket"] = page_df["machine_state"].apply(cls._derive_state_bucket)
        page_df["state_label"] = page_df["state_bucket"].apply(cls._derive_state_label)
        page_df = page_df.sort_values(["datetime", "canonical_machine_id"]).reset_index(drop=True)
        return page_df

    @staticmethod
    def _derive_kwh_per_good_unit(row: pd.Series) -> float | None:
        energy_total_kwh = CanonicalGoldReader._float_or_none(row.get("energy_total_kwh"))
        good_qty = CanonicalGoldReader._float_or_none(row.get("good_qty"))
        if energy_total_kwh is None or good_qty is None or good_qty <= 0:
            return None
        return energy_total_kwh / good_qty

    @staticmethod
    def _derive_maintenance_in_hour(row: pd.Series) -> int:
        source_flags = CanonicalGoldReader._load_source_flags(row.get("source_flags"))
        if bool(source_flags.get("maintenance_txn_in_hour")):
            return 1
        if CanonicalGoldReader._clean_text(row.get("machine_state")) == "maintenance":
            return 1
        return 0

    @staticmethod
    def _derive_state_bucket(machine_state: object) -> str:
        cleaned_state = CanonicalGoldReader._clean_text(machine_state)
        return cleaned_state or "unknown"

    @staticmethod
    def _derive_state_label(state_bucket: object) -> str:
        labels = {
            "setup_changeover": "Setup Changeover",
            "production": "Production",
            "planned_stop": "Planned Stop",
            "unplanned_stop": "Unplanned Stop",
            "idle": "Idle",
            "maintenance": "Maintenance",
            "energy_only": "Energy Only",
            "unknown": "Unknown / Unattributed",
        }
        cleaned_bucket = CanonicalGoldReader._clean_text(state_bucket) or "unknown"
        return labels.get(cleaned_bucket, cleaned_bucket.replace("_", " ").title())

    @staticmethod
    def _month_key_to_label(month_key: object) -> str | None:
        month_text = CanonicalGoldReader._clean_text(month_key)
        if month_text is None:
            return None
        month_dt = pd.to_datetime(f"{month_text}-01", errors="coerce")
        if pd.isna(month_dt):
            return None
        return month_dt.strftime("%B %Y")

    @staticmethod
    def _month_label_to_bounds(month_year: str) -> tuple[str, str] | None:
        month_dt = pd.to_datetime(month_year, format="%B %Y", errors="coerce")
        if pd.isna(month_dt):
            return None
        next_month_dt = month_dt + pd.offsets.MonthBegin(1)
        return (
            month_dt.strftime("%Y-%m-%dT00:00:00"),
            next_month_dt.strftime("%Y-%m-%dT00:00:00"),
        )

    @staticmethod
    def _load_source_flags(source_flags: object) -> dict[str, object]:
        cleaned_flags = CanonicalGoldReader._clean_text(source_flags)
        if cleaned_flags is None:
            return {}
        try:
            parsed = json.loads(cleaned_flags)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _clean_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sum_or_none(series: pd.Series) -> float | None:
        non_null = series.dropna()
        if non_null.empty:
            return None
        return float(non_null.sum())

    @staticmethod
    def _mean_or_none(series: pd.Series) -> float | None:
        non_null = series.dropna()
        if non_null.empty:
            return None
        return float(non_null.mean())

    @staticmethod
    def _safe_divide(numerator: object, denominator: object) -> float | None:
        clean_numerator = CanonicalGoldReader._float_or_none(numerator)
        clean_denominator = CanonicalGoldReader._float_or_none(denominator)
        if clean_numerator is None or clean_denominator is None or clean_denominator <= 0:
            return None
        return clean_numerator / clean_denominator

    @staticmethod
    def _select_efficiency_rows(page_df: pd.DataFrame) -> pd.DataFrame:
        if page_df.empty:
            return page_df.copy()

        return page_df[
            page_df["energy_total_kwh"].notna()
            & page_df["good_qty"].notna()
            & (page_df["good_qty"] > 0)
        ].copy()
