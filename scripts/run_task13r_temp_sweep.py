#!/usr/bin/env python3
"""Run the Task13R Jul 2025 -> Feb 2026 temp-DB sweep with checkpoints."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_gold_reader import CanonicalGoldReader
from core.canonical_materializer import CanonicalMaterializer
from core.runtime_paths import get_database_path


DEFAULT_MONTHS = [
    "July 2025",
    "August 2025",
    "September 2025",
    "October 2025",
    "November 2025",
    "December 2025",
    "January 2026",
    "February 2026",
]

BRONZE_MONTH_SQL = {
    "raw_energy_hourly": "substr(raw_timestamp, 1, 7)",
    "raw_csi_event": (
        "COALESCE("
        "substr(raw_start_time, 1, 7), "
        "substr(raw_end_time, 1, 7), "
        "substr(raw_prep_end_time, 1, 7), "
        "substr(json_extract(raw_payload_json, '$.班次內日期'), 1, 7)"
        ")"
    ),
    "raw_mes_report": "substr(json_extract(raw_payload_json, '$.報工時間'), 1, 7)",
    "raw_maintenance_txn": "substr(raw_transaction_date, 1, 7)",
}

SILVER_MONTH_SQL = {
    "energy_meter_hour": "substr(hour_ts, 1, 7)",
    "csi_job_event": (
        "COALESCE("
        "substr(prod_start_ts, 1, 7), "
        "substr(prod_end_ts, 1, 7), "
        "substr(prep_end_ts, 1, 7), "
        "substr(shift_date, 1, 7)"
        ")"
    ),
    "mes_report_event": "substr(report_ts, 1, 7)",
    "maintenance_txn_event": "substr(txn_ts, 1, 7)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "months",
        nargs="*",
        default=DEFAULT_MONTHS,
        help='Month labels to sweep. Defaults to "July 2025" -> "February 2026".',
    )
    parser.add_argument(
        "--shared-db",
        default=str(get_database_path()),
        help="Authoritative shared DB path to copy from. Never written by this script.",
    )
    parser.add_argument(
        "--temp-db",
        required=True,
        help="Writable temp DB path for the sweep.",
    )
    parser.add_argument(
        "--checkpoint-log",
        required=True,
        help="JSONL checkpoint log written after each month attempt.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip months already recorded with status=success in the checkpoint log.",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Optional source-root override. Defaults to repo Jan-Jun roots plus Task13 extension package mapping.",
    )
    parser.add_argument(
        "--gold-only",
        action="store_true",
        help="Skip extraction/Bronze/Silver and rerun Gold only against an existing temp DB month partition.",
    )
    parser.add_argument(
        "--debug-gold-stages",
        action="store_true",
        help="Run the Gold debug ladder and include per-stage timing/count output.",
    )
    parser.add_argument(
        "--gold-stage-warning-seconds",
        type=float,
        default=None,
        help="Optional warning threshold applied to each debug Gold stage.",
    )
    parser.add_argument(
        "--gold-stage-timeout-seconds",
        type=float,
        default=None,
        help="Optional hard timeout applied to each debug Gold stage.",
    )
    parser.add_argument(
        "--gold-debug-log",
        default=None,
        help="Optional JSONL log path for per-stage Gold debug start/result events.",
    )
    return parser.parse_args()


def ensure_temp_db(shared_db: Path, temp_db: Path) -> None:
    if temp_db.exists():
        return
    temp_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(shared_db, temp_db)


def load_completed_months(checkpoint_log: Path) -> set[str]:
    if not checkpoint_log.exists():
        return set()

    completed = set()
    for line in checkpoint_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("status") == "success" and payload.get("month"):
            completed.add(str(payload["month"]))
    return completed


def append_checkpoint(checkpoint_log: Path, payload: dict[str, object]) -> None:
    checkpoint_log.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def build_jsonl_logger(log_path: Path | None):
    if log_path is None:
        return None

    def _logger(payload: dict[str, object]) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    return _logger


def timed(label: str, fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, {label: round(time.perf_counter() - start, 3)}


def month_label_to_key(month: str) -> str:
    return CanonicalMaterializer._parse_month_bounds(month).month_key


def query_count(conn: sqlite3.Connection, table: str, month_sql: str, month_key: str) -> int:
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {month_sql} = ?",
        (month_key,),
    ).fetchone()
    return int(row[0] if row else 0)


def collect_month_counts(db_path: Path, month: str) -> dict[str, dict[str, int]]:
    month_key = month_label_to_key(month)
    conn = sqlite3.connect(db_path)
    try:
        bronze = {
            table: query_count(conn, table, expr, month_key)
            for table, expr in BRONZE_MONTH_SQL.items()
        }
        silver = {
            table: query_count(conn, table, expr, month_key)
            for table, expr in SILVER_MONTH_SQL.items()
        }
        gold_row = conn.execute(
            "SELECT COUNT(*) FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ?",
            (month_key,),
        ).fetchone()
        gold = {"fact_machine_hour": int(gold_row[0] if gold_row else 0)}
        return {"bronze": bronze, "silver": silver, "gold": gold}
    finally:
        conn.close()


def collect_quarantines(db_path: Path, month: str) -> dict[str, list[dict[str, object]]]:
    month_key = month_label_to_key(month)
    conn = sqlite3.connect(db_path)
    try:
        csi_rows = conn.execute(
            f"""
            SELECT raw_machine_id_or_label, COUNT(*) AS row_count
            FROM raw_csi_event
            WHERE {BRONZE_MONTH_SQL['raw_csi_event']} = ?
              AND canonical_machine_id IS NULL
            GROUP BY raw_machine_id_or_label
            ORDER BY row_count DESC, raw_machine_id_or_label
            """,
            (month_key,),
        ).fetchall()
        mes_rows = conn.execute(
            f"""
            SELECT json_extract(raw_payload_json, '$.資源') AS raw_resource, COUNT(*) AS row_count
            FROM raw_mes_report
            WHERE {BRONZE_MONTH_SQL['raw_mes_report']} = ?
              AND canonical_machine_id IS NULL
            GROUP BY raw_resource
            ORDER BY row_count DESC, raw_resource
            """,
            (month_key,),
        ).fetchall()
        return {
            "csi": [
                {"identifier": identifier, "row_count": int(row_count)}
                for identifier, row_count in csi_rows
            ],
            "mes": [
                {"identifier": identifier, "row_count": int(row_count)}
                for identifier, row_count in mes_rows
            ],
        }
    finally:
        conn.close()


def collect_quality_flags(db_path: Path, month: str) -> list[dict[str, object]]:
    month_key = month_label_to_key(month)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT quality_status, quality_flags_json, COUNT(*) AS row_count
            FROM energy_meter_hour
            WHERE substr(hour_ts, 1, 7) = ?
              AND quality_status IS NOT NULL
              AND quality_status <> 'ok'
            GROUP BY quality_status, quality_flags_json
            ORDER BY row_count DESC, quality_status
            """,
            (month_key,),
        ).fetchall()
        return [
            {
                "quality_status": quality_status,
                "quality_flags_json": quality_flags_json,
                "row_count": int(row_count),
            }
            for quality_status, quality_flags_json, row_count in rows
        ]
    finally:
        conn.close()


