#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_july_csi_spill_rows import (
    ETL_CSI_CANONICAL_MONTH_EXPR,
    RAW_CSI_CANONICAL_MONTH_EXPR,
    SILVER_CSI_CANONICAL_MONTH_EXPR,
    TARGET_MONTH,
    TARGET_MONTH_KEY,
    open_readonly,
    require_tables,
    validate_db_path,
)


AUGUST_MONTH = "August 2025"
AUGUST_MONTH_KEY = "2025-08"


def _normalize_key_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    text = str(value).strip()
    if text.endswith(".0"):
        try:
            parsed = float(text)
        except ValueError:
            return text
        if parsed.is_integer():
            return str(int(parsed))
    return text


def build_csi_identity_key(
    *,
    machine_id: object,
    start_time: object,
    end_time: object,
    prep_end_time: object,
    order_id: object,
    material: object,
    good_qty: object,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        _normalize_key_value(machine_id),
        _normalize_key_value(start_time),
        _normalize_key_value(end_time),
        _normalize_key_value(prep_end_time),
        _normalize_key_value(order_id),
        _normalize_key_value(material),
        _normalize_key_value(good_qty),
    )


def _fetch_rows(conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _fetch_one(conn: sqlite3.Connection, sql: str, params: tuple[object, ...] = ()) -> dict[str, object]:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else {}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _spill_key(row: dict[str, object]) -> tuple[str, str, str, str, str, str, str]:
    return build_csi_identity_key(
        machine_id=row.get("machine_id"),
        start_time=row.get("start_time"),
        end_time=row.get("end_time"),
        prep_end_time=row.get("setup_end"),
        order_id=row.get("order_id"),
        material=row.get("material"),
        good_qty=row.get("good_qty"),
    )


def _raw_key(row: dict[str, object]) -> tuple[str, str, str, str, str, str, str]:
    return build_csi_identity_key(
        machine_id=row.get("raw_machine_id_or_label"),
        start_time=row.get("raw_start_time"),
        end_time=row.get("raw_end_time"),
        prep_end_time=row.get("raw_prep_end_time"),
        order_id=row.get("raw_order_id"),
        material=row.get("raw_material"),
        good_qty=row.get("raw_good_qty"),
    )


def _silver_key(row: dict[str, object]) -> tuple[str, str, str, str, str, str, str]:
    return build_csi_identity_key(
        machine_id=row.get("raw_machine_id_or_label"),
        start_time=row.get("prod_start_ts"),
        end_time=row.get("prod_end_ts"),
        prep_end_time=row.get("prep_end_ts"),
        order_id=row.get("order_id"),
        material=row.get("material_code"),
        good_qty=row.get("good_qty"),
    )


def _numeric_sum(rows: list[dict[str, object]], field_name: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(field_name)
        if value is None:
            continue
        total += float(value)
    return total


def _summarize_spill_machines(rows: list[dict[str, object]], limit: int = 10) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("machine_id") or "")].append(row)

    summary = []
    for machine_id, machine_rows in grouped.items():
        end_values = [str(row.get("end_time")) for row in machine_rows if row.get("end_time") is not None]
        start_values = [str(row.get("start_time")) for row in machine_rows if row.get("start_time") is not None]
        summary.append(
            {
                "machine_id": machine_id,
                "row_count": len(machine_rows),
                "distinct_order_count": len({row.get("order_id") for row in machine_rows}),
                "good_qty_sum": _numeric_sum(machine_rows, "good_qty"),
                "min_start_time": min(start_values) if start_values else None,
                "max_end_time": max(end_values) if end_values else None,
            }
        )
    summary.sort(key=lambda item: (item["good_qty_sum"], item["row_count"]), reverse=True)
    return summary[:limit]


def _summarize_spill_orders(rows: list[dict[str, object]], limit: int = 10) -> list[dict[str, object]]:
    grouped: dict[tuple[object, object], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("machine_id"), row.get("order_id"))].append(row)

    summary = []
    for (machine_id, order_id), order_rows in grouped.items():
        end_values = [str(row.get("end_time")) for row in order_rows if row.get("end_time") is not None]
        start_values = [str(row.get("start_time")) for row in order_rows if row.get("start_time") is not None]
        summary.append(
            {
                "machine_id": machine_id,
                "order_id": order_id,
                "row_count": len(order_rows),
                "good_qty_sum": _numeric_sum(order_rows, "good_qty"),
                "min_start_time": min(start_values) if start_values else None,
                "max_end_time": max(end_values) if end_values else None,
            }
        )
    summary.sort(key=lambda item: (item["good_qty_sum"], item["row_count"]), reverse=True)
    return summary[:limit]


