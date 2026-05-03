"""Machine-learning training pipeline backed by canonical Gold `fact_machine_hour`."""

from __future__ import annotations

import json
import pickle
import re
import shutil
import sqlite3
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from core.canonical_ml_reader import (
    CanonicalMLReader,
    NONPRODUCTIVE_MACHINE_STATES,
    classify_missing_positive_good_qty_reason,
)
from core.ml_predictor import MLPredictor
from core.runtime_paths import get_database_path, get_models_dir

warnings.filterwarnings("ignore")

XGBOOST_IMPORT_FAILURE_REASON: str | None = None

try:
    from xgboost import XGBRegressor

    XGBOOST_AVAILABLE = True
except Exception as exc:
    XGBOOST_AVAILABLE = False
    XGBOOST_IMPORT_FAILURE_REASON = str(exc)
    print(
        "XGBoost unavailable; continuing with Random Forest only. "
        f"Reason: {XGBOOST_IMPORT_FAILURE_REASON}"
    )


CANONICAL_TRAINING_REQUIRED_COLUMNS = [
    "canonical_machine_id",
    "hour_ts",
    "energy_total_kwh",
    "good_qty",
    "team_leader",
    "material_code",
    "task_name",
    "team_size",
    "manpower",
    "hours_since_last_maintenance",
    "days_since_last_maintenance",
    "last_maintenance_work_order_type",
    "maintenance_txn_in_hour",
    "maintenance_distinct_work_order_count_30d",
    "cumulative_maintenance_count",
]

TRAINING_FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "month",
    "is_weekend",
    "is_night_shift",
    "machine_type_encoded",
    "machine_number",
    "team_size",
    "task_complexity",
    "hours_since_last_maintenance",
    "maintenance_urgency",
    "needs_maintenance",
    "maintenance_intensity_30d",
    "cumulative_maintenance_count",
    "production_qty",
    "last_maintenance_type_encoded",
    "team_leader_encoded",
    "material_code_encoded",
]

TRAINING_DATAFRAME_COLUMNS = [
    "machine_id",
    "datetime",
    "hour_ts",
    "energy_kwh",
    "production_qty",
    "kwh_per_unit",
    "team_leader",
    "team_size",
    "material_code",
    "task_name",
    "task_difficulty",
    "hours_since_last_maintenance",
    "days_since_last_maintenance",
    "maintenance_in_hour",
    "last_maintenance_type",
    "maintenance_intensity_30d",
    "cumulative_maintenance_count",
    "machine_state",
    "source_flags",
    "adapter_notes",
    "eligible_for_training",
    "blocked_reason",
]

TRAINING_FEATURE_CONTRACT_VERSION = "canonical_fact_machine_hour_ml_v1"
DEFAULT_RETRAINING_TASK_TAG = "canonical_retraining_candidate"
DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME = "canonical_retraining_artifacts"
PROVENANCE_SUFFIX = ".provenance.json"
TIME_AWARE_EVALUATION_STRATEGY = "time_aware_multi_month_holdout"
RANDOM_EVALUATION_STRATEGY = "random_row_split"
DEFAULT_TIME_AWARE_EVAL_MONTH_COUNT = 2

PROVENANCE_REQUIRED_KEYS = [
    "artifact_role",
    "artifact_state",
    "artifact_path",
    "artifact_version_id",
    "training_source",
    "active_db_path",
    "trained_at",
    "selected_model",
    "rows_loaded",
    "rows_after_filtering",
    "distinct_machines_after_filtering",
    "month_coverage",
    "feature_columns",
    "feature_contract_version",
    "task_tag",
    "model_path",
    "preprocessor_path",
    "promotion_success",
]


