from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from pathlib import Path

import pandas as pd

from core.canonical_ml_reader import CanonicalMLReader
from core.canonical_optimization_reader import CanonicalOptimizationReader
from core.maintenance_evidence import MaintenanceEvidenceReader
from core.ml_predictor import MLPredictor
from core.runtime_paths import get_database_path, get_models_dir


QUEUE_COLUMNS = [
    "job_id",
    "provenance_label",
    "source_mode",
    "source_month",
    "source_machine_id",
    "source_hour_ts",
    "preferred_machine_family",
    "material_code",
    "task_name",
    "task_difficulty",
    "quantity",
    "urgency_label",
    "urgency_rank",
    "team_leader",
    "team_size",
    "hour_of_day",
    "last_maintenance_type",
]

CANDIDATE_COLUMNS = [
    "assignment_strategy",
    "assignment_step",
    "job_id",
    "machine_id",
    "machine_family",
    "slot_index",
    "support_tier",
    "support_detail",
    "maintenance_status",
    "model_supported",
    "predicted_kwh_per_unit",
    "estimated_energy_cost",
    "transition_penalty",
    "maintenance_penalty",
    "support_penalty",
    "urgency_penalty",
    "model_unavailable_penalty",
    "total_score",
    "exclude_reason",
]

SCHEDULE_COLUMNS = [
    "job_id",
    "machine_id",
    "machine_family",
    "slot_index",
    "support_tier",
    "maintenance_status",
    "model_supported",
    "predicted_kwh_per_unit",
    "estimated_energy_cost",
    "transition_penalty",
    "maintenance_penalty",
    "support_penalty",
    "urgency_penalty",
    "model_unavailable_penalty",
    "total_score",
]

SUPPORT_TIER_RANK = {
    "Material + task history": 0,
    "Material + task-difficulty history": 1,
    "Material history only": 2,
    "Task-difficulty history only": 3,
    "Machine-family fallback": 4,
}

SUPPORT_TIER_MULTIPLIER = {
    "Material + task history": 0.00,
    "Material + task-difficulty history": 0.10,
    "Material history only": 0.20,
    "Task-difficulty history only": 0.28,
    "Machine-family fallback": 0.55,
}

URGENCY_WEIGHTS = {
    "High": 1.00,
    "Medium": 0.65,
    "Low": 0.35,
}

REAL_INPUT_REQUIRED_COLUMNS = [
    "preferred_machine_family",
    "material_code",
    "task_name",
    "quantity",
]

REAL_INPUT_OPTIONAL_COLUMNS = [
    "job_id",
    "task_difficulty",
    "urgency_label",
    "team_leader",
    "team_size",
    "hour_of_day",
    "last_maintenance_type",
]

REAL_INPUT_TEMPLATE_COLUMNS = [
    *REAL_INPUT_REQUIRED_COLUMNS,
    *REAL_INPUT_OPTIONAL_COLUMNS,
]

REAL_INPUT_COLUMN_ALIASES = {
    "jobid": "job_id",
    "preferredmachinefamily": "preferred_machine_family",
    "machinefamily": "preferred_machine_family",
    "material": "material_code",
    "materialcode": "material_code",
    "task": "task_name",
    "taskname": "task_name",
    "taskdifficulty": "task_difficulty",
    "urgency": "urgency_label",
    "teamleader": "team_leader",
    "teamsize": "team_size",
    "hourofday": "hour_of_day",
    "lastmaintenancetype": "last_maintenance_type",
}

ACTIVE_MODEL_FILENAME = "production_efficiency_model.pkl"
ACTIVE_PREPROCESSOR_FILENAME = "production_preprocessor.pkl"
ACTIVE_MODEL_PROVENANCE_FILENAME = "production_efficiency_model.provenance.json"
ACTIVE_PREPROCESSOR_PROVENANCE_FILENAME = "production_preprocessor.provenance.json"


def get_available_months(db_path: str | Path | None = None) -> list[str]:
    return CanonicalOptimizationReader(db_path=db_path).get_available_months()


def get_active_saved_artifact_binding() -> dict[str, object]:
    models_dir = get_models_dir().resolve()
    model_path = (models_dir / ACTIVE_MODEL_FILENAME).resolve()
    preprocessor_path = (models_dir / ACTIVE_PREPROCESSOR_FILENAME).resolve()
    model_provenance_path = (models_dir / ACTIVE_MODEL_PROVENANCE_FILENAME).resolve()
    preprocessor_provenance_path = (models_dir / ACTIVE_PREPROCESSOR_PROVENANCE_FILENAME).resolve()
    model_manifest = _read_manifest_summary(model_provenance_path)
    preprocessor_manifest = _read_manifest_summary(preprocessor_provenance_path)

    return {
        "model_path": str(model_path),
        "preprocessor_path": str(preprocessor_path),
        "model_provenance_path": str(model_provenance_path),
        "preprocessor_provenance_path": str(preprocessor_provenance_path),
        "task_tag": model_manifest.get("task_tag") or preprocessor_manifest.get("task_tag"),
        "artifact_version_id": (
            model_manifest.get("artifact_version_id")
            or preprocessor_manifest.get("artifact_version_id")
        ),
        "selected_model": (
            model_manifest.get("selected_model")
            or preprocessor_manifest.get("selected_model")
        ),
        "active_db_path": model_manifest.get("active_db_path") or preprocessor_manifest.get("active_db_path"),
        "model_manifest_summary": model_manifest,
        "preprocessor_manifest_summary": preprocessor_manifest,
        "paths_use_repo_models_dir": all(
            Path(candidate).parent == models_dir
            for candidate in (
                model_path,
                preprocessor_path,
                model_provenance_path,
                preprocessor_provenance_path,
            )
        ),
    }


def build_active_saved_predictor() -> tuple[MLPredictor, dict[str, object]]:
    binding = get_active_saved_artifact_binding()
    predictor = MLPredictor(
        model_path=binding["model_path"],
        preprocessor_path=binding["preprocessor_path"],
    )
    binding = {
        **binding,
        "predictor_instantiated_from_active_paths": True,
        "model_loaded": bool(getattr(predictor, "loaded_model", False)),
        "preprocessor_loaded": bool(getattr(predictor, "loaded_preprocessor", False)),
    }
    return predictor, binding


def get_real_input_queue_contract() -> dict[str, object]:
    return {
        "supported_extensions": [".csv", ".xlsx", ".xls"],
        "required_columns": list(REAL_INPUT_REQUIRED_COLUMNS),
        "optional_columns": list(REAL_INPUT_OPTIONAL_COLUMNS),
        "template_columns": list(REAL_INPUT_TEMPLATE_COLUMNS),
        "note": (
            "Rows are validated read-only, then normalized into the same prototype queue schema used by the "
            "real-seeded path. Missing required columns or invalid row values block the upload honestly."
        ),
    }


