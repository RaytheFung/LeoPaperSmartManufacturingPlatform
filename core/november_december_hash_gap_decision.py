"""Read-only November-to-December source-hash gap decision helper."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from core.data_contracts import load_source_manifest
from core.november_december_carry_forward_preflight import (
    SOURCE_PACKAGE_MONTH,
    SOURCE_PACKAGE_MONTH_KEY,
    TARGET_MONTH,
    TARGET_MONTH_KEY,
    _build_candidate_rows,
    _identity_key_from_candidate,
    _load_manifest_csi_dataframe,
    _normalize_key_value,
)
from core.november_december_overlap_proof import (
    _classify_candidate,
    _fetch_silver_rows,
    _coalesce_month_expr,
    _index_rows_by_key,
    _open_readonly,
    _select_column,
    _source_file_matches,
    _table_columns,
    _table_exists,
    _validate_db_path,
)
from core.runtime_paths import get_extended_raw_dataset_root


HASH_RESOLVED = "hash_resolved"
STABLE_IDENTITY_FALLBACK_SAFE = "stable_identity_fallback_safe"
SKIP_DUE_EXISTING_DUPLICATE = "skip_due_existing_duplicate"
BLOCK_UNRESOLVED = "block_unresolved"


def build_november_december_hash_gap_decision(
    *,
    db_path: str | Path,
    data_root: str | Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve or decide fallback handling for November-to-December hash gaps."""
    resolved_db = _validate_db_path(Path(db_path))
    root = Path(data_root) if data_root is not None else get_extended_raw_dataset_root()
    root = root.expanduser().resolve(strict=False)
    source_manifest = manifest if manifest is not None else load_source_manifest()

    source_df, source_path = _load_manifest_csi_dataframe(SOURCE_PACKAGE_MONTH_KEY, root, source_manifest)
    target_df, target_path = _load_manifest_csi_dataframe(TARGET_MONTH_KEY, root, source_manifest)
    candidates = _build_candidate_rows(source_df, SOURCE_PACKAGE_MONTH_KEY, TARGET_MONTH_KEY)

    with _open_readonly(resolved_db) as conn:
        raw_rows = _fetch_raw_rows_with_payload(conn, TARGET_MONTH_KEY) if _table_exists(conn, "raw_csi_event") else []
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

    exact_indexes = {
        "raw_source": _index_rows_by_key(raw_source_rows, _identity_key_from_raw_exact),
        "raw_target": _index_rows_by_key(raw_target_rows, _identity_key_from_raw_exact),
        "silver_source": _index_rows_by_key(silver_source_rows, _identity_key_from_silver_exact),
        "silver_target": _index_rows_by_key(silver_target_rows, _identity_key_from_silver_exact),
    }
    exact_classifications = [_classify_candidate(candidate, exact_indexes) for candidate in candidates]
    hash_gap_candidates = [
        candidate
        for candidate, classification in zip(candidates, exact_classifications)
        if not classification["source_hashes"]
    ]

    alternative_indexes = {
        "raw_source": _index_rows_by_key(raw_source_rows, _identity_key_from_raw_relaxed),
        "raw_target": _index_rows_by_key(raw_target_rows, _identity_key_from_raw_relaxed),
        "silver_source": _index_rows_by_key(silver_source_rows, _identity_key_from_silver_relaxed),
        "silver_target": _index_rows_by_key(silver_target_rows, _identity_key_from_silver_relaxed),
    }
    gap_decisions = [
        _decide_hash_gap(candidate, alternative_indexes)
        for candidate in hash_gap_candidates
    ]
    decision_summary = _decision_summary(gap_decisions)

    return {
        "purpose": "November-to-December source-hash gap resolution and fallback decision.",
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
        "candidate_count": len(candidates),
        "source_hash_gap_reproduction": {
            "source_hash_gap_count": len(hash_gap_candidates),
            "expected_b10_3_gap_count": 15,
            "gap_count_matches_b10_3": len(hash_gap_candidates) == 15,
        },
        "hash_gap_candidates": gap_decisions,
        "root_cause_classification": dict(sorted(Counter(item["root_cause"] for item in gap_decisions).items())),
        "alternative_matching_attempts": {
            "null_equivalent_identity_hash_resolved_count": decision_summary[HASH_RESOLVED],
            "stable_identity_fallback_safe_count": decision_summary[STABLE_IDENTITY_FALLBACK_SAFE],
            "skip_due_existing_duplicate_count": decision_summary[SKIP_DUE_EXISTING_DUPLICATE],
            "block_unresolved_count": decision_summary[BLOCK_UNRESOLVED],
            "timestamp_normalization": "parsed timestamps normalized to second precision for identity comparison",
            "string_normalization": "trimmed strings and treated workbook NaN as database NULL",
            "raw_payload_fingerprint": (
                "computed from matched raw_payload_json when present; used as supporting evidence only, "
                "not as a fabricated source_row_hash"
            ),
        },
        "fallback_policy_decision": _fallback_policy_decision(decision_summary),
        "include_skip_block_plan": {
            "hash_proven_include_count": len(candidates) - len(hash_gap_candidates),
            "hash_resolved_include_count": decision_summary[HASH_RESOLVED],
            "stable_identity_fallback_include_count": decision_summary[STABLE_IDENTITY_FALLBACK_SAFE],
            "skip_count": decision_summary[SKIP_DUE_EXISTING_DUPLICATE],
            "block_count": decision_summary[BLOCK_UNRESOLVED],
            "total_candidate_count": len(candidates),
        },
        "b10_5_execution_safety_decision": _b10_5_safety_decision(decision_summary),
        "duplicate_prevention_requirements": _duplicate_prevention_requirements(decision_summary),
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "writes_db": False,
        "changes_runtime_predicates": False,
        "changes_source_discovery_policy": False,
    }