class MLDataPreparer:
    """Prepare canonical Gold rows for ML retraining."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        preprocessor_path: str | Path | None = None,
        min_training_rows: int = 8,
        min_machine_count: int = 2,
    ):
        self.db_path = str(db_path or get_database_path())
        self.preprocessor_path = Path(
            preprocessor_path or (get_models_dir() / "production_preprocessor.pkl")
        )
        self.label_encoders: dict[str, LabelEncoder] = {}
        self.scaler = StandardScaler()
        self.feature_columns: list[str] = []
        self.categorical_columns = [
            "machine_type",
            "last_maintenance_type",
            "team_leader",
            "material_code",
        ]
        self.min_production = 1.0
        self.max_kwh_per_unit = 20.0
        self.feature_defaults: dict[str, float] = {}
        self.adapter_defaults = self._load_existing_preprocessor_defaults()
        self.min_training_rows = int(min_training_rows)
        self.min_machine_count = int(min_machine_count)
        self.last_blocked_df = pd.DataFrame()
        self.last_load_summary: dict[str, object] = {}
        self.last_month_coverage: list[str] = []
        self.last_team_size_fallback_summary: dict[str, object] = {}

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

    def load_data(self) -> pd.DataFrame:
        """Load canonical Gold rows and adapt them into a training dataframe."""
        fact_df = self._read_fact_machine_hour()
        machine_id = fact_df["canonical_machine_id"].map(CanonicalMLReader._clean_text)
        datetime_value = pd.to_datetime(fact_df["hour_ts"], errors="coerce")
        production_qty = pd.to_numeric(fact_df["good_qty"], errors="coerce")
        hours_since_last_maintenance = pd.to_numeric(
            fact_df["hours_since_last_maintenance"],
            errors="coerce",
        )
        energy_kwh = pd.to_numeric(fact_df["energy_total_kwh"], errors="coerce")
        machine_state = fact_df["machine_state"].map(CanonicalMLReader._clean_text)

        blocked_reason = pd.Series(index=fact_df.index, dtype="object")
        blocked_reason.loc[machine_id.isna()] = "missing_machine_id"
        blocked_reason.loc[blocked_reason.isna() & datetime_value.isna()] = "missing_timestamp"
        missing_positive_good_qty_mask = blocked_reason.isna() & (
            production_qty.isna() | production_qty.le(0)
        )
        blocked_reason.loc[
            missing_positive_good_qty_mask & machine_state.isin(NONPRODUCTIVE_MACHINE_STATES)
        ] = classify_missing_positive_good_qty_reason("setup_changeover")
        blocked_reason.loc[
            missing_positive_good_qty_mask & machine_state.eq("production")
        ] = fact_df.loc[
            missing_positive_good_qty_mask & machine_state.eq("production")
        ].apply(
            lambda row: classify_missing_positive_good_qty_reason("production", row=row),
            axis=1,
        )
        blocked_reason.loc[
            missing_positive_good_qty_mask & blocked_reason.isna()
        ] = classify_missing_positive_good_qty_reason(None)
        blocked_reason.loc[
            blocked_reason.isna() & hours_since_last_maintenance.isna()
        ] = "missing_hours_since_last_maintenance"
        blocked_reason.loc[
            blocked_reason.isna() & (energy_kwh.isna() | energy_kwh.le(0))
        ] = "missing_positive_energy_total_kwh"

        team_size = pd.to_numeric(fact_df["team_size"], errors="coerce")
        manpower = pd.to_numeric(fact_df["manpower"], errors="coerce")
        valid_team_size = team_size.where(team_size.gt(0))
        team_size_from_manpower = valid_team_size.isna() & manpower.gt(0)
        team_size_from_default = valid_team_size.isna() & ~team_size_from_manpower
        resolved_team_size = valid_team_size.copy()
        resolved_team_size.loc[team_size_from_manpower] = manpower.loc[team_size_from_manpower].round()
        resolved_team_size.loc[team_size_from_default] = float(
            self.adapter_defaults.get("team_size", 3.0)
        )

        task_difficulty = fact_df["task_name"].apply(CanonicalMLReader._derive_task_difficulty)
        task_difficulty_unmapped = task_difficulty.isna()
        blocked_reason.loc[blocked_reason.isna() & task_difficulty_unmapped] = "unmapped_task_name"

        team_leader = fact_df["team_leader"].map(CanonicalMLReader._clean_text).fillna("unknown")
        team_leader_unknown = team_leader.eq("unknown")
        material_code = fact_df["material_code"].map(CanonicalMLReader._clean_text).fillna("unknown")
        material_code_unknown = material_code.eq("unknown")
        last_maintenance_type = (
            fact_df["last_maintenance_work_order_type"]
            .map(CanonicalMLReader._clean_text)
            .fillna("unknown")
        )
        last_maintenance_type_unknown = last_maintenance_type.eq("unknown")

        maintenance_intensity_30d = pd.to_numeric(
            fact_df["maintenance_distinct_work_order_count_30d"],
            errors="coerce",
        ).fillna(0.0)
        cumulative_maintenance_count = pd.to_numeric(
            fact_df["cumulative_maintenance_count"],
            errors="coerce",
        ).fillna(0.0)
        days_since_last_maintenance = pd.to_numeric(
            fact_df["days_since_last_maintenance"],
            errors="coerce",
        )
        days_since_last_maintenance = days_since_last_maintenance.fillna(
            hours_since_last_maintenance / 24.0
        )
        maintenance_in_hour = (
            pd.to_numeric(fact_df["maintenance_txn_in_hour"], errors="coerce")
            .fillna(0)
            .astype(bool)
            .astype(int)
        )
        kwh_per_unit = energy_kwh / production_qty
        source_flags_json = (
            fact_df["source_flags"]
            .map(CanonicalMLReader._clean_text)
            .fillna(json.dumps({}, ensure_ascii=False, sort_keys=True))
        )

        note_flags = pd.DataFrame(
            {
                "team_size_from_manpower": np.where(
                    team_size_from_manpower,
                    "team_size_from_manpower",
                    "",
                ),
                "team_size_from_preprocessor_default": np.where(
                    team_size_from_default,
                    "team_size_from_preprocessor_default",
                    "",
                ),
                "task_difficulty_unmapped": np.where(
                    task_difficulty_unmapped,
                    "task_difficulty_unmapped",
                    "",
                ),
                "team_leader_unknown": np.where(team_leader_unknown, "team_leader_unknown", ""),
                "material_code_unknown": np.where(material_code_unknown, "material_code_unknown", ""),
                "last_maintenance_type_unknown": np.where(
                    last_maintenance_type_unknown,
                    "last_maintenance_type_unknown",
                    "",
                ),
            }
        )
        adapter_notes = note_flags.apply(
            lambda row: "; ".join(value for value in row if value),
            axis=1,
        )

        raw_training_df = pd.DataFrame(
            {
                "machine_id": machine_id,
                "datetime": datetime_value,
                "hour_ts": fact_df["hour_ts"].map(CanonicalMLReader._clean_text),
                "energy_kwh": energy_kwh,
                "production_qty": production_qty,
                "kwh_per_unit": kwh_per_unit,
                "team_leader": team_leader,
                "team_size": resolved_team_size,
                "material_code": material_code,
                "task_name": fact_df["task_name"].map(CanonicalMLReader._clean_text),
                "task_difficulty": task_difficulty,
                "hours_since_last_maintenance": hours_since_last_maintenance,
                "days_since_last_maintenance": days_since_last_maintenance,
                "maintenance_in_hour": maintenance_in_hour,
                "last_maintenance_type": last_maintenance_type,
                "maintenance_intensity_30d": maintenance_intensity_30d,
                "cumulative_maintenance_count": cumulative_maintenance_count,
                "machine_state": machine_state,
                "source_flags": source_flags_json,
                "adapter_notes": adapter_notes,
                "eligible_for_training": blocked_reason.isna().astype(int),
                "blocked_reason": blocked_reason,
            }
        )
        if raw_training_df.empty:
            raise ValueError("Canonical ML trainer found no rows in fact_machine_hour.")

        raw_training_df = raw_training_df.loc[:, TRAINING_DATAFRAME_COLUMNS].copy()

        blocked_df = raw_training_df[raw_training_df["eligible_for_training"] == 0].copy()
        training_df = raw_training_df[raw_training_df["eligible_for_training"] == 1].copy()
        if training_df.empty:
            raise ValueError(
                "Canonical ML trainer cannot proceed because every fact_machine_hour row was blocked."
            )

        filtered_df = training_df.copy()
        filtered_df = filtered_df[filtered_df["production_qty"] >= self.min_production]
        filtered_df = filtered_df[filtered_df["kwh_per_unit"] <= self.max_kwh_per_unit]
        filtered_df = filtered_df[filtered_df["energy_kwh"] >= 0.25]
        filtered_df = filtered_df[filtered_df["kwh_per_unit"].notna()]
        filtered_df = filtered_df.reset_index(drop=True)

        self.last_blocked_df = blocked_df.reset_index(drop=True)
        self.last_team_size_fallback_summary = self._build_team_size_fallback_summary(filtered_df)
        self.last_load_summary = {
            "fact_rows_read": int(len(raw_training_df)),
            "hard_blocked_rows": int(len(blocked_df)),
            "rows_after_hard_block": int(len(training_df)),
            "rows_after_filtering": int(len(filtered_df)),
            "distinct_machines_after_filtering": int(filtered_df["machine_id"].nunique()),
            "team_size_fallback_summary": dict(self.last_team_size_fallback_summary),
        }
        self.last_month_coverage = self._derive_month_coverage(filtered_df)
        self.last_load_summary["month_coverage"] = list(self.last_month_coverage)

        if len(filtered_df) < self.min_training_rows:
            raise ValueError(
                "Canonical ML trainer cannot proceed because too few eligible rows remain after "
                f"filtering: {len(filtered_df)} rows, need at least {self.min_training_rows}."
            )
        if filtered_df["machine_id"].nunique() < self.min_machine_count:
            raise ValueError(
                "Canonical ML trainer cannot proceed because too few machines remain after "
                f"filtering: {filtered_df['machine_id'].nunique()} machines, need at least {self.min_machine_count}."
            )

        print(
            "Loaded "
            f"{self.last_load_summary['fact_rows_read']:,} fact_machine_hour rows; "
            f"{self.last_load_summary['rows_after_filtering']:,} remain after canonical ML training filters"
        )
        return filtered_df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create training features from canonical Gold-derived rows."""
        df = df.copy()

        df["datetime"] = pd.to_datetime(df["datetime"])
        df["hour_of_day"] = df["datetime"].dt.hour
        df["day_of_week"] = df["datetime"].dt.dayofweek
        df["month"] = df["datetime"].dt.month
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["is_night_shift"] = (
            df["hour_of_day"].isin(range(20, 24)) | df["hour_of_day"].isin(range(0, 7))
        ).astype(int)

        machine_parts = df["machine_id"].astype(str).str.split("-", n=1, expand=True)
        df["machine_type"] = machine_parts[0].fillna("024")
        df["machine_number"] = pd.to_numeric(machine_parts[1], errors="coerce").fillna(1).astype(int)

        task_complexity_map = {"Easy": 1, "Medium": 2, "Hard": 3, "易": 1, "中": 2, "難": 3}
        df["task_complexity"] = df["task_difficulty"].map(task_complexity_map).fillna(2).astype(float)

        df["maintenance_urgency"] = df["hours_since_last_maintenance"] / 720.0
        df["needs_maintenance"] = (df["hours_since_last_maintenance"] > 1000).astype(int)

        df["maintenance_intensity_30d"] = df["maintenance_intensity_30d"].fillna(0.0)
        df["cumulative_maintenance_count"] = df["cumulative_maintenance_count"].fillna(0.0)
        df["days_since_last_maintenance"] = df["days_since_last_maintenance"].fillna(
            df["hours_since_last_maintenance"] / 24.0
        )

        return df

    def prepare_for_training(
        self,
        df: pd.DataFrame,
        *,
        fit: bool = True,
    ) -> tuple[pd.DataFrame, pd.Series, list[str]]:
        """Prepare scaled feature matrix and target while preserving predictor compatibility."""
        df = df.copy()

        for column_name in self.categorical_columns:
            df[column_name] = df[column_name].fillna("unknown").astype(str)
            encoded_column = f"{column_name}_encoded"
            if fit:
                le = LabelEncoder()
                le.fit(pd.Index(df[column_name].tolist() + ["unknown"]).unique())
                self.label_encoders[column_name] = le
            le = self.label_encoders.get(column_name)
            if le is None:
                raise ValueError(
                    "Canonical ML trainer cannot prepare features because label encoders "
                    f"have not been fit for {column_name}."
                )
            safe_values = df[column_name].where(df[column_name].isin(le.classes_), "unknown")
            df[encoded_column] = le.transform(safe_values)

        feature_columns = list(self.feature_columns) if (not fit and self.feature_columns) else list(
            TRAINING_FEATURE_COLUMNS
        )
        missing_features = [column for column in feature_columns if column not in df.columns]
        if missing_features:
            raise ValueError(
                "Canonical ML trainer cannot prepare features because required columns are missing: "
                + ", ".join(missing_features)
            )

        X = df.loc[:, feature_columns].copy()
        if fit:
            self.feature_defaults = X.median().to_dict()
            self.feature_columns = list(feature_columns)
            fill_defaults = dict(self.feature_defaults)
            X_scaled = self.scaler.fit_transform(X.fillna(fill_defaults))
        else:
            if not self.feature_columns:
                raise ValueError(
                    "Canonical ML trainer cannot transform evaluation rows because feature columns "
                    "have not been established."
                )
            fill_defaults = {column: self.feature_defaults.get(column, 0.0) for column in feature_columns}
            X_scaled = self.scaler.transform(X.fillna(fill_defaults))
        y = df["kwh_per_unit"].copy()
        X = pd.DataFrame(X_scaled, columns=feature_columns, index=X.index)

        print(f"Prepared {len(feature_columns)} features for training")
        print(f"Target variable (kwh_per_unit) range: {y.min():.2f} - {y.max():.2f}")
        return X, y, list(feature_columns)

    def save_preprocessor(self, filepath: str | Path | None = None) -> None:
        """Persist encoders, scaler, and feature metadata for inference."""
        package = {
            "feature_columns": self.feature_columns,
            "categorical_columns": self.categorical_columns,
            "label_encoders": self.label_encoders,
            "scaler": self.scaler,
            "feature_defaults": self.feature_defaults,
            "min_production": self.min_production,
            "max_kwh_per_unit": self.max_kwh_per_unit,
        }

        target_path = Path(filepath or (get_models_dir() / "production_preprocessor.pkl"))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as file_obj:
            pickle.dump(package, file_obj)
        print(f"Saved preprocessing bundle to {target_path}")

    def _read_fact_machine_hour(self) -> pd.DataFrame:
        if not self.fact_machine_hour_exists():
            raise ValueError(
                "Canonical ML trainer cannot proceed because fact_machine_hour does not exist in the active DB."
            )

        conn = sqlite3.connect(self.db_path)
        try:
            table_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(fact_machine_hour)").fetchall()
            }
            missing_columns = [
                column for column in CANONICAL_TRAINING_REQUIRED_COLUMNS if column not in table_columns
            ]
            if missing_columns:
                raise ValueError(
                    "Canonical ML trainer cannot proceed because fact_machine_hour is missing required "
                    "training columns: " + ", ".join(missing_columns)
                )
            fact_df = pd.read_sql_query(
                """
                SELECT
                    canonical_machine_id,
                    hour_ts,
                    energy_total_kwh,
                    good_qty,
                    order_id,
                    team_leader,
                    material_code,
                    task_name,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    unplanned_stop_minutes,
                    maintenance_minutes,
                    idle_minutes,
                    team_size,
                    manpower,
                    hours_since_last_maintenance,
                    days_since_last_maintenance,
                    last_maintenance_work_order_type,
                    maintenance_txn_in_hour,
                    maintenance_distinct_work_order_count_30d,
                    cumulative_maintenance_count,
                    machine_state,
                    csi_qty_alignment_status,
                    csi_qty_material_misalignment_flag,
                    csi_qty_minute_budget_anomaly_flag,
                    source_flags
                FROM fact_machine_hour
                ORDER BY hour_ts, canonical_machine_id
                """,
                conn,
            )
        finally:
            conn.close()
        return fact_df

    def _build_training_row(self, row: object) -> dict[str, object]:
        notes: list[str] = []
        blocked_reason = None

        datetime_value = pd.to_datetime(row.get("hour_ts"), errors="coerce")
        machine_id = CanonicalMLReader._clean_text(row.get("canonical_machine_id"))
        production_qty = CanonicalMLReader._float_or_none(row.get("good_qty"))
        hours_since_last_maintenance = CanonicalMLReader._float_or_none(
            row.get("hours_since_last_maintenance")
        )
        energy_kwh = CanonicalMLReader._float_or_none(row.get("energy_total_kwh"))

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
        elif energy_kwh is None or energy_kwh <= 0:
            blocked_reason = "missing_positive_energy_total_kwh"

        team_size = CanonicalMLReader._float_or_none(row.get("team_size"))
        if team_size is None or team_size <= 0:
            manpower = CanonicalMLReader._float_or_none(row.get("manpower"))
            if manpower is not None and manpower > 0:
                team_size = float(round(manpower))
                notes.append("team_size_from_manpower")
            else:
                team_size = float(self.adapter_defaults.get("team_size", 3.0))
                notes.append("team_size_from_preprocessor_default")

        task_difficulty = CanonicalMLReader._derive_task_difficulty(row.get("task_name"))
        if task_difficulty is None:
            if blocked_reason is None:
                blocked_reason = "unmapped_task_name"
            notes.append("task_difficulty_unmapped")

        team_leader = CanonicalMLReader._clean_text(row.get("team_leader")) or "unknown"
        if team_leader == "unknown":
            notes.append("team_leader_unknown")

        material_code = CanonicalMLReader._clean_text(row.get("material_code")) or "unknown"
        if material_code == "unknown":
            notes.append("material_code_unknown")

        last_maintenance_type = (
            CanonicalMLReader._clean_text(row.get("last_maintenance_work_order_type"))
            or "unknown"
        )
        if last_maintenance_type == "unknown":
            notes.append("last_maintenance_type_unknown")

        maintenance_intensity_30d = CanonicalMLReader._float_or_none(
            row.get("maintenance_distinct_work_order_count_30d")
        )
        if maintenance_intensity_30d is None:
            maintenance_intensity_30d = 0.0

        cumulative_maintenance_count = CanonicalMLReader._float_or_none(
            row.get("cumulative_maintenance_count")
        )
        if cumulative_maintenance_count is None:
            cumulative_maintenance_count = 0.0

        days_since_last_maintenance = CanonicalMLReader._float_or_none(
            row.get("days_since_last_maintenance")
        )
        if days_since_last_maintenance is None and hours_since_last_maintenance is not None:
            days_since_last_maintenance = hours_since_last_maintenance / 24.0

        maintenance_in_hour = int(
            bool(CanonicalMLReader._float_or_none(row.get("maintenance_txn_in_hour")) or 0)
        )
        kwh_per_unit = None
        if energy_kwh is not None and production_qty is not None and production_qty > 0:
            kwh_per_unit = energy_kwh / production_qty

        raw_source_flags = CanonicalMLReader._clean_text(row.get("source_flags"))
        source_flags_json = raw_source_flags or json.dumps({}, ensure_ascii=False, sort_keys=True)

        return {
            "machine_id": machine_id,
            "datetime": datetime_value if not pd.isna(datetime_value) else pd.NaT,
            "hour_ts": CanonicalMLReader._clean_text(row.get("hour_ts")),
            "energy_kwh": energy_kwh,
            "production_qty": production_qty,
            "kwh_per_unit": kwh_per_unit,
            "team_leader": team_leader,
            "team_size": team_size,
            "material_code": material_code,
            "task_name": CanonicalMLReader._clean_text(row.get("task_name")),
            "task_difficulty": task_difficulty,
            "hours_since_last_maintenance": hours_since_last_maintenance,
            "days_since_last_maintenance": days_since_last_maintenance,
            "maintenance_in_hour": maintenance_in_hour,
            "last_maintenance_type": last_maintenance_type,
            "maintenance_intensity_30d": maintenance_intensity_30d,
            "cumulative_maintenance_count": cumulative_maintenance_count,
            "machine_state": CanonicalMLReader._clean_text(row.get("machine_state")),
            "source_flags": source_flags_json,
            "adapter_notes": "; ".join(notes),
            "eligible_for_training": 0 if blocked_reason else 1,
            "blocked_reason": blocked_reason,
        }

    def _load_existing_preprocessor_defaults(self) -> dict[str, object]:
        if not self.preprocessor_path.exists():
            return {}
        try:
            with open(self.preprocessor_path, "rb") as file_obj:
                package = pickle.load(file_obj)
        except Exception:
            return {}
        defaults = package.get("feature_defaults", {})
        return defaults if isinstance(defaults, dict) else {}

    @staticmethod
    def _derive_month_coverage(df: pd.DataFrame) -> list[str]:
        if df.empty or "datetime" not in df.columns:
            return []
        month_series = pd.to_datetime(df["datetime"], errors="coerce").dropna()
        if month_series.empty:
            return []
        month_starts = sorted({value.to_period("M").to_timestamp() for value in month_series})
        return [month_start.strftime("%B %Y") for month_start in month_starts]

    @staticmethod
    def _adapter_note_mask(adapter_notes: pd.Series, token: str) -> pd.Series:
        normalized_notes = adapter_notes.fillna("").astype(str)
        pattern = rf"(?:^|;\s*){re.escape(token)}(?:$|;\s*)"
        return normalized_notes.str.contains(pattern, regex=True)

    @classmethod
    def _build_team_size_fallback_summary(cls, df: pd.DataFrame) -> dict[str, object]:
        if df.empty:
            return {
                "rows_using_team_size_from_preprocessor_default": 0,
                "distinct_machines_using_team_size_from_preprocessor_default": 0,
                "monthly_rows_using_team_size_from_preprocessor_default": {},
                "rows_using_team_size_from_manpower": 0,
                "distinct_machines_using_team_size_from_manpower": 0,
                "monthly_rows_using_team_size_from_manpower": {},
            }

        adapter_notes = df["adapter_notes"] if "adapter_notes" in df.columns else pd.Series(dtype="object")
        preprocessor_default_mask = cls._adapter_note_mask(
            adapter_notes,
            "team_size_from_preprocessor_default",
        )
        manpower_mask = cls._adapter_note_mask(
            adapter_notes,
            "team_size_from_manpower",
        )
        month_labels = pd.to_datetime(df["datetime"], errors="coerce").dt.strftime("%Y-%m")

        def _month_breakdown(mask: pd.Series) -> dict[str, int]:
            counts = month_labels[mask].dropna().value_counts().sort_index()
            return {str(month): int(count) for month, count in counts.items()}

        return {
            "rows_using_team_size_from_preprocessor_default": int(preprocessor_default_mask.sum()),
            "distinct_machines_using_team_size_from_preprocessor_default": int(
                df.loc[preprocessor_default_mask, "machine_id"].nunique()
            ),
            "monthly_rows_using_team_size_from_preprocessor_default": _month_breakdown(
                preprocessor_default_mask
            ),
            "rows_using_team_size_from_manpower": int(manpower_mask.sum()),
            "distinct_machines_using_team_size_from_manpower": int(
                df.loc[manpower_mask, "machine_id"].nunique()
            ),
            "monthly_rows_using_team_size_from_manpower": _month_breakdown(manpower_mask),
        }


