from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Sequence

import pandas as pd

from core.runtime_paths import get_database_path


RECENT_HISTORY_LIMIT = 50


def parse_maintenance_month_label(month_label: object) -> pd.Timestamp | None:
    if month_label is None:
        return None
    month_text = str(month_label).strip()
    if not month_text:
        return None
    parsed = pd.to_datetime(month_text, format="%B %Y", errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed


def sort_maintenance_month_labels(
    month_labels: Sequence[object],
    *,
    descending: bool = False,
) -> list[str]:
    parsed_rows: list[tuple[pd.Timestamp, str]] = []
    invalid_rows: list[str] = []
    for value in month_labels:
        month_text = _clean_text(value)
        if month_text is None:
            continue
        parsed = parse_maintenance_month_label(month_text)
        if parsed is None:
            invalid_rows.append(month_text)
        else:
            parsed_rows.append((parsed, month_text))

    parsed_rows.sort(key=lambda row: row[0], reverse=descending)
    invalid_rows.sort(reverse=descending)
    return [label for _, label in parsed_rows] + invalid_rows


class MaintenanceEvidenceReader:
    """Read-only maintenance evidence helper backed by existing maintenance tables."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_database_path())

    def build_coverage_snapshot(self) -> dict[str, object]:
        snapshot = {
            "maintenance_records_available": False,
            "records_stored": 0,
            "matched_records_stored": 0,
            "integrated_machine_count": 0,
            "total_three_way_matches": 0,
            "integration_coverage_ratio": None,
            "months_covered": [],
            "months_covered_count": 0,
            "earliest_month": None,
            "latest_month": None,
            "latest_maintenance_datetime": None,
            "latest_maintenance_datetime_label": "n/a",
            "legacy_risk_rows": 0,
        }

        conn = sqlite3.connect(self.db_path)
        try:
            if not _table_exists(conn, "maintenance_records"):
                return snapshot

            snapshot["maintenance_records_available"] = True
            totals = pd.read_sql_query(
                """
                SELECT
                    COUNT(*) AS records_stored,
                    SUM(
                        CASE
                            WHEN is_three_way_match = 1 AND machine_id IS NOT NULL THEN 1
                            ELSE 0
                        END
                    ) AS matched_records_stored,
                    COUNT(
                        DISTINCT CASE
                            WHEN is_three_way_match = 1 AND machine_id IS NOT NULL THEN machine_id
                            ELSE NULL
                        END
                    ) AS integrated_machine_count,
                    MAX(transaction_date) AS latest_maintenance_datetime
                FROM maintenance_records
                """,
                conn,
            ).iloc[0]

            snapshot["records_stored"] = int(totals["records_stored"] or 0)
            snapshot["matched_records_stored"] = int(totals["matched_records_stored"] or 0)
            snapshot["integrated_machine_count"] = int(totals["integrated_machine_count"] or 0)
            latest_dt = pd.to_datetime(totals["latest_maintenance_datetime"], errors="coerce")
            snapshot["latest_maintenance_datetime"] = latest_dt
            snapshot["latest_maintenance_datetime_label"] = format_maintenance_timestamp(latest_dt)

            if _table_exists(conn, "three_way_matches"):
                total_three_way_matches = conn.execute(
                    "SELECT COUNT(*) FROM three_way_matches"
                ).fetchone()
                snapshot["total_three_way_matches"] = int(total_three_way_matches[0] or 0)
                if snapshot["total_three_way_matches"] > 0:
                    snapshot["integration_coverage_ratio"] = (
                        snapshot["integrated_machine_count"] / snapshot["total_three_way_matches"]
                    )

            month_rows = pd.read_sql_query(
                """
                SELECT DISTINCT month_year
                FROM maintenance_records
                WHERE month_year IS NOT NULL
                  AND trim(month_year) <> ''
                """,
                conn,
            )
            sorted_months = sort_maintenance_month_labels(month_rows["month_year"].tolist())
            snapshot["months_covered"] = sorted_months
            snapshot["months_covered_count"] = len(sorted_months)
            snapshot["earliest_month"] = sorted_months[0] if sorted_months else None
            snapshot["latest_month"] = sorted_months[-1] if sorted_months else None

            if _table_exists(conn, "maintenance_ml_features"):
                risk_row = conn.execute("SELECT COUNT(*) FROM maintenance_ml_features").fetchone()
                snapshot["legacy_risk_rows"] = int(risk_row[0] or 0)
        finally:
            conn.close()

        return snapshot

    def build_machine_catalog(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            if not _table_exists(conn, "maintenance_records"):
                return pd.DataFrame(
                    columns=["machine_id", "total_events", "months_covered_count", "latest_maintenance_datetime"]
                )

            machine_df = pd.read_sql_query(
                """
                SELECT
                    machine_id,
                    COUNT(*) AS total_events,
                    COUNT(DISTINCT month_year) AS months_covered_count,
                    MAX(transaction_date) AS latest_maintenance_datetime
                FROM maintenance_records
                WHERE is_three_way_match = 1
                  AND machine_id IS NOT NULL
                  AND trim(machine_id) <> ''
                GROUP BY machine_id
                ORDER BY total_events DESC, latest_maintenance_datetime DESC, machine_id ASC
                """,
                conn,
            )
        finally:
            conn.close()

        if machine_df.empty:
            return machine_df

        machine_df["latest_maintenance_datetime"] = pd.to_datetime(
            machine_df["latest_maintenance_datetime"], errors="coerce"
        )
        machine_df["latest_maintenance_datetime_label"] = machine_df[
            "latest_maintenance_datetime"
        ].apply(format_maintenance_timestamp)
        machine_df["total_events"] = machine_df["total_events"].fillna(0).astype(int)
        machine_df["months_covered_count"] = machine_df["months_covered_count"].fillna(0).astype(int)
        return machine_df.reset_index(drop=True)

    def get_available_months(self) -> list[str]:
        return self.build_coverage_snapshot()["months_covered"]

    def build_monthly_record_counts(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            if not _table_exists(conn, "maintenance_records"):
                return pd.DataFrame(columns=["month_year", "count"])

            monthly_df = pd.read_sql_query(
                """
                SELECT month_year, COUNT(*) AS count
                FROM maintenance_records
                WHERE month_year IS NOT NULL
                  AND trim(month_year) <> ''
                GROUP BY month_year
                """,
                conn,
            )
        finally:
            conn.close()

        if monthly_df.empty:
            return monthly_df

        monthly_df["month_sort_key"] = monthly_df["month_year"].apply(parse_maintenance_month_label)
        monthly_df = monthly_df.sort_values(
            ["month_sort_key", "month_year"],
            ascending=[True, True],
            na_position="last",
        ).reset_index(drop=True)
        return monthly_df.loc[:, ["month_year", "count"]]

    def build_work_order_distribution(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            if not _table_exists(conn, "maintenance_records"):
                return pd.DataFrame(columns=["work_order_type", "count"])

            work_order_df = pd.read_sql_query(
                """
                SELECT work_order_type, COUNT(*) AS count
                FROM maintenance_records
                WHERE work_order_type IS NOT NULL
                  AND trim(work_order_type) <> ''
                GROUP BY work_order_type
                ORDER BY count DESC, work_order_type ASC
                """,
                conn,
            )
        finally:
            conn.close()

        return work_order_df

    def build_machine_evidence(
        self,
        machine_id: str,
        *,
        recent_window_limit: int = RECENT_HISTORY_LIMIT,
        as_of: pd.Timestamp | None = None,
    ) -> dict[str, object]:
        recent_window_limit = max(int(recent_window_limit), 1)
        evidence = {
            "machine_id": machine_id,
            "machine_has_history": False,
            "all_time_event_count": 0,
            "recent_window_event_count": 0,
            "recent_window_limit": recent_window_limit,
            "pm_ratio_all_time": None,
            "pm_ratio_recent_window": None,
            "latest_maintenance_datetime": None,
            "latest_maintenance_datetime_label": "n/a",
            "latest_work_order_type": None,
            "days_since_last_maintenance": None,
            "months_covered": [],
            "months_covered_count": 0,
            "history_window_limited": False,
            "history_window_note": f"No matched maintenance history is stored for {machine_id}.",
            "recent_history_df": pd.DataFrame(
                columns=[
                    "maintenance_datetime",
                    "work_order",
                    "work_order_type",
                    "material_code",
                    "month_year",
                    "days_since_previous",
                ]
            ),
        }

        machine_text = _clean_text(machine_id)
        if machine_text is None:
            return evidence

        conn = sqlite3.connect(self.db_path)
        try:
            if not _table_exists(conn, "maintenance_records"):
                return evidence

            history_df = pd.read_sql_query(
                """
                SELECT
                    id,
                    transaction_date,
                    work_order,
                    work_order_type,
                    material_code,
                    month_year
                FROM maintenance_records
                WHERE is_three_way_match = 1
                  AND machine_id = ?
                ORDER BY
                    CASE WHEN transaction_date IS NULL OR trim(transaction_date) = '' THEN 1 ELSE 0 END ASC,
                    transaction_date DESC,
                    id DESC
                """,
                conn,
                params=(machine_text,),
            )
        finally:
            conn.close()

        if history_df.empty:
            return evidence

        history_df["maintenance_datetime"] = pd.to_datetime(
            history_df["transaction_date"], errors="coerce"
        )
        history_df["work_order_type"] = history_df["work_order_type"].apply(_clean_text)
        history_df["days_since_previous"] = pd.NA

        dated_history_df = history_df[history_df["maintenance_datetime"].notna()].copy()
        if not dated_history_df.empty:
            dated_history_df = dated_history_df.sort_values(
                ["maintenance_datetime", "id"],
                ascending=[True, True],
            ).reset_index(drop=True)
            dated_history_df["days_since_previous"] = (
                dated_history_df["maintenance_datetime"].diff().dt.total_seconds() / 86400.0
            )
            history_df = history_df.merge(
                dated_history_df.loc[:, ["id", "days_since_previous"]],
                on="id",
                how="left",
                suffixes=("", "_computed"),
            )
            history_df["days_since_previous"] = history_df["days_since_previous_computed"]
            history_df = history_df.drop(columns=["days_since_previous_computed"])

        history_df = history_df.sort_values(
            ["maintenance_datetime", "id"],
            ascending=[False, False],
            na_position="last",
        ).reset_index(drop=True)

        recent_history_df = history_df.head(recent_window_limit).copy()
        total_events = int(len(history_df))
        recent_events = int(len(recent_history_df))
        latest_row = history_df.iloc[0]
        latest_dt = latest_row["maintenance_datetime"]
        months_covered = sort_maintenance_month_labels(
            history_df["month_year"].dropna().astype(str).unique().tolist()
        )
        all_time_pm_ratio = self._pm_ratio(history_df["work_order_type"])
        recent_pm_ratio = self._pm_ratio(recent_history_df["work_order_type"])

        evidence["machine_has_history"] = True
        evidence["all_time_event_count"] = total_events
        evidence["recent_window_event_count"] = recent_events
        evidence["pm_ratio_all_time"] = all_time_pm_ratio
        evidence["pm_ratio_recent_window"] = recent_pm_ratio
        evidence["latest_maintenance_datetime"] = latest_dt
        evidence["latest_maintenance_datetime_label"] = format_maintenance_timestamp(latest_dt)
        evidence["latest_work_order_type"] = _clean_text(latest_row.get("work_order_type"))
        evidence["days_since_last_maintenance"] = self._days_since(latest_dt, as_of=as_of)
        evidence["months_covered"] = months_covered
        evidence["months_covered_count"] = len(months_covered)
        evidence["history_window_limited"] = total_events > recent_window_limit
        evidence["history_window_note"] = (
            f"Showing the latest {recent_window_limit} events for readability."
            if evidence["history_window_limited"]
            else "All stored matched maintenance events fit within the current history window."
        )
        evidence["recent_history_df"] = recent_history_df.loc[
            :,
            [
                "maintenance_datetime",
                "work_order",
                "work_order_type",
                "material_code",
                "month_year",
                "days_since_previous",
            ],
        ].copy()
        return evidence

    def build_machine_context_payload(
        self,
        machine_id: str,
        *,
        recent_window_limit: int = RECENT_HISTORY_LIMIT,
        as_of: pd.Timestamp | None = None,
    ) -> dict[str, object]:
        evidence = self.build_machine_evidence(
            machine_id,
            recent_window_limit=recent_window_limit,
            as_of=as_of,
        )
        if not evidence["machine_has_history"]:
            return {
                "available": False,
                "machine_id": machine_id,
                "reason": f"No matched maintenance evidence is stored for {machine_id}.",
            }

        return {
            "available": True,
            "machine_id": machine_id,
            "days_since_last_maintenance": evidence["days_since_last_maintenance"],
            "total_events": evidence["all_time_event_count"],
            "pm_ratio_all_time": evidence["pm_ratio_all_time"],
            "recent_events_shown": evidence["recent_window_event_count"],
            "recent_window_limit": evidence["recent_window_limit"],
            "latest_work_order_type": evidence["latest_work_order_type"] or "unknown",
            "latest_maintenance_datetime_label": evidence["latest_maintenance_datetime_label"],
            "months_covered_count": evidence["months_covered_count"],
            "history_window_limited": evidence["history_window_limited"],
            "history_window_note": evidence["history_window_note"],
        }

    @staticmethod
    def _pm_ratio(work_order_types: pd.Series) -> float | None:
        cleaned = work_order_types.dropna().astype(str)
        if cleaned.empty:
            return None
        return float((cleaned.str.upper() == "PM").sum() / len(cleaned))

    @staticmethod
    def _days_since(
        maintenance_datetime: pd.Timestamp | None,
        *,
        as_of: pd.Timestamp | None = None,
    ) -> int | None:
        if maintenance_datetime is None or pd.isna(maintenance_datetime):
            return None
        anchor = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.now()
        if pd.isna(anchor):
            return None
        delta = anchor - maintenance_datetime
        return max(int(delta.total_seconds() // 86400), 0)


def format_maintenance_timestamp(value: object) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return "n/a"
    return timestamp.strftime("%Y-%m-%d %H:%M")


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "RECENT_HISTORY_LIMIT",
    "MaintenanceEvidenceReader",
    "format_maintenance_timestamp",
    "parse_maintenance_month_label",
    "sort_maintenance_month_labels",
]