def load_real_input_queue(
    file_bytes: bytes,
    *,
    file_name: str,
    month_year: str,
) -> dict[str, object]:
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        return {
            "blocked": True,
            "message": (
                f"Unsupported queue file type `{suffix or 'unknown'}`. "
                "Use CSV or Excel (`.xlsx`/`.xls`)."
            ),
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "raw_input_df": pd.DataFrame(),
        }

    if not file_bytes:
        return {
            "blocked": True,
            "message": "Uploaded queue file is empty.",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "raw_input_df": pd.DataFrame(),
        }

    try:
        if suffix == ".csv":
            raw_input_df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            raw_input_df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as exc:
        return {
            "blocked": True,
            "message": f"Queue file could not be parsed: {exc}",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "raw_input_df": pd.DataFrame(),
        }

    if raw_input_df.empty:
        return {
            "blocked": True,
            "message": "Uploaded queue file does not contain any rows.",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "raw_input_df": raw_input_df,
        }

    normalized_input_df = _normalize_real_input_columns(raw_input_df)
    missing_columns = [
        column_name
        for column_name in REAL_INPUT_REQUIRED_COLUMNS
        if column_name not in normalized_input_df.columns
    ]
    if missing_columns:
        return {
            "blocked": True,
            "message": (
                "Uploaded queue file is missing required columns: "
                + ", ".join(missing_columns)
            ),
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "raw_input_df": normalized_input_df,
            "missing_columns": missing_columns,
        }

    normalized_queue_payload = normalize_manual_queue(
        normalized_input_df.loc[:, [column for column in REAL_INPUT_TEMPLATE_COLUMNS if column in normalized_input_df.columns]].copy(),
        month_year=month_year,
        provenance_label="Real-input pilot queue",
        source_mode="real_input_queue_upload",
        source_machine_id="uploaded_pending_queue",
        validation_label="Real-input pilot queue",
    )
    normalized_queue_payload["raw_input_df"] = normalized_input_df
    normalized_queue_payload["input_summary"] = {
        "file_name": file_name,
        "file_type": suffix,
        "uploaded_rows": int(len(normalized_input_df)),
        "accepted_rows": int(len(normalized_queue_payload["queue_df"])),
    }
    return normalized_queue_payload


def build_scheduling_export_artifacts(
    payload: dict[str, object],
    *,
    runtime_mode: str,
    anchor_month: str,
) -> dict[str, object]:
    export_frames = {
        "queue_input.csv": _export_frame(payload.get("queue_df")),
        "optimized_schedule.csv": _export_frame(payload.get("optimized_schedule_df")),
        "candidate_scores.csv": _export_frame(payload.get("feasible_assignment_df")),
        "baseline_comparison.csv": _export_frame(payload.get("baseline_comparison_df")),
        "score_breakdown.csv": _export_frame(payload.get("score_breakdown_df")),
        "constraint_summary.csv": _export_frame(payload.get("constraint_summary_df")),
        "blocked_reasons.csv": _export_frame(payload.get("blocked_reasons_df")),
    }
    manifest = {
        "prototype": "constraint_aware_scheduling_prototype",
        "runtime_mode": runtime_mode,
        "anchor_month": anchor_month,
        "queue_provenance": payload.get("provenance_label"),
        "queue_generation_rule": payload.get("queue_generation_rule"),
        "seed_summary": payload.get("seed_summary"),
        "row_counts": {
            "queue_rows": int(len(_export_frame(payload.get("queue_df")))),
            "optimized_schedule_rows": int(len(_export_frame(payload.get("optimized_schedule_df")))),
            "candidate_rows": int(len(_export_frame(payload.get("feasible_assignment_df")))),
        },
        "non_defended_notice": (
            "Experimental pilot-review export only. Read-only prototype output. "
            "Not a live scheduling engine, solver approval, or shop-floor execution command."
        ),
        "export_files": list(export_frames.keys()),
    }
    return {
        "export_frames": export_frames,
        "manifest_json": json.dumps(manifest, indent=2, ensure_ascii=True),
    }


def build_real_seeded_queue(
    month_year: str,
    *,
    queue_size: int = 6,
    db_path: str | Path | None = None,
) -> dict[str, object]:
    month_df = _read_fact_rows(month_year=month_year, db_path=db_path)
    if month_df.empty:
        return {
            "blocked": True,
            "message": f"No canonical month slice is available for {month_year}.",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "queue_generation_rule": "none",
            "provenance_label": "Real-seeded synthetic queue",
        }

    seed_df = _build_queue_seed_frame(month_df)
    if seed_df.empty:
        return {
            "blocked": True,
            "message": (
                f"{month_year} does not have enough positive-good-qty, task-mapped canonical rows "
                "to seed the prototype queue honestly."
            ),
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
            "queue_generation_rule": "none",
            "provenance_label": "Real-seeded synthetic queue",
        }

    sample_count = max(1, min(int(queue_size), len(seed_df)))
    seed = _stable_seed(f"{month_year}|{sample_count}")
    sampled_df = seed_df.sample(
        n=sample_count,
        replace=False,
        weights=seed_df["seed_weight"],
        random_state=seed,
    ).sort_values(["seed_weight", "source_hour_ts", "material_code"], ascending=[False, True, True])

    quantity_reference = seed_df["median_good_qty"].dropna()
    scale_cycle = [0.85, 1.00, 1.15, 0.95, 1.05, 0.90, 1.10, 0.80]
    rows = []
    for index, (_, row) in enumerate(sampled_df.reset_index(drop=True).iterrows(), start=1):
        scaled_quantity = max(
            25.0,
            _round_to_step(float(row["median_good_qty"]) * scale_cycle[(index - 1) % len(scale_cycle)], 25.0),
        )
        urgency_label, urgency_rank = _volume_proxy_to_urgency(scaled_quantity, quantity_reference)
        rows.append(
            {
                "job_id": f"SYN-{index:02d}",
                "provenance_label": "Real-seeded synthetic queue",
                "source_mode": "real_seeded_synthetic_queue",
                "source_month": month_year,
                "source_machine_id": row["source_machine_id"],
                "source_hour_ts": row["source_hour_ts"],
                "preferred_machine_family": row["preferred_machine_family"],
                "material_code": row["material_code"],
                "task_name": row["task_name"],
                "task_difficulty": row["task_difficulty"],
                "quantity": scaled_quantity,
                "urgency_label": urgency_label,
                "urgency_rank": urgency_rank,
                "team_leader": row["team_leader"],
                "team_size": row["team_size"],
                "hour_of_day": row["hour_of_day"],
                "last_maintenance_type": row["last_maintenance_type"],
            }
        )

    return {
        "blocked": False,
        "message": None,
        "queue_df": pd.DataFrame(rows, columns=QUEUE_COLUMNS),
        "queue_generation_rule": (
            "Sample distinct material/task/family combinations from the selected canonical month "
            "with deterministic weighting by observed row count; keep material/task/family provenance, "
            "then scale the representative median good_qty by a fixed deterministic multiplier cycle."
        ),
        "provenance_label": "Real-seeded synthetic queue",
        "seed_summary": {
            "seed_month": month_year,
            "sample_count": sample_count,
            "candidate_seed_rows": int(len(seed_df)),
            "deterministic_seed": seed,
        },
    }