class MLModelTrainer:
    """Train multiple ML models and select the best."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_database_path())
        self.models: dict[str, object] = {}
        self.best_model = None
        self.best_model_name = None
        self.feature_importance: dict[str, float] = {}
        self.training_history: list[dict[str, object]] = []
        self.last_evaluation_summary: dict[str, object] = {}

    def train_all_models(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        *,
        evaluation_summary: dict[str, object] | None = None,
    ) -> dict[str, dict[str, float]]:
        """Train multiple models and compare performance."""
        results: dict[str, dict[str, float]] = {}
        common_metrics = dict(evaluation_summary or {})

        print("\nTraining Linear Regression...")
        lr_model = LinearRegression()
        lr_model.fit(X_train, y_train)
        lr_pred = lr_model.predict(X_test)
        lr_r2 = r2_score(y_test, lr_pred)
        lr_mae = mean_absolute_error(y_test, lr_pred)

        self.models["linear_regression"] = lr_model
        results["linear_regression"] = {
            "r2_score": lr_r2,
            "mae": lr_mae,
            "rmse": float(np.sqrt(mean_squared_error(y_test, lr_pred))),
            **common_metrics,
        }
        print(f"  R² Score: {lr_r2:.3f}, MAE: {lr_mae:.3f}")

        print("\nTraining Random Forest...")
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        rf_r2 = r2_score(y_test, rf_pred)
        rf_mae = mean_absolute_error(y_test, rf_pred)

        self.models["random_forest"] = rf_model
        results["random_forest"] = {
            "r2_score": rf_r2,
            "mae": rf_mae,
            "rmse": float(np.sqrt(mean_squared_error(y_test, rf_pred))),
            **common_metrics,
        }
        print(f"  R² Score: {rf_r2:.3f}, MAE: {rf_mae:.3f}")

        self.feature_importance = dict(zip(X_train.columns, rf_model.feature_importances_))

        if XGBOOST_AVAILABLE:
            print("\nTraining XGBoost...")
            xgb_model = XGBRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
            )
            xgb_model.fit(X_train, y_train)
            xgb_pred = xgb_model.predict(X_test)
            xgb_r2 = r2_score(y_test, xgb_pred)
            xgb_mae = mean_absolute_error(y_test, xgb_pred)

            self.models["xgboost"] = xgb_model
            results["xgboost"] = {
                "r2_score": xgb_r2,
                "mae": xgb_mae,
                "rmse": float(np.sqrt(mean_squared_error(y_test, xgb_pred))),
                **common_metrics,
            }
            print(f"  R² Score: {xgb_r2:.3f}, MAE: {xgb_mae:.3f}")

            if xgb_r2 > rf_r2:
                self.feature_importance = dict(zip(X_train.columns, xgb_model.feature_importances_))

        best_model_name = max(results, key=lambda name: results[name]["r2_score"])
        self.best_model = self.models[best_model_name]
        self.best_model_name = best_model_name

        print(
            f"\n✅ Best Model: {best_model_name.upper()} with R² = "
            f"{results[best_model_name]['r2_score']:.3f}"
        )
        self.last_evaluation_summary = common_metrics

        self.training_history.append(
            {
                "timestamp": datetime.now(),
                "models": results,
                "best_model": best_model_name,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "evaluation_summary": dict(common_metrics),
            }
        )
        return results

    def get_feature_importance_df(self) -> pd.DataFrame:
        """Get feature importance as a sorted DataFrame."""
        if not self.feature_importance:
            return pd.DataFrame()

        importance_df = pd.DataFrame(
            list(self.feature_importance.items()),
            columns=["Feature", "Importance"],
        )
        importance_df = importance_df.sort_values("Importance", ascending=False)
        importance_df["Importance"] = importance_df["Importance"] * 100
        return importance_df

    def save_model(self, filepath: str | Path | None = None) -> None:
        """Save the best model to disk and store metadata in the active DB."""
        target_path = Path(filepath or (get_models_dir() / "production_efficiency_model.pkl"))
        target_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            "model": self.best_model,
            "model_name": self.best_model_name,
            "feature_importance": self.feature_importance,
            "training_history": self.training_history,
            "timestamp": datetime.now(),
        }

        with open(target_path, "wb") as file_obj:
            pickle.dump(model_data, file_obj)

        print(f"Model saved to {target_path}")
        self._save_to_database()

    def _save_to_database(self) -> None:
        """Save model metadata to the active runtime DB."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT,
                model_type TEXT,
                training_date TIMESTAMP,
                r2_score REAL,
                mae REAL,
                feature_count INTEGER
            )
            """
        )

        latest_results = self.training_history[-1]
        best_scores = latest_results["models"][self.best_model_name]
        cursor.execute(
            """
            INSERT INTO ml_models (
                model_name,
                model_type,
                training_date,
                r2_score,
                mae,
                feature_count
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"production_efficiency_{datetime.now().strftime('%Y%m%d_%H%M')}",
                self.best_model_name,
                datetime.now(),
                best_scores["r2_score"],
                best_scores["mae"],
                len(self.feature_importance),
            ),
        )

        conn.commit()
        conn.close()


