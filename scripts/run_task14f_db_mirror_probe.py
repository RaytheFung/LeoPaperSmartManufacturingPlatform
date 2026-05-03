#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_ml_reader import CanonicalMLReader
from core.canonical_optimization_reader import CanonicalOptimizationReader
from core.experimental_scheduling import run_constraint_aware_scheduling
from core.ml_predictor import MLPredictor
from modules.optimization_module import (
    _build_model_preview_payload,
    build_schedule_tab_payload,
    build_team_insights_tab_payload,
)


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a Task14F working DB mirror and run read-only route-adjacent smokes."
    )
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--month", default="February 2026")
    parser.add_argument("--queue-size", type=int, default=3)
    return parser


def _read_sqlite_snapshot(db_path: Path) -> dict[str, object]:
    with sqlite3.connect(db_path) as conn:
        fact_rows = int(conn.execute("select count(*) from fact_machine_hour").fetchone()[0])
        min_month, max_month = conn.execute(
            "select min(substr(hour_ts, 1, 7)), max(substr(hour_ts, 1, 7)) from fact_machine_hour"
        ).fetchone()
    return {
        "db_path": str(db_path),
        "db_size_bytes": db_path.stat().st_size,
        "db_sha1": _sha1(db_path),
        "fact_machine_hour_rows": fact_rows,
        "month_key_min": min_month,
        "month_key_max": max_month,
    }


def _run_direct_predictor_smoke(
    *,
    predictor: MLPredictor,
    input_df,
) -> dict[str, object]:
    if input_df.empty:
        return {"passed": False, "reason": "no_input_rows"}

    eligible_df = input_df[input_df["eligible_for_inference"] == 1].copy()
    if eligible_df.empty:
        return {"passed": False, "reason": "no_eligible_rows"}

    row = eligible_df.iloc[0]
    prediction = predictor.predict_efficiency(
        machine_id=row["machine_id"],
        team_leader=row["team_leader"],
        material_code=row["material_code"],
        hours_since_maintenance=row["hours_since_last_maintenance"],
        task_difficulty=row["task_difficulty"],
        production_qty=row["production_qty"],
        team_size=row["team_size"],
        hour_of_day=row["hour_of_day"],
        is_weekend=row["is_weekend"],
        month=row["month"],
        last_maintenance_type=row["last_maintenance_type"],
        maintenance_intensity_30d=row["maintenance_intensity_30d"],
        cumulative_maintenance_count=row["cumulative_maintenance_count"],
    )
    return {
        "passed": prediction.get("source") == "model",
        "prediction_source": prediction.get("source"),
        "predicted_efficiency": float(prediction.get("efficiency", 0.0)),
        "confidence": float(prediction.get("confidence", 0.0)),
        "sample_machine_id": str(row["machine_id"]),
        "sample_hour_ts": str(row["hour_ts"]),
        "sample_month": str(row["month_year"]),
        "support_path": str(row.get("support_path") or ""),
    }


def _run_ml_smoke(*, db_path: Path, month_year: str) -> dict[str, object]:
    reader = CanonicalMLReader(db_path=db_path)
    predictor = MLPredictor()
    input_df = reader.build_month_input_dataframe(month_year, predictor=predictor)
    candidate_df = reader.build_prediction_candidates(input_df)
    prediction_df, blocked_prediction_df = reader.build_prediction_dataframe(
        candidate_df,
        predictor=predictor,
    )
    metrics = reader.build_month_readiness_metrics(
        input_df,
        candidate_df,
        blocked_prediction_df=blocked_prediction_df,
    )
    direct_smoke = _run_direct_predictor_smoke(
        predictor=predictor,
        input_df=input_df,
    )
    top_prediction = prediction_df.iloc[0].to_dict() if not prediction_df.empty else None
    if top_prediction is not None:
        top_prediction = {
            "machine_id": str(top_prediction["machine_id"]),
            "datetime": str(top_prediction["datetime"]),
            "predicted_efficiency": float(top_prediction["predicted_efficiency"]),
            "confidence": float(top_prediction["confidence"]),
            "top_driver": str(top_prediction["top_driver"]),
        }
    return {
        "passed": not input_df.empty and not candidate_df.empty and not prediction_df.empty,
        "month": month_year,
        "metrics": metrics,
        "candidate_rows": int(len(candidate_df)),
        "prediction_rows": int(len(prediction_df)),
        "blocked_prediction_rows": int(len(blocked_prediction_df)),
        "direct_predictor_smoke": direct_smoke,
        "top_prediction": top_prediction,
    }


def _run_optimization_smoke(*, db_path: Path, month_year: str) -> dict[str, object]:
    reader = CanonicalOptimizationReader(db_path=db_path)
    summary_df = reader.build_machine_summary(month_year)
    metrics = reader.build_month_metrics(summary_df) if not summary_df.empty else {}
    preview_payload = _build_model_preview_payload(month_year, db_path=db_path)
    schedule_payload = build_schedule_tab_payload(reader, month_year)
    team_payload = build_team_insights_tab_payload(reader, month_year)
    top_machine = summary_df.iloc[0].to_dict() if not summary_df.empty else None
    if top_machine is not None:
        top_machine = {
            "machine_id": str(top_machine["machine_id"]),
            "machine_family": str(top_machine["machine_family"]),
            "opportunity_score": float(top_machine["opportunity_score"]),
            "top_driver": str(top_machine["top_driver"]),
        }
    return {
        "passed": not summary_df.empty and bool(preview_payload.get("available")),
        "month": month_year,
        "machine_summary_rows": int(len(summary_df)),
        "metrics": metrics,
        "preview_available": bool(preview_payload.get("available")),
        "preview_reason": preview_payload.get("reason"),
        "schedule_blocked": bool(schedule_payload["blocked"]),
        "schedule_rows": int(len(schedule_payload["schedule_df"])),
        "team_blocked": bool(team_payload["blocked"]),
        "team_rows": int(len(team_payload["team_df"])),
        "top_machine": top_machine,
    }


def _run_experimental_smoke(*, db_path: Path, month_year: str, queue_size: int) -> dict[str, object]:
    payload = run_constraint_aware_scheduling(
        month_year,
        queue_size=queue_size,
        db_path=db_path,
    )
    return {
        "passed": not bool(payload["blocked"]),
        "month": month_year,
        "message": payload.get("message"),
        "queue_rows": int(len(payload.get("queue_df"))),
        "optimized_schedule_rows": int(len(payload.get("optimized_schedule_df", []))),
        "naive_schedule_rows": int(len(payload.get("naive_schedule_df", []))),
        "blocked_reasons_rows": int(len(payload.get("blocked_reasons_df", []))),
        "queue_generation_rule": payload.get("queue_generation_rule"),
        "provenance_label": payload.get("provenance_label"),
    }


def main() -> None:
    args = _build_parser().parse_args()
    db_path = Path(args.db_path).resolve()
    payload = {
        "mirror_snapshot": _read_sqlite_snapshot(db_path),
        "ml_smoke": _run_ml_smoke(db_path=db_path, month_year=args.month),
        "optimization_smoke": _run_optimization_smoke(db_path=db_path, month_year=args.month),
        "experimental_scheduling_smoke": _run_experimental_smoke(
            db_path=db_path,
            month_year=args.month,
            queue_size=args.queue_size,
        ),
    }
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
