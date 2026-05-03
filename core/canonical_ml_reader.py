from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from core.runtime_paths import get_database_path


CANONICAL_ML_REQUIRED_COLUMNS = [
    "canonical_machine_id",
    "hour_ts",
    "material_code",
    "task_name",
    "good_qty",
    "team_leader",
    "team_size",
    "manpower",
    "has_maintenance_history",
    "maintenance_txn_in_hour",
    "maintenance_distinct_work_order_count_7d",
    "maintenance_distinct_work_order_count_30d",
    "maintenance_distinct_work_order_in_hour_count",
    "cumulative_maintenance_count",
    "hours_since_last_maintenance",
    "last_maintenance_work_order_type",
]

CANONICAL_ML_INPUT_COLUMNS = [
    "month_year",
    "datetime",
    "hour_ts",
    "canonical_machine_id",
    "machine_id",
    "material_code",
    "team_leader",
    "task_name",
    "task_difficulty",
    "production_qty",
    "team_size",
    "hours_since_last_maintenance",
    "last_maintenance_type",
    "maintenance_intensity_30d",
    "cumulative_maintenance_count",
    "hour_of_day",
    "day_of_week",
    "month",
    "is_weekend",
    "adapter_notes",
    "eligible_for_inference",
    "blocked_reason",
]

CANONICAL_ML_PREDICTION_COLUMNS = [
    "machine_id",
    "month_year",
    "datetime",
    "predicted_efficiency",
    "confidence",
    "top_driver",
    "team_leader",
    "material_code",
    "production_qty",
    "hours_since_last_maintenance",
    "task_difficulty",
    "maintenance_intensity_30d",
    "cumulative_maintenance_count",
]

MISSING_POSITIVE_GOOD_QTY_NONPRODUCTIVE_REASON = (
    "missing_positive_good_qty_nonproductive_state"
)
MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON = (
    "missing_positive_good_qty_production_state"
)
MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON = (
    "missing_positive_good_qty_production_state_likely_state_label_contradiction"
)
MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON = (
    "missing_positive_good_qty_production_state_likely_quantity_overlay_gap"
)
MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON = (
    "missing_positive_good_qty_production_state_likely_order_or_material_context_conflict"
)
MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON = (
    "missing_positive_good_qty_production_state_likely_source_quality_or_anomaly_case"
)
MISSING_POSITIVE_GOOD_QTY_INSUFFICIENT_CONTEXT_REASON = (
    "missing_positive_good_qty_insufficient_context"
)

NONPRODUCTIVE_MACHINE_STATES = frozenset(
    {
        "setup_changeover",
        "planned_stop",
        "unplanned_stop",
        "maintenance",
        "idle",
    }
)

PRODUCTION_STATE_ZERO_GOOD_QTY_SUBREASONS = frozenset(
    {
        MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
        MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
        MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON,
        MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON,
    }
)