def run_month(
    pipeline,
    month: str,
    *,
    data_root: str | None,
    gold_only: bool,
    debug_gold_stages: bool,
    gold_stage_warning_seconds: float | None,
    gold_stage_timeout_seconds: float | None,
    gold_debug_log: Path | None,
) -> dict[str, object]:
    timings: dict[str, float] = {}
    materializer = CanonicalMaterializer(pipeline.db_path)

    source_files = None
    mapping_results: dict[str, object] = {}
    bronze_counts: dict[str, int] = {}
    silver_rows_by_table: dict[str, list[dict[str, object]]] = {}
    gold_debug: dict[str, object] | None = None
    bounds = materializer._parse_month_bounds(month)

    if not gold_only:
        from core.enhanced_etl_solution_CURRENT import EnhancedSmartManufacturingETL
        from modules.etl_module import _scope_etl_state_to_month

        source_files = pipeline.resolve_historical_month_sources(month, data_root=data_root)
        etl = EnhancedSmartManufacturingETL()

        _, timing = timed(
            "extract_seconds",
            etl.extract_all_sources,
            source_files["energy_files"],
            source_files["csi_file"],
            source_files["mes_file"],
        )
        timings.update(timing)

        _, timing = timed("scope_seconds", _scope_etl_state_to_month, etl, month)
        timings.update(timing)

        mapping_results, timing = timed("mapping_seconds", etl.create_comprehensive_mapping)
        timings.update(timing)

        _, timing = timed("bronze_save_seconds", pipeline.save_etl_results, mapping_results, month, etl)
        timings.update(timing)

        silver_start = time.perf_counter()
        bronze_counts, silver_rows_by_table = materializer._materialize_month_silver(
            bounds,
            month,
        )
        timings["silver_materialization_seconds"] = round(time.perf_counter() - silver_start, 3)

    gold_start = time.perf_counter()
    if debug_gold_stages:
        gold_debug = materializer.materialize_gold_month_debug(
            bounds,
            stage_duration_warning_seconds=gold_stage_warning_seconds,
            stage_timeout_seconds=gold_stage_timeout_seconds,
            stage_callback=build_jsonl_logger(gold_debug_log),
        )
        gold_df = pd.DataFrame()
    else:
        gold_df = materializer._materialize_gold_month(bounds)
    timings["gold_materialization_seconds"] = round(time.perf_counter() - gold_start, 3)

    counts = collect_month_counts(Path(pipeline.db_path), month)
    reader = CanonicalGoldReader(pipeline.db_path)
    payload_status = gold_debug["status"] if gold_debug is not None else "success"
    gold_row_count = (
        counts["gold"]["fact_machine_hour"]
        if gold_debug is not None
        else int(len(gold_df))
    )
    return {
        "status": payload_status,
        "month": month,
        "timings": timings,
        "source_files": source_files,
        "mapping_stats": mapping_results.get("mapping_stats", {}),
        "bronze_rows_used_by_table": bronze_counts,
        "silver_rows_materialized_by_table": {
            table_name: len(rows) for table_name, rows in silver_rows_by_table.items()
        },
        "month_counts_after_run": counts,
        "fact_machine_hour_rows_created": gold_row_count,
        "quarantines": collect_quarantines(Path(pipeline.db_path), month),
        "quality_flags": collect_quality_flags(Path(pipeline.db_path), month),
        "available_months_after_run": reader.get_available_months(),
        "gold_debug": gold_debug,
    }


