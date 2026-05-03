from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from core.maintenance_evidence import MaintenanceEvidenceReader
from core.runtime_paths import get_database_path


FEATURE_COLUMNS = [
    "hours_since_last_maintenance",
    "days_since_last_maintenance",
    "pm_ratio_all_time",
    "pm_ratio_recent_30d",
    "recent_events_count_30d",
    "maintenance_intensity_30d",
    "cumulative_maintenance_count",
    "weighted_kwh_per_good_unit_30d",
    "nonproductive_share_30d",
    "total_good_qty_30d",
    "machine_family",
]

DISPLAY_COLUMNS = [
    "Machine",
    "Snapshot Date",
    "Prototype Mode",
    "Risk Score",
    "Risk Band",
    "Days Since Last Maintenance",
    "Events (30d)",
    "PM Ratio (All Time)",
    "Weighted kWh / Good Unit (30d)",
    "Non-Productive Share (30d)",
    "Observed Maintenance <= Horizon",
]


def get_available_months(db_path: str | Path | None = None) -> list[str]:
    db_path = str(db_path or get_database_path())
    conn = sqlite3.connect(db_path)
    try:
        month_df = pd.read_sql_query(
            """
            SELECT DISTINCT substr(hour_ts, 1, 7) AS month_key
            FROM fact_machine_hour
            WHERE hour_ts IS NOT NULL
            ORDER BY month_key DESC
            """,
            conn,
        )
    finally:
        conn.close()
    labels = []
    for month_key in month_df["month_key"].tolist():
        month_dt = pd.to_datetime(f"{month_key}-01", errors="coerce")
        if not pd.isna(month_dt):
            labels.append(month_dt.strftime("%B %Y"))
    return labels


def build_predictive_maintenance_prototype(
    month_year: str,
    *,
    horizon_days: int = 14,
    db_path: str | Path | None = None,
) -> dict[str, object]:
    db_path = str(db_path or get_database_path())
    snapshot_df = _build_machine_day_snapshots(month_year, horizon_days=horizon_days, db_path=db_path)
    if snapshot_df.empty:
        return {
            "blocked": True,
            "message": f"No machine-day snapshot data is available through {month_year}.",
            "snapshot_df": pd.DataFrame(),
        }

    labeled_df = snapshot_df[snapshot_df["label_available"] == 1].copy()
    latest_month_df = _build_latest_month_slice(snapshot_df, month_year)
    if latest_month_df.empty:
        return {
            "blocked": True,
            "message": f"No latest machine snapshot is available inside {month_year}.",
            "snapshot_df": snapshot_df,
        }

    model_payload = _fit_weak_label_model(labeled_df)
    if model_payload["usable"]:
        scored_latest_df = _score_with_model(latest_month_df, model_payload)
        prototype_mode = "Weak-label model"
        eval_summary = {
            "eval_roc_auc": model_payload["eval_roc_auc"],
            "eval_average_precision": model_payload["eval_average_precision"],
            "train_rows": model_payload["train_rows"],
            "eval_rows": model_payload["eval_rows"],
        }
    else:
        scored_latest_df = _score_with_fallback(latest_month_df, labeled_df)
        prototype_mode = "Fallback evidence score"
        eval_summary = {
            "eval_roc_auc": None,
            "eval_average_precision": None,
            "train_rows": None,
            "eval_rows": None,
        }

    risk_table_df = _build_risk_table(scored_latest_df, prototype_mode, horizon_days)
    selected_machine_id = str(risk_table_df.iloc[0]["Machine"])
    selected_snapshot_row = scored_latest_df[scored_latest_df["machine_id"] == selected_machine_id].iloc[0]
    evidence_factors_df = _build_evidence_factor_table(selected_snapshot_row, snapshot_df)

    evidence_reader = MaintenanceEvidenceReader(db_path=db_path)
    evidence_payload = evidence_reader.build_machine_evidence(
        selected_machine_id,
        recent_window_limit=10,
        as_of=pd.Timestamp(selected_snapshot_row["snapshot_date"]) + pd.Timedelta(hours=23, minutes=59, seconds=59),
    )
    recent_work_order_df = evidence_payload["recent_history_df"].copy() if evidence_payload["machine_has_history"] else pd.DataFrame()
    maintenance_event_horizon_end = _date_label(_read_maintenance_event_horizon_end(db_path=db_path))

    return {
        "blocked": False,
        "message": None,
        "prototype_mode": prototype_mode,
        "horizon_days": int(horizon_days),
        "label_counts": {
            "labeled_snapshots": int(len(labeled_df)),
            "positive_labels": int(labeled_df["label"].sum()) if not labeled_df.empty else 0,
            "negative_labels": int((labeled_df["label"] == 0).sum()) if not labeled_df.empty else 0,
        },
        "snapshot_df": snapshot_df,
        "scored_latest_df": scored_latest_df,
        "risk_table_df": risk_table_df,
        "selected_machine_summary": {
            "machine_id": selected_machine_id,
            "snapshot_date": pd.Timestamp(selected_snapshot_row["snapshot_date"]).strftime("%Y-%m-%d"),
            "risk_score": round(float(selected_snapshot_row["risk_score"]), 4),
            "risk_band": str(selected_snapshot_row["risk_band"]),
            "days_since_last_maintenance": _int_or_none(selected_snapshot_row["days_since_last_maintenance"]),
            "recent_events_count_30d": int(selected_snapshot_row["recent_events_count_30d"]),
            "pm_ratio_all_time": round(float(selected_snapshot_row["pm_ratio_all_time"]), 4),
            "weighted_kwh_per_good_unit_30d": _round_or_none(selected_snapshot_row["weighted_kwh_per_good_unit_30d"], 6),
            "nonproductive_share_30d": _round_or_none(selected_snapshot_row["nonproductive_share_30d"], 4),
        },
        "evidence_factors_df": evidence_factors_df,
        "recent_work_order_df": recent_work_order_df,
        "maintenance_event_horizon_end": maintenance_event_horizon_end,
        "model_payload": model_payload,
        "eval_summary": eval_summary,
        "prototype_note": (
            "This is an experimental predictive-maintenance prototype built from weak labels on the existing maintenance tables. "
            f"Stored future-event observation currently reaches through {maintenance_event_horizon_end or 'the available maintenance-event history only'}. "
            "It is not a production maintenance recommendation engine."
        ),
    }