def train_production_model(
    db_path: str | Path | None = None,
    model_path: str | Path | None = None,
    preprocessor_path: str | Path | None = None,
    reference_preprocessor_path: str | Path | None = None,
    test_size: float = 0.2,
    random_state: int = 42,
    evaluation_strategy: str | None = None,
    holdout_month_count: int | None = None,
):
    """Train the production-efficiency model from canonical Gold only."""
    print("=" * 60)
    print("TRAINING PRODUCTION EFFICIENCY MODEL")
    print("=" * 60)

    print("\n1. Loading and preparing canonical Gold data...")
    preparer = MLDataPreparer(
        db_path=db_path,
        preprocessor_path=reference_preprocessor_path or preprocessor_path,
    )
    df = preparer.load_data()
    df = preparer.engineer_features(df)

    if evaluation_strategy == TIME_AWARE_EVALUATION_STRATEGY:
        print("\n2. Building time-aware train/eval split...")
        train_df, eval_df, split_summary = _build_time_aware_holdout_split(
            df,
            eval_month_count=holdout_month_count,
        )
        print("   Train months: " + (", ".join(split_summary["train_months"]) or "none"))
        print("   Eval months: " + (", ".join(split_summary["eval_months"]) or "none"))
    else:
        print("\n2. Splitting data into train/test sets...")
        train_df, eval_df, split_summary = _build_random_holdout_split(
            df,
            test_size=test_size,
            random_state=random_state,
        )

    X_train, y_train, feature_columns = preparer.prepare_for_training(train_df, fit=True)
    X_test, y_test, _ = preparer.prepare_for_training(eval_df, fit=False)
    print(f"   Training samples: {len(X_train):,}")
    print(f"   Test samples: {len(X_test):,}")

    evaluation_summary = {
        "evaluation_strategy": split_summary["evaluation_strategy"],
        "train_months": list(split_summary["train_months"]),
        "eval_months": list(split_summary["eval_months"]),
        "train_rows": int(split_summary["train_rows"]),
        "eval_rows": int(split_summary["eval_rows"]),
        "rows_loaded": int(preparer.last_load_summary.get("fact_rows_read", 0)),
        "rows_after_hard_block": int(preparer.last_load_summary.get("rows_after_hard_block", 0)),
        "rows_after_filtering": int(preparer.last_load_summary.get("rows_after_filtering", 0)),
        "distinct_machines_retained": int(
            preparer.last_load_summary.get("distinct_machines_after_filtering", 0)
        ),
    }

    print("\n3. Training models...")
    trainer = MLModelTrainer(db_path=db_path)
    results = trainer.train_all_models(
        X_train,
        X_test,
        y_train,
        y_test,
        evaluation_summary=evaluation_summary,
    )

    print("\n4. Model Performance Summary:")
    print("-" * 40)
    for model_name, scores in results.items():
        print(f"{model_name.upper()}")
        print(f"  R² Score: {scores['r2_score']:.3f}")
        print(f"  MAE: {scores['mae']:.3f} kWh/unit")
        print(f"  RMSE: {scores['rmse']:.3f} kWh/unit")
        print()

    print("5. Top 10 Most Important Features:")
    print("-" * 40)
    importance_df = trainer.get_feature_importance_df()
    for _, row in importance_df.head(10).iterrows():
        print(f"  {row['Feature']}: {row['Importance']:.1f}%")

    print("\n6. Saving model...")
    trainer.save_model(model_path)
    preparer.save_preprocessor(preprocessor_path)

    print("\n" + "=" * 60)
    print("✅ MODEL TRAINING COMPLETE!")
    print("=" * 60)
    return trainer, preparer


def _month_label_list(month_starts: list[pd.Timestamp]) -> list[str]:
    return [month_start.strftime("%B %Y") for month_start in month_starts]


