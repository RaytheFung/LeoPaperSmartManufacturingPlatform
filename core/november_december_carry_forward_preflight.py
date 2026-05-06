"""Read-only November-to-December CSI carry-forward preflight helper."""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from core.csi_boundary_inventory import (
    CSI_CANONICAL_TIMESTAMP_COLUMNS,
    CSI_IDENTITY_COLUMNS,
    SOURCE_ROW_HASH_COLUMNS,
    canonical_csi_event_month,
    classify_boundary_direction,
)
from core.data_contracts import load_source_manifest
from core.runtime_paths import get_extended_raw_dataset_root
from core.source_manifest_discovery import month_label_to_key, month_key_to_label, resolve_manifest_month_sources


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"

SOURCE_PACKAGE_MONTH_KEY = "2025-11"
SOURCE_PACKAGE_MONTH = "November 2025"
TARGET_MONTH_KEY = "2025-12"
TARGET_MONTH = "December 2025"
STABLE_IDENTITY_FIELDS = [
    "machine_id",
    "start_time",
    "end_time",
    "prep_end_time",
    "order_id",
    "material",
    "good_qty",
]


def build_november_december_csi_carry_forward_preflight(
    *,
    source_package_month: str = SOURCE_PACKAGE_MONTH,
    target_month: str = TARGET_MONTH,
    data_root: str | Path | None = None,
    source_package_db_path: str | Path | None = None,
    current_package_db_path: str | Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build read-only November-to-December CSI carry-forward preflight evidence."""
    source_month_key = _normalize_supported_month(source_package_month, SOURCE_PACKAGE_MONTH_KEY, "source package")
    target_month_key = _normalize_supported_month(target_month, TARGET_MONTH_KEY, "target")
    root = Path(data_root) if data_root is not None else get_extended_raw_dataset_root()
    root = root.expanduser().resolve(strict=False)
    source_manifest = manifest if manifest is not None else load_source_manifest()

    source_df, source_path = _load_manifest_csi_dataframe(source_month_key, root, source_manifest)
    target_df, target_path = _load_manifest_csi_dataframe(target_month_key, root, source_manifest)
    candidate_rows = _build_candidate_rows(source_df, source_month_key, target_month_key)
    target_rows = _build_target_rows(target_df, target_month_key)

    candidate_keys = [_identity_key_from_candidate(row) for row in candidate_rows]
    candidate_key_counter = Counter(candidate_keys)
    target_rows_by_key = _index_rows_by_key(target_rows, _identity_key_from_candidate)
    workbook_overlap = _build_workbook_overlap_summary(candidate_rows, target_rows_by_key, len(target_rows))

    source_db_evidence = _build_source_db_evidence(candidate_rows, source_package_db_path)
    current_db_overlap = _build_current_db_overlap_summary(candidate_rows, current_package_db_path)
    duplicate_summary = _build_duplicate_identity_summary(candidate_key_counter)

    return {
        "source_package_month": SOURCE_PACKAGE_MONTH,
        "source_package_month_key": SOURCE_PACKAGE_MONTH_KEY,
        "target_month": TARGET_MONTH,
        "target_month_key": TARGET_MONTH_KEY,
        "data_root": str(root),
        "source_csi_file": str(source_path),
        "source_csi_file_relative": str(source_path.relative_to(root)),
        "target_csi_file": str(target_path),
        "target_csi_file_relative": str(target_path.relative_to(root)),
        "uses_manifest_source_discovery": True,
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "writes_db": False,
        "candidate_identity_fields": list(STABLE_IDENTITY_FIELDS),
        "candidate_identity_evidence": _build_candidate_identity_evidence(
            candidate_rows,
            source_df,
            candidate_key_counter,
        ),
        "source_row_hash_bronze_evidence": source_db_evidence,
        "current_december_overlap_check": {
            "workbook_level_overlap": workbook_overlap,
            "bronze_db_overlap": current_db_overlap,
            "strongest_available_evidence": (
                "bronze_db_overlap" if current_db_overlap["status"] != "not_checked" else "workbook_level_overlap"
            ),
        },
        "reconciliation_strategy": [
            "Treat November-package CSI rows whose canonical event month is December 2025 as previous-package carry-forward candidates.",
            "Preserve source_package_month=November 2025 separately from canonical_event_month=2025-12.",
            "Use source_row_hash from Bronze/raw evidence when available; otherwise require a reviewed stable-identity fallback before any temp execution.",
            "Reject any candidate that overlaps the current December package by source_row_hash or stable identity unless a reviewer-approved tie-breaker exists.",
            "Run any future reconciliation only against a temp DB outside Git and outside the original runtime repo.",
            "Do not change runtime source discovery, canonical predicates, materialization, DQ wiring, or Streamlit behavior in this preflight.",
        ],
        "duplicate_prevention_plan": [
            "Require zero duplicate stable identity groups in the November candidate set before automatic inclusion.",
            "Require zero current December overlap by stable identity for automatic inclusion.",
            "Before any temp insert, block duplicate source_row_hash in raw_csi_event and csi_job_event for December canonical scope.",
            "If source_row_hash cannot be proven, block duplicate stable identity and preserve the source workbook payload reference.",
            "After any future temp-only reconciliation, prove raw and silver traceability and duplicate source-hash groups.",
        ],
        "abort_criteria": [
            "November source package is unreadable or missing required CSI columns.",
            "December target package is unreadable or missing required CSI columns.",
            "Candidate count cannot be reproduced from source workbook evidence.",
            "Duplicate stable identity groups are nonzero.",
            "Current December package overlap is nonzero or ambiguous without an approved tie-breaker.",
            "Stable identity fields are missing.",
            "Source-row hash is unavailable and no safe fallback is approved.",
            "Any DB path is inside the GitHub-safe tree, inside the original runtime repo, missing, or not opened read-only.",
            "Any future step would run ETL, backfill, materialization, write a DB, promote a temp DB, or change runtime behavior.",
        ],
        "proof_gaps": _build_proof_gaps(source_db_evidence, current_db_overlap),
        "safety": {
            "opened_source_workbooks_read_only": True,
            "source_package_db_path": source_db_evidence.get("db_path"),
            "current_package_db_path": current_db_overlap.get("db_path"),
            "db_paths_opened_read_only": source_db_evidence.get("opened_read_only", False)
            or current_db_overlap.get("opened_read_only", False),
            "writes_files": False,
            "writes_db": False,
            "runs_etl": False,
            "runs_backfill": False,
            "runs_materialization": False,
            "changes_runtime_predicates": False,
            "changes_source_discovery_policy": False,
        },
    }


def _normalize_supported_month(value: str, expected_month_key: str, role: str) -> str:
    try:
        month_key = month_label_to_key(str(value or "").strip())
    except ValueError as exc:
        raise ValueError(f"Unsupported {role} month for B10.2: {value}") from exc
    if month_key != expected_month_key:
        raise ValueError(
            f"Only {month_key_to_label(expected_month_key)} is supported as the B10.2 {role} month."
        )
    return month_key


def _load_manifest_csi_dataframe(
    month_key: str,
    data_root: Path,
    manifest: dict[str, Any],
) -> tuple[pd.DataFrame, Path]:
    sources = resolve_manifest_month_sources(month_key, data_root=data_root, manifest=manifest)
    csi_file = sources.get("csi_file")
    if not csi_file:
        raise ValueError(f"No CSI source file is defined for {month_key_to_label(month_key)}.")
    csi_path = _validate_source_path(csi_file, data_root)
    read_kwargs: dict[str, Any] = {}
    if csi_path.suffix.lower() == ".xls":
        read_kwargs["engine"] = "xlrd"
    df = pd.read_excel(csi_path, **read_kwargs)
    _require_csi_columns(df)
    return df, csi_path


def _require_csi_columns(df: pd.DataFrame) -> None:
    required = [
        *CSI_CANONICAL_TIMESTAMP_COLUMNS.values(),
        *CSI_IDENTITY_COLUMNS.values(),
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError("CSI source is missing required preflight columns: " + ", ".join(missing))


def _build_candidate_rows(
    source_df: pd.DataFrame,
    source_month_key: str,
    target_month_key: str,
) -> list[dict[str, Any]]:
    rows = []
    for source_row in source_df.to_dict("records"):
        canonical_month = canonical_csi_event_month(source_row)
        if canonical_month != target_month_key:
            continue
        direction = classify_boundary_direction(source_month_key, canonical_month)
        if direction != "forward_spill_to_next_month":
            continue
        rows.append(_workbook_row_to_candidate(source_row, canonical_month, direction))
    return rows


def _build_target_rows(target_df: pd.DataFrame, target_month_key: str) -> list[dict[str, Any]]:
    rows = []
    for target_row in target_df.to_dict("records"):
        canonical_month = canonical_csi_event_month(target_row)
        if canonical_month == target_month_key:
            rows.append(_workbook_row_to_candidate(target_row, canonical_month, "same_month"))
    return rows


def _workbook_row_to_candidate(row: dict[str, Any], canonical_month: str | None, direction: str) -> dict[str, Any]:
    return {
        "machine_id": row.get(CSI_IDENTITY_COLUMNS["machine"]),
        "start_time": _stringify_timestamp(row.get(CSI_CANONICAL_TIMESTAMP_COLUMNS["start"])),
        "end_time": _stringify_timestamp(row.get(CSI_CANONICAL_TIMESTAMP_COLUMNS["end"])),
        "prep_end_time": _stringify_timestamp(row.get(CSI_CANONICAL_TIMESTAMP_COLUMNS["prep_end"])),
        "shift_date": _stringify_timestamp(row.get(CSI_CANONICAL_TIMESTAMP_COLUMNS["shift_date"])),
        "order_id": row.get(CSI_IDENTITY_COLUMNS["order"]),
        "material": row.get(CSI_IDENTITY_COLUMNS["material"]),
        "good_qty": row.get(CSI_IDENTITY_COLUMNS["good_qty"]),
        "canonical_month": canonical_month,
        "boundary_direction": direction,
    }


def _stringify_timestamp(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value).strip()
    return parsed.isoformat(sep=" ")


def _build_candidate_identity_evidence(
    candidate_rows: list[dict[str, Any]],
    source_df: pd.DataFrame,
    candidate_key_counter: Counter[tuple[str, ...]],
) -> dict[str, Any]:
    duplicate_summary = _build_duplicate_identity_summary(candidate_key_counter)
    timestamp_values = _candidate_timestamp_values(candidate_rows)
    source_hash_columns = [column for column in SOURCE_ROW_HASH_COLUMNS if column in source_df.columns]
    return {
        "candidate_count": len(candidate_rows),
        "expected_b10_1_candidate_count": 142,
        "candidate_count_matches_b10_1": len(candidate_rows) == 142,
        "distinct_machine_count": len({_normalize_key_value(row.get("machine_id")) for row in candidate_rows}),
        "distinct_order_count": len({_normalize_key_value(row.get("order_id")) for row in candidate_rows}),
        "good_qty_sum": _numeric_sum(candidate_rows, "good_qty"),
        "min_event_timestamp": min(timestamp_values).isoformat(sep=" ") if timestamp_values else None,
        "max_event_timestamp": max(timestamp_values).isoformat(sep=" ") if timestamp_values else None,
        "canonical_month_distribution": dict(Counter(str(row.get("canonical_month")) for row in candidate_rows)),
        "direction_distribution": dict(Counter(str(row.get("boundary_direction")) for row in candidate_rows)),
        "duplicate_stable_identity_group_count": duplicate_summary["group_count"],
        "duplicate_stable_identity_row_count": duplicate_summary["row_count"],
        "source_row_hash_available_directly_in_workbook": bool(source_hash_columns),
        "source_row_hash_workbook_columns": source_hash_columns,
        "identity_fields_present": {field: True for field in STABLE_IDENTITY_FIELDS},
    }


def _build_workbook_overlap_summary(
    candidate_rows: list[dict[str, Any]],
    target_rows_by_key: dict[tuple[str, ...], list[dict[str, Any]]],
    target_canonical_row_count: int,
) -> dict[str, Any]:
    overlap_candidate_count = 0
    overlap_row_count = 0
    for candidate in candidate_rows:
        matches = target_rows_by_key.get(_identity_key_from_candidate(candidate), [])
        if matches:
            overlap_candidate_count += 1
            overlap_row_count += len(matches)
    return {
        "status": "zero_overlap" if overlap_candidate_count == 0 else "overlap_found",
        "evidence_strength": "workbook_identity_only_less_strong_than_bronze",
        "target_package_canonical_row_count": target_canonical_row_count,
        "candidate_overlap_count": overlap_candidate_count,
        "overlap_row_count": overlap_row_count,
    }


def _build_source_db_evidence(
    candidate_rows: list[dict[str, Any]],
    source_package_db_path: str | Path | None,
) -> dict[str, Any]:
    if source_package_db_path is None:
        return {
            "status": "not_checked",
            "reason": "No source_package_db_path was provided for November Bronze/raw evidence.",
            "db_path": None,
            "opened_read_only": False,
            "source_row_hash_available": False,
            "raw_identity_matched_candidate_count": None,
            "raw_hash_matched_candidate_count": None,
            "raw_matched_row_count": None,
            "silver_matched_candidate_count": None,
            "distinct_source_row_hash_count": None,
        }
    resolved_db = _validate_db_path(Path(source_package_db_path))
    with _open_readonly(resolved_db) as conn:
        raw_rows = _fetch_raw_rows(conn, TARGET_MONTH_KEY) if _table_exists(conn, "raw_csi_event") else []
        silver_rows = _fetch_silver_rows(conn, TARGET_MONTH_KEY) if _table_exists(conn, "csi_job_event") else []
    evidence = _match_hash_evidence(candidate_rows, raw_rows, silver_rows)
    evidence.update(
        {
            "status": "checked",
            "db_path": str(resolved_db),
            "opened_read_only": True,
        }
    )
    return evidence


def _build_current_db_overlap_summary(
    candidate_rows: list[dict[str, Any]],
    current_package_db_path: str | Path | None,
) -> dict[str, Any]:
    if current_package_db_path is None:
        return {
            "status": "not_checked",
            "reason": "No current_package_db_path was provided for December Bronze/raw overlap evidence.",
            "db_path": None,
            "opened_read_only": False,
            "raw_overlap_candidate_count": None,
            "raw_overlap_row_count": None,
            "silver_overlap_candidate_count": None,
            "silver_overlap_row_count": None,
        }
    resolved_db = _validate_db_path(Path(current_package_db_path))
    with _open_readonly(resolved_db) as conn:
        raw_rows = _fetch_raw_rows(conn, TARGET_MONTH_KEY) if _table_exists(conn, "raw_csi_event") else []
        silver_rows = _fetch_silver_rows(conn, TARGET_MONTH_KEY) if _table_exists(conn, "csi_job_event") else []
    raw_by_key = _index_rows_by_key(raw_rows, _identity_key_from_raw)
    silver_by_key = _index_rows_by_key(silver_rows, _identity_key_from_silver)
    raw_overlap_candidate_count = 0
    raw_overlap_row_count = 0
    silver_overlap_candidate_count = 0
    silver_overlap_row_count = 0
    for candidate in candidate_rows:
        key = _identity_key_from_candidate(candidate)
        raw_matches = raw_by_key.get(key, [])
        silver_matches = silver_by_key.get(key, [])
        if raw_matches:
            raw_overlap_candidate_count += 1
            raw_overlap_row_count += len(raw_matches)
        if silver_matches:
            silver_overlap_candidate_count += 1
            silver_overlap_row_count += len(silver_matches)
    status = (
        "zero_overlap"
        if raw_overlap_candidate_count == 0 and silver_overlap_candidate_count == 0
        else "overlap_found"
    )
    return {
        "status": status,
        "db_path": str(resolved_db),
        "opened_read_only": True,
        "raw_overlap_candidate_count": raw_overlap_candidate_count,
        "raw_overlap_row_count": raw_overlap_row_count,
        "silver_overlap_candidate_count": silver_overlap_candidate_count,
        "silver_overlap_row_count": silver_overlap_row_count,
        "raw_target_month_row_count": len(raw_rows),
        "silver_target_month_row_count": len(silver_rows),
    }


def _match_hash_evidence(
    candidate_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    silver_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_by_key = _index_rows_by_key(raw_rows, _identity_key_from_raw)
    silver_by_hash = {
        str(row["source_row_hash"]): row for row in silver_rows if row.get("source_row_hash") is not None
    }
    silver_by_key = _index_rows_by_key(silver_rows, _identity_key_from_silver)
    raw_identity_matched_candidate_count = 0
    raw_hash_matched_candidate_count = 0
    raw_matched_row_count = 0
    silver_matched_candidate_count = 0
    matched_hashes: set[str] = set()

    for candidate in candidate_rows:
        key = _identity_key_from_candidate(candidate)
        raw_matches = raw_by_key.get(key, [])
        if raw_matches:
            raw_identity_matched_candidate_count += 1
            raw_matched_row_count += len(raw_matches)
        raw_hashes = [
            str(row["source_row_hash"]) for row in raw_matches if row.get("source_row_hash") is not None
        ]
        if raw_hashes:
            raw_hash_matched_candidate_count += 1
        matched_hashes.update(raw_hashes)
        if any(source_hash in silver_by_hash for source_hash in raw_hashes) or silver_by_key.get(key):
            silver_matched_candidate_count += 1

    candidate_count = len(candidate_rows)
    return {
        "source_row_hash_available": bool(candidate_count)
        and raw_hash_matched_candidate_count == candidate_count,
        "raw_identity_matched_candidate_count": raw_identity_matched_candidate_count,
        "raw_unmatched_candidate_count": candidate_count - raw_identity_matched_candidate_count,
        "raw_hash_matched_candidate_count": raw_hash_matched_candidate_count,
        "raw_matched_row_count": raw_matched_row_count,
        "silver_matched_candidate_count": silver_matched_candidate_count,
        "silver_unmatched_candidate_count": candidate_count - silver_matched_candidate_count,
        "distinct_source_row_hash_count": len(matched_hashes),
    }


def _fetch_raw_rows(conn: sqlite3.Connection, target_month_key: str) -> list[dict[str, Any]]:
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
        f"SELECT {', '.join(select_columns)} FROM raw_csi_event WHERE {canonical_expr} = ?",
        (target_month_key,),
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_silver_rows(conn: sqlite3.Connection, target_month_key: str) -> list[dict[str, Any]]:
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
        f"SELECT {', '.join(select_columns)} FROM csi_job_event WHERE {canonical_expr} = ?",
        (target_month_key,),
    ).fetchall()
    return [dict(row) for row in rows]


def _select_column(columns: set[str], column_name: str, alias: str | None = None) -> str:
    output_name = alias or column_name
    if column_name in columns:
        return f"{column_name} AS {output_name}"
    return f"NULL AS {output_name}"


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


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


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


def _validate_source_path(path_value: str, data_root: Path) -> Path:
    path = Path(path_value)
    resolved = path.expanduser().resolve(strict=False) if path.is_absolute() else (data_root / path).resolve(strict=False)
    root = data_root.expanduser().resolve(strict=False)
    if not _path_is_relative_to(resolved, root):
        raise ValueError(f"Resolved CSI source path escapes data_root: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"CSI source file not found: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"CSI source path is not a file: {resolved}")
    return resolved


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _identity_key_from_candidate(row: dict[str, Any]) -> tuple[str, ...]:
    return _identity_key(
        row.get("machine_id"),
        row.get("start_time"),
        row.get("end_time"),
        row.get("prep_end_time"),
        row.get("order_id"),
        row.get("material"),
        row.get("good_qty"),
    )


def _identity_key_from_raw(row: dict[str, Any]) -> tuple[str, ...]:
    return _identity_key(
        row.get("raw_machine_id_or_label"),
        row.get("raw_start_time"),
        row.get("raw_end_time"),
        row.get("raw_prep_end_time"),
        row.get("raw_order_id"),
        row.get("raw_material"),
        row.get("raw_good_qty"),
    )


def _identity_key_from_silver(row: dict[str, Any]) -> tuple[str, ...]:
    return _identity_key(
        row.get("raw_machine_id_or_label"),
        row.get("prod_start_ts"),
        row.get("prod_end_ts"),
        row.get("prep_end_ts"),
        row.get("order_id"),
        row.get("material_code"),
        row.get("good_qty"),
    )


def _identity_key(
    machine_id: object,
    start_time: object,
    end_time: object,
    prep_end_time: object,
    order_id: object,
    material: object,
    good_qty: object,
) -> tuple[str, ...]:
    return (
        _normalize_key_value(machine_id),
        _normalize_key_value(start_time),
        _normalize_key_value(end_time),
        _normalize_key_value(prep_end_time),
        _normalize_key_value(order_id),
        _normalize_key_value(material),
        _normalize_key_value(good_qty),
    )


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


def _index_rows_by_key(
    rows: list[dict[str, Any]],
    key_builder: Any,
) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    indexed: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        indexed[key_builder(row)].append(row)
    return indexed


def _build_duplicate_identity_summary(counter: Counter[tuple[str, ...]]) -> dict[str, int]:
    duplicate_counts = [count for count in counter.values() if count > 1]
    return {
        "group_count": len(duplicate_counts),
        "row_count": sum(duplicate_counts),
    }


def _candidate_timestamp_values(candidate_rows: list[dict[str, Any]]) -> list[pd.Timestamp]:
    values: list[pd.Timestamp] = []
    for row in candidate_rows:
        for field in ("start_time", "end_time", "prep_end_time", "shift_date"):
            value = row.get(field)
            if value is None:
                continue
            parsed = pd.to_datetime(value, errors="coerce")
            if not pd.isna(parsed):
                values.append(parsed)
    return values


def _numeric_sum(rows: list[dict[str, Any]], field_name: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(field_name)
        if value is None or pd.isna(value):
            continue
        total += float(value)
    return total


def _build_proof_gaps(source_db_evidence: dict[str, Any], current_db_overlap: dict[str, Any]) -> list[str]:
    gaps = [
        "No ETL, backfill, canonical materialization, or Gold aggregation has been run by this preflight.",
        "Carry-forward inclusion remains a plan only; no row has been inserted or promoted.",
    ]
    if source_db_evidence["status"] == "not_checked":
        gaps.append("November Bronze/raw source-row-hash evidence was not checked because no source DB path was provided.")
    elif not source_db_evidence.get("source_row_hash_available"):
        gaps.append("Not every candidate has source-row-hash evidence in the supplied November DB.")
    if current_db_overlap["status"] == "not_checked":
        gaps.append("Current December Bronze/raw overlap was not checked because no current DB path was provided.")
    gaps.append("Workbook-level December overlap is identity-only and weaker than Bronze/raw source-row-hash evidence.")
    return gaps


__all__ = ["build_november_december_csi_carry_forward_preflight"]
