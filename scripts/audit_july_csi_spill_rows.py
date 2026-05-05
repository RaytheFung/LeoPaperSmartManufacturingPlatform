#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"

TARGET_MONTH = "July 2025"
TARGET_MONTH_KEY = "2025-07"

RAW_CSI_CANONICAL_MONTH_EXPR = (
    "COALESCE("
    "substr(raw_start_time, 1, 7), "
    "substr(raw_end_time, 1, 7), "
    "substr(raw_prep_end_time, 1, 7), "
    "substr(json_extract(raw_payload_json, '$.班次內日期'), 1, 7)"
    ")"
)
SILVER_CSI_CANONICAL_MONTH_EXPR = (
    "COALESCE("
    "substr(prod_start_ts, 1, 7), "
    "substr(prod_end_ts, 1, 7), "
    "substr(prep_end_ts, 1, 7), "
    "substr(shift_date, 1, 7)"
    ")"
)
ETL_CSI_CANONICAL_MONTH_EXPR = (
    "COALESCE("
    "substr(start_time, 1, 7), "
    "substr(end_time, 1, 7), "
    "substr(setup_end, 1, 7)"
    ")"
)
ETL_CSI_EXTRACTED_MONTH_EXPR = (
    "substr(start_time, 1, 7) = ? "
    "OR substr(end_time, 1, 7) = ? "
    "OR substr(setup_end, 1, 7) = ?"
)


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_db_path(db_path: Path) -> Path:
    resolved = db_path.expanduser().resolve()
    if path_is_relative_to(resolved, REPO_ROOT.resolve()):
        raise ValueError(f"Refusing DB path inside repo: {resolved}")
    if path_is_relative_to(resolved, ORIGINAL_RUNTIME_REPO_ROOT.resolve()):
        raise ValueError(f"Refusing DB path inside original runtime repo: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"DB path does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"DB path is not a file: {resolved}")
    return resolved


def open_readonly(db_path: Path) -> sqlite3.Connection:
    validated = validate_db_path(db_path)
    uri = f"file:{validated.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _month_key(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 7:
        return None
    return text[:7]


def classify_csi_row_scope(
    *,
    start_time: object = None,
    end_time: object = None,
    setup_end: object = None,
    shift_date: object = None,
    target_month_key: str = TARGET_MONTH_KEY,
) -> dict[str, object]:
    months = {
        "start_time_month": _month_key(start_time),
        "end_time_month": _month_key(end_time),
        "setup_end_month": _month_key(setup_end),
        "shift_date_month": _month_key(shift_date),
    }
    canonical_month = next((month for month in months.values() if month), None)
    extraction_intersects_target = any(month == target_month_key for month in months.values())

    if canonical_month == target_month_key:
        classification = "canonical_target_month"
    elif extraction_intersects_target:
        classification = "spill_outside_canonical_scope"
    elif canonical_month:
        classification = "outside_extraction_and_canonical_scope"
    else:
        classification = "unresolved_missing_month_evidence"

    return {
        **months,
        "canonical_month": canonical_month,
        "extraction_intersects_target": extraction_intersects_target,
        "canonical_in_target": canonical_month == target_month_key,
        "classification": classification,
    }