def _build_time_aware_holdout_split(
    df: pd.DataFrame,
    *,
    eval_month_count: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    if df.empty or "datetime" not in df.columns:
        raise ValueError(
            "Canonical ML trainer cannot build a time-aware evaluation split because the "
            "filtered dataframe is empty."
        )

    month_series = pd.to_datetime(df["datetime"], errors="coerce").dropna()
    month_starts = sorted({value.to_period("M").to_timestamp() for value in month_series})
    if len(month_starts) < 2:
        raise ValueError(
            "Canonical ML trainer cannot run time-aware reevaluation because fewer "
            "than two months remain after filtering."
        )

    resolved_eval_month_count = eval_month_count
    if resolved_eval_month_count is None:
        resolved_eval_month_count = (
            DEFAULT_TIME_AWARE_EVAL_MONTH_COUNT if len(month_starts) >= 4 else 1
        )
    resolved_eval_month_count = max(1, min(int(resolved_eval_month_count), len(month_starts) - 1))

    train_months = month_starts[:-resolved_eval_month_count]
    eval_months = month_starts[-resolved_eval_month_count:]
    if not train_months or not eval_months:
        raise ValueError(
            "Canonical ML trainer cannot run time-aware reevaluation because the "
            "resolved train/eval month assignment is empty."
        )

    period_series = pd.to_datetime(df["datetime"], errors="coerce").dt.to_period("M")
    train_periods = {month_start.to_period("M") for month_start in train_months}
    eval_periods = {month_start.to_period("M") for month_start in eval_months}
    train_df = df[period_series.isin(train_periods)].copy().reset_index(drop=True)
    eval_df = df[period_series.isin(eval_periods)].copy().reset_index(drop=True)

    if train_df.empty or eval_df.empty:
        raise ValueError(
            "Canonical ML trainer cannot run time-aware reevaluation because the "
            "resolved train/eval split produced an empty side."
        )

    return train_df, eval_df, {
        "evaluation_strategy": TIME_AWARE_EVALUATION_STRATEGY,
        "train_months": _month_label_list(train_months),
        "eval_months": _month_label_list(eval_months),
        "train_rows": int(len(train_df)),
        "eval_rows": int(len(eval_df)),
    }


def _build_random_holdout_split(
    df: pd.DataFrame,
    *,
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    train_df, eval_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
    )
    train_df = train_df.reset_index(drop=True)
    eval_df = eval_df.reset_index(drop=True)
    return train_df, eval_df, {
        "evaluation_strategy": RANDOM_EVALUATION_STRATEGY,
        "train_months": MLDataPreparer._derive_month_coverage(train_df),
        "eval_months": MLDataPreparer._derive_month_coverage(eval_df),
        "train_rows": int(len(train_df)),
        "eval_rows": int(len(eval_df)),
    }


def resolve_training_artifact_paths(
    model_path: str | Path | None = None,
    preprocessor_path: str | Path | None = None,
) -> tuple[Path, Path]:
    models_dir = get_models_dir()
    resolved_model_path = Path(model_path or (models_dir / "production_efficiency_model.pkl"))
    resolved_preprocessor_path = Path(
        preprocessor_path or (models_dir / "production_preprocessor.pkl")
    )
    return resolved_model_path, resolved_preprocessor_path


def get_canonical_retraining_status(
    db_path: str | Path | None = None,
    model_path: str | Path | None = None,
    preprocessor_path: str | Path | None = None,
) -> dict[str, object]:
    resolved_db_path = Path(db_path or get_database_path())
    resolved_model_path, resolved_preprocessor_path = resolve_training_artifact_paths(
        model_path=model_path,
        preprocessor_path=preprocessor_path,
    )

    status = {
        "db_path": str(resolved_db_path),
        "model_path": str(resolved_model_path),
        "preprocessor_path": str(resolved_preprocessor_path),
        "training_source": "fact_machine_hour",
        "ml_models_table_exists": _table_exists(resolved_db_path, "ml_models"),
        "fact_machine_hour_reachable": False,
        "required_columns_present": False,
        "missing_columns": [],
        "trainer_prerequisites_met": False,
        "blocker_reason": None,
        "load_summary": {},
        "month_coverage": [],
        "team_size_fallback_summary": {},
        "evaluation_strategy": None,
        "train_months": [],
        "eval_months": [],
        "train_rows": 0,
        "eval_rows": 0,
        "artifact_status": _read_artifact_status(
            resolved_model_path,
            resolved_preprocessor_path,
        ),
        "last_training_metadata": _read_latest_training_metadata(resolved_db_path),
    }

    preparer = MLDataPreparer(
        db_path=resolved_db_path,
        preprocessor_path=resolved_preprocessor_path,
    )

    if not preparer.fact_machine_hour_exists():
        status["blocker_reason"] = (
            "Canonical retraining is blocked because fact_machine_hour does not exist in the active DB."
        )
        return status

    status["fact_machine_hour_reachable"] = True

    try:
        fact_df = preparer._read_fact_machine_hour()
    except ValueError as exc:
        message = str(exc)
        status["blocker_reason"] = message
        if "missing required training columns:" in message:
            missing_text = message.split("missing required training columns:", 1)[1].strip()
            status["missing_columns"] = [value.strip() for value in missing_text.split(",") if value.strip()]
        return status

    missing_columns = [
        column for column in CANONICAL_TRAINING_REQUIRED_COLUMNS if column not in fact_df.columns
    ]
    status["required_columns_present"] = not missing_columns
    status["missing_columns"] = missing_columns
    if missing_columns:
        status["blocker_reason"] = (
            "Canonical retraining is blocked because fact_machine_hour is missing required columns: "
            + ", ".join(missing_columns)
        )
        return status

    try:
        filtered_df = preparer.load_data()
    except ValueError as exc:
        status["load_summary"] = dict(preparer.last_load_summary)
        status["month_coverage"] = list(preparer.last_month_coverage)
        status["team_size_fallback_summary"] = dict(preparer.last_team_size_fallback_summary)
        status["blocker_reason"] = str(exc)
        return status

    engineered_df = preparer.engineer_features(filtered_df)
    try:
        _, _, split_summary = _build_time_aware_holdout_split(
            engineered_df,
            eval_month_count=DEFAULT_TIME_AWARE_EVAL_MONTH_COUNT,
        )
    except ValueError as exc:
        status["load_summary"] = dict(preparer.last_load_summary)
        status["month_coverage"] = list(preparer.last_month_coverage)
        status["team_size_fallback_summary"] = dict(preparer.last_team_size_fallback_summary)
        status["blocker_reason"] = str(exc)
        return status

    status["load_summary"] = dict(preparer.last_load_summary)
    status["month_coverage"] = list(preparer.last_month_coverage)
    status["team_size_fallback_summary"] = dict(preparer.last_team_size_fallback_summary)
    status["evaluation_strategy"] = split_summary["evaluation_strategy"]
    status["train_months"] = list(split_summary["train_months"])
    status["eval_months"] = list(split_summary["eval_months"])
    status["train_rows"] = int(split_summary["train_rows"])
    status["eval_rows"] = int(split_summary["eval_rows"])
    status["trainer_prerequisites_met"] = True
    return status


def run_canonical_retraining(
    db_path: str | Path | None = None,
    model_path: str | Path | None = None,
    preprocessor_path: str | Path | None = None,
    test_size: float = 0.2,
    random_state: int = 42,
    task_tag: str = DEFAULT_RETRAINING_TASK_TAG,
    artifact_archive_dirname: str = DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME,
) -> dict[str, object]:
    resolved_db_path = Path(db_path or get_database_path())
    resolved_model_path, resolved_preprocessor_path = resolve_training_artifact_paths(
        model_path=model_path,
        preprocessor_path=preprocessor_path,
    )
    status = get_canonical_retraining_status(
        db_path=resolved_db_path,
        model_path=resolved_model_path,
        preprocessor_path=resolved_preprocessor_path,
    )
    if not status["trainer_prerequisites_met"]:
        raise ValueError(status["blocker_reason"] or "Canonical retraining prerequisites are not met.")

    version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate_paths = _build_versioned_artifact_paths(
        resolved_model_path,
        resolved_preprocessor_path,
        version_id=version_id,
        artifact_state="candidate",
        artifact_archive_dirname=artifact_archive_dirname,
    )

    trainer, preparer = train_production_model(
        db_path=resolved_db_path,
        model_path=candidate_paths["model_path"],
        preprocessor_path=candidate_paths["preprocessor_path"],
        reference_preprocessor_path=resolved_preprocessor_path,
        test_size=test_size,
        random_state=random_state,
        evaluation_strategy=TIME_AWARE_EVALUATION_STRATEGY,
        holdout_month_count=DEFAULT_TIME_AWARE_EVAL_MONTH_COUNT,
    )
    latest_history = trainer.training_history[-1]
    evaluation_summary = dict(trainer.last_evaluation_summary)
    trained_at = datetime.now().isoformat()
    common_provenance = _build_common_training_provenance(
        db_path=resolved_db_path,
        model_path=resolved_model_path,
        preprocessor_path=resolved_preprocessor_path,
        candidate_model_path=candidate_paths["model_path"],
        candidate_preprocessor_path=candidate_paths["preprocessor_path"],
        version_id=version_id,
        trained_at=trained_at,
        trainer=trainer,
        preparer=preparer,
        latest_history=latest_history,
        evaluation_summary=evaluation_summary,
        task_tag=task_tag,
    )
    _write_artifact_manifest(
        candidate_paths["model_manifest_path"],
        _build_artifact_manifest(
            common_provenance=common_provenance,
            artifact_role="model",
            artifact_state="candidate",
            artifact_path=candidate_paths["model_path"],
            candidate_model_path=candidate_paths["model_path"],
            candidate_preprocessor_path=candidate_paths["preprocessor_path"],
            promotion_success=False,
        ),
    )
    _write_artifact_manifest(
        candidate_paths["preprocessor_manifest_path"],
        _build_artifact_manifest(
            common_provenance=common_provenance,
            artifact_role="preprocessor",
            artifact_state="candidate",
            artifact_path=candidate_paths["preprocessor_path"],
            candidate_model_path=candidate_paths["model_path"],
            candidate_preprocessor_path=candidate_paths["preprocessor_path"],
            promotion_success=False,
        ),
    )

    candidate_status = _read_artifact_status(
        candidate_paths["model_path"],
        candidate_paths["preprocessor_path"],
    )
    predictor_smoke = _run_candidate_predictor_smoke(
        db_path=resolved_db_path,
        candidate_model_path=candidate_paths["model_path"],
        candidate_preprocessor_path=candidate_paths["preprocessor_path"],
        month_coverage=preparer.last_month_coverage,
    )
    promotion_gate = _build_promotion_gate(
        candidate_status,
        preparer.feature_columns,
        predictor_smoke,
    )
    candidate_predictor_evaluation = _evaluate_saved_predictor_on_holdout(
        model_path=candidate_paths["model_path"],
        preprocessor_path=candidate_paths["preprocessor_path"],
        eval_months=evaluation_summary.get("eval_months") or [],
        db_path=resolved_db_path,
    )
    active_predictor_evaluation = _evaluate_saved_predictor_on_holdout(
        model_path=resolved_model_path,
        preprocessor_path=resolved_preprocessor_path,
        eval_months=evaluation_summary.get("eval_months") or [],
        db_path=resolved_db_path,
    )
    artifact_decision = _build_artifact_decision(
        promotion_gate=promotion_gate,
        candidate_predictor_evaluation=candidate_predictor_evaluation,
        active_predictor_evaluation=active_predictor_evaluation,
    )
    promotion_success = bool(artifact_decision["promote"])

    _write_artifact_manifest(
        candidate_paths["model_manifest_path"],
        _build_artifact_manifest(
            common_provenance=common_provenance,
            artifact_role="model",
            artifact_state="candidate",
            artifact_path=candidate_paths["model_path"],
            candidate_model_path=candidate_paths["model_path"],
            candidate_preprocessor_path=candidate_paths["preprocessor_path"],
            promoted_at=datetime.now().isoformat() if promotion_success else None,
            promotion_success=promotion_success,
            predictor_smoke=predictor_smoke,
        ),
    )
    _write_artifact_manifest(
        candidate_paths["preprocessor_manifest_path"],
        _build_artifact_manifest(
            common_provenance=common_provenance,
            artifact_role="preprocessor",
            artifact_state="candidate",
            artifact_path=candidate_paths["preprocessor_path"],
            candidate_model_path=candidate_paths["model_path"],
            candidate_preprocessor_path=candidate_paths["preprocessor_path"],
            promoted_at=datetime.now().isoformat() if promotion_success else None,
            promotion_success=promotion_success,
            predictor_smoke=predictor_smoke,
        ),
    )

    backup_paths = {
        "model_path": None,
        "preprocessor_path": None,
        "model_manifest_path": None,
        "preprocessor_manifest_path": None,
    }
    if promotion_success:
        backup_paths = _backup_active_artifacts(
            resolved_model_path,
            resolved_preprocessor_path,
            version_id=version_id,
            artifact_archive_dirname=artifact_archive_dirname,
        )
        _promote_candidate_artifacts(
            candidate_model_path=candidate_paths["model_path"],
            candidate_preprocessor_path=candidate_paths["preprocessor_path"],
            active_model_path=resolved_model_path,
            active_preprocessor_path=resolved_preprocessor_path,
        )

        _write_artifact_manifest(
            resolved_model_path.with_suffix(PROVENANCE_SUFFIX),
            _build_artifact_manifest(
                common_provenance=common_provenance,
                artifact_role="model",
                artifact_state="active",
                artifact_path=resolved_model_path,
                candidate_model_path=candidate_paths["model_path"],
                candidate_preprocessor_path=candidate_paths["preprocessor_path"],
                backup_model_path=backup_paths["model_path"],
                backup_preprocessor_path=backup_paths["preprocessor_path"],
                promoted_at=datetime.now().isoformat(),
                promotion_success=True,
                predictor_smoke=predictor_smoke,
            ),
        )
        _write_artifact_manifest(
            resolved_preprocessor_path.with_suffix(PROVENANCE_SUFFIX),
            _build_artifact_manifest(
                common_provenance=common_provenance,
                artifact_role="preprocessor",
                artifact_state="active",
                artifact_path=resolved_preprocessor_path,
                candidate_model_path=candidate_paths["model_path"],
                candidate_preprocessor_path=candidate_paths["preprocessor_path"],
                backup_model_path=backup_paths["model_path"],
                backup_preprocessor_path=backup_paths["preprocessor_path"],
                promoted_at=datetime.now().isoformat(),
                promotion_success=True,
                predictor_smoke=predictor_smoke,
            ),
        )

    candidate_status = _read_artifact_status(
        candidate_paths["model_path"],
        candidate_paths["preprocessor_path"],
    )
    active_status = _read_artifact_status(
        resolved_model_path,
        resolved_preprocessor_path,
    )
    latest_metadata = _read_latest_training_metadata(resolved_db_path)

    return {
        "db_path": status["db_path"],
        "model_path": str(resolved_model_path),
        "preprocessor_path": str(resolved_preprocessor_path),
        "training_source": "fact_machine_hour",
        "rows_loaded": preparer.last_load_summary.get("fact_rows_read", 0),
        "rows_after_hard_block": preparer.last_load_summary.get("rows_after_hard_block", 0),
        "rows_after_filtering": preparer.last_load_summary.get("rows_after_filtering", 0),
        "distinct_machines_after_filtering": preparer.last_load_summary.get(
            "distinct_machines_after_filtering",
            0,
        ),
        "month_coverage": list(preparer.last_month_coverage),
        "team_size_fallback_summary": dict(preparer.last_team_size_fallback_summary),
        "evaluation_strategy": evaluation_summary.get("evaluation_strategy"),
        "train_months": list(evaluation_summary.get("train_months") or []),
        "eval_months": list(evaluation_summary.get("eval_months") or []),
        "train_rows": int(evaluation_summary.get("train_rows", 0)),
        "eval_rows": int(evaluation_summary.get("eval_rows", 0)),
        "selected_model": trainer.best_model_name,
        "evaluation_metrics": latest_history["models"][trainer.best_model_name],
        "all_model_metrics": latest_history["models"],
        "artifact_status": active_status,
        "candidate_artifact_status": candidate_status,
        "feature_columns": list(preparer.feature_columns),
        "feature_contract_version": TRAINING_FEATURE_CONTRACT_VERSION,
        "artifact_version_id": version_id,
        "promotion_gate": promotion_gate,
        "predictor_smoke": predictor_smoke,
        "candidate_predictor_evaluation": candidate_predictor_evaluation,
        "active_predictor_evaluation": active_predictor_evaluation,
        "artifact_decision": artifact_decision["decision"],
        "artifact_decision_reason": artifact_decision["reason"],
        "promotion_success": promotion_success,
        "candidate_paths": {
            "model_path": str(candidate_paths["model_path"]),
            "preprocessor_path": str(candidate_paths["preprocessor_path"]),
            "model_manifest_path": str(candidate_paths["model_manifest_path"]),
            "preprocessor_manifest_path": str(candidate_paths["preprocessor_manifest_path"]),
        },
        "backup_paths": {
            "model_path": str(backup_paths["model_path"]) if backup_paths["model_path"] else None,
            "preprocessor_path": (
                str(backup_paths["preprocessor_path"]) if backup_paths["preprocessor_path"] else None
            ),
            "model_manifest_path": (
                str(backup_paths["model_manifest_path"]) if backup_paths["model_manifest_path"] else None
            ),
            "preprocessor_manifest_path": (
                str(backup_paths["preprocessor_manifest_path"])
                if backup_paths["preprocessor_manifest_path"]
                else None
            ),
        },
        "training_provenance": {
            "source_table": "fact_machine_hour",
            "load_summary": dict(preparer.last_load_summary),
            "month_coverage": list(preparer.last_month_coverage),
            "team_size_fallback_summary": dict(preparer.last_team_size_fallback_summary),
            "active_db_path": str(resolved_db_path),
            "evaluation_strategy": evaluation_summary.get("evaluation_strategy"),
            "train_months": list(evaluation_summary.get("train_months") or []),
            "eval_months": list(evaluation_summary.get("eval_months") or []),
            "task_tag": task_tag,
        },
        "last_training_metadata": latest_metadata,
    }


def _read_artifact_status(model_path: Path, preprocessor_path: Path) -> dict[str, object]:
    model_info = _inspect_pickle_artifact(model_path, artifact_role="model")
    preprocessor_info = _inspect_pickle_artifact(preprocessor_path, artifact_role="preprocessor")
    return {
        "model_exists": model_info["exists"],
        "preprocessor_exists": preprocessor_info["exists"],
        "model_modified_at": model_info["modified_at"],
        "preprocessor_modified_at": preprocessor_info["modified_at"],
        "model_loadable": model_info["loadable"],
        "preprocessor_loadable": preprocessor_info["loadable"],
        "model_load_error": model_info["load_error"],
        "preprocessor_load_error": preprocessor_info["load_error"],
        "model_manifest_path": model_info["manifest_path"],
        "preprocessor_manifest_path": preprocessor_info["manifest_path"],
        "model_manifest_exists": model_info["manifest_exists"],
        "preprocessor_manifest_exists": preprocessor_info["manifest_exists"],
        "model_provenance_state": model_info["provenance_state"],
        "preprocessor_provenance_state": preprocessor_info["provenance_state"],
        "model_manifest_summary": model_info["manifest_summary"],
        "preprocessor_manifest_summary": preprocessor_info["manifest_summary"],
    }


def _build_common_training_provenance(
    db_path: Path,
    model_path: Path,
    preprocessor_path: Path,
    candidate_model_path: Path,
    candidate_preprocessor_path: Path,
    version_id: str,
    trained_at: str,
    trainer: MLModelTrainer,
    preparer: MLDataPreparer,
    latest_history: dict[str, object],
    evaluation_summary: dict[str, object],
    task_tag: str,
) -> dict[str, object]:
    selected_model = trainer.best_model_name
    selected_metrics = latest_history["models"][selected_model]
    return {
        "artifact_version_id": version_id,
        "training_source": "fact_machine_hour",
        "active_db_path": str(db_path),
        "trained_at": trained_at,
        "selected_model": selected_model,
        "rows_loaded": preparer.last_load_summary.get("fact_rows_read", 0),
        "rows_after_hard_block": preparer.last_load_summary.get("rows_after_hard_block", 0),
        "rows_after_filtering": preparer.last_load_summary.get("rows_after_filtering", 0),
        "distinct_machines_after_filtering": preparer.last_load_summary.get(
            "distinct_machines_after_filtering",
            0,
        ),
        "month_coverage": list(preparer.last_month_coverage),
        "evaluation_strategy": evaluation_summary.get("evaluation_strategy"),
        "train_months": list(evaluation_summary.get("train_months") or []),
        "eval_months": list(evaluation_summary.get("eval_months") or []),
        "train_rows": int(evaluation_summary.get("train_rows", 0)),
        "eval_rows": int(evaluation_summary.get("eval_rows", 0)),
        "feature_columns": list(preparer.feature_columns),
        "feature_contract_version": TRAINING_FEATURE_CONTRACT_VERSION,
        "task_tag": task_tag,
        "selected_model_metrics": dict(selected_metrics),
        "all_model_metrics": dict(latest_history["models"]),
        "model_path": str(model_path),
        "preprocessor_path": str(preprocessor_path),
        "candidate_model_path": str(candidate_model_path),
        "candidate_preprocessor_path": str(candidate_preprocessor_path),
    }


def _build_artifact_manifest(
    *,
    common_provenance: dict[str, object],
    artifact_role: str,
    artifact_state: str,
    artifact_path: Path,
    candidate_model_path: Path,
    candidate_preprocessor_path: Path,
    backup_model_path: Path | None = None,
    backup_preprocessor_path: Path | None = None,
    promoted_at: str | None = None,
    promotion_success: bool,
    predictor_smoke: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest = {
        "artifact_role": artifact_role,
        "artifact_state": artifact_state,
        "artifact_path": str(artifact_path),
        "artifact_version_id": common_provenance["artifact_version_id"],
        "training_source": common_provenance["training_source"],
        "active_db_path": common_provenance["active_db_path"],
        "trained_at": common_provenance["trained_at"],
        "selected_model": common_provenance["selected_model"],
        "rows_loaded": common_provenance["rows_loaded"],
        "rows_after_hard_block": common_provenance["rows_after_hard_block"],
        "rows_after_filtering": common_provenance["rows_after_filtering"],
        "distinct_machines_after_filtering": common_provenance["distinct_machines_after_filtering"],
        "month_coverage": list(common_provenance["month_coverage"]),
        "evaluation_strategy": common_provenance.get("evaluation_strategy"),
        "train_months": list(common_provenance.get("train_months") or []),
        "eval_months": list(common_provenance.get("eval_months") or []),
        "train_rows": common_provenance.get("train_rows"),
        "eval_rows": common_provenance.get("eval_rows"),
        "feature_columns": list(common_provenance["feature_columns"]),
        "feature_contract_version": common_provenance["feature_contract_version"],
        "task_tag": common_provenance["task_tag"],
        "model_path": common_provenance["model_path"],
        "preprocessor_path": common_provenance["preprocessor_path"],
        "candidate_model_path": str(candidate_model_path),
        "candidate_preprocessor_path": str(candidate_preprocessor_path),
        "backup_model_path": str(backup_model_path) if backup_model_path else None,
        "backup_preprocessor_path": str(backup_preprocessor_path) if backup_preprocessor_path else None,
        "promoted_at": promoted_at,
        "promotion_success": bool(promotion_success),
        "selected_model_metrics": dict(common_provenance["selected_model_metrics"]),
        "all_model_metrics": dict(common_provenance["all_model_metrics"]),
        "predictor_smoke": dict(predictor_smoke) if predictor_smoke else None,
    }
    return manifest


def _write_artifact_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_versioned_artifact_paths(
    active_model_path: Path,
    active_preprocessor_path: Path,
    *,
    version_id: str,
    artifact_state: str,
    artifact_archive_dirname: str = DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME,
) -> dict[str, Path]:
    archive_dir = active_model_path.parent / artifact_archive_dirname
    archive_dir.mkdir(parents=True, exist_ok=True)
    model_name = active_model_path.stem
    preprocessor_name = active_preprocessor_path.stem
    model_path = archive_dir / f"{model_name}.{artifact_state}.{version_id}{active_model_path.suffix}"
    preprocessor_path = (
        archive_dir
        / f"{preprocessor_name}.{artifact_state}.{version_id}{active_preprocessor_path.suffix}"
    )
    return {
        "model_path": model_path,
        "preprocessor_path": preprocessor_path,
        "model_manifest_path": model_path.with_suffix(PROVENANCE_SUFFIX),
        "preprocessor_manifest_path": preprocessor_path.with_suffix(PROVENANCE_SUFFIX),
    }


def _backup_active_artifacts(
    active_model_path: Path,
    active_preprocessor_path: Path,
    *,
    version_id: str,
    artifact_archive_dirname: str = DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME,
) -> dict[str, Path | None]:
    backup_paths = _build_versioned_artifact_paths(
        active_model_path,
        active_preprocessor_path,
        version_id=version_id,
        artifact_state="backup",
        artifact_archive_dirname=artifact_archive_dirname,
    )
    for source_path, backup_path in (
        (active_model_path, backup_paths["model_path"]),
        (active_preprocessor_path, backup_paths["preprocessor_path"]),
        (active_model_path.with_suffix(PROVENANCE_SUFFIX), backup_paths["model_manifest_path"]),
        (
            active_preprocessor_path.with_suffix(PROVENANCE_SUFFIX),
            backup_paths["preprocessor_manifest_path"],
        ),
    ):
        if source_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, backup_path)
        else:
            if "model_manifest_path" in backup_paths and backup_path == backup_paths["model_manifest_path"]:
                backup_paths["model_manifest_path"] = None
            elif (
                "preprocessor_manifest_path" in backup_paths
                and backup_path == backup_paths["preprocessor_manifest_path"]
            ):
                backup_paths["preprocessor_manifest_path"] = None
            elif backup_path == backup_paths["model_path"]:
                backup_paths["model_path"] = None
            elif backup_path == backup_paths["preprocessor_path"]:
                backup_paths["preprocessor_path"] = None
    return backup_paths


def _promote_candidate_artifacts(
    *,
    candidate_model_path: Path,
    candidate_preprocessor_path: Path,
    active_model_path: Path,
    active_preprocessor_path: Path,
) -> None:
    active_model_path.parent.mkdir(parents=True, exist_ok=True)
    active_preprocessor_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate_model_path, active_model_path)
    shutil.copy2(candidate_preprocessor_path, active_preprocessor_path)


