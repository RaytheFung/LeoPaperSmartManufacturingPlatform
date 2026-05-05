#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import traceback
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.backfill_rehearsal_preflight import build_historical_backfill_preflight_plan
from core.runtime_paths import get_extended_raw_dataset_root
from modules.etl_module import ETLPipelineModule
from scripts.audit_august_csi_spill_traceability import build_traceability_audit
from scripts.audit_july_csi_spill_rows import RAW_CSI_CANONICAL_MONTH_EXPR, SILVER_CSI_CANONICAL_MONTH_EXPR
from scripts.compare_source_discovery_modes import build_source_discovery_compare_diagnostics


TARGET_MONTH = "August 2025"
AUGUST_MONTH_KEY = "2025-08"
DEFAULT_TEMP_DB_PATH = Path("/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db")
ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"
ORIGINAL_RUNTIME_DB_PATH = ORIGINAL_RUNTIME_REPO_ROOT / "manufacturing_data.db"


AUGUST_PRUNE_RULES = {
    "etl_runs": {
        "where": "month_processed = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_processed"},
        "reason": "ETL run ledger rows are month-scoped by month_processed.",
    },
    "etl_energy_data": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "ETL Energy staging is month-scoped by month_year.",
    },
    "etl_csi_data": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "ETL CSI staging is month-scoped by month_year.",
    },
    "etl_mes_data": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "ETL MES staging is month-scoped by month_year.",
    },
    "raw_energy_hourly": {
        "where": "substr(raw_timestamp, 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"raw_timestamp"},
        "reason": "Bronze Energy is month-scoped by raw_timestamp.",
    },
    "raw_csi_event": {
        "where": f"{RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"raw_start_time", "raw_end_time", "raw_prep_end_time", "raw_payload_json"},
        "reason": "Bronze CSI uses the current first-available timestamp canonical month expression.",
    },
    "raw_mes_report": {
        "where": "substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"raw_payload_json"},
        "reason": "Bronze MES is month-scoped by report timestamp in raw_payload_json.",
    },
    "raw_maintenance_txn": {
        "where": "substr(raw_transaction_date, 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"raw_transaction_date"},
        "reason": "Bronze maintenance is month-scoped by transaction timestamp.",
    },
    "energy_meter_hour": {
        "where": "substr(hour_ts, 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"hour_ts"},
        "reason": "Silver Energy is month-scoped by hour_ts.",
    },
    "csi_job_event": {
        "where": f"{SILVER_CSI_CANONICAL_MONTH_EXPR} = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"prod_start_ts", "prod_end_ts", "prep_end_ts", "shift_date"},
        "reason": "Silver CSI uses the current first-available timestamp canonical month expression.",
    },
    "mes_report_event": {
        "where": "substr(report_ts, 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"report_ts"},
        "reason": "Silver MES is month-scoped by report_ts.",
    },
    "maintenance_txn_event": {
        "where": "substr(txn_ts, 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"txn_ts"},
        "reason": "Silver maintenance is month-scoped by txn_ts.",
    },
    "fact_machine_hour": {
        "where": "substr(hour_ts, 1, 7) = ?",
        "params": (AUGUST_MONTH_KEY,),
        "required_columns": {"hour_ts"},
        "reason": "Gold fact table is month-scoped by hour_ts.",
    },
    "machine_monthly_presence": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "Machine presence is explicitly month-scoped by month_year.",
    },
}


