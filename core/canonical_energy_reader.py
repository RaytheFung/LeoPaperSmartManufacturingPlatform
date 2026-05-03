from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from core.runtime_paths import get_database_path


CANONICAL_ENERGY_REQUIRED_COLUMNS = [
    "canonical_machine_id",
    "hour_ts",
    "machine_state",
    "energy_total_kwh",
    "setup_minutes",
    "production_minutes",
    "planned_stop_minutes",
    "unplanned_stop_minutes",
    "maintenance_minutes",
    "idle_minutes",
    "good_qty",
    "hours_since_last_maintenance",
]

CANONICAL_ENERGY_EXPORT_COLUMNS = [
    "month_year",
    "datetime",
    "hour_ts",
    "machine_id",
    "machine_state",
    "energy_total_kwh",
    "good_qty",
    "production_qty",
    "kwh_per_good_unit",
    "hours_since_last_maintenance",
    "hour_of_day",
    "tracked_minutes",
    "setup_energy_kwh",
    "production_energy_kwh",
    "planned_stop_energy_kwh",
    "unplanned_stop_energy_kwh",
    "maintenance_energy_kwh",
    "idle_energy_kwh",
    "unallocated_energy_kwh",
    "energy_attribution_method",
]

MACHINE_EFFICIENCY_RANKING_COLUMNS = [
    "machine_id",
    "weighted_kwh_per_good_unit",
    "row_count",
    "total_good_qty",
    "total_energy_kwh",
]

MAINTENANCE_EFFICIENCY_CURVE_COLUMNS = [
    "bucket",
    "weighted_kwh_per_good_unit",
    "row_count",
    "total_good_qty",
    "total_energy_kwh",
]

ATTRIBUTION_TRUST_COLUMNS = [
    "attribution_method",
    "attribution_label",
    "meaning",
    "row_count",
    "energy_kwh",
    "energy_share",
]

ENERGY_BUCKET_COLUMN_MAP = {
    "setup_energy_kwh": "Setup",
    "production_energy_kwh": "Production",
    "planned_stop_energy_kwh": "Planned Stop",
    "unplanned_stop_energy_kwh": "Unplanned Stop",
    "maintenance_energy_kwh": "Maintenance",
    "idle_energy_kwh": "Idle",
    "unallocated_energy_kwh": "Unallocated / Energy-Only",
}

_MINUTE_BUCKET_COLUMNS = [
    ("setup_minutes", "setup_energy_kwh"),
    ("production_minutes", "production_energy_kwh"),
    ("planned_stop_minutes", "planned_stop_energy_kwh"),
    ("unplanned_stop_minutes", "unplanned_stop_energy_kwh"),
    ("maintenance_minutes", "maintenance_energy_kwh"),
    ("idle_minutes", "idle_energy_kwh"),
]

_STATE_TO_BUCKET_COLUMN = {
    "setup_changeover": "setup_energy_kwh",
    "production": "production_energy_kwh",
    "planned_stop": "planned_stop_energy_kwh",
    "unplanned_stop": "unplanned_stop_energy_kwh",
    "maintenance": "maintenance_energy_kwh",
    "idle": "idle_energy_kwh",
}

ATTRIBUTION_METHOD_LABELS = {
    "minute_share": "Minute-share attribution",
    "machine_state_fallback": "Machine-state fallback",
    "unallocated": "Residual / Unallocated",
    "no_energy": "No positive energy",
}

ATTRIBUTION_METHOD_MEANINGS = {
    "minute_share": "Energy was distributed across operating states using canonical minute shares in the hour.",
    "machine_state_fallback": "Minute shares were unavailable, so the full hour's energy stayed with the row's canonical machine state.",
    "unallocated": "Positive energy remained on the row, but there was not enough canonical state evidence to place it into a specific operating state.",
    "no_energy": "The row is present in the month slice, but `energy_total_kwh` is null, zero, or non-positive so it does not contribute to month energy totals.",
}