def _build_promotion_gate(
    candidate_status: dict[str, object],
    feature_columns: list[str],
    predictor_smoke: dict[str, object],
) -> dict[str, object]:
    failures = []
    if not candidate_status["model_exists"]:
        failures.append("candidate_model_missing")
    if not candidate_status["preprocessor_exists"]:
        failures.append("candidate_preprocessor_missing")
    if not candidate_status["model_loadable"]:
        failures.append("candidate_model_not_loadable")
    if not candidate_status["preprocessor_loadable"]:
        failures.append("candidate_preprocessor_not_loadable")
    if candidate_status["model_provenance_state"] != "present":
        failures.append("candidate_model_provenance_not_present")
    if candidate_status["preprocessor_provenance_state"] != "present":
        failures.append("candidate_preprocessor_provenance_not_present")

    manifest_summary = candidate_status.get("preprocessor_manifest_summary") or {}
    manifest_features = manifest_summary.get("feature_columns") or []
    if list(feature_columns) != list(manifest_features):
        failures.append("candidate_preprocessor_feature_contract_mismatch")
    if not predictor_smoke.get("passed"):
        failures.append(
            str(
                predictor_smoke.get("failure_reason")
                or "candidate_predictor_smoke_failed"
            )
        )

    return {
        "passed": not failures,
        "failures": failures,
    }