def main() -> int:
    args = parse_args()
    shared_db = Path(args.shared_db).resolve()
    temp_db = Path(args.temp_db).resolve()
    checkpoint_log = Path(args.checkpoint_log).resolve()

    ensure_temp_db(shared_db, temp_db)
    completed_months = load_completed_months(checkpoint_log) if args.resume else set()
    if args.gold_only:
        pipeline = SimpleNamespace(db_path=str(temp_db))
    else:
        from modules.etl_module import ETLPipelineModule

        pipeline = ETLPipelineModule(db_path=str(temp_db))

    overall_status = "success"
    for month in args.months:
        if month in completed_months:
            append_checkpoint(
                checkpoint_log,
                {
                    "status": "skipped_existing_success",
                    "month": month,
                    "temp_db": str(temp_db),
                },
            )
            continue

        try:
            payload = run_month(
                pipeline,
                month,
                data_root=args.data_root,
                gold_only=args.gold_only,
                debug_gold_stages=args.debug_gold_stages,
                gold_stage_warning_seconds=args.gold_stage_warning_seconds,
                gold_stage_timeout_seconds=args.gold_stage_timeout_seconds,
                gold_debug_log=(
                    Path(args.gold_debug_log).resolve()
                    if args.gold_debug_log is not None
                    else None
                ),
            )
        except Exception as exc:
            payload = {
                "status": "error",
                "month": month,
                "temp_db": str(temp_db),
                "error": str(exc),
                "month_counts_after_run": collect_month_counts(temp_db, month),
                "quarantines": collect_quarantines(temp_db, month),
                "quality_flags": collect_quality_flags(temp_db, month),
            }
            overall_status = "error"
            append_checkpoint(checkpoint_log, payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            break

        if payload.get("status") == "error":
            overall_status = "error"

        payload["temp_db"] = str(temp_db)
        append_checkpoint(checkpoint_log, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0 if overall_status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