def build_predictive_maintenance_export_artifacts(
    payload: dict[str, object],
    *,
    runtime_mode: str,
    anchor_month: str,
) -> dict[str, object]:
    export_frames = {
        "maintenance_risk_table.csv": _export_frame(payload.get("risk_table_df")),
        "maintenance_evidence_factors.csv": _export_frame(payload.get("evidence_factors_df")),
        "maintenance_recent_work_orders.csv": _export_frame(payload.get("recent_work_order_df")),
        "maintenance_scored_snapshots.csv": _export_frame(payload.get("scored_latest_df")),
    }
    manifest = {
        "prototype": "predictive_maintenance_prototype",
        "runtime_mode": runtime_mode,
        "anchor_month": anchor_month,
        "prototype_mode": payload.get("prototype_mode"),
        "horizon_days": payload.get("horizon_days"),
        "label_counts": payload.get("label_counts"),
        "selected_machine_summary": payload.get("selected_machine_summary"),
        "non_defended_notice": (
            "Experimental pilot-review export only. Weak-label / fallback evidence output. "
            "Not a production predictive-maintenance recommendation."
        ),
        "export_files": list(export_frames.keys()),
    }
    return {
        "export_frames": export_frames,
        "manifest_json": json.dumps(manifest, indent=2, ensure_ascii=True),
    }