def normalize_timestamp_for_gap_match(value: object) -> str:
    """Normalize timestamps deterministically for B10.4 identity matching."""
    if value is None or pd.isna(value):
        return ""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value).strip()
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _decide_hash_gap(
    candidate: dict[str, Any],
    indexes: dict[str, dict[tuple[str, ...], list[dict[str, Any]]]],
) -> dict[str, Any]:
    relaxed_key = _identity_key_from_candidate_relaxed(candidate)
    source_matches = [
        *indexes["raw_source"].get(relaxed_key, []),
        *indexes["silver_source"].get(relaxed_key, []),
    ]
    target_matches = [
        *indexes["raw_target"].get(relaxed_key, []),
        *indexes["silver_target"].get(relaxed_key, []),
    ]
    source_hashes = _source_hashes(source_matches)
    target_hashes = _source_hashes(target_matches)
    source_payload_fingerprints = _raw_payload_fingerprints(source_matches)
    target_payload_fingerprints = _raw_payload_fingerprints(target_matches)

    if source_hashes:
        classification = HASH_RESOLVED
        root_cause = "null_material_good_qty_normalization_mismatch"
        matching_failure = "transformed_or_normalized_differently"
        fallback = "none_required"
        reason = "Relaxed matching treats workbook NaN material/good_qty as database NULL and recovers source_row_hash."
    elif target_hashes:
        classification = SKIP_DUE_EXISTING_DUPLICATE
        root_cause = "existing_target_duplicate_after_null_equivalent_matching"
        matching_failure = "not_present_in_source_package_bronze_as_unique_include_candidate"
        fallback = "skip"
        reason = "Candidate identity already has target-scope source-row-hash evidence."
    elif _is_stable_maintenance_null_quantity_candidate(candidate) and not target_matches:
        classification = STABLE_IDENTITY_FALLBACK_SAFE
        root_cause = "source_package_row_not_ingested_maintenance_null_quantity"
        matching_failure = "source_package_row_not_ingested"
        fallback = "machine_start_end_order_null_quantity_identity"
        reason = (
            "Maintenance/null-quantity workbook row is absent from November and December Bronze/Silver; "
            "fallback is limited to exact machine/start/end/order with NULL material and good_qty."
        )
    else:
        classification = BLOCK_UNRESOLVED
        root_cause = "ambiguous_or_insufficient_identity"
        matching_failure = "other"
        fallback = "none"
        reason = "Alternative matching did not recover a hash and the identity is not safe for fallback."

    return {
        "stable_identity_key": list(relaxed_key),
        "machine_id": _clean_json_value(candidate.get("machine_id")),
        "start_time": normalize_timestamp_for_gap_match(candidate.get("start_time")),
        "end_time": normalize_timestamp_for_gap_match(candidate.get("end_time")),
        "prep_end_time": normalize_timestamp_for_gap_match(candidate.get("prep_end_time")),
        "order_id": _clean_json_value(candidate.get("order_id")),
        "material": _clean_json_value(candidate.get("material")),
        "good_qty": _clean_json_value(candidate.get("good_qty")),
        "candidate_workbook_evidence": {
            "source_package_month": SOURCE_PACKAGE_MONTH,
            "canonical_event_month": TARGET_MONTH_KEY,
            "boundary_reason": "previous_package_forward_spill_to_target_month",
        },
        "exact_match_gap_reason": (
            "B10.3 exact stable-identity matching did not find a source_row_hash for this candidate; "
            "B10.4 rechecks with timestamp-second normalization and null-equivalent material/good_qty handling."
        ),
        "matching_failure_category": matching_failure,
        "source_match_count_after_relaxed_matching": len(source_matches),
        "target_match_count_after_relaxed_matching": len(target_matches),
        "source_hashes": sorted(source_hashes),
        "target_hashes": sorted(target_hashes),
        "source_raw_payload_fingerprints": sorted(source_payload_fingerprints),
        "target_raw_payload_fingerprints": sorted(target_payload_fingerprints),
        "root_cause": root_cause,
        "classification": classification,
        "fallback_policy": fallback,
        "reason": reason,
    }