class CanonicalEnergyReader:
    """Routed runtime analytics helper backed by fact_machine_hour only."""

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

    def read_month_energy_dataframe(self, month_year: str) -> pd.DataFrame:
        bounds = self._month_label_to_bounds(month_year)
        if bounds is None or not self.fact_machine_hour_exists():
            return pd.DataFrame(columns=CANONICAL_ENERGY_EXPORT_COLUMNS)
        start_ts, end_ts = bounds
        return self._read_energy_dataframe(start_ts=start_ts, end_ts=end_ts)

    def read_all_energy_dataframe(self) -> pd.DataFrame:
        if not self.fact_machine_hour_exists():
            return pd.DataFrame(columns=CANONICAL_ENERGY_EXPORT_COLUMNS)
        return self._read_energy_dataframe()

    def build_month_summary(self, energy_df: pd.DataFrame) -> dict[str, float | int | None]:
        efficiency_df = self._select_efficiency_rows(energy_df)
        efficiency_energy_kwh = self._sum_or_none(efficiency_df["energy_total_kwh"])
        efficiency_good_qty = self._sum_or_none(efficiency_df["good_qty"])
        return {
            "rows_loaded": int(len(energy_df)),
            "distinct_machines": int(energy_df["machine_id"].nunique()) if not energy_df.empty else 0,
            "total_energy_kwh": self._sum_or_none(energy_df["energy_total_kwh"]),
            "total_good_qty": self._sum_or_none(energy_df["good_qty"]),
            "efficiency_energy_kwh": efficiency_energy_kwh,
            "efficiency_good_qty": efficiency_good_qty,
            "weighted_kwh_per_good_unit": self._safe_divide(
                efficiency_energy_kwh,
                efficiency_good_qty,
            ),
            "unallocated_energy_kwh": self._sum_or_none(energy_df["unallocated_energy_kwh"]),
        }

    def build_energy_breakdown(self, energy_df: pd.DataFrame) -> pd.DataFrame:
        if energy_df.empty:
            return pd.DataFrame(columns=["energy_bucket", "energy_kwh"])

        rows = []
        for column_name, label in ENERGY_BUCKET_COLUMN_MAP.items():
            value = float(energy_df[column_name].fillna(0.0).sum())
            if value > 0:
                rows.append({"energy_bucket": label, "energy_kwh": value})

        if not rows:
            return pd.DataFrame(columns=["energy_bucket", "energy_kwh"])

        return pd.DataFrame(rows).sort_values("energy_kwh", ascending=False).reset_index(drop=True)

    def build_daily_state_energy(self, energy_df: pd.DataFrame) -> pd.DataFrame:
        if energy_df.empty:
            return pd.DataFrame()

        working_df = energy_df.copy()
        working_df["date"] = working_df["datetime"].dt.floor("D")
        grouped = (
            working_df.groupby("date", dropna=False)[list(ENERGY_BUCKET_COLUMN_MAP.keys())]
            .sum(min_count=1)
            .reset_index()
            .sort_values("date")
            .reset_index(drop=True)
        )
        rename_map = {column_name: label for column_name, label in ENERGY_BUCKET_COLUMN_MAP.items()}
        return grouped.rename(columns=rename_map)

    def build_attribution_trust_summary(self, energy_df: pd.DataFrame) -> pd.DataFrame:
        if energy_df.empty:
            return pd.DataFrame(columns=ATTRIBUTION_TRUST_COLUMNS)

        grouped = (
            energy_df.groupby("energy_attribution_method", dropna=False)
            .agg(
                row_count=("machine_id", "size"),
                energy_kwh=("energy_total_kwh", "sum"),
            )
            .reset_index()
        )
        grouped["attribution_method"] = grouped["energy_attribution_method"].fillna("unknown")
        grouped["attribution_label"] = grouped["attribution_method"].map(ATTRIBUTION_METHOD_LABELS).fillna(
            grouped["attribution_method"].str.replace("_", " ").str.title()
        )
        grouped["meaning"] = grouped["attribution_method"].map(ATTRIBUTION_METHOD_MEANINGS).fillna(
            "Category meaning is not yet documented."
        )
        total_energy = float(grouped["energy_kwh"].fillna(0.0).sum())
        grouped["energy_share"] = grouped["energy_kwh"].fillna(0.0) / total_energy if total_energy > 0 else 0.0
        grouped = grouped.loc[:, ATTRIBUTION_TRUST_COLUMNS].copy()
        grouped = grouped.sort_values(["energy_kwh", "row_count"], ascending=[False, False]).reset_index(
            drop=True
        )
        return grouped

    def build_attribution_coverage_summary(self, energy_df: pd.DataFrame) -> dict[str, float | int]:
        trust_df = self.build_attribution_trust_summary(energy_df)
        positive_energy_mask = energy_df["energy_total_kwh"].fillna(0.0) > 0 if not energy_df.empty else pd.Series(dtype=bool)
        positive_energy_rows = int(positive_energy_mask.sum()) if not energy_df.empty else 0

        def _energy_for(methods: set[str]) -> float:
            if trust_df.empty:
                return 0.0
            return float(
                trust_df.loc[trust_df["attribution_method"].isin(methods), "energy_kwh"].fillna(0.0).sum()
            )

        def _rows_for(methods: set[str]) -> int:
            if trust_df.empty:
                return 0
            return int(trust_df.loc[trust_df["attribution_method"].isin(methods), "row_count"].sum())

        total_energy_kwh = float(trust_df["energy_kwh"].fillna(0.0).sum()) if not trust_df.empty else 0.0
        attributed_methods = {"minute_share", "machine_state_fallback"}
        attributed_energy_kwh = _energy_for(attributed_methods)
        residual_energy_kwh = _energy_for({"unallocated"})
        attributed_positive_energy_rows = _rows_for(attributed_methods)
        residual_positive_energy_rows = _rows_for({"unallocated"})

        return {
            "total_rows": int(len(energy_df)),
            "total_energy_kwh": total_energy_kwh,
            "attributed_energy_kwh": attributed_energy_kwh,
            "residual_energy_kwh": residual_energy_kwh,
            "attributed_energy_share": (attributed_energy_kwh / total_energy_kwh) if total_energy_kwh > 0 else 0.0,
            "residual_energy_share": (residual_energy_kwh / total_energy_kwh) if total_energy_kwh > 0 else 0.0,
            "positive_energy_rows": positive_energy_rows,
            "attributed_positive_energy_rows": attributed_positive_energy_rows,
            "residual_positive_energy_rows": residual_positive_energy_rows,
            "attributed_positive_energy_row_share": (
                attributed_positive_energy_rows / positive_energy_rows if positive_energy_rows > 0 else 0.0
            ),
            "no_energy_rows": _rows_for({"no_energy"}),
        }

    def build_daily_energy_anomalies(self, daily_energy_df: pd.DataFrame) -> pd.DataFrame:
        if daily_energy_df.empty:
            return pd.DataFrame(columns=["date", "total_energy_kwh", "lower_bound", "upper_bound", "direction"])

        value_columns = [column for column in daily_energy_df.columns if column != "date"]
        if not value_columns:
            return pd.DataFrame(columns=["date", "total_energy_kwh", "lower_bound", "upper_bound", "direction"])

        working_df = daily_energy_df.copy()
        working_df["total_energy_kwh"] = working_df[value_columns].fillna(0.0).sum(axis=1)
        if working_df["total_energy_kwh"].notna().sum() < 4:
            return pd.DataFrame(columns=["date", "total_energy_kwh", "lower_bound", "upper_bound", "direction"])

        q1 = working_df["total_energy_kwh"].quantile(0.25)
        q3 = working_df["total_energy_kwh"].quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr <= 0:
            return pd.DataFrame(columns=["date", "total_energy_kwh", "lower_bound", "upper_bound", "direction"])

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        anomaly_df = working_df[
            (working_df["total_energy_kwh"] < lower_bound)
            | (working_df["total_energy_kwh"] > upper_bound)
        ].copy()
        if anomaly_df.empty:
            return pd.DataFrame(columns=["date", "total_energy_kwh", "lower_bound", "upper_bound", "direction"])

        anomaly_df["lower_bound"] = lower_bound
        anomaly_df["upper_bound"] = upper_bound
        anomaly_df["direction"] = anomaly_df["total_energy_kwh"].apply(
            lambda value: "High" if value > upper_bound else "Low"
        )
        return anomaly_df.loc[
            :,
            ["date", "total_energy_kwh", "lower_bound", "upper_bound", "direction"],
        ].reset_index(drop=True)

    def build_machine_efficiency_ranking(
        self,
        energy_df: pd.DataFrame,
        limit: int = 20,
        *,
        min_row_count: int = 1,
        min_total_good_qty: float = 0.0,
    ) -> pd.DataFrame:
        grouped = self.build_machine_energy_summary(
            energy_df,
            min_row_count=min_row_count,
            min_total_good_qty=min_total_good_qty,
        )
        if grouped.empty:
            return pd.DataFrame(columns=MACHINE_EFFICIENCY_RANKING_COLUMNS)

        grouped = grouped.sort_values(
            ["weighted_kwh_per_good_unit", "total_good_qty", "machine_id"],
            ascending=[True, False, True],
        ).head(limit)
        return grouped.reset_index(drop=True)

    def build_machine_energy_summary(
        self,
        energy_df: pd.DataFrame,
        *,
        min_row_count: int = 1,
        min_total_good_qty: float = 0.0,
    ) -> pd.DataFrame:
        if energy_df.empty:
            return pd.DataFrame(columns=MACHINE_EFFICIENCY_RANKING_COLUMNS)

        ranking_df = self._select_efficiency_rows(energy_df)
        if ranking_df.empty:
            return pd.DataFrame(columns=MACHINE_EFFICIENCY_RANKING_COLUMNS)

        grouped = (
            ranking_df.groupby("machine_id", dropna=False)
            .agg(
                row_count=("machine_id", "size"),
                total_good_qty=("good_qty", "sum"),
                total_energy_kwh=("energy_total_kwh", "sum"),
            )
            .reset_index()
        )
        grouped = grouped[grouped["row_count"] >= int(min_row_count)].copy()
        if min_total_good_qty > 0:
            grouped = grouped[grouped["total_good_qty"] >= float(min_total_good_qty)].copy()
        if grouped.empty:
            return pd.DataFrame(columns=MACHINE_EFFICIENCY_RANKING_COLUMNS)

        grouped["weighted_kwh_per_good_unit"] = grouped.apply(
            lambda row: self._safe_divide(row["total_energy_kwh"], row["total_good_qty"]),
            axis=1,
        )
        grouped = grouped[grouped["weighted_kwh_per_good_unit"].notna()].copy()
        if grouped.empty:
            return pd.DataFrame(columns=MACHINE_EFFICIENCY_RANKING_COLUMNS)

        grouped = grouped.loc[:, MACHINE_EFFICIENCY_RANKING_COLUMNS].copy()
        return grouped.reset_index(drop=True)

    def build_hourly_energy_profile(self, energy_df: pd.DataFrame) -> pd.DataFrame:
        if energy_df.empty:
            return pd.DataFrame(columns=["hour_of_day", "avg_energy_kwh", "total_energy_kwh", "row_count"])

        grouped = (
            energy_df.groupby("hour_of_day", dropna=False)
            .agg(
                avg_energy_kwh=("energy_total_kwh", "mean"),
                total_energy_kwh=("energy_total_kwh", "sum"),
                row_count=("machine_id", "size"),
            )
            .reset_index()
            .sort_values("hour_of_day")
            .reset_index(drop=True)
        )
        return grouped

    def build_maintenance_efficiency_curve(
        self,
        *,
        month_year: str | None = None,
        min_bucket_count: int = 20,
    ) -> pd.DataFrame:
        if month_year is None:
            working_df = self.read_all_energy_dataframe()
        else:
            working_df = self.read_month_energy_dataframe(month_year)

        if working_df.empty:
            return pd.DataFrame(columns=MAINTENANCE_EFFICIENCY_CURVE_COLUMNS)

        curve_df = self._select_efficiency_rows(working_df)
        curve_df = curve_df[
            curve_df["hours_since_last_maintenance"].notna()
            & curve_df["kwh_per_good_unit"].notna()
            & (curve_df["kwh_per_good_unit"] > 0)
            & (curve_df["kwh_per_good_unit"] < 20)
        ].copy()
        if curve_df.empty:
            return pd.DataFrame(columns=MAINTENANCE_EFFICIENCY_CURVE_COLUMNS)

        curve_df["bucket"] = pd.cut(
            curve_df["hours_since_last_maintenance"],
            bins=[0, 200, 500, 800, 1200, 2000, 4000],
            labels=["0-200h", "200-500h", "500-800h", "800-1200h", "1200-2000h", "2000-4000h"],
            include_lowest=False,
            right=True,
        )

        grouped = (
            curve_df.groupby("bucket", dropna=False, observed=False)
            .agg(
                row_count=("bucket", "size"),
                total_energy_kwh=("energy_total_kwh", "sum"),
                total_good_qty=("good_qty", "sum"),
            )
            .reset_index()
        )
        grouped = grouped[grouped["bucket"].notna()].copy()
        grouped = grouped[grouped["row_count"] >= min_bucket_count].copy()
        if grouped.empty:
            return pd.DataFrame(columns=MAINTENANCE_EFFICIENCY_CURVE_COLUMNS)

        grouped["weighted_kwh_per_good_unit"] = grouped.apply(
            lambda row: self._safe_divide(row["total_energy_kwh"], row["total_good_qty"]),
            axis=1,
        )
        grouped = grouped[grouped["weighted_kwh_per_good_unit"].notna()].copy()
        if grouped.empty:
            return pd.DataFrame(columns=MAINTENANCE_EFFICIENCY_CURVE_COLUMNS)

        grouped = grouped.loc[:, MAINTENANCE_EFFICIENCY_CURVE_COLUMNS].copy()
        return grouped.reset_index(drop=True)

    def _read_energy_dataframe(
        self,
        *,
        start_ts: str | None = None,
        end_ts: str | None = None,
    ) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            query = """
                SELECT
                    canonical_machine_id,
                    hour_ts,
                    machine_state,
                    energy_total_kwh,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    unplanned_stop_minutes,
                    maintenance_minutes,
                    idle_minutes,
                    good_qty,
                    hours_since_last_maintenance
                FROM fact_machine_hour
                WHERE hour_ts IS NOT NULL
            """
            params: list[str] = []
            if start_ts is not None:
                query += " AND hour_ts >= ?"
                params.append(start_ts)
            if end_ts is not None:
                query += " AND hour_ts < ?"
                params.append(end_ts)
            query += " ORDER BY hour_ts, canonical_machine_id"

            fact_df = pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()

        if fact_df.empty:
            return pd.DataFrame(columns=CANONICAL_ENERGY_EXPORT_COLUMNS)

        missing_columns = [
            column for column in CANONICAL_ENERGY_REQUIRED_COLUMNS if column not in fact_df.columns
        ]
        if missing_columns:
            raise ValueError(
                "fact_machine_hour is missing required canonical energy columns: "
                + ", ".join(missing_columns)
            )

        return self._build_energy_dataframe(fact_df)

    @classmethod
    def _build_energy_dataframe(cls, fact_df: pd.DataFrame) -> pd.DataFrame:
        energy_df = fact_df.copy()
        energy_df["datetime"] = pd.to_datetime(energy_df["hour_ts"], errors="coerce")
        energy_df["month_year"] = energy_df["datetime"].dt.strftime("%B %Y")
        energy_df["machine_id"] = energy_df["canonical_machine_id"]
        energy_df["production_qty"] = energy_df["good_qty"]
        energy_df["kwh_per_good_unit"] = energy_df.apply(cls._derive_kwh_per_good_unit, axis=1)
        energy_df["hour_of_day"] = energy_df["datetime"].dt.hour

        for _, energy_column in _MINUTE_BUCKET_COLUMNS:
            energy_df[energy_column] = 0.0
        energy_df["unallocated_energy_kwh"] = 0.0
        energy_df["energy_attribution_method"] = "unallocated"

        minute_columns = [minute_column for minute_column, _ in _MINUTE_BUCKET_COLUMNS]
        energy_df[minute_columns] = energy_df[minute_columns].fillna(0.0)
        energy_df["tracked_minutes"] = energy_df[minute_columns].sum(axis=1)

        for row_index, row in energy_df.iterrows():
            energy_total_kwh = cls._float_or_zero(row.get("energy_total_kwh"))
            if energy_total_kwh <= 0:
                energy_df.at[row_index, "energy_attribution_method"] = "no_energy"
                continue

            tracked_minutes = cls._float_or_zero(row.get("tracked_minutes"))
            if tracked_minutes > 0:
                allocated_energy = 0.0
                for minute_column, energy_column in _MINUTE_BUCKET_COLUMNS:
                    minute_value = cls._float_or_zero(row.get(minute_column))
                    if minute_value <= 0:
                        continue
                    bucket_energy = energy_total_kwh * (minute_value / tracked_minutes)
                    energy_df.at[row_index, energy_column] = bucket_energy
                    allocated_energy += bucket_energy

                residual_energy = energy_total_kwh - allocated_energy
                if residual_energy > 1e-9:
                    energy_df.at[row_index, "unallocated_energy_kwh"] = residual_energy
                energy_df.at[row_index, "energy_attribution_method"] = "minute_share"
                continue

            state_bucket_column = _STATE_TO_BUCKET_COLUMN.get(cls._clean_text(row.get("machine_state")))
            if state_bucket_column is not None:
                energy_df.at[row_index, state_bucket_column] = energy_total_kwh
                energy_df.at[row_index, "energy_attribution_method"] = "machine_state_fallback"
            else:
                energy_df.at[row_index, "unallocated_energy_kwh"] = energy_total_kwh
                energy_df.at[row_index, "energy_attribution_method"] = "unallocated"

        energy_df = energy_df.loc[:, CANONICAL_ENERGY_EXPORT_COLUMNS].copy()
        energy_df = energy_df.sort_values(["datetime", "machine_id"]).reset_index(drop=True)
        return energy_df

    @staticmethod
    def _derive_kwh_per_good_unit(row: pd.Series) -> float | None:
        energy_total_kwh = CanonicalEnergyReader._float_or_none(row.get("energy_total_kwh"))
        good_qty = CanonicalEnergyReader._float_or_none(row.get("good_qty"))
        if energy_total_kwh is None or good_qty is None or good_qty <= 0:
            return None
        return energy_total_kwh / good_qty

    @staticmethod
    def _month_key_to_label(month_key: object) -> str | None:
        month_text = CanonicalEnergyReader._clean_text(month_key)
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
        next_month = month_dt + pd.offsets.MonthBegin(1)
        start_ts = month_dt.strftime("%Y-%m-01T00:00:00")
        end_ts = next_month.strftime("%Y-%m-01T00:00:00")
        return start_ts, end_ts

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
        return float(value)

    @staticmethod
    def _float_or_zero(value: object) -> float:
        cleaned = CanonicalEnergyReader._float_or_none(value)
        return 0.0 if cleaned is None else cleaned

    @staticmethod
    def _sum_or_none(series: pd.Series) -> float | None:
        cleaned = series.dropna()
        if cleaned.empty:
            return None
        return float(cleaned.sum())

    @staticmethod
    def _mean_or_none(series: pd.Series) -> float | None:
        cleaned = series.dropna()
        if cleaned.empty:
            return None
        return float(cleaned.mean())

    @staticmethod
    def _safe_divide(numerator: object, denominator: object) -> float | None:
        clean_numerator = CanonicalEnergyReader._float_or_none(numerator)
        clean_denominator = CanonicalEnergyReader._float_or_none(denominator)
        if clean_numerator is None or clean_denominator is None or clean_denominator <= 0:
            return None
        return clean_numerator / clean_denominator

    @staticmethod
    def _select_efficiency_rows(energy_df: pd.DataFrame) -> pd.DataFrame:
        if energy_df.empty:
            return energy_df.copy()

        return energy_df[
            energy_df["energy_total_kwh"].notna()
            & energy_df["good_qty"].notna()
            & (energy_df["good_qty"] > 0)
        ].copy()