def _evaluate_saved_predictor_on_holdout(
    *,
    model_path: Path,
    preprocessor_path: Path,
    eval_months: list[str],
    db_path: Path,
) -> dict[str, object]:
    result: dict[str, object] = {
        "passed": False,
        "model_path": str(model_path),
        "preprocessor_path": str(preprocessor_path),
        "eval_months": list(eval_months),
        "rows_considered": 0,
        "rows_evaluated": 0,
        "rows_non_model_source": 0,
        "distinct_machines_retained": 0,
        "r2_score": None,
        "mae": None,
        "rmse": None,
        "failure_reason": None,
        "first_non_model_prediction": None,
    }

    predictor = MLPredictor(
        model_path=str(model_path),
        preprocessor_path=str(preprocessor_path),
    )
    if (
        not predictor.loaded_model
        or not predictor.loaded_preprocessor
        or predictor.scaler is None
        or not predictor.feature_columns
    ):
        result["failure_reason"] = "predictor_artifacts_not_loadable"
        return result
    if not eval_months:
        result["failure_reason"] = "no_eval_months_assigned"
        return result

    preparer = MLDataPreparer(
        db_path=db_path,
        preprocessor_path=preprocessor_path,
        min_training_rows=1,
        min_machine_count=1,
    )
    eval_input_df = preparer.engineer_features(preparer.load_data())
    eval_input_df["month_year"] = eval_input_df["datetime"].dt.strftime("%B %Y")
    eval_input_df = eval_input_df[eval_input_df["month_year"].isin(eval_months)].copy()

    if eval_input_df.empty:
        result["failure_reason"] = "no_eval_rows_available"
        return result

    eval_input_df = eval_input_df.reset_index(drop=True)
    result["rows_considered"] = int(len(eval_input_df))
    result["distinct_machines_retained"] = int(eval_input_df["machine_id"].nunique())

    merged_df = eval_input_df.copy()

    feature_df = pd.DataFrame(index=merged_df.index)
    defaults = predictor.feature_defaults or {}
    for column_name in predictor.feature_columns or []:
        feature_df[column_name] = float(defaults.get(column_name, 0.0))

    machine_parts = merged_df["machine_id"].astype(str).str.split("-", n=1, expand=True)
    machine_type = machine_parts[0].fillna("024")
    machine_number = pd.to_numeric(machine_parts[1], errors="coerce").fillna(1).astype(int)
    task_complexity_map = {"Easy": 1, "Medium": 2, "Hard": 3, "易": 1, "中": 2, "難": 3}
    task_complexity = merged_df["task_difficulty"].map(task_complexity_map).fillna(2).astype(float)
    is_night_shift = (
        merged_df["hour_of_day"].astype(int).isin(range(20, 24))
        | merged_df["hour_of_day"].astype(int).isin(range(0, 7))
    ).astype(int)
    maintenance_urgency = merged_df["hours_since_last_maintenance"].astype(float) / 720.0
    needs_maintenance = (merged_df["hours_since_last_maintenance"].astype(float) > 1000).astype(int)

    direct_columns = {
        "hour_of_day": merged_df["hour_of_day"].astype(int),
        "day_of_week": pd.to_datetime(merged_df["datetime"], errors="coerce").dt.dayofweek.fillna(0).astype(int),
        "month": merged_df["month"].astype(int),
        "is_weekend": merged_df["is_weekend"].astype(int),
        "is_night_shift": is_night_shift,
        "machine_number": machine_number,
        "team_size": merged_df["team_size"].astype(float),
        "task_complexity": task_complexity,
        "hours_since_last_maintenance": merged_df["hours_since_last_maintenance"].astype(float),
        "maintenance_urgency": maintenance_urgency,
        "needs_maintenance": needs_maintenance,
        "maintenance_intensity_30d": merged_df["maintenance_intensity_30d"].astype(float),
        "cumulative_maintenance_count": merged_df["cumulative_maintenance_count"].astype(float),
        "production_qty": merged_df["production_qty"].astype(float),
    }
    for column_name, values in direct_columns.items():
        if column_name in feature_df.columns:
            feature_df[column_name] = values

    def _encode_series(raw_values: pd.Series, label_name: str) -> pd.Series:
        encoder = predictor.label_encoders.get(label_name)
        if encoder is None:
            return pd.Series(0, index=raw_values.index, dtype=int)
        class_map = {value: index for index, value in enumerate(encoder.classes_)}
        fallback_value = "unknown" if "unknown" in class_map else next(iter(class_map.keys()), None)
        safe_values = raw_values.fillna(fallback_value).astype(str)
        encoded = safe_values.map(class_map)
        if fallback_value is not None:
            encoded = encoded.fillna(class_map.get(fallback_value, 0))
        else:
            encoded = encoded.fillna(0)
        return encoded.astype(int)

    encoded_columns = {
        "machine_type_encoded": _encode_series(machine_type, "machine_type"),
        "team_leader_encoded": _encode_series(merged_df["team_leader"], "team_leader"),
        "material_code_encoded": _encode_series(merged_df["material_code"], "material_code"),
        "last_maintenance_type_encoded": _encode_series(
            merged_df["last_maintenance_type"],
            "last_maintenance_type",
        ),
    }
    for column_name, values in encoded_columns.items():
        if column_name in feature_df.columns:
            feature_df[column_name] = values

    scaled_array = predictor.scaler.transform(feature_df.loc[:, predictor.feature_columns])
    scaled_df = pd.DataFrame(scaled_array, columns=predictor.feature_columns, index=feature_df.index)
    raw_predictions = pd.Series(predictor.model.predict(scaled_df), index=merged_df.index, dtype=float)
    truth_mask = merged_df["kwh_per_unit"].notna()
    model_mask = raw_predictions.notna() & raw_predictions.ge(0) & raw_predictions.le(predictor.max_kwh_per_unit)
    valid_mask = truth_mask & model_mask

    result["rows_non_model_source"] = int((truth_mask & ~model_mask).sum())
    if result["rows_non_model_source"] and result["first_non_model_prediction"] is None:
        first_row = merged_df.loc[truth_mask & ~model_mask].iloc[0]
        result["first_non_model_prediction"] = {
            "month_year": first_row["month_year"],
            "machine_id": first_row["machine_id"],
            "hour_ts": first_row["hour_ts"],
            "source": "fallback",
        }

    if not bool(valid_mask.any()):
        result["failure_reason"] = "no_model_predictions_on_holdout"
        return result

    clipped_predictions = raw_predictions.clip(lower=0.0, upper=predictor.max_kwh_per_unit)
    targets = merged_df.loc[valid_mask, "kwh_per_unit"].astype(float)
    predictions = clipped_predictions.loc[valid_mask].astype(float)

    result["rows_evaluated"] = int(valid_mask.sum())
    result["r2_score"] = float(r2_score(targets, predictions))
    result["mae"] = float(mean_absolute_error(targets, predictions))
    result["rmse"] = float(np.sqrt(mean_squared_error(targets, predictions)))
    result["passed"] = True
    result["failure_reason"] = None
    return result