def normalize_manual_queue(
    edited_queue_df: pd.DataFrame,
    *,
    month_year: str,
    provenance_label: str = "Manual demo input",
    source_mode: str = "manual_demo_queue",
    source_machine_id: str = "manual_demo_input",
    validation_label: str = "Manual demo queue",
) -> dict[str, object]:
    if edited_queue_df is None or edited_queue_df.empty:
        return {
            "blocked": True,
            "message": f"{validation_label} is empty.",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
        }

    rows = []
    invalid_rows = []
    for index, (_, row) in enumerate(edited_queue_df.iterrows(), start=1):
        material_code = _clean_text(row.get("material_code"))
        task_name = _clean_text(row.get("task_name"))
        preferred_machine_family = _clean_text(row.get("preferred_machine_family"))
        quantity = _float_or_none(row.get("quantity"))
        task_difficulty = _clean_text(row.get("task_difficulty")) or CanonicalMLReader._derive_task_difficulty(task_name)

        if (
            material_code is None
            or task_name is None
            or preferred_machine_family is None
            or quantity is None
            or quantity <= 0
        ):
            invalid_rows.append(index)
            continue

        urgency_label = _normalize_urgency_label(row.get("urgency_label"))
        rows.append(
            {
                "job_id": _clean_text(row.get("job_id")) or f"MAN-{index:02d}",
                "provenance_label": provenance_label,
                "source_mode": source_mode,
                "source_month": month_year,
                "source_machine_id": source_machine_id,
                "source_hour_ts": None,
                "preferred_machine_family": preferred_machine_family,
                "material_code": material_code,
                "task_name": task_name,
                "task_difficulty": task_difficulty,
                "quantity": _round_to_step(quantity, 25.0),
                "urgency_label": urgency_label,
                "urgency_rank": _urgency_rank(urgency_label),
                "team_leader": _clean_text(row.get("team_leader")) or "unknown",
                "team_size": _float_or_none(row.get("team_size")),
                "hour_of_day": _int_or_none(row.get("hour_of_day")) or 8,
                "last_maintenance_type": _clean_text(row.get("last_maintenance_type")) or "unknown",
            }
        )

    queue_df = pd.DataFrame(rows, columns=QUEUE_COLUMNS)
    if queue_df.empty:
        return {
            "blocked": True,
            "message": f"{validation_label} did not contain any valid rows after validation.",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
        }

    return {
        "blocked": False,
        "message": None if not invalid_rows else f"Skipped invalid manual queue rows: {invalid_rows}",
        "queue_df": queue_df,
    }


def run_constraint_aware_scheduling(
    month_year: str,
    *,
    queue_size: int = 6,
    max_jobs_per_machine: int = 2,
    queue_mode: str = "real_seeded",
    manual_queue_df: pd.DataFrame | None = None,
    predictor: MLPredictor | None = None,
    db_path: str | Path | None = None,
) -> dict[str, object]:
    db_path = str(db_path or get_database_path())
    month_df = _read_fact_rows(month_year=month_year, db_path=db_path)
    if month_df.empty:
        return {
            "blocked": True,
            "message": f"No canonical month slice is available for {month_year}.",
            "queue_df": pd.DataFrame(columns=QUEUE_COLUMNS),
        }

    if queue_mode == "manual":
        queue_payload = normalize_manual_queue(
            manual_queue_df if manual_queue_df is not None else pd.DataFrame(),
            month_year=month_year,
        )
        queue_generation_rule = "User-defined demo queue entered in the experimental UI."
    elif queue_mode == "real_input":
        queue_df = manual_queue_df.copy() if isinstance(manual_queue_df, pd.DataFrame) else pd.DataFrame()
        queue_payload = {
            "blocked": queue_df.empty,
            "message": "Validated real-input queue is empty." if queue_df.empty else None,
            "queue_df": queue_df,
            "provenance_label": "Real-input pilot queue",
        }
        queue_generation_rule = (
            "Uploaded pending queue file validated against the narrow pilot-review queue contract."
        )
    else:
        queue_payload = build_real_seeded_queue(month_year, queue_size=queue_size, db_path=db_path)
        queue_generation_rule = queue_payload.get("queue_generation_rule", "none")

    if queue_payload["blocked"]:
        return {
            "blocked": True,
            "message": queue_payload["message"],
            "queue_df": queue_payload["queue_df"],
        }

    queue_df = queue_payload["queue_df"].copy()
    month_context = _build_month_context(month_df, month_year)
    month_end = month_context["month_end"]
    history_df = _read_fact_rows(month_end=month_end, db_path=db_path)
    machine_profiles_df = _build_machine_profiles(month_df, month_year, db_path=db_path)
    if machine_profiles_df.empty:
        return {
            "blocked": True,
            "message": f"No canonical machine pool is available for {month_year}.",
            "queue_df": queue_df,
        }

    support_maps = _build_support_maps(history_df)
    active_artifact_binding = get_active_saved_artifact_binding()
    if predictor is None:
        predictor, active_artifact_binding = build_active_saved_predictor()
    else:
        active_artifact_binding = {
            **active_artifact_binding,
            "predictor_instantiated_from_active_paths": False,
            "model_loaded": bool(getattr(predictor, "loaded_model", False)),
            "preprocessor_loaded": bool(getattr(predictor, "loaded_preprocessor", False)),
        }

    optimized_result = _assign_jobs(
        queue_df,
        machine_profiles_df,
        support_maps,
        month_context,
        predictor,
        strategy="optimized",
        max_jobs_per_machine=max_jobs_per_machine,
    )
    if not optimized_result["schedule_df"].empty:
        swap_result = _run_best_swap_pass(
            queue_df,
            optimized_result["schedule_df"],
            machine_profiles_df,
            support_maps,
            month_context,
            predictor,
            max_jobs_per_machine=max_jobs_per_machine,
        )
        if swap_result["improved"]:
            optimized_result["schedule_df"] = swap_result["schedule_df"]
            optimized_result["swap_summary"] = swap_result["swap_summary"]
    else:
        optimized_result["swap_summary"] = "No optimized assignments were available for a swap pass."

    naive_result = _assign_jobs(
        queue_df,
        machine_profiles_df,
        support_maps,
        month_context,
        predictor,
        strategy="naive",
        max_jobs_per_machine=max_jobs_per_machine,
    )

    optimized_schedule_df = optimized_result["schedule_df"].copy()
    naive_schedule_df = naive_result["schedule_df"].copy()
    optimized_candidate_df = optimized_result["candidate_df"].copy()

    baseline_comparison_df = _build_baseline_comparison(optimized_schedule_df, naive_schedule_df)
    score_breakdown_df = _build_score_breakdown(optimized_schedule_df, naive_schedule_df)
    blocked_reasons_df = _build_blocked_reason_summary(
        optimized_candidate_df,
        optimized_result["unscheduled_df"],
    )
    feasible_assignment_df = _build_feasible_assignment_table(optimized_candidate_df)

    return {
        "blocked": False,
        "message": queue_payload["message"],
        "queue_df": queue_df,
        "queue_generation_rule": queue_generation_rule,
        "provenance_label": queue_payload.get("provenance_label", "Manual demo input"),
        "seed_summary": queue_payload.get("seed_summary"),
        "active_artifact_binding": active_artifact_binding,
        "machine_pool_df": machine_profiles_df,
        "feasible_assignment_df": feasible_assignment_df,
        "optimized_schedule_df": optimized_schedule_df,
        "naive_schedule_df": naive_schedule_df,
        "baseline_comparison_df": baseline_comparison_df,
        "score_breakdown_df": score_breakdown_df,
        "blocked_reasons_df": blocked_reasons_df,
        "constraint_summary_df": _build_constraint_summary(month_context, max_jobs_per_machine),
        "swap_summary": optimized_result.get("swap_summary", "No swap pass applied."),
        "optimization_note": (
            "This is a deterministic constraint-aware prototype with a transparent weighted score. "
            "It is not an approved live scheduling engine or shop-floor feasibility proof."
        ),
    }