GLOBAL_OR_AMBIGUOUS_TABLE_REASONS = {
    "machine_inventory": "Global inventory state; last_seen_date is not safe enough for August partition deletion.",
    "three_way_matches": "Global mapping state; first/last matched dates do not make row deletion safely month-scoped.",
    "unified_view": "Derived/global legacy surface; no conservative August delete predicate is defined.",
    "ml_models": "Model metadata/artifact table; model artifacts must not be modified.",
    "sqlite_sequence": "SQLite internal sequence table.",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one August 2025 historical backfill rehearsal against a temp DB only.",
    )
    parser.add_argument("--temp-db-path", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=get_extended_raw_dataset_root())
    parser.add_argument("--month", default=TARGET_MONTH)
    parser.add_argument("--original-db-path", type=Path, default=ORIGINAL_RUNTIME_DB_PATH)
    args = parser.parse_args(argv)

    try:
        evidence = run_august_temp_backfill_rehearsal(
            temp_db_path=args.temp_db_path,
            data_root=args.data_root,
            month=args.month,
            original_db_path=args.original_db_path,
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
    return 0 if evidence.get("status") == "success" else 2


def run_august_temp_backfill_rehearsal(
    *,
    temp_db_path: str | Path,
    data_root: str | Path,
    month: str = TARGET_MONTH,
    original_db_path: str | Path = ORIGINAL_RUNTIME_DB_PATH,
) -> dict[str, Any]:
    temp_db = Path(temp_db_path).expanduser().resolve(strict=False)
    source_root = Path(data_root).expanduser().resolve(strict=False)
    original_db = Path(original_db_path).expanduser().resolve(strict=False)
    _validate_target_month(month)
    _validate_temp_db_path(temp_db)
    if not temp_db.exists():
        raise FileNotFoundError(f"Temp DB does not exist: {temp_db}")

    original_before = _file_stat(original_db) if original_db.exists() else {"path": str(original_db), "exists": False}
    started_at = _utc_now()
    started_perf = time.perf_counter()
    temp_before = {**_file_stat(temp_db), "sha256": _sha256_file(temp_db)}
    isolation_evidence = isolate_august_baseline_partitions(temp_db)

    pipeline = ETLPipelineModule(db_path=temp_db)
    extraction_capture: dict[str, Any] = {}
    original_save = pipeline.save_etl_results

    def capture_and_save(mapping_results, month_name, etl_instance=None):
        extraction_capture.update(_summarize_etl_state(etl_instance, mapping_results))
        return original_save(mapping_results, month_name, etl_instance)

    pipeline.save_etl_results = capture_and_save

    source_default = pipeline.resolve_historical_month_sources(month, data_root=source_root)
    source_legacy = pipeline.resolve_historical_month_sources(month, data_root=source_root, discovery_mode="legacy")
    compare_diagnostic = build_source_discovery_compare_diagnostics(
        month_labels=[month],
        data_root=source_root,
        pipeline=ETLPipelineModule(db_path=temp_db, initialize_schema=False),
    )
    preflight_plan = build_historical_backfill_preflight_plan(month, data_root=source_root, db_path=temp_db)

    exception_payload = None
    captured_stdout = StringIO()
    try:
        with redirect_stdout(captured_stdout):
            rehearsal_result = pipeline.run_historical_canonical_backfill([month], data_root=source_root)
    except Exception as exc:
        rehearsal_result = {"status": "exception", "message": str(exc)}
        exception_payload = {
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    traceability_evidence: dict[str, Any]
    try:
        traceability_evidence = build_traceability_audit(temp_db)
    except Exception as exc:
        traceability_evidence = {
            "status": "error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    ended_at = _utc_now()
    duration_seconds = round(time.perf_counter() - started_perf, 3)
    temp_after = {**_file_stat(temp_db), "sha256": _sha256_file(temp_db)}
    original_after = _file_stat(original_db) if original_db.exists() else {"path": str(original_db), "exists": False}
    post_run_counts = summarize_august_temp_db(temp_db)
    duplicate_evidence = inspect_august_source_hash_duplicates(temp_db)
    safety_evidence = {
        "temp_db_inside_github_safe_repo": _path_is_relative_to(temp_db, REPO_ROOT),
        "temp_db_inside_original_runtime_repo": _path_is_relative_to(temp_db, ORIGINAL_RUNTIME_REPO_ROOT),
        "original_runtime_db_unchanged_by_size_mtime": _same_size_and_mtime(original_before, original_after),
        "live_db_write_allowed": False,
        "repo_db_write_allowed": False,
        "runs_march_2026": False,
    }
    traceability_result = traceability_evidence.get("traceability_result") if isinstance(traceability_evidence, dict) else {}
    traceability_passed = (
        isinstance(traceability_result, dict)
        and traceability_result.get("raw_august_unmatched_spill_row_count") == 0
        and traceability_result.get("silver_august_unmatched_spill_row_count") == 0
    )
    rehearsal_succeeded = rehearsal_result.get("status") == "success"

    return {
        "status": "success" if rehearsal_succeeded and traceability_passed else "partial_error",
        "target_month": month,
        "target_month_key": AUGUST_MONTH_KEY,
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
        "isolation_evidence": isolation_evidence,
        "etl_extraction_evidence": extraction_capture.get("extraction", {}),
        "mapping_evidence": extraction_capture.get("mapping", {}),
        "temp_db_evidence": {
            "before": temp_before,
            "after": temp_after,
            "post_run_august_counts": post_run_counts,
        },
        "spill_traceability_evidence": traceability_evidence,
        "duplicate_idempotence_evidence": duplicate_evidence,
        "runtime_evidence": {
            "started_at_utc": started_at,
            "ended_at_utc": ended_at,
            "duration_seconds": duration_seconds,
            "exception": exception_payload,
            "captured_stdout": captured_stdout.getvalue().splitlines(),
        },
        "rehearsal_result": rehearsal_result,
        "original_runtime_db_evidence": {
            "before": original_before,
            "after": original_after,
        },
        "safety_evidence": safety_evidence,
    }


def isolate_august_baseline_partitions(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path).expanduser().resolve(strict=False)
    _validate_temp_db_path(db)
    if not db.exists():
        raise FileNotFoundError(f"DB path does not exist: {db}")

    conn = sqlite3.connect(db)
    try:
        inspected = inspect_temp_db_tables(conn)
        pruned: dict[str, Any] = {}
        skipped: dict[str, Any] = {}

        for table_name in sorted(inspected):
            columns = set(inspected[table_name])
            pre_total_count = _count_all_table_rows(conn, table_name)
            if table_name not in AUGUST_PRUNE_RULES:
                skipped[table_name] = {
                    "columns": inspected[table_name],
                    "pre_total_row_count": pre_total_count,
                    "post_total_row_count": pre_total_count,
                    "reason": GLOBAL_OR_AMBIGUOUS_TABLE_REASONS.get(
                        table_name,
                        "No conservative August-specific delete predicate is defined for this table.",
                    ),
                }
                continue

            rule = AUGUST_PRUNE_RULES[table_name]
            missing_columns = sorted(set(rule["required_columns"]) - columns)
            if missing_columns:
                skipped[table_name] = {
                    "columns": inspected[table_name],
                    "pre_total_row_count": pre_total_count,
                    "post_total_row_count": pre_total_count,
                    "reason": "Required columns are missing for conservative August pruning: " + ", ".join(missing_columns),
                }
                continue

            pre_count = _count_table_rows(conn, table_name, rule["where"], rule["params"])
            conn.execute(
                f"DELETE FROM {_quote_identifier(table_name)} WHERE {rule['where']}",
                rule["params"],
            )
            post_count = _count_table_rows(conn, table_name, rule["where"], rule["params"])
            pruned[table_name] = {
                "delete_condition": rule["where"],
                "params": list(rule["params"]),
                "pre_prune_august_count": pre_count,
                "post_prune_august_count": post_count,
                "pre_total_row_count": pre_total_count,
                "post_total_row_count": _count_all_table_rows(conn, table_name),
                "deleted_rows": pre_count - post_count if isinstance(pre_count, int) and isinstance(post_count, int) else None,
                "reason": rule["reason"],
            }

        conn.commit()
        return {
            "tables_inspected": inspected,
            "tables_pruned": pruned,
            "tables_skipped": skipped,
        }
    finally:
        conn.close()


def inspect_temp_db_tables(conn: sqlite3.Connection) -> dict[str, list[str]]:
    tables = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
    ]
    return {
        table_name: [row[1] for row in conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()]
        for table_name in tables
    }


def summarize_august_temp_db(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path).expanduser().resolve(strict=False)
    _validate_temp_db_path(db)
    if not db.exists():
        raise FileNotFoundError(f"DB path does not exist: {db}")

    table_specs = {
        "etl_runs": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM etl_runs WHERE month_processed = ?",
            "params": (TARGET_MONTH,),
        },
        "etl_energy_data": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM etl_energy_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(datetime) AS min_datetime, MAX(datetime) AS max_datetime, SUM(electricity_kwh) AS energy_kwh_sum FROM etl_energy_data WHERE month_year = ?",
        },
        "etl_csi_data": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM etl_csi_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(start_time) AS min_start_time, MAX(end_time) AS max_end_time, SUM(good_qty) AS good_qty_sum FROM etl_csi_data WHERE month_year = ?",
        },
        "etl_mes_data": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM etl_mes_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(planned_start) AS min_planned_start, MAX(planned_end) AS max_planned_end, SUM(planned_qty) AS planned_qty_sum FROM etl_mes_data WHERE month_year = ?",
        },
        "raw_energy_hourly": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM raw_energy_hourly WHERE substr(raw_timestamp, 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(raw_timestamp) AS min_raw_timestamp, MAX(raw_timestamp) AS max_raw_timestamp, SUM(raw_kwh) AS raw_kwh_sum FROM raw_energy_hourly WHERE substr(raw_timestamp, 1, 7) = ?",
        },
        "raw_csi_event": {
            "count_sql": f"SELECT COUNT(*) AS row_count FROM raw_csi_event WHERE {AUGUST_PRUNE_RULES['raw_csi_event']['where']}",
            "params": AUGUST_PRUNE_RULES["raw_csi_event"]["params"],
            "range_sql": f"SELECT MIN(raw_start_time) AS min_raw_start_time, MAX(raw_end_time) AS max_raw_end_time, SUM(raw_good_qty) AS raw_good_qty_sum FROM raw_csi_event WHERE {AUGUST_PRUNE_RULES['raw_csi_event']['where']}",
        },
        "raw_mes_report": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM raw_mes_report WHERE substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(json_extract(raw_payload_json, '$.\"報工時間\"')) AS min_report_time, MAX(json_extract(raw_payload_json, '$.\"報工時間\"')) AS max_report_time, SUM(raw_planned_qty) AS raw_planned_qty_sum FROM raw_mes_report WHERE substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = ?",
        },
        "raw_maintenance_txn": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM raw_maintenance_txn WHERE substr(raw_transaction_date, 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(raw_transaction_date) AS min_raw_transaction_date, MAX(raw_transaction_date) AS max_raw_transaction_date, SUM(raw_quantity) AS raw_quantity_sum FROM raw_maintenance_txn WHERE substr(raw_transaction_date, 1, 7) = ?",
        },
        "energy_meter_hour": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM energy_meter_hour WHERE substr(hour_ts, 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(hour_ts) AS min_hour_ts, MAX(hour_ts) AS max_hour_ts, SUM(kwh) AS kwh_sum FROM energy_meter_hour WHERE substr(hour_ts, 1, 7) = ?",
            "flags_sql": "SELECT COUNT(*) AS flagged_row_count FROM energy_meter_hour WHERE substr(hour_ts, 1, 7) = ? AND quality_flags_json IS NOT NULL AND TRIM(quality_flags_json) NOT IN ('', '{}')",
        },
        "csi_job_event": {
            "count_sql": f"SELECT COUNT(*) AS row_count FROM csi_job_event WHERE {AUGUST_PRUNE_RULES['csi_job_event']['where']}",
            "params": AUGUST_PRUNE_RULES["csi_job_event"]["params"],
            "range_sql": f"SELECT MIN(prod_start_ts) AS min_prod_start_ts, MAX(prod_end_ts) AS max_prod_end_ts, SUM(good_qty) AS good_qty_sum FROM csi_job_event WHERE {AUGUST_PRUNE_RULES['csi_job_event']['where']}",
        },
        "mes_report_event": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM mes_report_event WHERE substr(report_ts, 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(report_ts) AS min_report_ts, MAX(report_ts) AS max_report_ts, SUM(required_qty) AS required_qty_sum, SUM(reported_qty) AS reported_qty_sum FROM mes_report_event WHERE substr(report_ts, 1, 7) = ?",
        },
        "maintenance_txn_event": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM maintenance_txn_event WHERE substr(txn_ts, 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(txn_ts) AS min_txn_ts, MAX(txn_ts) AS max_txn_ts, SUM(quantity) AS quantity_sum FROM maintenance_txn_event WHERE substr(txn_ts, 1, 7) = ?",
        },
        "fact_machine_hour": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ?",
            "params": (AUGUST_MONTH_KEY,),
            "range_sql": "SELECT MIN(hour_ts) AS min_hour_ts, MAX(hour_ts) AS max_hour_ts, SUM(energy_total_kwh) AS energy_total_kwh_sum, SUM(good_qty) AS good_qty_sum, SUM(scrap_qty) AS scrap_qty_sum FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ?",
            "flags_sql": "SELECT COUNT(*) AS flagged_row_count FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ? AND source_flags IS NOT NULL AND TRIM(source_flags) NOT IN ('', '{}')",
        },
        "machine_monthly_presence": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM machine_monthly_presence WHERE month_year = ?",
            "params": (TARGET_MONTH,),
        },
    }

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        existing_tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        result: dict[str, Any] = {}
        for table_name, spec in table_specs.items():
            if table_name not in existing_tables:
                result[table_name] = {"present": False}
                continue
            table_result: dict[str, Any] = {"present": True}
            table_result["august_row_count"] = _query_one(conn, spec["count_sql"], spec.get("params", ()))
            if spec.get("range_sql"):
                table_result["range_and_aggregate"] = _query_one(conn, spec["range_sql"], spec.get("params", ()))
            if spec.get("flags_sql"):
                table_result["august_rows_with_flags"] = _query_one(conn, spec["flags_sql"], spec.get("params", ()))
            result[table_name] = table_result
        return result
    finally:
        conn.close()