def _is_stable_maintenance_null_quantity_candidate(candidate: dict[str, Any]) -> bool:
    order_id = str(candidate.get("order_id") or "").strip()
    material = _normalize_null_equivalent(candidate.get("material"))
    good_qty = _normalize_null_equivalent(candidate.get("good_qty"))
    return (
        bool(candidate.get("machine_id"))
        and bool(candidate.get("start_time"))
        and bool(candidate.get("end_time"))
        and order_id in {"日保養", "月保養", "計劃保養"}
        and material == ""
        and good_qty == ""
    )


def _fallback_policy_decision(decision_summary: Counter[str]) -> dict[str, Any]:
    block_count = decision_summary[BLOCK_UNRESOLVED]
    fallback_count = decision_summary[STABLE_IDENTITY_FALLBACK_SAFE]
    hash_resolved_count = decision_summary[HASH_RESOLVED]
    skip_count = decision_summary[SKIP_DUE_EXISTING_DUPLICATE]
    if block_count:
        return {
            "fallback_policy": "blocked",
            "reason": f"{block_count} source-hash gap candidates remain unresolved.",
        }
    if fallback_count:
        return {
            "fallback_policy": "approved_for_narrow_maintenance_null_quantity_rows",
            "reason": (
                f"{fallback_count} maintenance/null-quantity candidates are absent from source and target Bronze/Silver "
                "and may use exact stable-identity fallback with stricter duplicate checks."
            ),
        }
    if skip_count:
        return {
            "fallback_policy": "not_required_with_duplicate_skips",
            "reason": (
                f"{hash_resolved_count} source-hash gaps recover source_row_hash evidence after safe normalization; "
                f"{skip_count} source-hash gaps are existing target duplicates and must be skipped."
            ),
        }
    return {
        "fallback_policy": "not_required",
        "reason": "All source-hash gaps were resolved by source-row-hash evidence.",
    }


def _b10_5_safety_decision(decision_summary: Counter[str]) -> dict[str, Any]:
    block_count = decision_summary[BLOCK_UNRESOLVED]
    fallback_count = decision_summary[STABLE_IDENTITY_FALLBACK_SAFE]
    skip_count = decision_summary[SKIP_DUE_EXISTING_DUPLICATE]
    if block_count:
        return {
            "safe_for_b10_5_temp_reconciliation": False,
            "reason": f"{block_count} candidates remain blocked.",
        }
    if fallback_count:
        return {
            "safe_for_b10_5_temp_reconciliation": True,
            "reason": (
                "No block_unresolved candidates remain; B10.5 may proceed as temp-only execution only if it enforces "
                "hash-first duplicate checks plus the approved stable-identity fallback checks."
            ),
        }
    if skip_count:
        return {
            "safe_for_b10_5_temp_reconciliation": True,
            "reason": (
                "No block_unresolved candidates remain; B10.5 may proceed as temp-only execution with the "
                "target-duplicate candidates excluded and no stable-identity fallback rows inserted."
            ),
        }
    return {
        "safe_for_b10_5_temp_reconciliation": True,
        "reason": "No block_unresolved candidates remain and all gap candidates recovered source-row-hash evidence.",
    }


def _decision_summary(gap_decisions: list[dict[str, Any]]) -> Counter[str]:
    return Counter(item["classification"] for item in gap_decisions)


def _source_hashes(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["source_row_hash"])
        for row in rows
        if row.get("source_row_hash") is not None and str(row["source_row_hash"]).strip()
    }