def _assign_jobs(
    queue_df: pd.DataFrame,
    machine_profiles_df: pd.DataFrame,
    support_maps: dict[str, dict[tuple[str, str], int] | dict[tuple[str, str, str], int]],
    month_context: dict[str, object],
    predictor: MLPredictor,
    *,
    strategy: str,
    max_jobs_per_machine: int,
) -> dict[str, object]:
    order_df = queue_df.copy()
    if strategy == "optimized":
        order_df = order_df.sort_values(
            ["urgency_rank", "quantity", "job_id"],
            ascending=[False, False, True],
        ).reset_index(drop=True)
    else:
        order_df = order_df.reset_index(drop=True)

    machine_slots: dict[str, list[dict[str, object]]] = {
        machine_id: []
        for machine_id in machine_profiles_df["machine_id"].tolist()
    }
    candidate_frames = []
    chosen_rows = []
    unscheduled_rows = []

    for step, (_, job_row) in enumerate(order_df.iterrows(), start=1):
        candidate_df = _evaluate_job_candidates(
            job_row,
            machine_profiles_df,
            support_maps,
            month_context,
            predictor,
            machine_slots,
            assignment_strategy=strategy,
            assignment_step=step,
            max_jobs_per_machine=max_jobs_per_machine,
        )
        candidate_frames.append(candidate_df)
        feasible_df = candidate_df[candidate_df["exclude_reason"].isna()].copy()
        if feasible_df.empty:
            unscheduled_rows.append(
                {
                    "job_id": job_row["job_id"],
                    "reason": "No feasible machine survived the current prototype constraints.",
                }
            )
            continue

        if strategy == "optimized":
            selected_row = feasible_df.sort_values(
                [
                    "total_score",
                    "support_rank",
                    "model_supported",
                    "machine_id",
                ],
                ascending=[True, True, False, True],
            ).iloc[0]
        else:
            selected_row = feasible_df.sort_values(
                ["machine_id", "slot_index", "support_rank", "job_id"],
                ascending=[True, True, True, True],
            ).iloc[0]

        chosen_rows.append(selected_row[SCHEDULE_COLUMNS].to_dict())
        machine_slots[selected_row["machine_id"]].append(
            {
                "job_id": job_row["job_id"],
                "material_code": job_row["material_code"],
                "slot_index": int(selected_row["slot_index"]),
            }
        )

    candidate_df = (
        pd.concat(candidate_frames, ignore_index=True)
        if candidate_frames
        else pd.DataFrame(columns=CANDIDATE_COLUMNS + ["support_rank"])
    )
    schedule_df = pd.DataFrame(chosen_rows, columns=SCHEDULE_COLUMNS)
    if not schedule_df.empty:
        schedule_df = schedule_df.sort_values(["machine_id", "slot_index", "job_id"]).reset_index(drop=True)

    return {
        "candidate_df": candidate_df,
        "schedule_df": schedule_df,
        "unscheduled_df": pd.DataFrame(unscheduled_rows),
    }


def _run_best_swap_pass(
    queue_df: pd.DataFrame,
    schedule_df: pd.DataFrame,
    machine_profiles_df: pd.DataFrame,
    support_maps: dict[str, dict[tuple[str, str], int] | dict[tuple[str, str, str], int]],
    month_context: dict[str, object],
    predictor: MLPredictor,
    *,
    max_jobs_per_machine: int,
) -> dict[str, object]:
    if len(schedule_df) < 2:
        return {
            "improved": False,
            "schedule_df": schedule_df,
            "swap_summary": "Swap pass skipped because fewer than two jobs were assigned.",
        }

    queue_lookup = queue_df.set_index("job_id")
    best_schedule_df = schedule_df.copy()
    best_total = float(schedule_df["total_score"].fillna(0.0).sum())
    best_summary = "No improving swap was found."

    for left_index in range(len(schedule_df) - 1):
        left_row = schedule_df.iloc[left_index]
        for right_index in range(left_index + 1, len(schedule_df)):
            right_row = schedule_df.iloc[right_index]
            if left_row["machine_id"] == right_row["machine_id"]:
                continue

            swapped_df = schedule_df.copy()
            swapped_df.loc[left_index, ["machine_id", "slot_index"]] = [
                right_row["machine_id"],
                int(right_row["slot_index"]),
            ]
            swapped_df.loc[right_index, ["machine_id", "slot_index"]] = [
                left_row["machine_id"],
                int(left_row["slot_index"]),
            ]
            reevaluated_df = _reevaluate_fixed_schedule(
                swapped_df,
                queue_lookup,
                machine_profiles_df,
                support_maps,
                month_context,
                predictor,
                max_jobs_per_machine=max_jobs_per_machine,
            )
            if reevaluated_df.empty:
                continue

            reevaluated_total = float(reevaluated_df["total_score"].fillna(0.0).sum())
            if reevaluated_total + 1e-9 < best_total:
                best_total = reevaluated_total
                best_schedule_df = reevaluated_df
                best_summary = (
                    f"One best swap improved the composite score by {float(schedule_df['total_score'].fillna(0.0).sum()) - best_total:.2f} "
                    f"prototype points: {left_row['job_id']} <-> {right_row['job_id']}."
                )

    return {
        "improved": not best_schedule_df.equals(schedule_df),
        "schedule_df": best_schedule_df,
        "swap_summary": best_summary,
    }


