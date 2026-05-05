#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.backfill_rehearsal_preflight import build_historical_backfill_preflight_plan
from core.runtime_paths import get_extended_raw_dataset_root
from modules.etl_module import ETLPipelineModule
from scripts.compare_source_discovery_modes import build_source_discovery_compare_diagnostics


TARGET_MONTH = "July 2025"
DEFAULT_TEMP_DB_PATH = Path("/tmp/leopaper_stage_b6_3_july_rehearsal/july_rehearsal.db")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a July 2025 historical backfill rehearsal against a temp DB only.",
    )
    parser.add_argument("--temp-db-path", type=Path, default=DEFAULT_TEMP_DB_PATH)
    parser.add_argument("--data-root", type=Path, default=get_extended_raw_dataset_root())
    parser.add_argument("--month", default=TARGET_MONTH)
    args = parser.parse_args(argv)

    try:
        evidence = run_july_temp_backfill_rehearsal(
            temp_db_path=args.temp_db_path,
            data_root=args.data_root,
            month=args.month,
        )
    except Exception as exc:
        payload = {
            "status": "error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 1

    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence.get("rehearsal_result", {}).get("status") == "success" else 2


def run_july_temp_backfill_rehearsal(
    *,
    temp_db_path: str | Path,
    data_root: str | Path,
    month: str = TARGET_MONTH,
) -> dict[str, Any]:
    temp_db = Path(temp_db_path).expanduser().resolve(strict=False)
    source_root = Path(data_root).expanduser().resolve(strict=False)
    _validate_target_month(month)
    _validate_temp_db_path(temp_db)
    if not temp_db.exists():
        raise FileNotFoundError(f"Temp DB does not exist: {temp_db}")

    started_at = _utc_now()
    started_perf = time.perf_counter()
    pre_stat = _file_stat(temp_db)
    pre_sha256 = _sha256_file(temp_db)

    pipeline = ETLPipelineModule(db_path=temp_db)
    extraction_capture: dict[str, Any] = {}
    original_save = pipeline.save_etl_results

    def capture_and_save(mapping_results, month_name, etl_instance=None):
        extraction_capture.update(_summarize_etl_state(etl_instance, mapping_results))
        return original_save(mapping_results, month_name, etl_instance)

    pipeline.save_etl_results = capture_and_save

    source_default = pipeline.resolve_historical_month_sources(month, data_root=source_root)
    source_legacy = pipeline.resolve_historical_month_sources(
        month,
        data_root=source_root,
        discovery_mode="legacy",
    )
    compare_diagnostic = build_source_discovery_compare_diagnostics(
        month_labels=[month],
        data_root=source_root,
        pipeline=ETLPipelineModule(db_path=temp_db, initialize_schema=False),
    )
    preflight_plan = build_historical_backfill_preflight_plan(
        month,
        data_root=source_root,
        db_path=temp_db,
    )

    exception_payload = None
    try:
        rehearsal_result = pipeline.run_historical_canonical_backfill([month], data_root=source_root)
    except Exception as exc:
        rehearsal_result = {"status": "exception", "message": str(exc)}
        exception_payload = {
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    ended_at = _utc_now()
    duration_seconds = round(time.perf_counter() - started_perf, 3)
    post_stat = _file_stat(temp_db)
    post_sha256 = _sha256_file(temp_db)

    return {
        "status": "success",
        "target_month": month,
        "temp_db_path": str(temp_db),
        "data_root": str(source_root),
        "source_discovery_evidence": {
            "default_source_discovery_mode": source_default.get("source_discovery_mode", "legacy"),
            "default_backfill_readiness": source_default.get("backfill_readiness"),
            "explicit_legacy_backfill_readiness": source_legacy.get("backfill_readiness"),
            "compare_diagnostic": compare_diagnostic,
            "expected_source_files": preflight_plan["expected_source_files"],
            "missing_source_files": _missing_source_files(source_default),
        },
        "etl_extraction_evidence": extraction_capture.get("extraction", {}),
        "mapping_evidence": extraction_capture.get("mapping", {}),
        "temp_db_evidence": {
            "before": {**pre_stat, "sha256": pre_sha256},
            "after": {**post_stat, "sha256": post_sha256},
            "table_counts": summarize_temp_db(temp_db),
        },
        "runtime_evidence": {
            "started_at_utc": started_at,
            "ended_at_utc": ended_at,
            "duration_seconds": duration_seconds,
            "exception": exception_payload,
        },
        "rehearsal_result": rehearsal_result,
        "safety_evidence": {
            "temp_db_inside_repo": _path_is_relative_to(temp_db, REPO_ROOT),
            "repo_root": str(REPO_ROOT),
            "live_db_write_allowed": False,
            "repo_db_write_allowed": False,
        },
    }


def summarize_temp_db(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path).expanduser().resolve(strict=False)
    if _path_is_relative_to(db, REPO_ROOT):
        raise ValueError(f"Refusing to inspect DB path inside repo: {db}")
    if not db.exists():
        raise FileNotFoundError(f"DB path does not exist: {db}")

    tables = {
        "etl_runs": {
            "count_sql": "SELECT COUNT(*) FROM etl_runs WHERE month_processed = ?",
            "params": (TARGET_MONTH,),
        },
        "etl_energy_data": {
            "count_sql": "SELECT COUNT(*) FROM etl_energy_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(datetime), MAX(datetime), SUM(electricity_kwh) FROM etl_energy_data WHERE month_year = ?",
        },
        "etl_csi_data": {
            "count_sql": "SELECT COUNT(*) FROM etl_csi_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(start_time), MAX(end_time), SUM(good_qty) FROM etl_csi_data WHERE month_year = ?",
        },
        "etl_mes_data": {
            "count_sql": "SELECT COUNT(*) FROM etl_mes_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(planned_start), MAX(planned_end), SUM(planned_qty) FROM etl_mes_data WHERE month_year = ?",
        },
        "raw_energy_hourly": {
            "count_sql": "SELECT COUNT(*) FROM raw_energy_hourly WHERE substr(raw_timestamp, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(raw_timestamp), MAX(raw_timestamp), SUM(raw_kwh) FROM raw_energy_hourly WHERE substr(raw_timestamp, 1, 7) = '2025-07'",
        },
        "raw_csi_event": {
            "count_sql": "SELECT COUNT(*) FROM raw_csi_event WHERE substr(raw_start_time, 1, 7) = '2025-07' OR substr(raw_end_time, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(raw_start_time), MAX(raw_end_time), SUM(raw_good_qty) FROM raw_csi_event WHERE substr(raw_start_time, 1, 7) = '2025-07' OR substr(raw_end_time, 1, 7) = '2025-07'",
        },
        "raw_mes_report": {
            "count_sql": "SELECT COUNT(*) FROM raw_mes_report WHERE substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(json_extract(raw_payload_json, '$.\"報工時間\"')), MAX(json_extract(raw_payload_json, '$.\"報工時間\"')), SUM(raw_planned_qty) FROM raw_mes_report WHERE substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = '2025-07'",
        },
        "raw_maintenance_txn": {
            "count_sql": "SELECT COUNT(*) FROM raw_maintenance_txn WHERE substr(raw_transaction_date, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(raw_transaction_date), MAX(raw_transaction_date), SUM(raw_quantity) FROM raw_maintenance_txn WHERE substr(raw_transaction_date, 1, 7) = '2025-07'",
        },
        "energy_meter_hour": {
            "count_sql": "SELECT COUNT(*) FROM energy_meter_hour WHERE substr(hour_ts, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(hour_ts), MAX(hour_ts), SUM(kwh) FROM energy_meter_hour WHERE substr(hour_ts, 1, 7) = '2025-07'",
            "flags_sql": "SELECT COUNT(*) FROM energy_meter_hour WHERE substr(hour_ts, 1, 7) = '2025-07' AND quality_flags_json IS NOT NULL AND TRIM(quality_flags_json) NOT IN ('', '{}')",
        },
        "csi_job_event": {
            "count_sql": "SELECT COUNT(*) FROM csi_job_event WHERE substr(prod_start_ts, 1, 7) = '2025-07' OR substr(prod_end_ts, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(prod_start_ts), MAX(prod_end_ts), SUM(good_qty) FROM csi_job_event WHERE substr(prod_start_ts, 1, 7) = '2025-07' OR substr(prod_end_ts, 1, 7) = '2025-07'",
        },
        "mes_report_event": {
            "count_sql": "SELECT COUNT(*) FROM mes_report_event WHERE substr(report_ts, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(report_ts), MAX(report_ts), SUM(required_qty), SUM(reported_qty) FROM mes_report_event WHERE substr(report_ts, 1, 7) = '2025-07'",
        },
        "maintenance_txn_event": {
            "count_sql": "SELECT COUNT(*) FROM maintenance_txn_event WHERE substr(txn_ts, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(txn_ts), MAX(txn_ts), SUM(quantity) FROM maintenance_txn_event WHERE substr(txn_ts, 1, 7) = '2025-07'",
        },
        "fact_machine_hour": {
            "count_sql": "SELECT COUNT(*) FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = '2025-07'",
            "range_sql": "SELECT MIN(hour_ts), MAX(hour_ts), SUM(energy_total_kwh), SUM(good_qty), SUM(scrap_qty) FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = '2025-07'",
            "flags_sql": "SELECT COUNT(*) FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = '2025-07' AND source_flags IS NOT NULL AND TRIM(source_flags) NOT IN ('', '{}')",
        },
    }

    conn = sqlite3.connect(db)
    try:
        existing_tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        result: dict[str, Any] = {}
        for table_name, spec in tables.items():
            if table_name not in existing_tables:
                result[table_name] = {"present": False}
                continue
            table_result: dict[str, Any] = {"present": True}
            table_result["july_row_count"] = _query_scalar(
                conn,
                spec["count_sql"],
                spec.get("params", ()),
            )
            if spec.get("range_sql"):
                table_result["range_and_aggregate"] = _query_one(
                    conn,
                    spec["range_sql"],
                    spec.get("params", ()),
                )
            if spec.get("flags_sql"):
                table_result["july_rows_with_source_flags"] = _query_scalar(conn, spec["flags_sql"])
            result[table_name] = table_result
        return result
    finally:
        conn.close()


def _summarize_etl_state(etl_instance: Any, mapping_results: dict[str, Any]) -> dict[str, Any]:
    extraction: dict[str, Any] = {}
    if etl_instance is not None:
        for label, attr in (("energy", "energy_data"), ("csi", "csi_data"), ("mes", "mes_data")):
            df = getattr(etl_instance, attr, None)
            extraction[label] = _summarize_dataframe(df)

    partial_matches = (
        mapping_results.get("partial_matches")
        or getattr(etl_instance, "partial_matches", None)
        or {}
    )
    mapping = {
        "three_way_match_count": len(mapping_results.get("three_way_matches") or []),
        "mapping_stats": mapping_results.get("mapping_stats") or {},
        "partial_match_counts": {
            key: len(value) if isinstance(value, list) else None
            for key, value in partial_matches.items()
        },
        "energy_to_csi_count": len(mapping_results.get("energy_to_csi") or {}),
        "energy_to_mes_count": len(mapping_results.get("energy_to_mes") or {}),
        "csi_to_mes_count": len(mapping_results.get("csi_to_mes") or {}),
    }
    return {"extraction": extraction, "mapping": mapping}


def _summarize_dataframe(df: Any) -> dict[str, Any]:
    if df is None:
        return {"row_count": None}
    summary: dict[str, Any] = {"row_count": int(len(df))}
    for column in ("datetime", "工程開始時間", "工程結束時間", "報工時間"):
        if hasattr(df, "columns") and column in df.columns:
            series = df[column].dropna().astype(str)
            if not series.empty:
                summary[f"{column}_min"] = str(series.min())
                summary[f"{column}_max"] = str(series.max())
    return summary


def _missing_source_files(source_payload: dict[str, Any]) -> list[str]:
    candidates = [
        *source_payload.get("energy_files", []),
        *([source_payload.get("csi_file")] if source_payload.get("csi_file") else []),
        *([source_payload.get("mes_file")] if source_payload.get("mes_file") else []),
    ]
    return [str(path) for path in candidates if path and not Path(path).exists()]


def _query_scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    try:
        row = conn.execute(sql, params).fetchone()
    except sqlite3.Error as exc:
        return {"error": str(exc)}
    return row[0] if row else None


def _query_one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
    try:
        row = conn.execute(sql, params).fetchone()
    except sqlite3.Error as exc:
        return [{"error": str(exc)}]
    return list(row) if row else []


def _validate_target_month(month: str) -> None:
    if str(month).strip() != TARGET_MONTH:
        raise ValueError(f"Refusing to run non-July rehearsal month: {month}")


def _validate_temp_db_path(db_path: Path) -> None:
    if _path_is_relative_to(db_path, REPO_ROOT):
        raise ValueError(f"Refusing DB path inside repo: {db_path}")
    if db_path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError(f"Temp DB path must use a DB suffix: {db_path}")


def _path_is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _file_stat(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