def _fetch_one(conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> dict[str, object]:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else {}


def _fetch_all(conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def require_tables(conn: sqlite3.Connection) -> None:
    required_tables = ("etl_csi_data", "raw_csi_event", "csi_job_event")
    missing = [table_name for table_name in required_tables if not _table_exists(conn, table_name)]
    if missing:
        raise ValueError("DB is missing required tables: " + ", ".join(missing))


def build_audit(db_path: Path) -> dict[str, object]:
    resolved_db_path = validate_db_path(db_path)
    with open_readonly(resolved_db_path) as conn:
        require_tables(conn)

        etl_count = _fetch_one(
            conn,
            """
            SELECT
                COUNT(*) AS row_count,
                MIN(start_time) AS min_start_time,
                MAX(end_time) AS max_end_time,
                SUM(good_qty) AS good_qty_sum
            FROM etl_csi_data
            WHERE month_year = ?
            """,
            (TARGET_MONTH,),
        )
        raw_count = _fetch_one(
            conn,
            f"""
            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT source_row_hash) AS distinct_source_row_hash_count,
                MIN(raw_start_time) AS min_start_time,
                MAX(raw_end_time) AS max_end_time,
                SUM(raw_good_qty) AS good_qty_sum
            FROM raw_csi_event
            WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?
            """,
            (TARGET_MONTH_KEY,),
        )
        silver_count = _fetch_one(
            conn,
            f"""
            SELECT
                COUNT(*) AS row_count,
                COUNT(DISTINCT source_row_hash) AS distinct_source_row_hash_count,
                MIN(prod_start_ts) AS min_start_time,
                MAX(prod_end_ts) AS max_end_time,
                SUM(good_qty) AS good_qty_sum
            FROM csi_job_event
            WHERE {SILVER_CSI_CANONICAL_MONTH_EXPR} = ?
            """,
            (TARGET_MONTH_KEY,),
        )
        etl_canonical_like_count = _fetch_one(
            conn,
            f"""
            SELECT
                COUNT(*) AS row_count,
                MIN(start_time) AS min_start_time,
                MAX(end_time) AS max_end_time,
                SUM(good_qty) AS good_qty_sum
            FROM etl_csi_data
            WHERE month_year = ?
              AND {ETL_CSI_CANONICAL_MONTH_EXPR} = ?
            """,
            (TARGET_MONTH, TARGET_MONTH_KEY),
        )
        spill_count = _fetch_one(
            conn,
            f"""
            SELECT
                COUNT(*) AS row_count,
                MIN(start_time) AS min_start_time,
                MAX(end_time) AS max_end_time,
                SUM(good_qty) AS good_qty_sum
            FROM etl_csi_data
            WHERE month_year = ?
              AND ({ETL_CSI_CANONICAL_MONTH_EXPR} IS NULL OR {ETL_CSI_CANONICAL_MONTH_EXPR} <> ?)
            """,
            (TARGET_MONTH, TARGET_MONTH_KEY),
        )
        extracted_but_not_canonical_months = _fetch_all(
            conn,
            f"""
            SELECT
                substr(start_time, 1, 7) AS start_time_month,
                substr(end_time, 1, 7) AS end_time_month,
                substr(setup_end, 1, 7) AS setup_end_month,
                'unavailable_in_etl_csi_data' AS shift_date_month,
                {ETL_CSI_CANONICAL_MONTH_EXPR} AS canonical_month,
                COUNT(*) AS row_count,
                SUM(good_qty) AS good_qty_sum,
                MIN(start_time) AS min_start_time,
                MAX(end_time) AS max_end_time
            FROM etl_csi_data
            WHERE month_year = ?
              AND ({ETL_CSI_CANONICAL_MONTH_EXPR} IS NULL OR {ETL_CSI_CANONICAL_MONTH_EXPR} <> ?)
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY row_count DESC, good_qty_sum DESC
            """,
            (TARGET_MONTH, TARGET_MONTH_KEY),
        )
        machine_summary = _fetch_all(
            conn,
            f"""
            SELECT
                machine_id,
                COUNT(*) AS row_count,
                COUNT(DISTINCT order_id) AS distinct_order_count,
                SUM(good_qty) AS good_qty_sum,
                MIN(start_time) AS min_start_time,
                MAX(end_time) AS max_end_time
            FROM etl_csi_data
            WHERE month_year = ?
              AND ({ETL_CSI_CANONICAL_MONTH_EXPR} IS NULL OR {ETL_CSI_CANONICAL_MONTH_EXPR} <> ?)
            GROUP BY machine_id
            ORDER BY row_count DESC, good_qty_sum DESC
            """,
            (TARGET_MONTH, TARGET_MONTH_KEY),
        )
        order_summary = _fetch_all(
            conn,
            f"""
            SELECT
                machine_id,
                order_id,
                substr(start_time, 1, 7) AS start_time_month,
                substr(end_time, 1, 7) AS end_time_month,
                substr(setup_end, 1, 7) AS setup_end_month,
                'unavailable_in_etl_csi_data' AS shift_date_month,
                COUNT(*) AS row_count,
                SUM(good_qty) AS good_qty_sum,
                MIN(start_time) AS min_start_time,
                MAX(end_time) AS max_end_time
            FROM etl_csi_data
            WHERE month_year = ?
              AND ({ETL_CSI_CANONICAL_MONTH_EXPR} IS NULL OR {ETL_CSI_CANONICAL_MONTH_EXPR} <> ?)
            GROUP BY machine_id, order_id, start_time_month, end_time_month, setup_end_month
            ORDER BY row_count DESC, good_qty_sum DESC
            LIMIT 25
            """,
            (TARGET_MONTH, TARGET_MONTH_KEY),
        )
        duplicate_evidence = {
            "raw_canonical_duplicate_source_row_hash_groups": _fetch_one(
                conn,
                f"""
                SELECT COUNT(*) AS duplicate_group_count
                FROM (
                    SELECT source_row_hash
                    FROM raw_csi_event
                    WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?
                    GROUP BY source_row_hash
                    HAVING COUNT(*) > 1
                )
                """,
                (TARGET_MONTH_KEY,),
            )["duplicate_group_count"],
            "silver_canonical_duplicate_source_row_hash_groups": _fetch_one(
                conn,
                f"""
                SELECT COUNT(*) AS duplicate_group_count
                FROM (
                    SELECT source_row_hash
                    FROM csi_job_event
                    WHERE {SILVER_CSI_CANONICAL_MONTH_EXPR} = ?
                    GROUP BY source_row_hash
                    HAVING COUNT(*) > 1
                )
                """,
                (TARGET_MONTH_KEY,),
            )["duplicate_group_count"],
            "etl_july_duplicate_signature_groups": _fetch_one(
                conn,
                """
                SELECT COUNT(*) AS duplicate_group_count
                FROM (
                    SELECT machine_id, start_time, end_time, setup_end, order_id, material, good_qty
                    FROM etl_csi_data
                    WHERE month_year = ?
                    GROUP BY machine_id, start_time, end_time, setup_end, order_id, material, good_qty
                    HAVING COUNT(*) > 1
                )
                """,
                (TARGET_MONTH,),
            )["duplicate_group_count"],
        }

    extracted_rows = int(etl_count["row_count"] or 0)
    raw_rows = int(raw_count["row_count"] or 0)
    silver_rows = int(silver_count["row_count"] or 0)
    spill_rows = int(spill_count["row_count"] or 0)
    row_difference = extracted_rows - raw_rows
    all_spill_rows_outside_target = all(
        row.get("canonical_month") != TARGET_MONTH_KEY for row in extracted_but_not_canonical_months
    )

    if row_difference == spill_rows and raw_rows == silver_rows and all_spill_rows_outside_target:
        verdict = "legitimate_spill_rows_outside_canonical_july_scope"
    elif raw_rows != silver_rows:
        verdict = "raw_silver_predicate_mismatch"
    elif any(value for value in duplicate_evidence.values()):
        verdict = "duplicate_or_row_hash_issue_requires_review"
    else:
        verdict = "unresolved"

    return {
        "db_path": str(resolved_db_path),
        "target_month": TARGET_MONTH,
        "target_month_key": TARGET_MONTH_KEY,
        "canonical_predicates": {
            "raw_csi_event": RAW_CSI_CANONICAL_MONTH_EXPR,
            "csi_job_event": SILVER_CSI_CANONICAL_MONTH_EXPR,
            "etl_csi_data_equivalent_without_shift_date": ETL_CSI_CANONICAL_MONTH_EXPR,
            "etl_extraction_intersects_month": ETL_CSI_EXTRACTED_MONTH_EXPR,
        },
        "row_count_reconciliation": {
            "etl_csi_data_month_year_july": etl_count,
            "raw_csi_event_canonical_july": raw_count,
            "csi_job_event_canonical_july": silver_count,
            "etl_csi_data_canonical_like_july": etl_canonical_like_count,
            "etl_csi_data_spill_rows_outside_canonical_july": spill_count,
            "etl_minus_raw_canonical_july": row_difference,
            "etl_minus_silver_canonical_july": extracted_rows - silver_rows,
        },
        "spill_row_classification": {
            "verdict": verdict,
            "all_spill_rows_outside_target_canonical_month": all_spill_rows_outside_target,
            "month_summary": extracted_but_not_canonical_months,
        },
        "machine_summary": machine_summary,
        "order_summary_top_25": order_summary,
        "duplicate_evidence": duplicate_evidence,
        "safety": {
            "opened_read_only": True,
            "repo_root": str(REPO_ROOT),
            "original_runtime_repo_root": str(ORIGINAL_RUNTIME_REPO_ROOT),
            "db_path_inside_repo": False,
            "db_path_inside_original_runtime_repo": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit for July 2025 CSI spill rows outside canonical July scope.",
    )
    parser.add_argument("--db-path", type=Path, required=True, help="Existing DB path outside repo roots.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    try:
        audit = build_audit(args.db_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(audit, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
