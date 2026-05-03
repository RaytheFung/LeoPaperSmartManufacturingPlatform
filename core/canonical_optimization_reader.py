from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from core.runtime_paths import get_database_path


CANONICAL_OPTIMIZATION_REQUIRED_COLUMNS = [
    "canonical_machine_id",
    "hour_ts",
    "machine_state",
    "energy_total_kwh",
    "setup_minutes",
    "production_minutes",
    "planned_stop_minutes",
    "unplanned_stop_minutes",
    "idle_minutes",
    "good_qty",
    "scrap_qty",
    "hours_since_last_maintenance",
]

CANONICAL_OPTIMIZATION_SUMMARY_COLUMNS = [
    "canonical_machine_id",
    "machine_id",
    "machine_family",
    "eligible_rows",
    "total_energy_kwh",
    "total_good_qty",
    "total_scrap_qty",
    "total_setup_minutes",
    "total_production_minutes",
    "total_planned_stop_minutes",
    "total_unplanned_stop_minutes",
    "total_idle_minutes",
    "avg_kwh_per_good_unit",
    "avg_hours_since_last_maintenance",
    "maintenance_state_hours",
    "production_state_hours",
    "setup_state_hours",
    "scrap_rate",
    "productive_hours",
    "nonproductive_hours",
    "utilization_proxy",
    "opportunity_score",
    "opportunity_flag",
    "top_driver",
    "energy_intensity_component",
    "nonproductive_component",
    "maintenance_recency_component",
    "scrap_component",
]

CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS = [
    "hour_of_day",
    "shift_label",
    "eligible_rows",
    "distinct_machines",
    "total_energy_kwh",
    "total_good_qty",
    "avg_kwh_per_good_unit",
    "productive_hours",
    "nonproductive_hours",
    "utilization_proxy",
    "schedule_score",
    "schedule_flag",
    "top_driver",
]

CANONICAL_OPTIMIZATION_TEAM_COLUMNS = [
    "team_leader",
    "rows_with_team",
    "distinct_machines",
    "production_rows",
    "total_energy_kwh",
    "total_good_qty",
    "total_scrap_qty",
    "avg_kwh_per_good_unit",
    "scrap_rate",
    "productive_hours",
    "nonproductive_hours",
    "utilization_proxy",
    "avg_hours_since_last_maintenance",
    "team_effectiveness_score",
    "team_band",
    "top_driver",
]


