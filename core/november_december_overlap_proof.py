"""Read-only November-to-December CSI Bronze/hash overlap proof."""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from core.november_december_carry_forward_preflight import (
    ORIGINAL_RUNTIME_REPO_ROOT,
    REPO_ROOT,
    SOURCE_PACKAGE_MONTH,
    SOURCE_PACKAGE_MONTH_KEY,
    TARGET_MONTH,
    TARGET_MONTH_KEY,
    _build_candidate_rows,
    _build_target_rows,
    _identity_key_from_candidate,
    _identity_key_from_raw,
    _identity_key_from_silver,
    _index_rows_by_key,
    _load_manifest_csi_dataframe,
    _normalize_key_value,
    _path_is_relative_to,
)
from core.data_contracts import load_source_manifest
from core.runtime_paths import get_extended_raw_dataset_root


OVERLAP_CLASS_TRUE_DUPLICATE = "true_duplicate_already_present"
OVERLAP_CLASS_DIFFERENT_HASH = "same_identity_but_different_provenance_hash"
OVERLAP_CLASS_NOT_PRESENT = "workbook_artifact_not_present_in_bronze"
OVERLAP_CLASS_UNRESOLVED = "unresolved"


def build_november_december_overlap_proof(
    *,
    db_path: str | Path,
    data_root: str | Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build read-only Bronze/hash proof for November-to-December CSI overlaps."""
    resolved_db = _validate_db_path(Path(db_path))
    root = Path(data_root) if data_root is not None else get_extended_raw_dataset_root()
    root = root.expanduser().resolve(strict=False)
    source_manifest = manifest if manifest is not None else load_source_manifest()

    source_df, source_path = _load_manifest_csi_dataframe(SOURCE_PACKAGE_MONTH_KEY, root, source_manifest)
    target_df, target_path = _load_manifest_csi_dataframe(TARGET_MONTH_KEY, root, source_manifest)
    candidates = _build_candidate_rows(source_df, SOURCE_PACKAGE_MONTH_KEY, TARGET_MONTH_KEY)
    target_rows = _build_target_rows(target_df, TARGET_MONTH_KEY)
    workbook_overlap_candidates = _find_workbook_overlap_candidates(candidates, target_rows)

    with _open_readonly(resolved_db) as conn:
        raw_rows = _fetch_raw_rows(conn, TARGET_MONTH_KEY) if _table_exists(conn, "raw_csi_event") else []
        silver_rows = _fetch_silver_rows(conn, TARGET_MONTH_KEY) if _table_exists(conn, "csi_job_event") else []
        table_status = {
            "raw_csi_event": _table_exists(conn, "raw_csi_event"),
            "csi_job_event": _table_exists(conn, "csi_job_event"),
        }

    source_relative = str(source_path.relative_to(root))
    target_relative = str(target_path.relative_to(root))
    raw_source_rows = [row for row in raw_rows if _source_file_matches(row.get("source_file"), source_relative)]
    raw_target_rows = [row for row in raw_rows if _source_file_matches(row.get("source_file"), target_relative)]
    silver_source_rows = [row for row in silver_rows if _source_file_matches(row.get("source_file"), source_relative)]
    silver_target_rows = [row for row in silver_rows if _source_file_matches(row.get("source_file"), target_relative)]

    indexes = {
        "raw_source": _index_rows_by_key(raw_source_rows, _identity_key_from_raw),
        "raw_target": _index_rows_by_key(raw_target_rows, _identity_key_from_raw),
        "silver_source": _index_rows_by_key(silver_source_rows, _identity_key_from_silver),
        "silver_target": _index_rows_by_key(silver_target_rows, _identity_key_from_silver),
    }

    all_candidate_classifications = [
        _classify_candidate(candidate, indexes) for candidate in candidates
    ]
    overlap_keys = {_identity_key_from_candidate(candidate) for candidate in workbook_overlap_candidates}
    seven_overlap_classifications = [
        classification
        for classification in all_candidate_classifications
        if tuple(classification["stable_identity_key"]) in overlap_keys
    ]
    include_skip_plan = _build_include_skip_plan(all_candidate_classifications)
    source_hash_evidence = _source_hash_evidence(all_candidate_classifications)

    return {
        "purpose": "November-to-December CSI Bronze/hash overlap proof and include/skip planning.",
        "db_evidence_source": {
            "db_path": str(resolved_db),
            "opened_read_only": True,
            "tables_available": table_status,
        },
        "source_package_month": SOURCE_PACKAGE_MONTH,
        "source_package_month_key": SOURCE_PACKAGE_MONTH_KEY,
        "target_month": TARGET_MONTH,
        "target_month_key": TARGET_MONTH_KEY,
        "data_root": str(root),
        "source_csi_file_relative": source_relative,
        "target_csi_file_relative": target_relative,
        "candidate_identity_reproduction": _candidate_reproduction(candidates),
        "workbook_level_overlap_reproduction": {
            "overlap_count": len(workbook_overlap_candidates),
            "expected_b10_2_overlap_count": 7,
            "overlap_count_matches_b10_2": len(workbook_overlap_candidates) == 7,
        },
        "bronze_raw_silver_overlap_proof": {
            "raw_december_canonical_row_count": len(raw_rows),
            "silver_december_canonical_row_count": len(silver_rows),
            "raw_source_package_candidate_scope_row_count": len(raw_source_rows),
            "raw_current_package_target_scope_row_count": len(raw_target_rows),
            "silver_source_package_candidate_scope_row_count": len(silver_source_rows),
            "silver_current_package_target_scope_row_count": len(silver_target_rows),
            "candidate_raw_source_hash_matched_count": sum(
                1 for item in all_candidate_classifications if item["source_hashes"]
            ),
            "candidate_raw_or_silver_target_identity_matched_count": sum(
                1 for item in all_candidate_classifications if item["target_identity_present"]
            ),
        },
        "seven_overlap_classification": {
            "classifications": seven_overlap_classifications,
            "summary": _classification_summary(seven_overlap_classifications),
        },
        "include_skip_unresolved_plan": include_skip_plan,
        "source_row_hash_evidence": source_hash_evidence,
        "b10_4_execution_safety_decision": _b10_4_safety_decision(include_skip_plan, source_hash_evidence),
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "writes_db": False,
        "changes_runtime_predicates": False,
        "changes_source_discovery_policy": False,
    }


def _find_workbook_overlap_candidates(
    candidates: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    target_by_key = _index_rows_by_key(target_rows, _identity_key_from_candidate)
    return [
        candidate
        for candidate in candidates
        if target_by_key.get(_identity_key_from_candidate(candidate))
    ]


def _classify_candidate(
    candidate: dict[str, Any],
    indexes: dict[str, dict[tuple[str, ...], list[dict[str, Any]]]],
) -> dict[str, Any]:
    key = _identity_key_from_candidate(candidate)
    raw_source_matches = indexes["raw_source"].get(key, [])
    raw_target_matches = indexes["raw_target"].get(key, [])
    silver_source_matches = indexes["silver_source"].get(key, [])
    silver_target_matches = indexes["silver_target"].get(key, [])
    source_hashes = _source_hashes([*raw_source_matches, *silver_source_matches])
    target_hashes = _source_hashes([*raw_target_matches, *silver_target_matches])
    target_identity_present = bool(raw_target_matches or silver_target_matches)

    if not target_identity_present:
        overlap_classification = OVERLAP_CLASS_NOT_PRESENT
        include_skip_decision = "include"
        reason = "Stable identity is not present in current December Bronze/Silver target-package scope."
    elif source_hashes and target_hashes and source_hashes.intersection(target_hashes):
        overlap_classification = OVERLAP_CLASS_TRUE_DUPLICATE
        include_skip_decision = "skip"
        reason = "Source-row hash already exists in current December target-package scope."
    elif source_hashes and target_hashes and not source_hashes.intersection(target_hashes):
        overlap_classification = OVERLAP_CLASS_DIFFERENT_HASH
        include_skip_decision = "block_unresolved"
        reason = "Stable identity exists in December target-package scope with different source-row hash."
    else:
        overlap_classification = OVERLAP_CLASS_UNRESOLVED
        include_skip_decision = "block_unresolved"
        reason = "Stable identity exists in December target-package scope but source-row-hash comparison is incomplete."

    return {
        "stable_identity_key": list(key),
        "machine_id": _json_clean_value(candidate.get("machine_id")),
        "order_id": _json_clean_value(candidate.get("order_id")),
        "material": _json_clean_value(candidate.get("material")),
        "good_qty": _json_clean_value(candidate.get("good_qty")),
        "source_hashes": sorted(source_hashes),
        "target_hashes": sorted(target_hashes),
        "raw_source_match_count": len(raw_source_matches),
        "raw_target_match_count": len(raw_target_matches),
        "silver_source_match_count": len(silver_source_matches),
        "silver_target_match_count": len(silver_target_matches),
        "target_identity_present": target_identity_present,
        "classification": overlap_classification,
        "include_skip_decision": include_skip_decision,
        "reason": reason,
    }


def _source_hashes(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["source_row_hash"])
        for row in rows
        if row.get("source_row_hash") is not None and str(row["source_row_hash"]).strip()
    }


def _candidate_reproduction(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(candidates),
        "expected_b10_2_candidate_count": 142,
        "candidate_count_matches_b10_2": len(candidates) == 142,
        "distinct_machine_count": len({_normalize_key_value(row.get("machine_id")) for row in candidates}),
        "distinct_order_count": len({_normalize_key_value(row.get("order_id")) for row in candidates}),
        "good_qty_sum": _numeric_sum(candidates, "good_qty"),
        "duplicate_stable_identity_group_count": _duplicate_identity_group_count(candidates),
    }


def _build_include_skip_plan(classifications: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(item["include_skip_decision"] for item in classifications)
    classification_counts = Counter(item["classification"] for item in classifications)
    return {
        "include_count": decision_counts.get("include", 0),
        "skip_count": decision_counts.get("skip", 0),
        "unresolved_count": decision_counts.get("block_unresolved", 0),
        "classification_counts": dict(sorted(classification_counts.items())),
        "total_candidate_count": len(classifications),
    }


def _source_hash_evidence(classifications: list[dict[str, Any]]) -> dict[str, Any]:
    source_hash_matched = [item for item in classifications if item["source_hashes"]]
    target_hash_matched = [item for item in classifications if item["target_hashes"]]
    return {
        "candidate_source_hash_matched_count": len(source_hash_matched),
        "candidate_source_hash_unmatched_count": len(classifications) - len(source_hash_matched),
        "target_hash_matched_candidate_count": len(target_hash_matched),
        "source_row_hash_available_for_all_candidates": len(source_hash_matched) == len(classifications),
    }


def _b10_4_safety_decision(
    include_skip_plan: dict[str, Any],
    source_hash_evidence: dict[str, Any],
) -> dict[str, Any]:
    unresolved_count = include_skip_plan["unresolved_count"]
    if unresolved_count:
        return {
            "safe_for_b10_4_temp_reconciliation": False,
            "reason": f"{unresolved_count} candidate identities remain unresolved or ambiguous.",
        }
    unmatched_hash_count = source_hash_evidence["candidate_source_hash_unmatched_count"]
    if unmatched_hash_count:
        return {
            "safe_for_b10_4_temp_reconciliation": False,
            "reason": (
                f"{unmatched_hash_count} candidate identities do not yet have source-row-hash evidence; "
                "a reviewed fallback or source-hash proof is required before execution."
            ),
        }
    return {
        "safe_for_b10_4_temp_reconciliation": True,
        "reason": "All candidates are classified as include or true-duplicate skip by Bronze/hash evidence.",
    }


def _classification_summary(classifications: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(item["classification"] for item in classifications).items()))


def _duplicate_identity_group_count(candidates: list[dict[str, Any]]) -> int:
    counts = Counter(_identity_key_from_candidate(row) for row in candidates)
    return sum(1 for count in counts.values() if count > 1)


def _numeric_sum(rows: list[dict[str, Any]], field_name: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(field_name)
        if value is None:
            continue
        numeric_value = float(value)
        if numeric_value != numeric_value:
            continue
        total += numeric_value
    return total


def _json_clean_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


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
        _select_column(columns, "source_file"),
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


def _source_file_matches(source_file: object, expected_relative_path: str) -> bool:
    if source_file is None:
        return False
    source_text = str(source_file).replace("\\", "/")
    expected_text = expected_relative_path.replace("\\", "/")
    return source_text.endswith(expected_text) or Path(source_text).name == Path(expected_text).name


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


__all__ = ["build_november_december_overlap_proof"]
