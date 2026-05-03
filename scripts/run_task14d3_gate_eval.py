#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pickle
import shutil
import sys
import types
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only Task14D3 gate evaluation against the live DB (or an optional temp copy) and "
            "emit one JSON summary."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--working-db-path")
    parser.add_argument("--temp-db-path")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _log(enabled: bool, message: str) -> None:
    if enabled:
        print(message, flush=True)


def _load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build import spec for {module_name} at {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_runtime_paths_module(repo_root: Path):
    workspace_root = repo_root.parent
    module = types.ModuleType("core.runtime_paths")
    module._REPO_ROOT = repo_root
    module._WORKSPACE_ROOT = workspace_root
    module._SOURCE_DATA_ROOT_NAME = "source_data"
    module._RAW_DATASET_ROOT_NAME = "2025_jan_jun_initial"
    module._EXTENDED_RAW_DATASET_ROOT_NAME = "2025_jul_2026_feb_collected"
    module._LEGACY_RAW_DATASET_ROOT_NAME = "2025 DataSet(JAN to JUN)"
    module._LEGACY_EXTENDED_RAW_DATASET_ROOT_NAME = "DataSet Package(New Collected)"

    def get_repo_root() -> Path:
        return repo_root

    def get_workspace_root() -> Path:
        return workspace_root

    def get_database_path() -> Path:
        return repo_root / "manufacturing_data.db"

    def get_data_dir() -> Path:
        return repo_root / "data"

    def get_models_dir() -> Path:
        return repo_root / "models"

    def get_etl_outputs_dir() -> Path:
        return repo_root / "etl_outputs"

    def get_raw_dataset_root() -> Path:
        repo_local = repo_root / module._SOURCE_DATA_ROOT_NAME / module._RAW_DATASET_ROOT_NAME
        if repo_local.exists():
            return repo_local
        legacy_repo_local = repo_root / module._LEGACY_RAW_DATASET_ROOT_NAME
        if legacy_repo_local.exists():
            return legacy_repo_local
        return workspace_root / module._LEGACY_RAW_DATASET_ROOT_NAME

    def get_extended_raw_dataset_root() -> Path:
        repo_local = repo_root / module._SOURCE_DATA_ROOT_NAME / module._EXTENDED_RAW_DATASET_ROOT_NAME
        if repo_local.exists():
            return repo_local
        legacy_repo_local = repo_root / module._LEGACY_EXTENDED_RAW_DATASET_ROOT_NAME
        if legacy_repo_local.exists():
            return legacy_repo_local
        return workspace_root / module._LEGACY_EXTENDED_RAW_DATASET_ROOT_NAME

    def resolve_dataset_subdir(data_root: Path | str | None, live_name: str, *legacy_names: str) -> Path:
        root = Path(data_root) if data_root is not None else get_raw_dataset_root()
        for folder_name in (live_name, *legacy_names):
            candidate = root / folder_name
            if candidate.exists():
                return candidate
        return root / live_name

    def get_energy_dataset_dir(data_root: Path | str | None = None) -> Path:
        return resolve_dataset_subdir(
            data_root,
            "Energy Usage 1hr Interval",
            "Energy Usage 1hr Interval(JAN to JUN)",
        )

    def get_csi_dataset_dir(data_root: Path | str | None = None) -> Path:
        return resolve_dataset_subdir(
            data_root,
            "CSI Monthly",
            "CSI Monthly(JAN to JUN)",
        )

    def get_mes_dataset_dir(data_root: Path | str | None = None) -> Path:
        return resolve_dataset_subdir(
            data_root,
            "MES Monthly",
            "MES Monthly(JAN to JUN)",
        )

    module.get_repo_root = get_repo_root
    module.get_workspace_root = get_workspace_root
    module.get_database_path = get_database_path
    module.get_data_dir = get_data_dir
    module.get_models_dir = get_models_dir
    module.get_etl_outputs_dir = get_etl_outputs_dir
    module.get_raw_dataset_root = get_raw_dataset_root
    module.get_extended_raw_dataset_root = get_extended_raw_dataset_root
    module.resolve_dataset_subdir = resolve_dataset_subdir
    module.get_energy_dataset_dir = get_energy_dataset_dir
    module.get_csi_dataset_dir = get_csi_dataset_dir
    module.get_mes_dataset_dir = get_mes_dataset_dir
    sys.modules["core.runtime_paths"] = module
    return module


def _build_canonical_ml_reader_module():
    module = types.ModuleType("core.canonical_ml_reader")

    class CanonicalMLReader:
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
                import pandas as pd  # local import keeps bootstrap order simple

                if pd.isna(value):
                    return None
            except TypeError:
                pass
            except Exception:
                pass
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

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

    module.CanonicalMLReader = CanonicalMLReader
    sys.modules["core.canonical_ml_reader"] = module
    return module


def _build_ml_predictor_module():
    module = types.ModuleType("core.ml_predictor")

    class MLPredictor:
        def __init__(self, model_path="models/production_efficiency_model.pkl", preprocessor_path="models/production_preprocessor.pkl"):
            self.model = None
            self.model_name = None
            self.feature_importance = None
            self.feature_columns = None
            self.categorical_columns = []
            self.label_encoders = {}
            self.scaler = None
            self.feature_defaults = {}
            self.min_production = 1.0
            self.max_kwh_per_unit = 20.0
            self.loaded_model = False
            self.loaded_preprocessor = False
            if Path(model_path).exists():
                self.load_model(model_path)
            if Path(preprocessor_path).exists():
                self._load_preprocessor(preprocessor_path)

        def load_model(self, filepath):
            try:
                with open(filepath, "rb") as file_obj:
                    model_data = pickle.load(file_obj)
                self.model = model_data["model"]
                self.model_name = model_data["model_name"]
                self.feature_importance = model_data.get("feature_importance")
                self.loaded_model = True
                return True
            except Exception:
                return False

        def _load_preprocessor(self, filepath):
            try:
                with open(filepath, "rb") as file_obj:
                    bundle = pickle.load(file_obj)
                self.feature_columns = bundle.get("feature_columns", [])
                self.categorical_columns = bundle.get("categorical_columns", [])
                self.label_encoders = bundle.get("label_encoders", {})
                self.scaler = bundle.get("scaler")
                self.feature_defaults = bundle.get("feature_defaults", {})
                self.min_production = bundle.get("min_production", self.min_production)
                self.max_kwh_per_unit = bundle.get("max_kwh_per_unit", self.max_kwh_per_unit)
                self.loaded_preprocessor = True
                return True
            except Exception:
                return False

    module.MLPredictor = MLPredictor
    sys.modules["core.ml_predictor"] = module
    return module


def _encode_with_label_encoder(raw_value, encoder) -> int:
    if encoder is None:
        return 0
    class_map = {value: index for index, value in enumerate(encoder.classes_)}
    fallback_value = "unknown" if "unknown" in class_map else next(iter(class_map.keys()), None)
    safe_value = fallback_value if raw_value is None else str(raw_value)
    encoded = class_map.get(safe_value)
    if encoded is None and fallback_value is not None:
        encoded = class_map.get(fallback_value, 0)
    return int(0 if encoded is None else encoded)


def _predict_single_row(predictor, row):
    import numpy as np
    import pandas as pd

    if (
        not getattr(predictor, "loaded_model", False)
        or not getattr(predictor, "loaded_preprocessor", False)
        or getattr(predictor, "scaler", None) is None
        or not getattr(predictor, "feature_columns", None)
    ):
        return {"source": "fallback", "reason": "predictor_artifacts_unavailable"}

    feature_defaults = predictor.feature_defaults or {}
    feature_df = pd.DataFrame(index=[0])
    for column_name in predictor.feature_columns:
        feature_df[column_name] = [float(feature_defaults.get(column_name, 0.0))]

    machine_id = str(row["machine_id"])
    machine_parts = machine_id.split("-", 1)
    machine_type = machine_parts[0] if machine_parts else "024"
    try:
        machine_number = int(machine_parts[1]) if len(machine_parts) > 1 else 1
    except ValueError:
        machine_number = 1
    task_complexity_map = {"Easy": 1, "Medium": 2, "Hard": 3, "易": 1, "中": 2, "難": 3}
    task_complexity = float(task_complexity_map.get(row["task_difficulty"], 2))
    hour_of_day = int(row["hour_of_day"])
    needs_maintenance = int(float(row["hours_since_last_maintenance"]) > 1000)
    maintenance_urgency = float(row["hours_since_last_maintenance"]) / 720.0
    is_night_shift = int(hour_of_day in set(range(20, 24)) | set(range(0, 7)))

    direct_columns = {
        "hour_of_day": hour_of_day,
        "day_of_week": int(pd.to_datetime(row["datetime"], errors="coerce").dayofweek),
        "month": int(row["month"]),
        "is_weekend": int(bool(row["is_weekend"])),
        "is_night_shift": is_night_shift,
        "machine_number": machine_number,
        "team_size": float(row["team_size"]),
        "task_complexity": task_complexity,
        "hours_since_last_maintenance": float(row["hours_since_last_maintenance"]),
        "maintenance_urgency": maintenance_urgency,
        "needs_maintenance": needs_maintenance,
        "maintenance_intensity_30d": float(row["maintenance_intensity_30d"]),
        "cumulative_maintenance_count": float(row["cumulative_maintenance_count"]),
        "production_qty": float(row["production_qty"]),
        "machine_type_encoded": _encode_with_label_encoder(
            machine_type,
            predictor.label_encoders.get("machine_type"),
        ),
        "team_leader_encoded": _encode_with_label_encoder(
            row["team_leader"],
            predictor.label_encoders.get("team_leader"),
        ),
        "material_code_encoded": _encode_with_label_encoder(
            row["material_code"],
            predictor.label_encoders.get("material_code"),
        ),
        "last_maintenance_type_encoded": _encode_with_label_encoder(
            row["last_maintenance_type"],
            predictor.label_encoders.get("last_maintenance_type"),
        ),
    }
    for column_name, value in direct_columns.items():
        if column_name in feature_df.columns:
            feature_df.at[0, column_name] = value

    scaled_array = predictor.scaler.transform(feature_df.loc[:, predictor.feature_columns])
    scaled_df = pd.DataFrame(scaled_array, columns=predictor.feature_columns)
    prediction = float(predictor.model.predict(scaled_df)[0])
    if np.isnan(prediction) or prediction < 0 or prediction > predictor.max_kwh_per_unit:
        return {"source": "fallback", "reason": "prediction_out_of_range"}
    return {"source": "model", "efficiency": prediction, "confidence": 1.0}


def _evaluate_saved_bundle_on_holdout(
    *,
    predictor_cls,
    model_path: Path,
    preprocessor_path: Path,
    engineered_df,
    eval_months: list[str],
    verbose: bool = False,
):
    import numpy as np
    import pandas as pd
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    result = {
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

    predictor = predictor_cls(
        model_path=str(model_path),
        preprocessor_path=str(preprocessor_path),
    )
    _log(verbose, f"holdout_predictor_loaded:{model_path.name}")
    if (
        not getattr(predictor, "loaded_model", False)
        or not getattr(predictor, "loaded_preprocessor", False)
        or getattr(predictor, "scaler", None) is None
        or not getattr(predictor, "feature_columns", None)
    ):
        result["failure_reason"] = "predictor_artifacts_not_loadable"
        return result
    if not eval_months:
        result["failure_reason"] = "no_eval_months_assigned"
        return result

    eval_input_df = engineered_df[engineered_df["month_year"].isin(eval_months)].copy()
    _log(verbose, f"holdout_eval_rows:{len(eval_input_df)}:{model_path.name}")
    if eval_input_df.empty:
        result["failure_reason"] = "no_eval_rows_available"
        return result

    eval_input_df = eval_input_df.reset_index(drop=True)
    result["rows_considered"] = int(len(eval_input_df))
    result["distinct_machines_retained"] = int(eval_input_df["machine_id"].nunique())

    feature_df = pd.DataFrame(index=eval_input_df.index)
    feature_defaults = predictor.feature_defaults or {}
    for column_name in predictor.feature_columns:
        feature_df[column_name] = float(feature_defaults.get(column_name, 0.0))

    machine_parts = eval_input_df["machine_id"].astype(str).str.split("-", n=1, expand=True)
    machine_type = machine_parts[0].fillna("024")
    machine_number = pd.to_numeric(machine_parts[1], errors="coerce").fillna(1).astype(int)
    task_complexity_map = {"Easy": 1, "Medium": 2, "Hard": 3, "易": 1, "中": 2, "難": 3}
    task_complexity = eval_input_df["task_difficulty"].map(task_complexity_map).fillna(2).astype(float)
    is_night_shift = (
        eval_input_df["hour_of_day"].astype(int).isin(range(20, 24))
        | eval_input_df["hour_of_day"].astype(int).isin(range(0, 7))
    ).astype(int)
    maintenance_urgency = eval_input_df["hours_since_last_maintenance"].astype(float) / 720.0
    needs_maintenance = (eval_input_df["hours_since_last_maintenance"].astype(float) > 1000).astype(int)

    direct_columns = {
        "hour_of_day": eval_input_df["hour_of_day"].astype(int),
        "day_of_week": pd.to_datetime(eval_input_df["datetime"], errors="coerce").dt.dayofweek.fillna(0).astype(int),
        "month": eval_input_df["month"].astype(int),
        "is_weekend": eval_input_df["is_weekend"].astype(int),
        "is_night_shift": is_night_shift,
        "machine_number": machine_number,
        "team_size": eval_input_df["team_size"].astype(float),
        "task_complexity": task_complexity,
        "hours_since_last_maintenance": eval_input_df["hours_since_last_maintenance"].astype(float),
        "maintenance_urgency": maintenance_urgency,
        "needs_maintenance": needs_maintenance,
        "maintenance_intensity_30d": eval_input_df["maintenance_intensity_30d"].astype(float),
        "cumulative_maintenance_count": eval_input_df["cumulative_maintenance_count"].astype(float),
        "production_qty": eval_input_df["production_qty"].astype(float),
    }
    for column_name, values in direct_columns.items():
        if column_name in feature_df.columns:
            feature_df[column_name] = values

    encoded_columns = {
        "machine_type_encoded": machine_type.map(
            lambda value: _encode_with_label_encoder(value, predictor.label_encoders.get("machine_type"))
        ),
        "team_leader_encoded": eval_input_df["team_leader"].map(
            lambda value: _encode_with_label_encoder(value, predictor.label_encoders.get("team_leader"))
        ),
        "material_code_encoded": eval_input_df["material_code"].map(
            lambda value: _encode_with_label_encoder(value, predictor.label_encoders.get("material_code"))
        ),
        "last_maintenance_type_encoded": eval_input_df["last_maintenance_type"].map(
            lambda value: _encode_with_label_encoder(
                value,
                predictor.label_encoders.get("last_maintenance_type"),
            )
        ),
    }
    for column_name, values in encoded_columns.items():
        if column_name in feature_df.columns:
            feature_df[column_name] = values.astype(int)

    scaled_array = predictor.scaler.transform(feature_df.loc[:, predictor.feature_columns])
    _log(verbose, f"holdout_scaled:{model_path.name}")
    scaled_df = pd.DataFrame(scaled_array, columns=predictor.feature_columns, index=feature_df.index)
    raw_predictions = pd.Series(predictor.model.predict(scaled_df), index=eval_input_df.index, dtype=float)
    _log(verbose, f"holdout_predicted:{model_path.name}")
    truth_mask = eval_input_df["kwh_per_unit"].notna()
    model_mask = raw_predictions.notna() & raw_predictions.ge(0) & raw_predictions.le(predictor.max_kwh_per_unit)
    valid_mask = truth_mask & model_mask

    result["rows_non_model_source"] = int((truth_mask & ~model_mask).sum())
    if result["rows_non_model_source"]:
        first_row = eval_input_df.loc[truth_mask & ~model_mask].iloc[0]
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
    targets = eval_input_df.loc[valid_mask, "kwh_per_unit"].astype(float)
    predictions = clipped_predictions.loc[valid_mask].astype(float)

    result["rows_evaluated"] = int(valid_mask.sum())
    result["r2_score"] = float(r2_score(targets, predictions))
    result["mae"] = float(mean_absolute_error(targets, predictions))
    result["rmse"] = float(np.sqrt(mean_squared_error(targets, predictions)))
    result["passed"] = True
    return result


def _run_direct_predictor_smoke(
    *,
    predictor_cls,
    model_path: Path,
    preprocessor_path: Path,
    candidate_df,
):
    result = {
        "passed": False,
        "failure_reason": None,
        "prediction_source": None,
        "predicted_efficiency": None,
        "confidence": None,
        "sample_month": None,
        "sample_machine_id": None,
        "sample_hour_ts": None,
        "candidate_rows_considered": 0,
        "first_failure": None,
    }
    if candidate_df.empty:
        result["failure_reason"] = "no_candidate_rows_available"
        return result

    predictor = predictor_cls(
        model_path=str(model_path),
        preprocessor_path=str(preprocessor_path),
    )
    if (
        not getattr(predictor, "loaded_model", False)
        or not getattr(predictor, "loaded_preprocessor", False)
        or getattr(predictor, "scaler", None) is None
        or not getattr(predictor, "feature_columns", None)
    ):
        result["failure_reason"] = "predictor_artifacts_unavailable"
        return result

    for _, row in candidate_df.iterrows():
        result["candidate_rows_considered"] = int(result["candidate_rows_considered"]) + 1
        prediction = _predict_single_row(predictor, row)
        source = prediction.get("source")
        if source != "model" and result["first_failure"] is None:
            result["first_failure"] = {
                "month": row["month_year"],
                "machine_id": row["machine_id"],
                "hour_ts": row["hour_ts"],
                "prediction_source": source,
            }
            continue

        if source == "model":
            result.update(
                {
                    "passed": True,
                    "failure_reason": None,
                    "prediction_source": source,
                    "predicted_efficiency": float(prediction["efficiency"]),
                    "confidence": float(prediction["confidence"]),
                    "sample_month": row["month_year"],
                    "sample_machine_id": row["machine_id"],
                    "sample_hour_ts": row["hour_ts"],
                }
            )
            return result

    result["failure_reason"] = "predictor_returned_non_model_source"
    return result


def _bootstrap_core_modules(repo_root: Path, *, verbose: bool = False):
    core_dir = repo_root / "core"
    core_package = sys.modules.get("core")
    if core_package is None:
        core_package = types.ModuleType("core")
        core_package.__path__ = [str(core_dir)]
        sys.modules["core"] = core_package

    _log(verbose, "bootstrap_runtime_paths_start")
    _build_runtime_paths_module(repo_root)
    _log(verbose, "bootstrap_runtime_paths_done")
    _log(verbose, "bootstrap_canonical_ml_reader_start")
    _build_canonical_ml_reader_module()
    _log(verbose, "bootstrap_canonical_ml_reader_done")
    _log(verbose, "bootstrap_ml_predictor_start")
    _build_ml_predictor_module()
    _log(verbose, "bootstrap_ml_predictor_done")
    _log(verbose, "bootstrap_ml_trainer_start")
    module = _load_module("core.ml_trainer", core_dir / "ml_trainer.py")
    _log(verbose, "bootstrap_ml_trainer_done")
    return module


def main() -> None:
    args = _build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    _log(args.verbose, "bootstrap_core_start")
    ml_trainer = _bootstrap_core_modules(repo_root, verbose=args.verbose)
    _log(args.verbose, "bootstrap_core_done")

    live_db = repo_root / "manufacturing_data.db"
    live_model = repo_root / "models/production_efficiency_model.pkl"
    live_preprocessor = repo_root / "models/production_preprocessor.pkl"
    live_model_provenance = repo_root / "models/production_efficiency_model.provenance.json"
    live_preprocessor_provenance = repo_root / "models/production_preprocessor.provenance.json"
    staged_root = repo_root / "models/task14c_artifacts/staged_candidate_20260418_070130"
    staged_model = staged_root / "production_efficiency_model.candidate.task14c.pkl"
    staged_preprocessor = staged_root / "production_preprocessor.candidate.task14c.pkl"
    staged_summary_path = staged_root / "task14b_eval_summary.source.json"
    task14c_backup_root = repo_root / "models/task14c_artifacts/live_backup_20260418_070130"

    if args.working_db_path:
        temp_db_path = None
        working_db_path = Path(args.working_db_path).resolve()
        _log(args.verbose, f"using_working_db:{working_db_path}")
    elif args.temp_db_path:
        temp_db_path = Path(args.temp_db_path).resolve()
        _log(args.verbose, "copy_db_start")
        shutil.copy2(live_db, temp_db_path)
        working_db_path = temp_db_path
        _log(args.verbose, f"copy_db_done:{temp_db_path}")
    else:
        temp_db_path = None
        working_db_path = live_db
        _log(args.verbose, f"using_live_db:{live_db}")

    sqlite_connect = ml_trainer.sqlite3.connect

    def _readonly_aware_connect(path, *connect_args, **connect_kwargs):
        if str(path) == str(live_db):
            return sqlite_connect(
                f"file:{live_db}?mode=ro",
                *connect_args,
                uri=True,
                **connect_kwargs,
            )
        return sqlite_connect(path, *connect_args, **connect_kwargs)

    ml_trainer.sqlite3.connect = _readonly_aware_connect

    _log(args.verbose, "load_staged_summary_start")
    staged_summary = json.loads(staged_summary_path.read_text(encoding="utf-8"))
    _log(args.verbose, "load_staged_summary_done")

    _log(args.verbose, "prepare_load_data_start")
    preparer = ml_trainer.MLDataPreparer(
        db_path=working_db_path,
        preprocessor_path=live_preprocessor,
        min_training_rows=1,
        min_machine_count=1,
    )
    filtered_df = preparer.load_data()
    engineered_df = preparer.engineer_features(filtered_df)
    engineered_df["month_year"] = engineered_df["datetime"].dt.strftime("%B %Y")
    _log(args.verbose, f"prepare_load_data_done:{len(filtered_df)}")

    _log(args.verbose, "split_start")
    _, _, split_summary = ml_trainer._build_time_aware_holdout_split(
        engineered_df,
        eval_month_count=2,
    )
    eval_months = split_summary["eval_months"]
    _log(args.verbose, json.dumps({"split_summary": split_summary}))

    _log(args.verbose, "active_eval_start")
    active_eval = _evaluate_saved_bundle_on_holdout(
        predictor_cls=sys.modules["core.ml_predictor"].MLPredictor,
        model_path=live_model,
        preprocessor_path=live_preprocessor,
        engineered_df=engineered_df,
        eval_months=eval_months,
        verbose=args.verbose,
    )
    _log(args.verbose, json.dumps({"active_eval": active_eval}))

    _log(args.verbose, "candidate_eval_start")
    candidate_eval = _evaluate_saved_bundle_on_holdout(
        predictor_cls=sys.modules["core.ml_predictor"].MLPredictor,
        model_path=staged_model,
        preprocessor_path=staged_preprocessor,
        engineered_df=engineered_df,
        eval_months=eval_months,
        verbose=args.verbose,
    )
    _log(args.verbose, json.dumps({"candidate_eval": candidate_eval}))

    _log(args.verbose, "candidate_smoke_start")
    candidate_smoke = _run_direct_predictor_smoke(
        predictor_cls=sys.modules["core.ml_predictor"].MLPredictor,
        model_path=staged_model,
        preprocessor_path=staged_preprocessor,
        candidate_df=engineered_df[engineered_df["month_year"].isin(eval_months)].copy(),
    )
    _log(args.verbose, json.dumps({"candidate_smoke": candidate_smoke}))

    payload = {
        "repo_root": str(repo_root),
        "live_db_path": str(live_db),
        "temp_db_path": str(temp_db_path) if temp_db_path is not None else None,
        "working_db_path": str(working_db_path),
        "live_db_sha1": _sha1(live_db),
        "live_checksums": {
            "model": _sha256(live_model),
            "preprocessor": _sha256(live_preprocessor),
            "model_provenance": _sha256(live_model_provenance),
            "preprocessor_provenance": _sha256(live_preprocessor_provenance),
        },
        "staged_checksums": {
            "model": _sha256(staged_model),
            "preprocessor": _sha256(staged_preprocessor),
            "summary": _sha256(staged_summary_path),
        },
        "task14c_backup_checksums": {
            "model": _sha256(task14c_backup_root / "production_efficiency_model.pkl"),
            "preprocessor": _sha256(task14c_backup_root / "production_preprocessor.pkl"),
            "model_provenance": _sha256(
                task14c_backup_root / "production_efficiency_model.provenance.json"
            ),
            "preprocessor_provenance": _sha256(
                task14c_backup_root / "production_preprocessor.provenance.json"
            ),
        },
        "load_summary": dict(preparer.last_load_summary),
        "month_coverage": list(preparer.last_month_coverage),
        "team_size_fallback_summary": dict(preparer.last_team_size_fallback_summary),
        "split_summary": split_summary,
        "task14b_protocol": staged_summary.get("protocol"),
        "active_eval": active_eval,
        "candidate_eval": candidate_eval,
        "candidate_smoke": candidate_smoke,
        "candidate_model_name": staged_summary.get("candidate_training", {}).get("best_model_name"),
        "candidate_model_timestamp": None,
    }
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