class CanonicalOptimizationReader:
    """Month-scoped Optimization helper backed by fact_machine_hour only."""

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

    def build_machine_summary(self, month_year: str) -> pd.DataFrame:
        working_df = self._prepare_month_fact_dataframe(month_year)
        if working_df.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_SUMMARY_COLUMNS)

        grouped = (
            working_df.groupby("canonical_machine_id", dropna=False)
            .agg(
                eligible_rows=("eligible_for_energy_intensity", "sum"),
                total_energy_kwh=("energy_total_kwh", "sum"),
                total_good_qty=("good_qty", "sum"),
                total_scrap_qty=("scrap_qty", "sum"),
                total_setup_minutes=("setup_minutes", "sum"),
                total_production_minutes=("production_minutes", "sum"),
                total_planned_stop_minutes=("planned_stop_minutes", "sum"),
                total_unplanned_stop_minutes=("unplanned_stop_minutes", "sum"),
                total_idle_minutes=("idle_minutes", "sum"),
                safe_energy_kwh=("safe_energy_kwh", "sum"),
                safe_good_qty=("safe_good_qty", "sum"),
                avg_hours_since_last_maintenance=("hours_since_last_maintenance", "mean"),
                maintenance_state_hours=("machine_state", lambda values: int((values == "maintenance").sum())),
                production_state_hours=("machine_state", lambda values: int((values == "production").sum())),
                setup_state_hours=("machine_state", lambda values: int((values == "setup_changeover").sum())),
            )
            .reset_index()
        )

        grouped["machine_id"] = grouped["canonical_machine_id"]
        grouped["machine_family"] = grouped["canonical_machine_id"].apply(self._derive_machine_family)
        grouped["avg_kwh_per_good_unit"] = grouped.apply(
            lambda row: self._safe_divide(row["safe_energy_kwh"], row["safe_good_qty"]),
            axis=1,
        )
        grouped["scrap_rate"] = grouped.apply(
            lambda row: self._safe_divide(
                row["total_scrap_qty"],
                self._coalesce_number(row["total_good_qty"]) + self._coalesce_number(row["total_scrap_qty"]),
            ),
            axis=1,
        )
        grouped["productive_hours"] = grouped["total_production_minutes"].fillna(0.0) / 60.0
        grouped["nonproductive_hours"] = (
            grouped["total_setup_minutes"].fillna(0.0)
            + grouped["total_planned_stop_minutes"].fillna(0.0)
            + grouped["total_unplanned_stop_minutes"].fillna(0.0)
            + grouped["total_idle_minutes"].fillna(0.0)
        ) / 60.0
        tracked_minutes = (
            grouped["total_production_minutes"].fillna(0.0)
            + grouped["total_setup_minutes"].fillna(0.0)
            + grouped["total_planned_stop_minutes"].fillna(0.0)
            + grouped["total_unplanned_stop_minutes"].fillna(0.0)
            + grouped["total_idle_minutes"].fillna(0.0)
        )
        grouped["utilization_proxy"] = tracked_minutes.where(
            tracked_minutes > 0,
            pd.NA,
        )
        grouped["utilization_proxy"] = grouped["total_production_minutes"].fillna(0.0) / grouped["utilization_proxy"]
        grouped["nonproductive_share"] = grouped.apply(
            lambda row: self._safe_divide(
                row["nonproductive_hours"],
                self._coalesce_number(row["productive_hours"]) + self._coalesce_number(row["nonproductive_hours"]),
            ),
            axis=1,
        )

        self._apply_opportunity_scoring(grouped)

        summary_df = grouped.loc[:, CANONICAL_OPTIMIZATION_SUMMARY_COLUMNS].copy()
        summary_df = summary_df.sort_values(
            ["opportunity_score", "total_energy_kwh", "canonical_machine_id"],
            ascending=[False, False, True],
        ).reset_index(drop=True)
        return summary_df

    def build_schedule_summary(self, month_year: str) -> pd.DataFrame:
        working_df = self._prepare_month_fact_dataframe(month_year)
        if working_df.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS)

        schedule_df = working_df[working_df["hour_of_day"].notna()].copy()
        if schedule_df.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS)

        grouped = (
            schedule_df.groupby(["hour_of_day", "shift_label"], dropna=False)
            .agg(
                eligible_rows=("eligible_for_energy_intensity", "sum"),
                distinct_machines=("canonical_machine_id", "nunique"),
                total_energy_kwh=("safe_energy_kwh", "sum"),
                total_good_qty=("safe_good_qty", "sum"),
                tracked_minutes=("tracked_minutes", "sum"),
                production_minutes=("production_minutes", "sum"),
                nonproductive_minutes=("nonproductive_minutes", "sum"),
            )
            .reset_index()
        )
        grouped = grouped[grouped["eligible_rows"] > 0].copy()
        if grouped.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS)

        grouped["avg_kwh_per_good_unit"] = grouped.apply(
            lambda row: self._safe_divide(row["total_energy_kwh"], row["total_good_qty"]),
            axis=1,
        )
        grouped["productive_hours"] = grouped["production_minutes"].fillna(0.0) / 60.0
        grouped["nonproductive_hours"] = grouped["nonproductive_minutes"].fillna(0.0) / 60.0
        grouped["utilization_proxy"] = grouped.apply(
            lambda row: self._safe_divide(row["production_minutes"], row["tracked_minutes"]),
            axis=1,
        )

        efficiency_component = 1.0 - self._normalize_series(grouped["avg_kwh_per_good_unit"])
        utilization_component = grouped["utilization_proxy"].fillna(0.0).clip(lower=0.0, upper=1.0)
        volume_component = self._normalize_series(grouped["total_good_qty"])

        grouped["schedule_score"] = (
            efficiency_component * 0.55
            + utilization_component * 0.30
            + volume_component * 0.15
        ).round(4)
        grouped["schedule_flag"] = grouped["schedule_score"].apply(self._schedule_flag)
        grouped["top_driver"] = [
            self._schedule_driver_label(components)
            for components in zip(
                efficiency_component.tolist(),
                utilization_component.tolist(),
                volume_component.tolist(),
            )
        ]

        result_df = grouped.loc[:, CANONICAL_OPTIMIZATION_SCHEDULE_COLUMNS].copy()
        result_df = result_df.sort_values(
            ["schedule_score", "hour_of_day"],
            ascending=[False, True],
        ).reset_index(drop=True)
        result_df["hour_of_day"] = result_df["hour_of_day"].astype(int)
        result_df["eligible_rows"] = result_df["eligible_rows"].astype(int)
        result_df["distinct_machines"] = result_df["distinct_machines"].astype(int)
        return result_df

    def build_team_insights(self, month_year: str) -> pd.DataFrame:
        working_df = self._prepare_month_fact_dataframe(month_year)
        if working_df.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_TEAM_COLUMNS)

        team_df = working_df.copy()
        team_df["team_leader"] = team_df["team_leader"].fillna("").astype(str).str.strip()
        team_df = team_df[team_df["team_leader"] != ""].copy()
        if team_df.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_TEAM_COLUMNS)

        grouped = (
            team_df.groupby("team_leader", dropna=False)
            .agg(
                rows_with_team=("team_leader", "size"),
                distinct_machines=("canonical_machine_id", "nunique"),
                production_rows=("machine_state", lambda values: int((values == "production").sum())),
                total_energy_kwh=("safe_energy_kwh", "sum"),
                total_good_qty=("safe_good_qty", "sum"),
                total_scrap_qty=("scrap_qty", "sum"),
                tracked_minutes=("tracked_minutes", "sum"),
                production_minutes=("production_minutes", "sum"),
                nonproductive_minutes=("nonproductive_minutes", "sum"),
                avg_hours_since_last_maintenance=("hours_since_last_maintenance", "mean"),
            )
            .reset_index()
        )
        grouped = grouped[grouped["total_good_qty"] > 0].copy()
        if grouped.empty:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_TEAM_COLUMNS)

        grouped["avg_kwh_per_good_unit"] = grouped.apply(
            lambda row: self._safe_divide(row["total_energy_kwh"], row["total_good_qty"]),
            axis=1,
        )
        grouped["scrap_rate"] = grouped.apply(
            lambda row: self._safe_divide(
                row["total_scrap_qty"],
                self._coalesce_number(row["total_good_qty"]) + self._coalesce_number(row["total_scrap_qty"]),
            ),
            axis=1,
        )
        grouped["productive_hours"] = grouped["production_minutes"].fillna(0.0) / 60.0
        grouped["nonproductive_hours"] = grouped["nonproductive_minutes"].fillna(0.0) / 60.0
        grouped["utilization_proxy"] = grouped.apply(
            lambda row: self._safe_divide(row["production_minutes"], row["tracked_minutes"]),
            axis=1,
        )

        efficiency_component = 1.0 - self._normalize_series(grouped["avg_kwh_per_good_unit"])
        utilization_component = grouped["utilization_proxy"].fillna(0.0).clip(lower=0.0, upper=1.0)
        scrap_component = 1.0 - grouped["scrap_rate"].fillna(0.0).clip(lower=0.0, upper=1.0)
        volume_component = self._normalize_series(grouped["total_good_qty"])

        grouped["team_effectiveness_score"] = (
            efficiency_component * 0.45
            + utilization_component * 0.25
            + scrap_component * 0.20
            + volume_component * 0.10
        ).round(4)
        grouped["team_band"] = grouped["team_effectiveness_score"].apply(self._team_band)
        grouped["top_driver"] = [
            self._team_driver_label(components)
            for components in zip(
                efficiency_component.tolist(),
                utilization_component.tolist(),
                scrap_component.tolist(),
                volume_component.tolist(),
            )
        ]

        result_df = grouped.loc[:, CANONICAL_OPTIMIZATION_TEAM_COLUMNS].copy()
        result_df = result_df.sort_values(
            ["team_effectiveness_score", "total_good_qty", "team_leader"],
            ascending=[False, False, True],
        ).reset_index(drop=True)
        result_df["rows_with_team"] = result_df["rows_with_team"].astype(int)
        result_df["distinct_machines"] = result_df["distinct_machines"].astype(int)
        result_df["production_rows"] = result_df["production_rows"].astype(int)
        return result_df

    def build_month_metrics(self, summary_df: pd.DataFrame) -> dict[str, float | int | None]:
        if summary_df.empty:
            return {
                "machine_count_in_canonical_optimization_view": 0,
                "total_energy_kwh": None,
                "total_good_qty": None,
                "machines_with_opportunity_score": 0,
                "avg_utilization_proxy": None,
            }

        return {
            "machine_count_in_canonical_optimization_view": int(summary_df["canonical_machine_id"].nunique()),
            "total_energy_kwh": self._sum_or_none(summary_df["total_energy_kwh"]),
            "total_good_qty": self._sum_or_none(summary_df["total_good_qty"]),
            "machines_with_opportunity_score": int(summary_df["opportunity_score"].notna().sum()),
            "avg_utilization_proxy": self._mean_or_none(summary_df["utilization_proxy"]),
        }

    def _read_month_fact_dataframe(self, month_year: str) -> pd.DataFrame:
        if not self.fact_machine_hour_exists():
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_REQUIRED_COLUMNS)

        bounds = self._month_label_to_bounds(month_year)
        if bounds is None:
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_REQUIRED_COLUMNS)
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
            return pd.DataFrame(columns=CANONICAL_OPTIMIZATION_REQUIRED_COLUMNS)

        missing_columns = [
            column for column in CANONICAL_OPTIMIZATION_REQUIRED_COLUMNS if column not in fact_df.columns
        ]
        if missing_columns:
            raise ValueError(
                "fact_machine_hour is missing required Optimization columns: "
                + ", ".join(missing_columns)
            )

        return fact_df

    def _apply_opportunity_scoring(self, summary_df: pd.DataFrame) -> None:
        efficiency_component = self._normalize_series(summary_df["avg_kwh_per_good_unit"])
        maintenance_component = self._normalize_series(summary_df["avg_hours_since_last_maintenance"])
        nonproductive_component = summary_df["nonproductive_share"].fillna(0.0).clip(lower=0.0, upper=1.0)
        scrap_component = summary_df["scrap_rate"].fillna(0.0).clip(lower=0.0, upper=1.0)

        summary_df["energy_intensity_component"] = efficiency_component.round(4)
        summary_df["nonproductive_component"] = nonproductive_component.round(4)
        summary_df["maintenance_recency_component"] = maintenance_component.round(4)
        summary_df["scrap_component"] = scrap_component.round(4)
        summary_df["opportunity_score"] = (
            efficiency_component * 0.40
            + nonproductive_component * 0.30
            + maintenance_component * 0.15
            + scrap_component * 0.15
        ).round(4)
        summary_df["opportunity_flag"] = summary_df["opportunity_score"].apply(self._opportunity_flag)
        summary_df["top_driver"] = [
            self._top_driver_label(components)
            for components in zip(
                efficiency_component.tolist(),
                nonproductive_component.tolist(),
                maintenance_component.tolist(),
                scrap_component.tolist(),
            )
        ]

    def _prepare_month_fact_dataframe(self, month_year: str) -> pd.DataFrame:
        fact_df = self._read_month_fact_dataframe(month_year)
        if fact_df.empty:
            return fact_df

        working_df = fact_df.copy()
        numeric_columns = [
            "energy_total_kwh",
            "setup_minutes",
            "production_minutes",
            "planned_stop_minutes",
            "unplanned_stop_minutes",
            "idle_minutes",
            "good_qty",
            "scrap_qty",
            "hours_since_last_maintenance",
        ]
        for column in numeric_columns:
            working_df[column] = pd.to_numeric(working_df[column], errors="coerce")

        working_df["machine_state"] = working_df["machine_state"].fillna("").astype(str).str.strip()
        safe_qty_mask = (
            working_df["energy_total_kwh"].notna()
            & working_df["good_qty"].notna()
            & (working_df["good_qty"] > 0)
        )
        working_df["safe_energy_kwh"] = working_df["energy_total_kwh"].where(safe_qty_mask, 0.0)
        working_df["safe_good_qty"] = working_df["good_qty"].where(safe_qty_mask, 0.0)
        working_df["eligible_for_energy_intensity"] = safe_qty_mask.astype(int)

        working_df["tracked_minutes"] = (
            working_df["production_minutes"].fillna(0.0)
            + working_df["setup_minutes"].fillna(0.0)
            + working_df["planned_stop_minutes"].fillna(0.0)
            + working_df["unplanned_stop_minutes"].fillna(0.0)
            + working_df["idle_minutes"].fillna(0.0)
        )
        working_df["nonproductive_minutes"] = (
            working_df["setup_minutes"].fillna(0.0)
            + working_df["planned_stop_minutes"].fillna(0.0)
            + working_df["unplanned_stop_minutes"].fillna(0.0)
            + working_df["idle_minutes"].fillna(0.0)
        )

        hour_dt = pd.to_datetime(working_df["hour_ts"], errors="coerce")
        working_df["hour_of_day"] = hour_dt.dt.hour
        working_df["shift_label"] = working_df["hour_of_day"].apply(self._shift_label)
        return working_df

    @staticmethod
    def _top_driver_label(components: tuple[float, float, float, float]) -> str:
        labels = [
            "High kWh per good unit",
            "High non-productive share",
            "Long time since last maintenance",
            "Elevated scrap rate",
        ]
        max_component = max(components)
        if max_component <= 0:
            return "No strong canonical opportunity signal"
        return labels[components.index(max_component)]

    @staticmethod
    def _schedule_driver_label(components: tuple[float, float, float]) -> str:
        labels = [
            "Low kWh per good unit",
            "High utilization",
            "High output coverage",
        ]
        max_component = max(components)
        if max_component <= 0:
            return "No strong canonical scheduling signal"
        return labels[components.index(max_component)]

    @staticmethod
    def _team_driver_label(components: tuple[float, float, float, float]) -> str:
        labels = [
            "Low kWh per good unit",
            "High utilization",
            "Low scrap rate",
            "High output coverage",
        ]
        max_component = max(components)
        if max_component <= 0:
            return "No strong canonical team signal"
        return labels[components.index(max_component)]

    @staticmethod
    def _opportunity_flag(score: object) -> str:
        if score is None or pd.isna(score):
            return "No signal"
        if float(score) >= 0.55:
            return "High"
        if float(score) >= 0.30:
            return "Medium"
        return "Low"

    @staticmethod
    def _schedule_flag(score: object) -> str:
        if score is None or pd.isna(score):
            return "No signal"
        if float(score) >= 0.67:
            return "Preferred"
        if float(score) >= 0.40:
            return "Watch"
        return "Avoid"

    @staticmethod
    def _team_band(score: object) -> str:
        if score is None or pd.isna(score):
            return "No signal"
        if float(score) >= 0.67:
            return "Strong"
        if float(score) >= 0.40:
            return "Stable"
        return "Watch"

    @staticmethod
    def _normalize_series(series: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() == 0:
            return pd.Series([0.0] * len(series), index=series.index, dtype=float)

        min_value = numeric.min(skipna=True)
        max_value = numeric.max(skipna=True)
        if pd.isna(min_value) or pd.isna(max_value) or max_value <= min_value:
            return pd.Series([0.0] * len(series), index=series.index, dtype=float)

        normalized = (numeric - min_value) / (max_value - min_value)
        return normalized.fillna(0.0).clip(lower=0.0, upper=1.0)

    @staticmethod
    def _month_key_to_label(month_key: object) -> str | None:
        month_text = CanonicalOptimizationReader._clean_text(month_key)
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
    def _shift_label(hour_of_day: object) -> str:
        if hour_of_day is None or pd.isna(hour_of_day):
            return "Unknown"
        hour_value = int(hour_of_day)
        if 7 <= hour_value < 15:
            return "Day"
        if 15 <= hour_value < 23:
            return "Evening"
        return "Night"

    @staticmethod
    def _clean_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _derive_machine_family(machine_id: object) -> str | None:
        clean_machine_id = CanonicalOptimizationReader._clean_text(machine_id)
        if clean_machine_id is None:
            return None
        if "-" in clean_machine_id:
            return clean_machine_id.split("-", 1)[0]
        return clean_machine_id

    @staticmethod
    def _coalesce_number(value: object) -> float:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)

    @staticmethod
    def _safe_divide(numerator: object, denominator: object) -> float | None:
        if numerator is None or denominator is None:
            return None
        if pd.isna(numerator) or pd.isna(denominator):
            return None
        denominator_value = float(denominator)
        if denominator_value <= 0:
            return None
        return float(numerator) / denominator_value

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