def _raw_payload_fingerprints(rows: list[dict[str, Any]]) -> set[str]:
    fingerprints: set[str] = set()
    for row in rows:
        payload = row.get("raw_payload_json")
        if payload is None or not str(payload).strip():
            continue
        normalized = _normalize_payload_text(str(payload))
        fingerprints.add(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return fingerprints


def _normalize_payload_text(payload: str) -> str:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return payload.strip()
    return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fetch_raw_rows_with_payload(conn: Any, target_month_key: str) -> list[dict[str, Any]]:
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
        _select_column(columns, "raw_payload_json"),
    ]
    rows = conn.execute(
        f"SELECT {', '.join(select_columns)} FROM raw_csi_event WHERE {canonical_expr} = ?",
        (target_month_key,),
    ).fetchall()
    return [dict(row) for row in rows]


def _duplicate_prevention_requirements(decision_summary: Counter[str]) -> list[str]:
    requirements = [
        "Before any temp insert, reject candidates whose source_row_hash is already present in raw_csi_event or csi_job_event for December canonical scope.",
        "Exclude every skip_due_existing_duplicate candidate from the insertion plan and report each skipped identity explicitly.",
        "After any temp-only execution, prove duplicate source_row_hash groups are zero for raw_csi_event and csi_job_event.",
        "After any temp-only execution, report included hash-proven rows separately from skipped duplicate rows.",
    ]
    if decision_summary[STABLE_IDENTITY_FALLBACK_SAFE]:
        requirements.extend(
            [
                "For stable-identity fallback rows, require exact machine_id, start_time, end_time, order_id, and NULL material/good_qty semantics to remain unchanged.",
                "For stable-identity fallback rows, require zero current-package raw/silver target-scope matches by relaxed stable identity.",
            ]
        )
    else:
        requirements.append(
            "Do not insert any stable-identity-only fallback row in B10.5 unless a later report explicitly approves that fallback."
        )
    return requirements


def _identity_key_from_candidate_relaxed(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_null_equivalent(row.get("machine_id")),
        normalize_timestamp_for_gap_match(row.get("start_time")),
        normalize_timestamp_for_gap_match(row.get("end_time")),
        normalize_timestamp_for_gap_match(row.get("prep_end_time")),
        _normalize_null_equivalent(row.get("order_id")),
        _normalize_null_equivalent(row.get("material")),
        _normalize_null_equivalent(row.get("good_qty")),
    )


def _identity_key_from_raw_relaxed(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_null_equivalent(row.get("raw_machine_id_or_label")),
        normalize_timestamp_for_gap_match(row.get("raw_start_time")),
        normalize_timestamp_for_gap_match(row.get("raw_end_time")),
        normalize_timestamp_for_gap_match(row.get("raw_prep_end_time")),
        _normalize_null_equivalent(row.get("raw_order_id")),
        _normalize_null_equivalent(row.get("raw_material")),
        _normalize_null_equivalent(row.get("raw_good_qty")),
    )


def _identity_key_from_silver_relaxed(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_null_equivalent(row.get("raw_machine_id_or_label")),
        normalize_timestamp_for_gap_match(row.get("prod_start_ts")),
        normalize_timestamp_for_gap_match(row.get("prod_end_ts")),
        normalize_timestamp_for_gap_match(row.get("prep_end_ts")),
        _normalize_null_equivalent(row.get("order_id")),
        _normalize_null_equivalent(row.get("material_code")),
        _normalize_null_equivalent(row.get("good_qty")),
    )


def _identity_key_from_raw_exact(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_key_value(row.get("raw_machine_id_or_label")),
        _normalize_key_value(row.get("raw_start_time")),
        _normalize_key_value(row.get("raw_end_time")),
        _normalize_key_value(row.get("raw_prep_end_time")),
        _normalize_key_value(row.get("raw_order_id")),
        _normalize_key_value(row.get("raw_material")),
        _normalize_key_value(row.get("raw_good_qty")),
    )


def _identity_key_from_silver_exact(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_key_value(row.get("raw_machine_id_or_label")),
        _normalize_key_value(row.get("prod_start_ts")),
        _normalize_key_value(row.get("prod_end_ts")),
        _normalize_key_value(row.get("prep_end_ts")),
        _normalize_key_value(row.get("order_id")),
        _normalize_key_value(row.get("material_code")),
        _normalize_key_value(row.get("good_qty")),
    )


def _normalize_null_equivalent(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat"}:
        return ""
    if text.endswith(".0"):
        try:
            parsed = float(text)
        except ValueError:
            return text
        if parsed.is_integer():
            return str(int(parsed))
    return text


def _clean_json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


__all__ = [
    "build_november_december_hash_gap_decision",
    "normalize_timestamp_for_gap_match",
]