def _reevaluate_fixed_schedule(
    schedule_df: pd.DataFrame,
    queue_lookup: pd.DataFrame,
    machine_profiles_df: pd.DataFrame,
    support_maps: dict[str, dict[tuple[str, str], int] | dict[tuple[str, str, str], int]],
    month_context: dict[str, object],
    predictor: MLPredictor,
    *,
    max_jobs_per_machine: int,
) -> pd.DataFrame:
    if schedule_df.empty:
        return schedule_df

    machine_slots: dict[str, list[dict[str, object]]] = {
        machine_id: []
        for machine_id in machine_profiles_df["machine_id"].tolist()
    }
    scored_rows = []
    for _, scheduled_row in schedule_df.sort_values(["slot_index", "machine_id", "job_id"]).iterrows():
        job_row = queue_lookup.loc[scheduled_row["job_id"]].copy()
        job_row["job_id"] = scheduled_row["job_id"]
        candidate_df = _evaluate_job_candidates(
            job_row,
            machine_profiles_df,
            support_maps,
            month_context,
            predictor,
            machine_slots,
            assignment_strategy="optimized",
            assignment_step=int(scheduled_row["slot_index"]),
            max_jobs_per_machine=max_jobs_per_machine,
            machine_id_filter=str(scheduled_row["machine_id"]),
            slot_index_filter=int(scheduled_row["slot_index"]),
        )
        feasible_df = candidate_df[candidate_df["exclude_reason"].isna()].copy()
        if feasible_df.empty:
            return pd.DataFrame(columns=SCHEDULE_COLUMNS)
        selected = feasible_df.iloc[0]
        scored_rows.append(selected[SCHEDULE_COLUMNS].to_dict())
        machine_slots[selected["machine_id"]].append(
            {
                "job_id": job_row["job_id"],
                "material_code": job_row["material_code"],
                "slot_index": int(selected["slot_index"]),
            }
        )

    return pd.DataFrame(scored_rows, columns=SCHEDULE_COLUMNS).sort_values(
        ["machine_id", "slot_index", "job_id"]
    ).reset_index(drop=True)


def _evaluate_job_candidates(
    job_row: pd.Series,
    machine_profiles_df: pd.DataFrame,
    support_maps: dict[str, dict[tuple[str, str], int] | dict[tuple[str, str, str], int]],
    month_context: dict[str, object],
    predictor: MLPredictor,
    machine_slots: dict[str, list[dict[str, object]]],
    *,
    assignment_strategy: str,
    assignment_step: int,
    max_jobs_per_machine: int,
    machine_id_filter: str | None = None,
    slot_index_filter: int | None = None,
) -> pd.DataFrame:
    preferred_family = _clean_text(job_row.get("preferred_machine_family"))
    family_pool_df = machine_profiles_df.copy()
    if preferred_family is not None:
        same_family_df = family_pool_df[family_pool_df["machine_family"] == preferred_family].copy()
        if not same_family_df.empty:
            family_pool_df = same_family_df

    if machine_id_filter is not None:
        family_pool_df = family_pool_df[family_pool_df["machine_id"] == machine_id_filter].copy()

    rows = []
    for _, machine_row in family_pool_df.iterrows():
        machine_id = str(machine_row["machine_id"])
        scheduled_jobs = machine_slots.get(machine_id, [])
        slot_index = int(slot_index_filter or (len(scheduled_jobs) + 1))
        exclude_reason = None
        if slot_index > max_jobs_per_machine:
            exclude_reason = "max_jobs_per_machine_reached"

        support_tier, support_detail = _resolve_support_tier(job_row, machine_row, support_maps)
        maintenance_status, maintenance_penalty, maintenance_exclude_reason = _resolve_maintenance_penalty(
            machine_row,
            month_context,
        )
        if exclude_reason is None and support_tier is None:
            exclude_reason = "incompatible_machine_family"
        if exclude_reason is None and maintenance_exclude_reason is not None:
            exclude_reason = maintenance_exclude_reason

        transition_penalty = 0.0
        if scheduled_jobs:
            prior_material = _clean_text(scheduled_jobs[-1].get("material_code"))
            if prior_material is not None and prior_material != _clean_text(job_row.get("material_code")):
                transition_penalty = float(month_context["transition_penalty_cost"])

        support_penalty = float(month_context["transition_penalty_cost"]) * SUPPORT_TIER_MULTIPLIER.get(
            support_tier or "Machine-family fallback",
            0.65,
        )
        urgency_penalty = float(month_context["transition_penalty_cost"]) * URGENCY_WEIGHTS.get(
            str(job_row.get("urgency_label") or "Medium"),
            0.65,
        ) * max(slot_index - 1, 0)

        prediction_payload = _predict_candidate(job_row, machine_row, month_context, predictor, slot_index)
        model_unavailable_penalty = (
            0.0 if prediction_payload["model_supported"] else float(month_context["transition_penalty_cost"]) * 0.65
        )
        total_score = (
            float(prediction_payload["estimated_energy_cost"] or 0.0)
            + transition_penalty
            + maintenance_penalty
            + support_penalty
            + urgency_penalty
            + model_unavailable_penalty
        )

        rows.append(
            {
                "assignment_strategy": assignment_strategy,
                "assignment_step": assignment_step,
                "job_id": job_row["job_id"],
                "machine_id": machine_id,
                "machine_family": machine_row["machine_family"],
                "slot_index": slot_index,
                "support_tier": support_tier,
                "support_detail": support_detail,
                "maintenance_status": maintenance_status,
                "model_supported": prediction_payload["model_supported"],
                "predicted_kwh_per_unit": prediction_payload["predicted_kwh_per_unit"],
                "estimated_energy_cost": prediction_payload["estimated_energy_cost"],
                "transition_penalty": round(float(transition_penalty), 4),
                "maintenance_penalty": round(float(maintenance_penalty), 4),
                "support_penalty": round(float(support_penalty), 4),
                "urgency_penalty": round(float(urgency_penalty), 4),
                "model_unavailable_penalty": round(float(model_unavailable_penalty), 4),
                "total_score": round(float(total_score), 4),
                "exclude_reason": exclude_reason,
                "support_rank": SUPPORT_TIER_RANK.get(support_tier or "Machine-family fallback", 99),
            }
        )

    candidate_df = pd.DataFrame(rows)
    if candidate_df.empty:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS + ["support_rank"])
    return candidate_df


def _resolve_support_tier(
    job_row: pd.Series,
    machine_row: pd.Series,
    support_maps: dict[str, dict[tuple[str, str], int] | dict[tuple[str, str, str], int]],
) -> tuple[str | None, str]:
    machine_id = str(machine_row["machine_id"])
    material_code = _clean_text(job_row.get("material_code")) or ""
    task_name = _clean_text(job_row.get("task_name")) or ""
    task_difficulty = _clean_text(job_row.get("task_difficulty")) or ""
    machine_family = _clean_text(machine_row.get("machine_family"))
    preferred_family = _clean_text(job_row.get("preferred_machine_family"))

    joint_support = int(support_maps["joint"].get((machine_id, material_code, task_name), 0))
    material_support = int(support_maps["material"].get((machine_id, material_code), 0))
    difficulty_support = int(support_maps["difficulty"].get((machine_id, task_difficulty), 0))

    if joint_support > 0:
        return "Material + task history", f"{joint_support} historical rows on this exact material/task pair."
    if material_support > 0 and difficulty_support > 0:
        return (
            "Material + task-difficulty history",
            f"{material_support} material rows and {difficulty_support} task-difficulty rows on this machine.",
        )
    if material_support > 0:
        return "Material history only", f"{material_support} historical rows on this material."
    if difficulty_support > 0:
        return "Task-difficulty history only", f"{difficulty_support} historical rows on this task-difficulty tier."
    if preferred_family is not None and machine_family == preferred_family:
        return "Machine-family fallback", "Family match only; exact material/task support was sparse."
    return None, "Machine does not match the preferred family for this demo job."