def inspect_august_source_hash_duplicates(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path).expanduser().resolve(strict=False)
    _validate_temp_db_path(db)
    conn = sqlite3.connect(db)
    try:
        existing_tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        results: dict[str, Any] = {}
        for table_name, rule in AUGUST_PRUNE_RULES.items():
            if table_name not in existing_tables:
                continue
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()]
            if "source_row_hash" not in columns:
                results[table_name] = {
                    "has_source_row_hash": False,
                    "august_duplicate_hash_group_count": None,
                }
                continue
            duplicate_count = _query_scalar(
                conn,
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT source_row_hash
                    FROM {_quote_identifier(table_name)}
                    WHERE {rule['where']}
                    GROUP BY source_row_hash
                    HAVING COUNT(*) > 1
                )
                """,
                rule["params"],
            )
            results[table_name] = {
                "has_source_row_hash": True,
                "august_duplicate_hash_group_count": duplicate_count,
            }
        return results
    finally:
        conn.close()


def _summarize_etl_state(etl_instance: Any, mapping_results: dict[str, Any]) -> dict[str, Any]:
    extraction: dict[str, Any] = {}
    if etl_instance is not None:
        for label, attr in (("energy", "energy_data"), ("csi", "csi_data"), ("mes", "mes_data")):
            df = getattr(etl_instance, attr, None)
            extraction[label] = _summarize_dataframe(df)

    partial_matches = mapping_results.get("partial_matches") or getattr(etl_instance, "partial_matches", None) or {}
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


def _query_one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    try:
        row = conn.execute(sql, params).fetchone()
    except sqlite3.Error as exc:
        return {"error": str(exc)}
    return dict(row) if row is not None else {}


def _count_table_rows(
    conn: sqlite3.Connection,
    table_name: str,
    where_clause: str,
    params: tuple[Any, ...] = (),
) -> Any:
    return _query_scalar(conn, f"SELECT COUNT(*) FROM {_quote_identifier(table_name)} WHERE {where_clause}", params)


def _count_all_table_rows(conn: sqlite3.Connection, table_name: str) -> Any:
    return _query_scalar(conn, f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}")


def _validate_target_month(month: str) -> None:
    if str(month).strip() != TARGET_MONTH:
        raise ValueError(f"Refusing to run non-August rehearsal month: {month}")


def _validate_temp_db_path(db_path: Path) -> None:
    if _path_is_relative_to(db_path, REPO_ROOT):
        raise ValueError(f"Refusing DB path inside repo: {db_path}")
    if _path_is_relative_to(db_path, ORIGINAL_RUNTIME_REPO_ROOT):
        raise ValueError(f"Refusing DB path inside original runtime repo: {db_path}")
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


def _same_size_and_mtime(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return before.get("size_bytes") == after.get("size_bytes") and before.get("mtime_ns") == after.get("mtime_ns")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
