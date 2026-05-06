"""Read-only CSI boundary-month carry-forward preflight helper."""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"

TARGET_MONTH = "August 2025"
TARGET_MONTH_KEY = "2025-08"
PREVIOUS_PACKAGE_MONTH = "July 2025"

ETL_CSI_CANONICAL_MONTH_EXPR = (
    "COALESCE("
    "substr(start_time, 1, 7), "
    "substr(end_time, 1, 7), "
    "substr(setup_end, 1, 7)"
    ")"
)
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

CANDIDATE_IDENTITY_FIELDS = [
    "machine_id",
    "start_time",
    "end_time",
    "prep_end_time",
    "order_id",
    "material",
    "good_qty",
]


def build_csi_carry_forward_preflight(
    target_month: str = TARGET_MONTH,
    db_path: str | Path | None = None,
    current_package_db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build read-only carry-forward evidence for boundary-month CSI rows.

    `db_path` is the previous-package evidence DB. For Stage B9.1 this helper
    intentionally supports August 2025 only and requires an explicit DB path
    outside both LeoPaper repo roots.
    """
    normalized_target_month = str(target_month or "").strip()
    if normalized_target_month != TARGET_MONTH:
        raise ValueError("Only August 2025 is supported by the Stage B9.1 preflight helper.")
    if db_path is None:
        raise ValueError("db_path is required and must point to an existing temp DB outside repo roots.")

    resolved_candidate_db = _validate_db_path(Path(db_path))
    resolved_current_db = _validate_db_path(Path(current_package_db_path)) if current_package_db_path else None

    with _open_readonly(resolved_candidate_db) as conn:
        _require_table(conn, "etl_csi_data")
        candidate_rows = _fetch_candidate_rows(conn)
        previous_raw_rows = _fetch_raw_rows(conn) if _table_exists(conn, "raw_csi_event") else []
        previous_silver_rows = _fetch_silver_rows(conn) if _table_exists(conn, "csi_job_event") else []

    if resolved_current_db is not None:
        with _open_readonly(resolved_current_db) as conn:
            current_raw_rows = _fetch_raw_rows(conn) if _table_exists(conn, "raw_csi_event") else []
            current_silver_rows = _fetch_silver_rows(conn) if _table_exists(conn, "csi_job_event") else []
    else:
        current_raw_rows = []
        current_silver_rows = []

    candidate_keys = [_candidate_key(row) for row in candidate_rows]
    candidate_key_counter = Counter(candidate_keys)
    previous_hash_evidence = _build_source_hash_evidence(candidate_rows, previous_raw_rows, previous_silver_rows)
    overlap_summary = _build_current_overlap_summary(
        candidate_rows,
        current_raw_rows,
        current_silver_rows,
        current_package_db_path=resolved_current_db,
    )
    candidate_count = len(candidate_rows)

    return {
        "target_month": TARGET_MONTH,
        "previous_package_month": PREVIOUS_PACKAGE_MONTH,
        "canonical_month_key": TARGET_MONTH_KEY,
        "current_policy": (
            "Keep first-available timestamp CSI canonical month semantics; do not silently exclude "
            "previous-package rows whose event timestamp canonicalizes to the target month."
        ),
        "carry_forward_required": candidate_count > 0,
        "candidate_count": candidate_count,
        "candidate_identity_fields": list(CANDIDATE_IDENTITY_FIELDS),
        "source_row_hash_available": previous_hash_evidence["all_candidates_have_raw_source_row_hash"],
        "duplicate_risk_summary": _build_duplicate_risk_summary(
            candidate_count,
            candidate_key_counter,
            overlap_summary,
            previous_hash_evidence,
        ),
        "current_package_overlap_summary": overlap_summary,
        "reconciliation_strategy": [
            "Treat previous-package candidate identities as target-month canonical CSI candidates.",
            "Match by source_row_hash when available after raw identity matching.",
            "Fall back to the stable composite CSI identity when source_row_hash is not present on the candidate surface.",
            "Do not insert, upsert, or materialize rows in this preflight stage.",
        ],
        "planned_inclusion_stage": "Stage B9.2 temp-only carry-forward rehearsal, if approved.",
        "planned_duplicate_prevention": [
            "Reject candidate identities already present in current-package raw or silver target-month scope.",
            "Reject duplicate candidate composite identities unless an explicit source_row_hash tie-breaker is available.",
            "Require zero duplicate source_row_hash groups after any future temp-only carry-forward run.",
        ],
        "planned_post_run_evidence": [
            "candidate identities included by source package and canonical month",
            "raw and silver source_row_hash match counts",
            "current-package overlap and duplicate identity counts",
            "raw_csi_event and csi_job_event duplicate source_row_hash group counts",
            "Gold fact_machine_hour delta with and without carry-forward",
            "proof that only a temp DB outside Git was written",
        ],
        "abort_criteria": [
            "db_path is missing, repo-local, original-runtime-local, or not an existing file.",
            "target month is not August 2025 for this narrow Stage B9.1 helper.",
            "required ETL CSI staging table is unavailable.",
            "candidate identity fields are insufficient for duplicate prevention.",
            "current-package overlap is non-zero and no approved tie-breaker exists.",
            "future execution would write a live DB, repo DB, raw workbook, etl_outputs, or model artifact.",
        ],
        "proof_gaps": _build_proof_gaps(resolved_current_db, previous_hash_evidence),
        "candidate_identity_summary": _build_candidate_identity_summary(candidate_rows),
        "source_row_hash_evidence": previous_hash_evidence,
        "safety": {
            "candidate_db_path": str(resolved_candidate_db),
            "current_package_db_path": str(resolved_current_db) if resolved_current_db else None,
            "opened_read_only": True,
            "writes_files": False,
            "runs_etl": False,
            "runs_backfill": False,
            "runs_materialization": False,
            "changes_runtime_predicates": False,
            "changes_source_discovery_policy": False,
        },
    }


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_db_path(db_path: Path) -> Path:
    resolved = db_path.expanduser().resolve()
    if _path_is_relative_to(resolved, REPO_ROOT.resolve()):
        raise ValueError(f"Refusing DB path inside repo: {resolved}")
    if _path_is_relative_to(resolved, ORIGINAL_RUNTIME_REPO_ROOT.resolve()):
        raise ValueError(f"Refusing DB path inside original runtime repo: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"DB path does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"DB path is not a file: {resolved}")
    return resolved


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _require_table(conn: sqlite3.Connection, table_name: str) -> None:
    if not _table_exists(conn, table_name):
        raise ValueError(f"DB is missing required table: {table_name}")


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _select_column(columns: set[str], column_name: str, alias: str | None = None) -> str:
    output_name = alias or column_name
    if column_name in columns:
        return f"{column_name} AS {output_name}"
    return f"NULL AS {output_name}"


def _fetch_candidate_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = _table_columns(conn, "etl_csi_data")
    canonical_expr = _coalesce_month_expr(
        columns,
        ["start_time", "end_time", "setup_end"],
    )
    select_columns = [
        _select_column(columns, "id"),
        _select_column(columns, "machine_id"),
        _select_column(columns, "start_time"),
        _select_column(columns, "end_time"),
        _select_column(columns, "setup_end", "prep_end_time"),
        _select_column(columns, "order_id"),
        _select_column(columns, "material"),
        _select_column(columns, "good_qty"),
        f"{canonical_expr} AS canonical_month",
    ]
    rows = conn.execute(
        f"""
        SELECT {", ".join(select_columns)}
        FROM etl_csi_data
        WHERE month_year = ?
          AND {canonical_expr} = ?
        """,
        (PREVIOUS_PACKAGE_MONTH, TARGET_MONTH_KEY),
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_raw_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = _table_columns(conn, "raw_csi_event")
    canonical_expr = _coalesce_month_expr(
        columns,
        ["raw_start_time", "raw_end_time", "raw_prep_end_time"],
        json_payload_paths=[("raw_payload_json", "$.班次內日期")],
    )
    select_columns = [
        _select_column(columns, "source_row_hash"),
        _select_column(columns, "source_file"),
        _select_column(columns, "raw_machine_id_or_label"),
        _select_column(columns, "raw_start_time"),
        _select_column(columns, "raw_end_time"),
        _select_column(columns, "raw_prep_end_time"),
        _select_column(columns, "raw_order_id"),
        _select_column(columns, "raw_material"),
        _select_column(columns, "raw_good_qty"),
    ]
    rows = conn.execute(
        f"""
        SELECT {", ".join(select_columns)}
        FROM raw_csi_event
        WHERE {canonical_expr} = ?
        """,
        (TARGET_MONTH_KEY,),
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_silver_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = _table_columns(conn, "csi_job_event")
    canonical_expr = _coalesce_month_expr(
        columns,
        ["prod_start_ts", "prod_end_ts", "prep_end_ts", "shift_date"],
    )
    select_columns = [
        _select_column(columns, "source_row_hash"),
        _select_column(columns, "raw_machine_id_or_label"),
        _select_column(columns, "prod_start_ts"),
        _select_column(columns, "prod_end_ts"),
        _select_column(columns, "prep_end_ts"),
        _select_column(columns, "order_id"),
        _select_column(columns, "material_code"),
        _select_column(columns, "good_qty"),
    ]
    rows = conn.execute(
        f"""
        SELECT {", ".join(select_columns)}
        FROM csi_job_event
        WHERE {canonical_expr} = ?
        """,
        (TARGET_MONTH_KEY,),
    ).fetchall()
    return [dict(row) for row in rows]


def _coalesce_month_expr(
    columns: set[str],
    timestamp_columns: list[str],
    json_payload_paths: list[tuple[str, str]] | None = None,
) -> str:
    parts = [f"substr({column}, 1, 7)" for column in timestamp_columns if column in columns]
    for column, json_path in json_payload_paths or []:
        if column in columns:
            parts.append(f"substr(json_extract({column}, '{json_path}'), 1, 7)")
    if not parts:
        return "NULL"
    if len(parts) == 1:
        return parts[0]
    return "COALESCE(" + ", ".join(parts) + ")"


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


def _identity_key(
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


def _candidate_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return _identity_key(
        machine_id=row.get("machine_id"),
        start_time=row.get("start_time"),
        end_time=row.get("end_time"),
        prep_end_time=row.get("prep_end_time"),
        order_id=row.get("order_id"),
        material=row.get("material"),
        good_qty=row.get("good_qty"),
    )


def _raw_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return _identity_key(
        machine_id=row.get("raw_machine_id_or_label"),
        start_time=row.get("raw_start_time"),
        end_time=row.get("raw_end_time"),
        prep_end_time=row.get("raw_prep_end_time"),
        order_id=row.get("raw_order_id"),
        material=row.get("raw_material"),
        good_qty=row.get("raw_good_qty"),
    )


def _silver_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return _identity_key(
        machine_id=row.get("raw_machine_id_or_label"),
        start_time=row.get("prod_start_ts"),
        end_time=row.get("prod_end_ts"),
        prep_end_time=row.get("prep_end_ts"),
        order_id=row.get("order_id"),
        material=row.get("material_code"),
        good_qty=row.get("good_qty"),
    )


def _index_rows_by_key(
    rows: list[dict[str, Any]], key_builder: Any
) -> dict[tuple[str, str, str, str, str, str, str], list[dict[str, Any]]]:
    indexed: dict[tuple[str, str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        indexed[key_builder(row)].append(row)
    return indexed


def _build_source_hash_evidence(
    candidate_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    silver_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_by_key = _index_rows_by_key(raw_rows, _raw_key)
    silver_by_hash = {
        str(row["source_row_hash"]): row
        for row in silver_rows
        if row.get("source_row_hash") is not None
    }
    silver_by_key = _index_rows_by_key(silver_rows, _silver_key)

    raw_matched_candidate_count = 0
    raw_hash_matched_candidate_count = 0
    raw_matched_row_count = 0
    silver_matched_candidate_count = 0
    matched_hashes: set[str] = set()
    source_file_counter: Counter[str] = Counter()

    for candidate in candidate_rows:
        key = _candidate_key(candidate)
        raw_matches = raw_by_key.get(key, [])
        if raw_matches:
            raw_matched_candidate_count += 1
            raw_matched_row_count += len(raw_matches)
        raw_hashes = [
            str(row["source_row_hash"])
            for row in raw_matches
            if row.get("source_row_hash") is not None
        ]
        if raw_hashes:
            raw_hash_matched_candidate_count += 1
        matched_hashes.update(raw_hashes)
        for raw_row in raw_matches:
            if raw_row.get("source_file"):
                source_file_counter[str(raw_row["source_file"])] += 1

        if any(source_hash in silver_by_hash for source_hash in raw_hashes) or silver_by_key.get(key):
            silver_matched_candidate_count += 1

    candidate_count = len(candidate_rows)
    return {
        "previous_package_raw_identity_matched_candidate_count": raw_matched_candidate_count,
        "previous_package_raw_unmatched_candidate_count": candidate_count - raw_matched_candidate_count,
        "previous_package_raw_hash_matched_candidate_count": raw_hash_matched_candidate_count,
        "previous_package_raw_matched_row_count": raw_matched_row_count,
        "previous_package_silver_matched_candidate_count": silver_matched_candidate_count,
        "previous_package_silver_unmatched_candidate_count": candidate_count - silver_matched_candidate_count,
        "distinct_source_row_hash_count": len(matched_hashes),
        "all_candidates_have_raw_source_row_hash": bool(candidate_count)
        and raw_hash_matched_candidate_count == candidate_count,
        "raw_source_files_for_matches": [
            {"source_file": source_file, "matched_raw_row_count": count}
            for source_file, count in source_file_counter.most_common()
        ],
    }


def _build_current_overlap_summary(
    candidate_rows: list[dict[str, Any]],
    current_raw_rows: list[dict[str, Any]],
    current_silver_rows: list[dict[str, Any]],
    *,
    current_package_db_path: Path | None,
) -> dict[str, Any]:
    if current_package_db_path is None:
        return {
            "status": "not_checked",
            "reason": "No current_package_db_path was provided.",
            "current_package_db_path": None,
            "raw_overlap_candidate_count": None,
            "silver_overlap_candidate_count": None,
            "raw_overlap_row_count": None,
            "silver_overlap_row_count": None,
        }

    raw_by_key = _index_rows_by_key(current_raw_rows, _raw_key)
    silver_by_key = _index_rows_by_key(current_silver_rows, _silver_key)
    raw_overlap_candidate_count = 0
    silver_overlap_candidate_count = 0
    raw_overlap_row_count = 0
    silver_overlap_row_count = 0

    for candidate in candidate_rows:
        key = _candidate_key(candidate)
        raw_matches = raw_by_key.get(key, [])
        silver_matches = silver_by_key.get(key, [])
        if raw_matches:
            raw_overlap_candidate_count += 1
            raw_overlap_row_count += len(raw_matches)
        if silver_matches:
            silver_overlap_candidate_count += 1
            silver_overlap_row_count += len(silver_matches)

    status = "zero_overlap" if raw_overlap_candidate_count == 0 and silver_overlap_candidate_count == 0 else "overlap_found"
    return {
        "status": status,
        "current_package_db_path": str(current_package_db_path),
        "raw_overlap_candidate_count": raw_overlap_candidate_count,
        "silver_overlap_candidate_count": silver_overlap_candidate_count,
        "raw_overlap_row_count": raw_overlap_row_count,
        "silver_overlap_row_count": silver_overlap_row_count,
        "current_raw_target_month_row_count": len(current_raw_rows),
        "current_silver_target_month_row_count": len(current_silver_rows),
    }


def _numeric_sum(rows: list[dict[str, Any]], field_name: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(field_name)
        if value is None:
            continue
        total += float(value)
    return total


def _build_candidate_identity_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    machine_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    order_rows: dict[tuple[object, object], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        machine_rows[str(row.get("machine_id") or "")].append(row)
        order_rows[(row.get("machine_id"), row.get("order_id"))].append(row)

    machine_summary = []
    for machine_id, grouped_rows in machine_rows.items():
        machine_summary.append(
            {
                "machine_id": machine_id,
                "row_count": len(grouped_rows),
                "distinct_order_count": len({row.get("order_id") for row in grouped_rows}),
                "good_qty_sum": _numeric_sum(grouped_rows, "good_qty"),
            }
        )
    machine_summary.sort(key=lambda item: (item["good_qty_sum"], item["row_count"]), reverse=True)

    order_summary = []
    for (machine_id, order_id), grouped_rows in order_rows.items():
        order_summary.append(
            {
                "machine_id": machine_id,
                "order_id": order_id,
                "row_count": len(grouped_rows),
                "good_qty_sum": _numeric_sum(grouped_rows, "good_qty"),
            }
        )
    order_summary.sort(key=lambda item: (item["good_qty_sum"], item["row_count"]), reverse=True)

    return {
        "canonical_months": dict(Counter(str(row.get("canonical_month")) for row in rows)),
        "distinct_machine_count": len({row.get("machine_id") for row in rows}),
        "distinct_order_count": len({row.get("order_id") for row in rows}),
        "good_qty_sum": _numeric_sum(rows, "good_qty"),
        "min_start_time": min([str(row.get("start_time")) for row in rows if row.get("start_time")], default=None),
        "max_end_time": max([str(row.get("end_time")) for row in rows if row.get("end_time")], default=None),
        "machine_summary_top_10_by_good_qty": machine_summary[:10],
        "order_summary_top_10_by_good_qty": order_summary[:10],
    }


def _build_duplicate_risk_summary(
    candidate_count: int,
    candidate_key_counter: Counter[tuple[str, str, str, str, str, str, str]],
    overlap_summary: dict[str, Any],
    source_hash_evidence: dict[str, Any],
) -> dict[str, Any]:
    duplicate_candidate_groups = sum(1 for count in candidate_key_counter.values() if count > 1)
    duplicate_candidate_rows = sum(count for count in candidate_key_counter.values() if count > 1)
    return {
        "candidate_duplicate_identity_group_count": duplicate_candidate_groups,
        "candidate_duplicate_identity_row_count": duplicate_candidate_rows,
        "current_raw_overlap_candidate_count": overlap_summary.get("raw_overlap_candidate_count"),
        "current_silver_overlap_candidate_count": overlap_summary.get("silver_overlap_candidate_count"),
        "source_row_hash_distinct_count": source_hash_evidence["distinct_source_row_hash_count"],
        "duplicate_prevention_required": candidate_count > 0,
        "risk_level": _duplicate_risk_level(duplicate_candidate_groups, overlap_summary),
    }


def _duplicate_risk_level(duplicate_candidate_groups: int, overlap_summary: dict[str, Any]) -> str:
    raw_overlap = overlap_summary.get("raw_overlap_candidate_count")
    silver_overlap = overlap_summary.get("silver_overlap_candidate_count")
    if duplicate_candidate_groups or (raw_overlap and raw_overlap > 0) or (silver_overlap and silver_overlap > 0):
        return "requires_blocking_review"
    if raw_overlap == 0 and silver_overlap == 0:
        return "controlled_zero_overlap_in_current_package"
    return "unknown_until_current_package_overlap_is_checked"


def _build_proof_gaps(current_db_path: Path | None, source_hash_evidence: dict[str, Any]) -> list[str]:
    gaps = [
        "No ETL, backfill, canonical materialization, or Gold aggregation has been run by this preflight.",
        "Carry-forward inclusion remains a plan only; no row has been inserted or promoted.",
    ]
    if current_db_path is None:
        gaps.append("Current August package overlap was not checked because current_package_db_path was not provided.")
    if not source_hash_evidence["all_candidates_have_raw_source_row_hash"]:
        gaps.append("Not every candidate has proven raw source_row_hash evidence in the provided previous-package DB.")
    gaps.append("Future B9.2 must prove duplicate source_row_hash groups remain zero after any temp-only carry-forward run.")
    return gaps