def _resolve_maintenance_penalty(
    machine_row: pd.Series,
    month_context: dict[str, object],
) -> tuple[str, float, str | None]:
    transition_penalty_cost = float(month_context["transition_penalty_cost"])
    maintenance_available = bool(machine_row.get("maintenance_available"))
    days_since_last_maintenance = _float_or_none(machine_row.get("days_since_last_maintenance"))
    pm_ratio_all_time = _float_or_none(machine_row.get("pm_ratio_all_time"))
    total_events = _float_or_none(machine_row.get("total_events"))
    avg_hours = _float_or_none(machine_row.get("latest_hours_since_last_maintenance"))

    if maintenance_available:
        risk = 0.0
        if days_since_last_maintenance is not None:
            risk += min(days_since_last_maintenance / 120.0, 2.0) * 0.35
        if pm_ratio_all_time is not None:
            if pm_ratio_all_time < 0.10:
                risk += 0.35
            elif pm_ratio_all_time < 0.30:
                risk += 0.15
        if total_events is not None and total_events < 5:
            risk += 0.10
        if (days_since_last_maintenance or 0) >= 180 and (pm_ratio_all_time or 0) <= 0.05:
            return "Maintenance blackout", round(transition_penalty_cost * risk, 4), "maintenance_blackout"
        return "Evidence-backed maintenance profile", round(transition_penalty_cost * risk, 4), None

    if avg_hours is not None and avg_hours >= 3000:
        return (
            "Maintenance blackout",
            round(transition_penalty_cost * 1.10, 4),
            "maintenance_blackout",
        )

    evidence_gap_penalty = 0.40 if avg_hours is None else min(avg_hours / 1800.0, 1.0) * 0.30
    return "Maintenance evidence gap", round(transition_penalty_cost * evidence_gap_penalty, 4), None


def _predict_candidate(
    job_row: pd.Series,
    machine_row: pd.Series,
    month_context: dict[str, object],
    predictor: MLPredictor,
    slot_index: int,
) -> dict[str, object]:
    quantity = _float_or_none(job_row.get("quantity"))
    task_difficulty = _clean_text(job_row.get("task_difficulty"))
    hours_since_last_maintenance = _float_or_none(machine_row.get("latest_hours_since_last_maintenance"))

    if quantity is None or quantity <= 0 or task_difficulty is None or hours_since_last_maintenance is None:
        return {
            "model_supported": False,
            "predicted_kwh_per_unit": None,
            "estimated_energy_cost": None,
        }

    hour_of_day = (_int_or_none(job_row.get("hour_of_day")) or 8) + max(slot_index - 1, 0)
    prediction = predictor.predict_efficiency(
        machine_id=str(machine_row["machine_id"]),
        team_leader=_clean_text(job_row.get("team_leader")) or "unknown",
        material_code=_clean_text(job_row.get("material_code")) or "unknown",
        hours_since_maintenance=hours_since_last_maintenance,
        task_difficulty=task_difficulty,
        production_qty=quantity,
        team_size=_float_or_none(job_row.get("team_size")) or _float_or_none(machine_row.get("recent_team_size")) or 2.0,
        hour_of_day=min(max(hour_of_day, 0), 23),
        is_weekend=False,
        month=int(month_context["month_dt"].month),
        last_maintenance_type=_clean_text(machine_row.get("last_maintenance_type")) or _clean_text(job_row.get("last_maintenance_type")) or "unknown",
        maintenance_intensity_30d=_float_or_none(machine_row.get("maintenance_intensity_30d")) or 0.0,
        cumulative_maintenance_count=_float_or_none(machine_row.get("cumulative_maintenance_count")) or 0.0,
    )
    if prediction.get("source") != "model":
        return {
            "model_supported": False,
            "predicted_kwh_per_unit": None,
            "estimated_energy_cost": None,
        }

    predicted_kwh_per_unit = float(prediction["efficiency"])
    estimated_energy_cost = predicted_kwh_per_unit * quantity * float(month_context["cost_per_kwh"])
    return {
        "model_supported": True,
        "predicted_kwh_per_unit": round(predicted_kwh_per_unit, 6),
        "estimated_energy_cost": round(float(estimated_energy_cost), 4),
    }