def _build_machine_day_snapshots(
    month_year: str,
    *,
    horizon_days: int,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    month_dt = pd.to_datetime(month_year, format="%B %Y", errors="coerce")
    if pd.isna(month_dt):
        return pd.DataFrame()
    month_end = month_dt + pd.offsets.MonthEnd(0)
    next_month = month_dt + pd.offsets.MonthBegin(1)

    fact_df = _read_daily_fact_aggregate(next_month.strftime("%Y-%m-%dT00:00:00"), db_path=db_path)
    if fact_df.empty:
        return pd.DataFrame()

    fact_df["snapshot_date"] = pd.to_datetime(fact_df["snapshot_date"], errors="coerce")
    fact_df["machine_family"] = fact_df["machine_id"].fillna("").astype(str).str.split("-").str[0]
    fact_df["month_label"] = fact_df["snapshot_date"].dt.strftime("%B %Y")
    fact_df = fact_df[fact_df["snapshot_date"] <= month_end].copy()
    if fact_df.empty:
        return pd.DataFrame()

    fact_df = _add_trailing_operational_features(fact_df)
    maintenance_df = _read_maintenance_events(db_path=db_path)
    snapshot_df = _attach_maintenance_features_and_labels(
        fact_df,
        maintenance_df,
        horizon_days=horizon_days,
    )
    return snapshot_df


def _read_daily_fact_aggregate(
    upper_bound_ts: str,
    *,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    db_path = str(db_path or get_database_path())
    conn = sqlite3.connect(db_path)
    try:
        fact_df = pd.read_sql_query(
            """
            SELECT
                canonical_machine_id AS machine_id,
                date(hour_ts) AS snapshot_date,
                MAX(hours_since_last_maintenance) AS hours_since_last_maintenance,
                MAX(days_since_last_maintenance) AS days_since_last_maintenance,
                SUM(CASE WHEN good_qty > 0 THEN good_qty ELSE 0 END) AS daily_good_qty,
                SUM(CASE WHEN energy_total_kwh > 0 THEN energy_total_kwh ELSE 0 END) AS daily_energy_kwh,
                SUM(COALESCE(idle_minutes, 0) + COALESCE(setup_minutes, 0) + COALESCE(planned_stop_minutes, 0) + COALESCE(unplanned_stop_minutes, 0)) AS daily_nonproductive_minutes,
                SUM(
                    COALESCE(production_minutes, 0)
                    + COALESCE(idle_minutes, 0)
                    + COALESCE(setup_minutes, 0)
                    + COALESCE(planned_stop_minutes, 0)
                    + COALESCE(unplanned_stop_minutes, 0)
                ) AS daily_tracked_minutes
            FROM fact_machine_hour
            WHERE hour_ts < ?
              AND canonical_machine_id IS NOT NULL
            GROUP BY canonical_machine_id, date(hour_ts)
            ORDER BY snapshot_date, machine_id
            """,
            conn,
            params=(upper_bound_ts,),
        )
    finally:
        conn.close()

    numeric_columns = [
        "hours_since_last_maintenance",
        "days_since_last_maintenance",
        "daily_good_qty",
        "daily_energy_kwh",
        "daily_nonproductive_minutes",
        "daily_tracked_minutes",
    ]
    for column_name in numeric_columns:
        fact_df[column_name] = pd.to_numeric(fact_df[column_name], errors="coerce")
    return fact_df


def _add_trailing_operational_features(fact_df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for machine_id, machine_df in fact_df.groupby("machine_id", dropna=False):
        machine_df = machine_df.sort_values("snapshot_date").copy()
        machine_df = machine_df.set_index("snapshot_date")
        machine_df["total_good_qty_30d"] = machine_df["daily_good_qty"].rolling("30D", min_periods=1).sum()
        machine_df["total_energy_kwh_30d"] = machine_df["daily_energy_kwh"].rolling("30D", min_periods=1).sum()
        machine_df["nonproductive_minutes_30d"] = machine_df["daily_nonproductive_minutes"].rolling("30D", min_periods=1).sum()
        machine_df["tracked_minutes_30d"] = machine_df["daily_tracked_minutes"].rolling("30D", min_periods=1).sum()
        machine_df["weighted_kwh_per_good_unit_30d"] = (
            machine_df["total_energy_kwh_30d"] / machine_df["total_good_qty_30d"].replace(0.0, pd.NA)
        )
        machine_df["nonproductive_share_30d"] = (
            machine_df["nonproductive_minutes_30d"] / machine_df["tracked_minutes_30d"].replace(0.0, pd.NA)
        )
        machine_df = machine_df.reset_index()
        frames.append(machine_df)

    if not frames:
        return fact_df
    return pd.concat(frames, ignore_index=True)


def _read_maintenance_events(
    *,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    db_path = str(db_path or get_database_path())
    conn = sqlite3.connect(db_path)
    try:
        maintenance_df = pd.read_sql_query(
            """
            SELECT
                COALESCE(canonical_machine_id, machine_id) AS machine_id,
                datetime(transaction_date) AS transaction_ts,
                date(transaction_date) AS event_date,
                UPPER(COALESCE(work_order_type, '')) AS work_order_type
            FROM maintenance_records
            WHERE (canonical_machine_id IS NOT NULL AND trim(canonical_machine_id) <> '')
               OR (machine_id IS NOT NULL AND trim(machine_id) <> '')
            ORDER BY transaction_ts
            """,
            conn,
        )
    finally:
        conn.close()

    if maintenance_df.empty:
        return maintenance_df

    maintenance_df["event_date"] = pd.to_datetime(maintenance_df["event_date"], errors="coerce")
    maintenance_df["is_pm"] = (maintenance_df["work_order_type"] == "PM").astype(int)
    return maintenance_df


def _read_maintenance_event_horizon_end(
    *,
    db_path: str | Path | None = None,
) -> pd.Timestamp | None:
    maintenance_df = _read_maintenance_events(db_path=db_path)
    if maintenance_df.empty:
        return None
    horizon_end = pd.to_datetime(maintenance_df["event_date"], errors="coerce").max()
    if pd.isna(horizon_end):
        return None
    return horizon_end


def _attach_maintenance_features_and_labels(
    snapshot_df: pd.DataFrame,
    maintenance_df: pd.DataFrame,
    *,
    horizon_days: int,
) -> pd.DataFrame:
    max_event_date = maintenance_df["event_date"].max() if not maintenance_df.empty else pd.NaT
    frames = []
    for machine_id, machine_snapshot_df in snapshot_df.groupby("machine_id", dropna=False):
        machine_events_df = maintenance_df[maintenance_df["machine_id"] == machine_id].copy() if not maintenance_df.empty else pd.DataFrame()
        machine_snapshot_df = machine_snapshot_df.sort_values("snapshot_date").copy()
        rows = []
        for _, row in machine_snapshot_df.iterrows():
            snapshot_date = pd.Timestamp(row["snapshot_date"])
            past_events_df = (
                machine_events_df[machine_events_df["event_date"] <= snapshot_date].copy()
                if not machine_events_df.empty
                else pd.DataFrame()
            )
            recent_30d_df = (
                past_events_df[past_events_df["event_date"] > snapshot_date - pd.Timedelta(days=30)].copy()
                if not past_events_df.empty
                else pd.DataFrame()
            )
            future_horizon_df = (
                machine_events_df[
                    (machine_events_df["event_date"] > snapshot_date)
                    & (machine_events_df["event_date"] <= snapshot_date + pd.Timedelta(days=horizon_days))
                ].copy()
                if not machine_events_df.empty
                else pd.DataFrame()
            )

            label_available = (
                int(not pd.isna(max_event_date) and snapshot_date + pd.Timedelta(days=horizon_days) <= max_event_date)
                if not pd.isna(snapshot_date)
                else 0
            )
            label = None
            if label_available:
                label = 1 if not future_horizon_df.empty else 0

            days_since_last_maintenance = row["days_since_last_maintenance"]
            if pd.isna(days_since_last_maintenance) and not past_events_df.empty:
                days_since_last_maintenance = max(
                    int((snapshot_date - past_events_df["event_date"].max()).days),
                    0,
                )

            rows.append(
                {
                    **row.to_dict(),
                    "hours_since_last_maintenance": row["hours_since_last_maintenance"],
                    "days_since_last_maintenance": days_since_last_maintenance,
                    "cumulative_maintenance_count": int(len(past_events_df)),
                    "recent_events_count_30d": int(len(recent_30d_df)),
                    "maintenance_intensity_30d": int(len(recent_30d_df)),
                    "pm_ratio_all_time": float(past_events_df["is_pm"].mean()) if not past_events_df.empty else 0.0,
                    "pm_ratio_recent_30d": float(recent_30d_df["is_pm"].mean()) if not recent_30d_df.empty else 0.0,
                    "label_available": int(label_available),
                    "label": label,
                    "observed_future_event_within_horizon": bool(label == 1),
                }
            )
        frames.append(pd.DataFrame(rows))

    if not frames:
        return pd.DataFrame()
    result_df = pd.concat(frames, ignore_index=True)
    result_df["days_since_last_maintenance"] = pd.to_numeric(
        result_df["days_since_last_maintenance"],
        errors="coerce",
    )
    return result_df


def _build_latest_month_slice(snapshot_df: pd.DataFrame, month_year: str) -> pd.DataFrame:
    month_df = snapshot_df[snapshot_df["month_label"] == month_year].copy()
    if month_df.empty:
        return pd.DataFrame()
    latest_df = (
        month_df.sort_values(["snapshot_date", "machine_id"])
        .groupby("machine_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    return latest_df


def _fit_weak_label_model(labeled_df: pd.DataFrame) -> dict[str, object]:
    if labeled_df.empty:
        return {"usable": False, "reason": "No labeled machine-day snapshots are available."}

    positive_count = int(labeled_df["label"].sum())
    negative_count = int((labeled_df["label"] == 0).sum())
    unique_dates = sorted(pd.Timestamp(value) for value in labeled_df["snapshot_date"].dropna().unique().tolist())
    if len(labeled_df) < 200 or positive_count < 25 or negative_count < 25 or len(unique_dates) < 20:
        return {
            "usable": False,
            "reason": "Weak labels are too sparse or too shallow for a time-aware classifier.",
        }

    cutoff_index = max(int(len(unique_dates) * 0.8) - 1, 0)
    cutoff_date = unique_dates[cutoff_index]
    train_df = labeled_df[labeled_df["snapshot_date"] <= cutoff_date].copy()
    eval_df = labeled_df[labeled_df["snapshot_date"] > cutoff_date].copy()
    if train_df.empty or eval_df.empty:
        return {
            "usable": False,
            "reason": "Time-aware split left train or eval empty.",
        }
    if train_df["label"].nunique() < 2 or eval_df["label"].nunique() < 2:
        return {
            "usable": False,
            "reason": "Time-aware split produced a single-class train or eval fold.",
        }

    numeric_features = [column for column in FEATURE_COLUMNS if column != "machine_family"]
    categorical_features = ["machine_family"]
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )
    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)),
        ]
    )

    pipeline.fit(train_df[FEATURE_COLUMNS], train_df["label"].astype(int))
    eval_probability = pipeline.predict_proba(eval_df[FEATURE_COLUMNS])[:, 1]
    return {
        "usable": True,
        "reason": None,
        "pipeline": pipeline,
        "train_rows": int(len(train_df)),
        "eval_rows": int(len(eval_df)),
        "train_positive_labels": int(train_df["label"].sum()),
        "eval_positive_labels": int(eval_df["label"].sum()),
        "eval_roc_auc": float(roc_auc_score(eval_df["label"].astype(int), eval_probability)),
        "eval_average_precision": float(
            average_precision_score(eval_df["label"].astype(int), eval_probability)
        ),
    }


def _score_with_model(latest_month_df: pd.DataFrame, model_payload: dict[str, object]) -> pd.DataFrame:
    scored_df = latest_month_df.copy()
    probability = model_payload["pipeline"].predict_proba(scored_df[FEATURE_COLUMNS])[:, 1]
    scored_df["risk_score"] = probability
    scored_df["risk_band"] = scored_df["risk_score"].apply(_risk_band)
    return scored_df.sort_values(["risk_score", "machine_id"], ascending=[False, True]).reset_index(drop=True)


def _score_with_fallback(latest_month_df: pd.DataFrame, labeled_df: pd.DataFrame) -> pd.DataFrame:
    reference_df = labeled_df if not labeled_df.empty else latest_month_df
    scored_df = latest_month_df.copy()
    scored_df["risk_score"] = (
        0.35 * _normalize_series_value(reference_df["days_since_last_maintenance"], scored_df["days_since_last_maintenance"])
        + 0.20 * _normalize_series_value(reference_df["recent_events_count_30d"], scored_df["recent_events_count_30d"])
        + 0.15 * _normalize_series_value(reference_df["weighted_kwh_per_good_unit_30d"], scored_df["weighted_kwh_per_good_unit_30d"])
        + 0.15 * _normalize_series_value(reference_df["nonproductive_share_30d"], scored_df["nonproductive_share_30d"])
        + 0.15 * (
            1.0 - _normalize_series_value(reference_df["pm_ratio_all_time"], scored_df["pm_ratio_all_time"])
        )
    )
    scored_df["risk_band"] = scored_df["risk_score"].apply(_risk_band)
    return scored_df.sort_values(["risk_score", "machine_id"], ascending=[False, True]).reset_index(drop=True)


def _build_risk_table(
    scored_df: pd.DataFrame,
    prototype_mode: str,
    horizon_days: int,
) -> pd.DataFrame:
    table_df = pd.DataFrame(
        {
            "Machine": scored_df["machine_id"],
            "Snapshot Date": pd.to_datetime(scored_df["snapshot_date"]).dt.strftime("%Y-%m-%d"),
            "Prototype Mode": prototype_mode,
            "Risk Score": scored_df["risk_score"].round(4),
            "Risk Band": scored_df["risk_band"],
            "Days Since Last Maintenance": scored_df["days_since_last_maintenance"].fillna(0).round(0).astype(int),
            "Events (30d)": scored_df["recent_events_count_30d"].fillna(0).round(0).astype(int),
            "PM Ratio (All Time)": scored_df["pm_ratio_all_time"].fillna(0.0).round(4),
            "Weighted kWh / Good Unit (30d)": scored_df["weighted_kwh_per_good_unit_30d"].fillna(0.0).round(6),
            "Non-Productive Share (30d)": scored_df["nonproductive_share_30d"].fillna(0.0).round(4),
            "Observed Maintenance <= Horizon": scored_df["observed_future_event_within_horizon"].map(
                lambda value: f"Yes ({horizon_days}d)" if bool(value) else f"No ({horizon_days}d)"
            ),
        }
    )
    return table_df.loc[:, DISPLAY_COLUMNS].copy()


def _build_evidence_factor_table(
    selected_snapshot_row: pd.Series,
    snapshot_df: pd.DataFrame,
) -> pd.DataFrame:
    factor_specs = [
        (
            "Days since last maintenance",
            selected_snapshot_row["days_since_last_maintenance"],
            snapshot_df["days_since_last_maintenance"],
            "Higher than the peer snapshot range.",
        ),
        (
            "Recent maintenance events (30d)",
            selected_snapshot_row["recent_events_count_30d"],
            snapshot_df["recent_events_count_30d"],
            "Repeated maintenance activity inside the trailing 30-day window.",
        ),
        (
            "Weighted kWh / Good Unit (30d)",
            selected_snapshot_row["weighted_kwh_per_good_unit_30d"],
            snapshot_df["weighted_kwh_per_good_unit_30d"],
            "Energy intensity is elevated versus the wider snapshot set.",
        ),
        (
            "Non-productive share (30d)",
            selected_snapshot_row["nonproductive_share_30d"],
            snapshot_df["nonproductive_share_30d"],
            "A larger share of tracked minutes is non-productive.",
        ),
        (
            "Low PM ratio (all time)",
            1.0 - float(selected_snapshot_row["pm_ratio_all_time"] or 0.0),
            1.0 - snapshot_df["pm_ratio_all_time"].fillna(0.0),
            "Preventive-maintenance share is low relative to total history.",
        ),
    ]

    rows = []
    for label, value, reference_series, interpretation in factor_specs:
        percentile = _percentile_rank(reference_series, value)
        rows.append(
            {
                "Evidence Factor": label,
                "Selected Snapshot Value": _round_or_none(value, 6),
                "Peer Percentile": round(percentile, 4),
                "Interpretation": interpretation,
            }
        )
    factor_df = pd.DataFrame(rows)
    return factor_df.sort_values("Peer Percentile", ascending=False).reset_index(drop=True)


def _normalize_series_value(reference_series: pd.Series, value_series: pd.Series) -> pd.Series:
    reference_min = pd.to_numeric(reference_series, errors="coerce").min()
    reference_max = pd.to_numeric(reference_series, errors="coerce").max()
    if pd.isna(reference_min) or pd.isna(reference_max) or reference_max == reference_min:
        return pd.Series([0.0] * len(value_series), index=value_series.index)
    return (
        pd.to_numeric(value_series, errors="coerce").fillna(reference_min) - reference_min
    ) / (reference_max - reference_min)


def _percentile_rank(reference_series: pd.Series, value: object) -> float:
    reference = pd.to_numeric(reference_series, errors="coerce").dropna()
    numeric_value = _float_or_none(value)
    if reference.empty or numeric_value is None:
        return 0.0
    return float((reference <= numeric_value).mean())


def _risk_band(score: float) -> str:
    if score >= 0.70:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


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


def _int_or_none(value: object) -> int | None:
    numeric_value = _float_or_none(value)
    if numeric_value is None:
        return None
    return int(round(numeric_value))


def _round_or_none(value: object, digits: int) -> float | None:
    numeric_value = _float_or_none(value)
    if numeric_value is None:
        return None
    return round(numeric_value, digits)


def _date_label(value: object) -> str | None:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.strftime("%Y-%m-%d")


def _export_frame(frame: object) -> pd.DataFrame:
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    return pd.DataFrame()