class CanonicalMLReader:
    """Canonical ML input helper backed by fact_machine_hour only."""

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

    def build_month_input_dataframe(self, month_year: str, predictor=None) -> pd.DataFrame:
        fact_df = self._read_month_fact_dataframe(month_year)
        if fact_df.empty:
            return pd.DataFrame(columns=CANONICAL_ML_INPUT_COLUMNS)

        defaults = self._predictor_defaults(predictor)
        input_rows = []
        for _, row in fact_df.iterrows():
            input_rows.append(self._build_input_row(row, defaults))

        input_df = pd.DataFrame(input_rows)
        if input_df.empty:
            return pd.DataFrame(columns=CANONICAL_ML_INPUT_COLUMNS)

        input_df = input_df.loc[:, CANONICAL_ML_INPUT_COLUMNS].copy()
        input_df = input_df.sort_values(["datetime", "machine_id"]).reset_index(drop=True)
        return input_df

    def build_prediction_candidates(self, input_df: pd.DataFrame) -> pd.DataFrame:
        if input_df.empty:
            return pd.DataFrame(columns=CANONICAL_ML_INPUT_COLUMNS)

        eligible_df = input_df[input_df["eligible_for_inference"] == 1].copy()
        if eligible_df.empty:
            return pd.DataFrame(columns=CANONICAL_ML_INPUT_COLUMNS)

        eligible_df = eligible_df.sort_values(
            ["machine_id", "datetime"],
            ascending=[True, False],
        )
        latest_per_machine = eligible_df.drop_duplicates(subset=["machine_id"], keep="first")
        latest_per_machine = latest_per_machine.sort_values(
            ["datetime", "machine_id"],
            ascending=[True, True],
        ).reset_index(drop=True)
        return latest_per_machine.loc[:, CANONICAL_ML_INPUT_COLUMNS].copy()

    def get_predictor_status(self, predictor=None) -> dict[str, object]:
        predictor = predictor or self._build_predictor()
        model_artifact_present = bool(getattr(predictor, "loaded_model", False))
        preprocessor_present = bool(getattr(predictor, "loaded_preprocessor", False))
        return {
            "model_artifact_present": model_artifact_present,
            "predictor_bundle_present": preprocessor_present,
            "canonical_inference_enabled": model_artifact_present and preprocessor_present,
        }

    def build_prediction_dataframe(
        self,
        candidate_df: pd.DataFrame,
        predictor=None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        if candidate_df.empty:
            return (
                pd.DataFrame(columns=CANONICAL_ML_PREDICTION_COLUMNS),
                pd.DataFrame(columns=CANONICAL_ML_INPUT_COLUMNS),
            )

        predictor = predictor or self._build_predictor()
        status = self.get_predictor_status(predictor)
        if not status["canonical_inference_enabled"]:
            blocked_df = candidate_df.copy()
            blocked_df["blocked_reason"] = "predictor_artifacts_unavailable"
            return pd.DataFrame(columns=CANONICAL_ML_PREDICTION_COLUMNS), blocked_df

        prediction_rows = []
        blocked_rows = []
        for _, row in candidate_df.iterrows():
            prediction = predictor.predict_efficiency(
                machine_id=row["machine_id"],
                team_leader=row["team_leader"],
                material_code=row["material_code"],
                hours_since_maintenance=row["hours_since_last_maintenance"],
                task_difficulty=row["task_difficulty"],
                production_qty=row["production_qty"],
                team_size=row["team_size"],
                hour_of_day=row["hour_of_day"],
                is_weekend=bool(row["is_weekend"]),
                month=row["month"],
                last_maintenance_type=row["last_maintenance_type"],
                maintenance_intensity_30d=row["maintenance_intensity_30d"],
                cumulative_maintenance_count=row["cumulative_maintenance_count"],
            )
            if prediction.get("source") != "model":
                blocked_row = row.copy()
                blocked_row["blocked_reason"] = "predictor_returned_non_model_source"
                blocked_rows.append(blocked_row)
                continue

            prediction_rows.append(
                {
                    "machine_id": row["machine_id"],
                    "month_year": row["month_year"],
                    "datetime": row["datetime"],
                    "predicted_efficiency": float(prediction["efficiency"]),
                    "confidence": float(prediction["confidence"]),
                    "top_driver": self._top_driver_from_prediction(prediction),
                    "team_leader": row["team_leader"],
                    "material_code": row["material_code"],
                    "production_qty": row["production_qty"],
                    "hours_since_last_maintenance": row["hours_since_last_maintenance"],
                    "task_difficulty": row["task_difficulty"],
                    "maintenance_intensity_30d": row["maintenance_intensity_30d"],
                    "cumulative_maintenance_count": row["cumulative_maintenance_count"],
                }
            )

        prediction_df = pd.DataFrame(prediction_rows)
        if prediction_df.empty:
            prediction_df = pd.DataFrame(columns=CANONICAL_ML_PREDICTION_COLUMNS)
        else:
            prediction_df = prediction_df.loc[:, CANONICAL_ML_PREDICTION_COLUMNS].copy()
            prediction_df = prediction_df.sort_values(["datetime", "machine_id"]).reset_index(drop=True)

        blocked_df = pd.DataFrame(blocked_rows)
        if blocked_df.empty:
            blocked_df = pd.DataFrame(columns=CANONICAL_ML_INPUT_COLUMNS)
        else:
            blocked_df = blocked_df.loc[:, CANONICAL_ML_INPUT_COLUMNS].copy()
            blocked_df = blocked_df.sort_values(["datetime", "machine_id"]).reset_index(drop=True)

        return prediction_df, blocked_df

    def build_month_readiness_metrics(
        self,
        input_df: pd.DataFrame,
        candidate_df: pd.DataFrame,
        blocked_prediction_df: pd.DataFrame | None = None,
    ) -> dict[str, int]:
        if blocked_prediction_df is None:
            blocked_prediction_df = pd.DataFrame()
        return {
            "canonical_rows_loaded_for_ml": int(len(input_df)),
            "distinct_machines": int(input_df["machine_id"].nunique()) if not input_df.empty else 0,
            "rows_eligible_for_inference": int(input_df["eligible_for_inference"].sum()) if not input_df.empty else 0,
            "rows_blocked_for_missing_features": int((input_df["eligible_for_inference"] == 0).sum()) if not input_df.empty else 0,
            "machines_eligible_for_inference": int(candidate_df["machine_id"].nunique()) if not candidate_df.empty else 0,
            "machines_blocked_after_predictor_gate": int(blocked_prediction_df["machine_id"].nunique()) if not blocked_prediction_df.empty else 0,
        }

    def _read_month_fact_dataframe(self, month_year: str) -> pd.DataFrame:
        if not self.fact_machine_hour_exists():
            return pd.DataFrame(columns=CANONICAL_ML_REQUIRED_COLUMNS)

        bounds = self._month_label_to_bounds(month_year)
        if bounds is None:
            return pd.DataFrame(columns=CANONICAL_ML_REQUIRED_COLUMNS)
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
            return pd.DataFrame(columns=CANONICAL_ML_REQUIRED_COLUMNS)

        missing_columns = [
            column for column in CANONICAL_ML_REQUIRED_COLUMNS if column not in fact_df.columns
        ]
        if missing_columns:
            raise ValueError(
                "fact_machine_hour is missing required canonical ML columns: "
                + ", ".join(missing_columns)
            )
        return fact_df

    def _build_input_row(self, row: pd.Series, defaults: dict[str, object]) -> dict[str, object]:
        notes: list[str] = []
        blocked_reason = None

        datetime_value = pd.to_datetime(row.get("hour_ts"), errors="coerce")
        machine_id = self._clean_text(row.get("canonical_machine_id"))
        production_qty = self._float_or_none(row.get("good_qty"))
        hours_since_last_maintenance = self._float_or_none(row.get("hours_since_last_maintenance"))

        if machine_id is None:
            blocked_reason = "missing_machine_id"
        elif pd.isna(datetime_value):
            blocked_reason = "missing_timestamp"
        elif production_qty is None or production_qty <= 0:
            blocked_reason = classify_missing_positive_good_qty_reason(
                row.get("machine_state"),
                row=row,
            )
        elif hours_since_last_maintenance is None:
            blocked_reason = "missing_hours_since_last_maintenance"

        team_size = self._float_or_none(row.get("team_size"))
        if team_size is None or team_size <= 0:
            manpower = self._float_or_none(row.get("manpower"))
            if manpower is not None and manpower > 0:
                team_size = float(round(manpower))
                notes.append("team_size_from_manpower")
            else:
                team_size = self._float_or_none(defaults.get("team_size"))
                notes.append("team_size_from_preprocessor_default")

        task_difficulty = self._derive_task_difficulty(row.get("task_name"))
        if task_difficulty is None:
            if blocked_reason is None:
                blocked_reason = "unmapped_task_name"
            notes.append("task_difficulty_unmapped")

        last_maintenance_type = (
            self._clean_text(row.get("last_maintenance_work_order_type"))
            or "unknown"
        )
        if last_maintenance_type == "unknown":
            notes.append("last_maintenance_type_unknown")

        maintenance_intensity_30d = self._float_or_none(row.get("maintenance_distinct_work_order_count_30d"))
        if maintenance_intensity_30d is None:
            maintenance_intensity_30d = 0.0

        cumulative_maintenance_count = self._float_or_none(row.get("cumulative_maintenance_count"))
        if cumulative_maintenance_count is None:
            cumulative_maintenance_count = 0.0

        team_leader = self._clean_text(row.get("team_leader")) or "unknown"
        if team_leader == "unknown":
            notes.append("team_leader_unknown")

        material_code = self._clean_text(row.get("material_code")) or "unknown"
        if material_code == "unknown":
            notes.append("material_code_unknown")

        return {
            "month_year": datetime_value.strftime("%B %Y") if not pd.isna(datetime_value) else None,
            "datetime": datetime_value if not pd.isna(datetime_value) else pd.NaT,
            "hour_ts": self._clean_text(row.get("hour_ts")),
            "canonical_machine_id": machine_id,
            "machine_id": machine_id,
            "material_code": material_code,
            "team_leader": team_leader,
            "task_name": self._clean_text(row.get("task_name")),
            "task_difficulty": task_difficulty,
            "production_qty": production_qty,
            "team_size": team_size,
            "hours_since_last_maintenance": hours_since_last_maintenance,
            "last_maintenance_type": last_maintenance_type,
            "maintenance_intensity_30d": maintenance_intensity_30d,
            "cumulative_maintenance_count": cumulative_maintenance_count,
            "hour_of_day": int(datetime_value.hour) if not pd.isna(datetime_value) else None,
            "day_of_week": int(datetime_value.dayofweek) if not pd.isna(datetime_value) else None,
            "month": int(datetime_value.month) if not pd.isna(datetime_value) else None,
            "is_weekend": int(datetime_value.dayofweek >= 5) if not pd.isna(datetime_value) else None,
            "adapter_notes": "; ".join(notes),
            "eligible_for_inference": 0 if blocked_reason else 1,
            "blocked_reason": blocked_reason,
        }

    @staticmethod
    def _derive_task_difficulty(task_name: object) -> str | None:
        task_text = CanonicalMLReader._clean_text(task_name)
        if task_text is None:
            return None
        task_text_lower = task_text.lower()
        has_print_keyword = "印" in task_text or "print" in task_text_lower
        has_finishing_keyword = (
            "光" in task_text
            or "uv" in task_text_lower
            or "油" in task_text
            or "上光" in task_text
            or "啞" in task_text
            or "gp-led" in task_text_lower
            or "手感" in task_text
        )
        if has_print_keyword and ("+" in task_text or has_finishing_keyword):
            return "Hard"
        if has_print_keyword:
            return "Medium"
        if has_finishing_keyword:
            return "Easy"
        return None

    @staticmethod
    def _top_driver_from_prediction(prediction: dict[str, object]) -> str | None:
        impacts = prediction.get("feature_impacts") or {}
        if not isinstance(impacts, dict) or not impacts:
            return None
        label, narrative = next(iter(impacts.items()))
        return f"{label}: {narrative}"

    @staticmethod
    def _predictor_defaults(predictor) -> dict[str, object]:
        defaults = getattr(predictor, "feature_defaults", {}) if predictor is not None else {}
        return {
            "team_size": defaults.get("team_size", 3.0),
        }

    @staticmethod
    def _load_source_flags(source_flags: object) -> dict[str, object]:
        cleaned_flags = CanonicalMLReader._clean_text(source_flags)
        if cleaned_flags is None:
            return {}
        try:
            parsed = json.loads(cleaned_flags)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _month_key_to_label(month_key: object) -> str | None:
        month_text = CanonicalMLReader._clean_text(month_key)
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
    def _clean_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_predictor():
        from core.ml_predictor import MLPredictor

        return MLPredictor()


def classify_missing_positive_good_qty_reason(machine_state: object, row: object | None = None) -> str:
    normalized_state = CanonicalMLReader._clean_text(machine_state)
    if normalized_state in NONPRODUCTIVE_MACHINE_STATES:
        return MISSING_POSITIVE_GOOD_QTY_NONPRODUCTIVE_REASON
    if normalized_state == "production":
        return classify_production_state_zero_good_qty_subreason(row)
    return MISSING_POSITIVE_GOOD_QTY_INSUFFICIENT_CONTEXT_REASON


def classify_production_state_zero_good_qty_subreason(row: object | None) -> str:
    if row is None:
        return MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON
    if _is_source_quality_or_anomaly_case(row):
        return MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON
    if _is_order_or_material_context_conflict(row):
        return MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON
    if _is_state_label_contradiction(row):
        return MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON
    if _is_quantity_overlay_gap(row):
        return MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON
    return MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON


def _is_source_quality_or_anomaly_case(row: object) -> bool:
    anomaly_flag = _row_float(row, "csi_qty_minute_budget_anomaly_flag")
    alignment_status = _row_text(row, "csi_qty_alignment_status")
    allocation_warning = _row_source_flag_value(row, "csi_qty_allocation_warning")
    return (
        (anomaly_flag is not None and anomaly_flag > 0)
        or alignment_status == "missing_positive_row_basis_minutes"
        or allocation_warning == "csi_qty_no_positive_production_minutes"
    )


def _is_order_or_material_context_conflict(row: object) -> bool:
    material_misalignment_flag = _row_float(row, "csi_qty_material_misalignment_flag")
    alignment_status = _row_text(row, "csi_qty_alignment_status")
    return (
        (material_misalignment_flag is not None and material_misalignment_flag > 0)
        or alignment_status == "material_misaligned"
    )


def _is_state_label_contradiction(row: object) -> bool:
    production_minutes = _row_float(row, "production_minutes")
    return (
        production_minutes is not None
        and production_minutes > 0
        and any(
            (_row_float(row, column_name) or 0.0) > 0
            for column_name in (
                "setup_minutes",
                "planned_stop_minutes",
                "unplanned_stop_minutes",
                "maintenance_minutes",
                "idle_minutes",
            )
        )
    )


def _is_quantity_overlay_gap(row: object) -> bool:
    production_minutes = _row_float(row, "production_minutes")
    if production_minutes is None or production_minutes <= 0:
        return False
    has_only_production_minutes = not any(
        (_row_float(row, column_name) or 0.0) > 0
        for column_name in (
            "setup_minutes",
            "planned_stop_minutes",
            "unplanned_stop_minutes",
            "maintenance_minutes",
            "idle_minutes",
        )
    )
    return (
        has_only_production_minutes
        and _row_text(row, "order_id") is not None
        and _row_text(row, "material_code") is not None
        and _row_text(row, "task_name") is not None
    )


def _row_value(row: object, key: str) -> object:
    if row is None:
        return None
    if hasattr(row, "get"):
        return row.get(key)
    try:
        return row[key]  # type: ignore[index]
    except Exception:
        return None


def _row_text(row: object, key: str) -> str | None:
    return CanonicalMLReader._clean_text(_row_value(row, key))


def _row_float(row: object, key: str) -> float | None:
    return CanonicalMLReader._float_or_none(_row_value(row, key))


def _row_source_flag_value(row: object, key: str) -> object:
    source_flags = CanonicalMLReader._load_source_flags(_row_value(row, "source_flags"))
    return source_flags.get(key)