def _build_month_context(month_df: pd.DataFrame, month_year: str) -> dict[str, object]:
    month_dt = pd.to_datetime(month_year, format="%B %Y", errors="coerce")
    positive_cost_df = month_df[
        month_df["energy_total_kwh"].fillna(0.0) > 0
    ].copy()
    total_cost = positive_cost_df["energy_total_cost"].fillna(0.0).sum()
    total_kwh = positive_cost_df["energy_total_kwh"].fillna(0.0).sum()
    cost_per_kwh = float(total_cost / total_kwh) if total_kwh > 0 and total_cost > 0 else 1.0

    setup_df = month_df[
        (month_df["energy_total_kwh"].fillna(0.0) > 0)
        & (
            (month_df["setup_minutes"].fillna(0.0) > 0)
            | (month_df["machine_state"].fillna("").astype(str) == "setup_changeover")
        )
    ].copy()
    if not setup_df.empty:
        transition_penalty_cost = float(setup_df["energy_total_kwh"].median()) * cost_per_kwh
    else:
        transition_penalty_cost = float(positive_cost_df["energy_total_kwh"].median()) * cost_per_kwh if not positive_cost_df.empty else 25.0

    return {
        "month_year": month_year,
        "month_dt": month_dt,
        "month_end": (month_dt + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%dT23:59:59"),
        "cost_per_kwh": max(cost_per_kwh, 1.0),
        "transition_penalty_cost": max(round(transition_penalty_cost, 4), 5.0),
    }


def _build_machine_profiles(
    month_df: pd.DataFrame,
    month_year: str,
    *,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    optimization_reader = CanonicalOptimizationReader(db_path=db_path)
    summary_df = optimization_reader.build_machine_summary(month_year)
    if summary_df.empty:
        return summary_df

    latest_rows_df = (
        month_df.sort_values(["hour_ts", "canonical_machine_id"])
        .groupby("canonical_machine_id", as_index=False)
        .tail(1)
        .loc[
            :,
            [
                "canonical_machine_id",
                "hours_since_last_maintenance",
                "team_size",
                "last_maintenance_work_order_type",
                "maintenance_distinct_work_order_count_30d",
                "cumulative_maintenance_count",
            ],
        ]
        .rename(
            columns={
                "canonical_machine_id": "machine_id",
                "hours_since_last_maintenance": "latest_hours_since_last_maintenance",
                "team_size": "recent_team_size",
                "last_maintenance_work_order_type": "last_maintenance_type",
                "maintenance_distinct_work_order_count_30d": "maintenance_intensity_30d",
            }
        )
    )

    as_of = pd.Timestamp(_build_month_context(month_df, month_year)["month_end"])
    evidence_reader = MaintenanceEvidenceReader(db_path=db_path)
    evidence_rows = []
    for machine_id in summary_df["machine_id"].tolist():
        payload = evidence_reader.build_machine_context_payload(machine_id, as_of=as_of)
        evidence_rows.append(
            {
                "machine_id": machine_id,
                "maintenance_available": bool(payload.get("available")),
                "days_since_last_maintenance": payload.get("days_since_last_maintenance"),
                "pm_ratio_all_time": payload.get("pm_ratio_all_time"),
                "total_events": payload.get("total_events"),
            }
        )

    machine_profiles_df = summary_df.merge(latest_rows_df, on="machine_id", how="left").merge(
        pd.DataFrame(evidence_rows),
        on="machine_id",
        how="left",
    )
    return machine_profiles_df


def _build_support_maps(history_df: pd.DataFrame) -> dict[str, dict[tuple[str, str], int] | dict[tuple[str, str, str], int]]:
    support_df = history_df.copy()
    support_df["machine_id"] = support_df["canonical_machine_id"].fillna("").astype(str)
    support_df["material_code"] = support_df["material_code"].fillna("").astype(str)
    support_df["task_name"] = support_df["task_name"].fillna("").astype(str)
    support_df["task_difficulty"] = support_df["task_name"].apply(CanonicalMLReader._derive_task_difficulty).fillna("")

    support_df = support_df[
        (support_df["machine_id"] != "")
        & ((support_df["material_code"] != "") | (support_df["task_difficulty"] != ""))
    ].copy()

    joint = (
        support_df[
            (support_df["material_code"] != "")
            & (support_df["task_name"] != "")
        ]
        .groupby(["machine_id", "material_code", "task_name"])
        .size()
        .to_dict()
    )
    material = (
        support_df[support_df["material_code"] != ""]
        .groupby(["machine_id", "material_code"])
        .size()
        .to_dict()
    )
    difficulty = (
        support_df[support_df["task_difficulty"] != ""]
        .groupby(["machine_id", "task_difficulty"])
        .size()
        .to_dict()
    )
    return {
        "joint": joint,
        "material": material,
        "difficulty": difficulty,
    }


def _build_queue_seed_frame(month_df: pd.DataFrame) -> pd.DataFrame:
    seed_df = month_df.copy()
    seed_df["task_difficulty"] = seed_df["task_name"].apply(CanonicalMLReader._derive_task_difficulty)
    seed_df["preferred_machine_family"] = seed_df["canonical_machine_id"].fillna("").astype(str).str.split("-").str[0]
    seed_df["team_leader"] = seed_df["team_leader"].fillna("unknown").astype(str)
    seed_df = seed_df[
        (seed_df["good_qty"].fillna(0.0) > 0)
        & (seed_df["energy_total_kwh"].fillna(0.0) > 0)
        & seed_df["material_code"].notna()
        & seed_df["task_name"].notna()
        & seed_df["task_difficulty"].notna()
        & seed_df["preferred_machine_family"].ne("")
    ].copy()
    if seed_df.empty:
        return pd.DataFrame()

    grouped = (
        seed_df.groupby(
            [
                "preferred_machine_family",
                "material_code",
                "task_name",
                "task_difficulty",
            ],
            dropna=False,
        )
        .agg(
            source_machine_id=("canonical_machine_id", "first"),
            source_hour_ts=("hour_ts", "first"),
            team_leader=("team_leader", "first"),
            team_size=("team_size", "median"),
            hour_of_day=("hour_ts", lambda values: pd.to_datetime(values, errors="coerce").dt.hour.mode().iloc[0]),
            last_maintenance_type=("last_maintenance_work_order_type", "first"),
            median_good_qty=("good_qty", "median"),
            seed_weight=("canonical_machine_id", "size"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["median_good_qty"].fillna(0.0) > 0].copy()
    return grouped


def _build_baseline_comparison(
    optimized_schedule_df: pd.DataFrame,
    naive_schedule_df: pd.DataFrame,
) -> pd.DataFrame:
    metrics = [
        ("Assigned jobs", float(len(optimized_schedule_df)), float(len(naive_schedule_df))),
        (
            "Composite score",
            float(optimized_schedule_df["total_score"].fillna(0.0).sum()) if not optimized_schedule_df.empty else 0.0,
            float(naive_schedule_df["total_score"].fillna(0.0).sum()) if not naive_schedule_df.empty else 0.0,
        ),
        (
            "Predicted energy cost",
            float(optimized_schedule_df["estimated_energy_cost"].fillna(0.0).sum()) if not optimized_schedule_df.empty else 0.0,
            float(naive_schedule_df["estimated_energy_cost"].fillna(0.0).sum()) if not naive_schedule_df.empty else 0.0,
        ),
        (
            "Material transition penalty",
            float(optimized_schedule_df["transition_penalty"].fillna(0.0).sum()) if not optimized_schedule_df.empty else 0.0,
            float(naive_schedule_df["transition_penalty"].fillna(0.0).sum()) if not naive_schedule_df.empty else 0.0,
        ),
    ]
    rows = []
    for metric_name, optimized_value, naive_value in metrics:
        rows.append(
            {
                "Metric": metric_name,
                "Optimized": round(optimized_value, 4),
                "Naive": round(naive_value, 4),
                "Delta (Optimized - Naive)": round(optimized_value - naive_value, 4),
            }
        )
    return pd.DataFrame(rows)


def _build_score_breakdown(
    optimized_schedule_df: pd.DataFrame,
    naive_schedule_df: pd.DataFrame,
) -> pd.DataFrame:
    component_map = {
        "Predicted energy cost": "estimated_energy_cost",
        "Transition penalty": "transition_penalty",
        "Maintenance penalty": "maintenance_penalty",
        "Support penalty": "support_penalty",
        "Urgency penalty": "urgency_penalty",
        "Model unavailable penalty": "model_unavailable_penalty",
        "Composite total": "total_score",
    }
    rows = []
    for label, column_name in component_map.items():
        optimized_value = float(optimized_schedule_df[column_name].fillna(0.0).sum()) if not optimized_schedule_df.empty else 0.0
        naive_value = float(naive_schedule_df[column_name].fillna(0.0).sum()) if not naive_schedule_df.empty else 0.0
        rows.append(
            {
                "Score Component": label,
                "Optimized": round(optimized_value, 4),
                "Naive": round(naive_value, 4),
                "Delta (Naive - Optimized)": round(naive_value - optimized_value, 4),
            }
        )
    return pd.DataFrame(rows)


def _build_feasible_assignment_table(candidate_df: pd.DataFrame) -> pd.DataFrame:
    if candidate_df.empty:
        return pd.DataFrame()
    feasible_df = candidate_df[candidate_df["exclude_reason"].isna()].copy()
    if feasible_df.empty:
        return pd.DataFrame()
    feasible_df = feasible_df.sort_values(
        ["job_id", "total_score", "support_rank", "machine_id"]
    ).groupby("job_id", as_index=False).head(5)
    return feasible_df.loc[:, CANDIDATE_COLUMNS].reset_index(drop=True)


def _build_blocked_reason_summary(
    candidate_df: pd.DataFrame,
    unscheduled_df: pd.DataFrame,
) -> pd.DataFrame:
    candidate_blocked_df = candidate_df[candidate_df["exclude_reason"].notna()].copy() if not candidate_df.empty else pd.DataFrame()
    rows = []
    if not candidate_blocked_df.empty:
        counts = candidate_blocked_df["exclude_reason"].value_counts().sort_index()
        for reason, count in counts.items():
            rows.append({"Blocked / Excluded Reason": reason, "Count": int(count), "Scope": "candidate"})
    if unscheduled_df is not None and not unscheduled_df.empty:
        counts = unscheduled_df["reason"].value_counts().sort_index()
        for reason, count in counts.items():
            rows.append({"Blocked / Excluded Reason": reason, "Count": int(count), "Scope": "job"})
    return pd.DataFrame(rows)


def _build_constraint_summary(
    month_context: dict[str, object],
    max_jobs_per_machine: int,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Constraint": "One job -> one machine slot",
                "Rule": "Each demo job can occupy only one machine and one slot inside the prototype horizon.",
            },
            {
                "Constraint": "Machine compatibility",
                "Rule": "Machines must match the preferred family, then use historical material/task support tiers; family-only fallback is allowed when exact support is sparse.",
            },
            {
                "Constraint": "Maintenance blackout heuristic",
                "Rule": "Black out machines when maintenance evidence is stale and weak (`>=180` days with PM ratio `<=0.05`) or when no evidence exists and latest canonical maintenance age is extremely high (`>=3000h`).",
            },
            {
                "Constraint": "Material transition penalty",
                "Rule": f"Changing material on the same machine adds the selected-month median setup-energy cost proxy ({month_context['transition_penalty_cost']:.2f} prototype cost points).",
            },
            {
                "Constraint": "Urgency proxy",
                "Rule": "No live due-date feed exists, so urgency is proxied from seeded quantity percentile and later machine slots receive a larger penalty.",
            },
            {
                "Constraint": "Max jobs per machine",
                "Rule": f"At most {int(max_jobs_per_machine)} demo jobs per machine inside this prototype horizon.",
            },
        ]
    )


def _read_fact_rows(
    *,
    month_year: str | None = None,
    month_end: str | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    db_path = str(db_path or get_database_path())
    conn = sqlite3.connect(db_path)
    try:
        if month_year is not None:
            start_ts, end_ts = _month_label_to_bounds(month_year)
            query = """
                SELECT
                    canonical_machine_id,
                    hour_ts,
                    machine_state,
                    material_code,
                    task_name,
                    good_qty,
                    energy_total_kwh,
                    energy_total_cost,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    unplanned_stop_minutes,
                    idle_minutes,
                    team_leader,
                    team_size,
                    hours_since_last_maintenance,
                    last_maintenance_work_order_type,
                    maintenance_distinct_work_order_count_30d,
                    cumulative_maintenance_count
                FROM fact_machine_hour
                WHERE hour_ts >= ?
                  AND hour_ts < ?
                ORDER BY hour_ts, canonical_machine_id
            """
            fact_df = pd.read_sql_query(query, conn, params=(start_ts, end_ts))
        elif month_end is not None:
            query = """
                SELECT
                    canonical_machine_id,
                    hour_ts,
                    machine_state,
                    material_code,
                    task_name,
                    good_qty,
                    energy_total_kwh,
                    energy_total_cost,
                    setup_minutes,
                    production_minutes,
                    planned_stop_minutes,
                    unplanned_stop_minutes,
                    idle_minutes,
                    team_leader,
                    team_size,
                    hours_since_last_maintenance,
                    last_maintenance_work_order_type,
                    maintenance_distinct_work_order_count_30d,
                    cumulative_maintenance_count
                FROM fact_machine_hour
                WHERE hour_ts <= ?
                ORDER BY hour_ts, canonical_machine_id
            """
            fact_df = pd.read_sql_query(query, conn, params=(month_end,))
        else:
            fact_df = pd.read_sql_query("SELECT * FROM fact_machine_hour ORDER BY hour_ts, canonical_machine_id", conn)
    finally:
        conn.close()

    if fact_df.empty:
        return fact_df

    numeric_columns = [
        "good_qty",
        "energy_total_kwh",
        "energy_total_cost",
        "setup_minutes",
        "production_minutes",
        "planned_stop_minutes",
        "unplanned_stop_minutes",
        "idle_minutes",
        "team_size",
        "hours_since_last_maintenance",
        "maintenance_distinct_work_order_count_30d",
        "cumulative_maintenance_count",
    ]
    for column_name in numeric_columns:
        if column_name in fact_df.columns:
            fact_df[column_name] = pd.to_numeric(fact_df[column_name], errors="coerce")
    return fact_df


def _month_label_to_bounds(month_year: str) -> tuple[str, str]:
    month_dt = pd.to_datetime(month_year, format="%B %Y", errors="raise")
    next_month_dt = month_dt + pd.offsets.MonthBegin(1)
    return (
        month_dt.strftime("%Y-%m-%dT00:00:00"),
        next_month_dt.strftime("%Y-%m-%dT00:00:00"),
    )


def _volume_proxy_to_urgency(quantity: float, quantity_reference: pd.Series) -> tuple[str, int]:
    if quantity_reference.empty:
        return "Medium", 2
    p75 = float(quantity_reference.quantile(0.75))
    p35 = float(quantity_reference.quantile(0.35))
    if quantity >= p75:
        return "High", 3
    if quantity >= p35:
        return "Medium", 2
    return "Low", 1


def _normalize_urgency_label(value: object) -> str:
    cleaned = _clean_text(value)
    if cleaned is None:
        return "Medium"
    lowered = cleaned.lower()
    if lowered.startswith("h"):
        return "High"
    if lowered.startswith("l"):
        return "Low"
    return "Medium"


def _urgency_rank(label: str) -> int:
    return {"High": 3, "Medium": 2, "Low": 1}.get(str(label), 2)


def _stable_seed(value: str) -> int:
    return int(hashlib.sha1(value.encode("utf-8")).hexdigest()[:8], 16)


def _read_manifest_summary(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _round_to_step(value: float, step: float) -> float:
    return round(float(value) / step) * step


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _normalize_real_input_columns(input_df: pd.DataFrame) -> pd.DataFrame:
    renamed_columns = {}
    for column_name in input_df.columns:
        original_name = str(column_name).strip()
        compact_name = "".join(character for character in original_name.lower() if character.isalnum())
        fallback_name = (
            original_name.strip()
            .lower()
            .replace("/", "_")
            .replace("-", "_")
            .replace(" ", "_")
        )
        renamed_columns[column_name] = REAL_INPUT_COLUMN_ALIASES.get(compact_name, fallback_name)
    return input_df.rename(columns=renamed_columns)


def _export_frame(frame: object) -> pd.DataFrame:
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    return pd.DataFrame()