def _build_artifact_decision(
    *,
    promotion_gate: dict[str, object],
    candidate_predictor_evaluation: dict[str, object],
    active_predictor_evaluation: dict[str, object],
) -> dict[str, object]:
    if not promotion_gate.get("passed"):
        return {
            "promote": False,
            "decision": "retained_prior_active",
            "reason": "promotion_gate_failed: " + ", ".join(promotion_gate.get("failures") or []),
        }

    if not candidate_predictor_evaluation.get("passed"):
        return {
            "promote": False,
            "decision": "retained_prior_active",
            "reason": str(
                candidate_predictor_evaluation.get("failure_reason")
                or "candidate_predictor_evaluation_failed"
            ),
        }

    candidate_r2 = candidate_predictor_evaluation.get("r2_score")
    if candidate_r2 is None or float(candidate_r2) <= 0:
        return {
            "promote": False,
            "decision": "retained_prior_active",
            "reason": "candidate_holdout_r2_not_positive",
        }

    if active_predictor_evaluation.get("passed"):
        candidate_r2 = float(candidate_predictor_evaluation["r2_score"])
        active_r2 = float(active_predictor_evaluation["r2_score"])
        candidate_mae = float(candidate_predictor_evaluation["mae"])
        candidate_rmse = float(candidate_predictor_evaluation["rmse"])
        active_mae = float(active_predictor_evaluation["mae"])
        active_rmse = float(active_predictor_evaluation["rmse"])
        if candidate_r2 > active_r2:
            return {
                "promote": True,
                "decision": "promoted_candidate",
                "reason": "candidate_outperformed_active_artifacts_on_holdout_r2",
            }
        if np.isclose(candidate_r2, active_r2) and candidate_mae <= active_mae and candidate_rmse <= active_rmse:
            return {
                "promote": True,
                "decision": "promoted_candidate",
                "reason": "candidate_matched_active_r2_and_improved_error_metrics",
            }
        return {
            "promote": False,
            "decision": "retained_prior_active",
            "reason": "candidate_did_not_outperform_active_artifacts_on_holdout",
        }

    return {
        "promote": True,
        "decision": "promoted_candidate",
        "reason": "candidate_passed_gate_and_active_holdout_baseline_unavailable",
    }


def _run_candidate_predictor_smoke(
    *,
    db_path: Path,
    candidate_model_path: Path,
    candidate_preprocessor_path: Path,
    month_coverage: list[str],
) -> dict[str, object]:
    reader = CanonicalMLReader(db_path=db_path)
    predictor = MLPredictor(
        model_path=str(candidate_model_path),
        preprocessor_path=str(candidate_preprocessor_path),
    )
    predictor_status = reader.get_predictor_status(predictor)
    months_considered: list[str] = []
    for month_label in list(month_coverage):
        if month_label not in months_considered:
            months_considered.append(month_label)
    for month_label in reader.get_available_months():
        if month_label not in months_considered:
            months_considered.append(month_label)

    smoke_result: dict[str, object] = {
        "passed": False,
        "failure_reason": None,
        "prediction_source": None,
        "predicted_efficiency": None,
        "confidence": None,
        "sample_month": None,
        "sample_machine_id": None,
        "sample_hour_ts": None,
        "candidate_rows_considered": 0,
        "months_considered": months_considered,
        "predictor_status": predictor_status,
        "first_failure": None,
    }
    if not predictor_status["canonical_inference_enabled"]:
        smoke_result["failure_reason"] = "candidate_predictor_artifacts_unavailable"
        return smoke_result
    if not months_considered:
        smoke_result["failure_reason"] = "no_fact_machine_hour_months_available"
        return smoke_result

    for month_label in months_considered:
        input_df = reader.build_month_input_dataframe(month_label, predictor=predictor)
        candidate_df = reader.build_prediction_candidates(input_df)
        if candidate_df.empty:
            continue

        for _, row in candidate_df.iterrows():
            smoke_result["candidate_rows_considered"] = int(
                smoke_result["candidate_rows_considered"]
            ) + 1
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
            prediction_source = prediction.get("source")
            if smoke_result["first_failure"] is None and prediction_source != "model":
                smoke_result["first_failure"] = {
                    "month": month_label,
                    "machine_id": row["machine_id"],
                    "hour_ts": row["hour_ts"],
                    "prediction_source": prediction_source,
                }

            if prediction_source == "model":
                smoke_result.update(
                    {
                        "passed": True,
                        "failure_reason": None,
                        "prediction_source": prediction_source,
                        "predicted_efficiency": float(prediction["efficiency"]),
                        "confidence": float(prediction["confidence"]),
                        "sample_month": month_label,
                        "sample_machine_id": row["machine_id"],
                        "sample_hour_ts": row["hour_ts"],
                    }
                )
                return smoke_result

    if int(smoke_result["candidate_rows_considered"]) == 0:
        smoke_result["failure_reason"] = "no_canonical_prediction_candidates"
    else:
        smoke_result["failure_reason"] = "candidate_predictor_returned_non_model_source"
    return smoke_result


def _inspect_pickle_artifact(path: Path, artifact_role: str) -> dict[str, object]:
    exists = path.exists()
    modified_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat() if exists else None
    loadable = False
    load_error = None
    if exists:
        try:
            with open(path, "rb") as file_obj:
                payload = pickle.load(file_obj)
            if artifact_role == "model":
                loadable = isinstance(payload, dict) and {"model", "model_name"}.issubset(payload.keys())
            else:
                loadable = isinstance(payload, dict) and {
                    "feature_columns",
                    "scaler",
                }.issubset(payload.keys())
            if not loadable:
                load_error = f"{artifact_role} artifact payload shape is unexpected"
        except Exception as exc:
            load_error = str(exc)

    manifest_path = path.with_suffix(PROVENANCE_SUFFIX)
    manifest_info = _read_provenance_manifest(
        manifest_path,
        expected_role=artifact_role,
        expected_artifact_path=path,
    )
    return {
        "exists": exists,
        "modified_at": modified_at,
        "loadable": loadable,
        "load_error": load_error,
        "manifest_path": str(manifest_path),
        "manifest_exists": manifest_info["exists"],
        "provenance_state": manifest_info["state"],
        "manifest_summary": manifest_info["summary"],
    }


def _read_provenance_manifest(
    manifest_path: Path,
    *,
    expected_role: str,
    expected_artifact_path: Path,
) -> dict[str, object]:
    if not manifest_path.exists():
        return {"exists": False, "state": "absent", "summary": None}

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"exists": True, "state": "ambiguous", "summary": None}

    missing_keys = [key for key in PROVENANCE_REQUIRED_KEYS if key not in payload]
    if missing_keys:
        return {"exists": True, "state": "ambiguous", "summary": None}
    if payload.get("artifact_role") != expected_role:
        return {"exists": True, "state": "ambiguous", "summary": None}
    if Path(payload.get("artifact_path", "")) != expected_artifact_path:
        return {"exists": True, "state": "ambiguous", "summary": None}

    return {
        "exists": True,
        "state": "present",
        "summary": {
            "artifact_version_id": payload.get("artifact_version_id"),
            "trained_at": payload.get("trained_at"),
            "selected_model": payload.get("selected_model"),
            "promotion_success": payload.get("promotion_success"),
            "feature_columns": payload.get("feature_columns"),
            "task_tag": payload.get("task_tag"),
            "evaluation_strategy": payload.get("evaluation_strategy"),
            "train_months": payload.get("train_months"),
            "eval_months": payload.get("eval_months"),
        },
    }


def _table_exists(db_path: Path, table_name: str) -> bool:
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def _read_latest_training_metadata(db_path: Path) -> dict[str, object] | None:
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    try:
        table_row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'ml_models'
            """
        ).fetchone()
        if table_row is None:
            return None

        metadata_row = conn.execute(
            """
            SELECT model_name, model_type, training_date, r2_score, mae, feature_count
            FROM ml_models
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()

    if metadata_row is None:
        return None

    return {
        "model_name": metadata_row[0],
        "model_type": metadata_row[1],
        "training_date": metadata_row[2],
        "r2_score": metadata_row[3],
        "mae": metadata_row[4],
        "feature_count": metadata_row[5],
    }


if __name__ == "__main__":
    train_production_model()