def build_traceability_audit(db_path: Path) -> dict[str, object]:
    resolved_db_path = validate_db_path(db_path)
    with open_readonly(resolved_db_path) as conn:
        require_tables(conn)

        spill_rows = _fetch_rows(
            conn,
            f"""
            SELECT
                id,
                machine_id,
                start_time,
                end_time,
                setup_end,
                order_id,
                material,
                good_qty,
                {ETL_CSI_CANONICAL_MONTH_EXPR} AS canonical_month
            FROM etl_csi_data
            WHERE month_year = ?
              AND ({ETL_CSI_CANONICAL_MONTH_EXPR} IS NULL OR {ETL_CSI_CANONICAL_MONTH_EXPR} <> ?)
            """,
            (TARGET_MONTH, TARGET_MONTH_KEY),
        )
        raw_august_rows = _fetch_rows(
            conn,
            f"""
            SELECT
                source_row_hash,
                source_file,
                raw_machine_id_or_label,
                raw_start_time,
                raw_end_time,
                raw_prep_end_time,
                raw_order_id,
                raw_material,
                raw_good_qty
            FROM raw_csi_event
            WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?
            """,
            (AUGUST_MONTH_KEY,),
        )
        silver_august_rows = _fetch_rows(
            conn,
            f"""
            SELECT
                source_row_hash,
                raw_machine_id_or_label,
                prod_start_ts,
                prod_end_ts,
                prep_end_ts,
                order_id,
                material_code,
                good_qty
            FROM csi_job_event
            WHERE {SILVER_CSI_CANONICAL_MONTH_EXPR} = ?
            """,
            (AUGUST_MONTH_KEY,),
        )

        surface_context: dict[str, object] = {
            "raw_csi_event_canonical_august": _fetch_one(
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
                (AUGUST_MONTH_KEY,),
            ),
            "csi_job_event_canonical_august": _fetch_one(
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
                (AUGUST_MONTH_KEY,),
            ),
            "etl_csi_data_august": _fetch_one(
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
                (AUGUST_MONTH,),
            ),
        }
        if _table_exists(conn, "fact_machine_hour"):
            surface_context["fact_machine_hour_august_context"] = _fetch_one(
                conn,
                """
                SELECT
                    COUNT(*) AS row_count,
                    MIN(hour_ts) AS min_hour_ts,
                    MAX(hour_ts) AS max_hour_ts,
                    SUM(good_qty) AS good_qty_sum
                FROM fact_machine_hour
                WHERE substr(hour_ts, 1, 7) = ?
                """,
                (AUGUST_MONTH_KEY,),
            )

        duplicate_evidence = {
            "raw_august_duplicate_source_row_hash_groups": _fetch_one(
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
                (AUGUST_MONTH_KEY,),
            )["duplicate_group_count"],
            "silver_august_duplicate_source_row_hash_groups": _fetch_one(
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
                (AUGUST_MONTH_KEY,),
            )["duplicate_group_count"],
        }

    raw_by_identity: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in raw_august_rows:
        raw_by_identity[_raw_key(row)].append(row)

    silver_by_hash = {
        str(row["source_row_hash"]): row
        for row in silver_august_rows
        if row.get("source_row_hash") is not None
    }
    silver_by_identity: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in silver_august_rows:
        silver_by_identity[_silver_key(row)].append(row)

    raw_matched_spill_rows: list[dict[str, object]] = []
    silver_matched_spill_rows: list[dict[str, object]] = []
    unmatched_raw: list[dict[str, object]] = []
    unmatched_silver: list[dict[str, object]] = []
    raw_matched_source_hashes: set[str] = set()
    silver_hash_matched_source_hashes: set[str] = set()
    raw_match_row_count = 0
    raw_source_file_counter: Counter[str] = Counter()

    for spill_row in spill_rows:
        identity_key = _spill_key(spill_row)
        raw_matches = raw_by_identity.get(identity_key, [])
        if raw_matches:
            raw_matched_spill_rows.append(spill_row)
            raw_match_row_count += len(raw_matches)
            for raw_row in raw_matches:
                if raw_row.get("source_row_hash"):
                    raw_matched_source_hashes.add(str(raw_row["source_row_hash"]))
                if raw_row.get("source_file"):
                    raw_source_file_counter[str(raw_row["source_file"])] += 1
        else:
            unmatched_raw.append(spill_row)

        raw_hashes = [
            str(raw_row["source_row_hash"])
            for raw_row in raw_matches
            if raw_row.get("source_row_hash") is not None
        ]
        matching_silver_hashes = [source_hash for source_hash in raw_hashes if source_hash in silver_by_hash]
        if matching_silver_hashes:
            silver_matched_spill_rows.append(spill_row)
            silver_hash_matched_source_hashes.update(matching_silver_hashes)
        elif silver_by_identity.get(identity_key):
            silver_matched_spill_rows.append(spill_row)
        else:
            unmatched_silver.append(spill_row)

    spill_count = len(spill_rows)
    raw_match_count = len(raw_matched_spill_rows)
    silver_match_count = len(silver_matched_spill_rows)
    if spill_count and raw_match_count == spill_count and silver_match_count == spill_count:
        verdict = "august_raw_and_silver_traceability_proven_in_current_temp_db"
    elif spill_count and raw_match_count == spill_count:
        verdict = "august_raw_traceability_proven_silver_traceability_incomplete"
    elif spill_count:
        verdict = "august_traceability_incomplete"
    else:
        verdict = "no_july_spill_rows_found"

    return {
        "db_path": str(resolved_db_path),
        "source_month": TARGET_MONTH,
        "source_month_key": TARGET_MONTH_KEY,
        "target_trace_month": AUGUST_MONTH,
        "target_trace_month_key": AUGUST_MONTH_KEY,
        "matching_key": {
            "primary": "source_row_hash after matching July spill identity to August raw canonical rows",
            "fallback": "machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty",
            "reason": "etl_csi_data spill rows do not carry source_row_hash directly, so raw identity matching is needed before source-hash silver matching.",
        },
        "spill_identity_summary": {
            "spill_row_count": spill_count,
            "canonical_months": dict(Counter(str(row.get("canonical_month")) for row in spill_rows)),
            "distinct_machine_count": len({row.get("machine_id") for row in spill_rows}),
            "distinct_order_count": len({row.get("order_id") for row in spill_rows}),
            "good_qty_sum": _numeric_sum(spill_rows, "good_qty"),
            "min_start_time": min([str(row.get("start_time")) for row in spill_rows if row.get("start_time")], default=None),
            "max_end_time": max([str(row.get("end_time")) for row in spill_rows if row.get("end_time")], default=None),
        },
        "surface_context": surface_context,
        "traceability_result": {
            "verdict": verdict,
            "raw_august_matched_spill_row_count": raw_match_count,
            "raw_august_unmatched_spill_row_count": len(unmatched_raw),
            "raw_august_matched_row_count": raw_match_row_count,
            "raw_august_matched_distinct_source_row_hash_count": len(raw_matched_source_hashes),
            "silver_august_matched_spill_row_count": silver_match_count,
            "silver_august_unmatched_spill_row_count": len(unmatched_silver),
            "silver_august_hash_matched_distinct_source_row_hash_count": len(silver_hash_matched_source_hashes),
            "raw_source_files_for_matches": [
                {"source_file": source_file, "matched_raw_row_count": count}
                for source_file, count in raw_source_file_counter.most_common()
            ],
        },
        "unmatched_rows": {
            "raw_august_unmatched": unmatched_raw,
            "silver_august_unmatched": unmatched_silver,
        },
        "machine_summary_top_10_by_good_qty": _summarize_spill_machines(spill_rows),
        "order_summary_top_10_by_good_qty": _summarize_spill_orders(spill_rows),
        "duplicate_evidence": duplicate_evidence,
        "safety": {
            "opened_read_only": True,
            "db_path_inside_repo": False,
            "db_path_inside_original_runtime_repo": False,
            "runs_etl": False,
            "runs_materialization": False,
            "writes_files": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only August traceability audit for July-package CSI spill rows.",
    )
    parser.add_argument("--db-path", type=Path, required=True, help="Existing DB path outside repo roots.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    try:
        audit = build_traceability_audit(args.db_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(audit, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
