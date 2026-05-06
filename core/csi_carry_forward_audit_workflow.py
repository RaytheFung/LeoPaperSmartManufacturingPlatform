"""Workflow preflight helpers for CSI carry-forward audit records."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from core.csi_carry_forward_audit_schema import (
    AUDIT_RUNS_COLUMNS,
    CANDIDATES_COLUMNS,
    GOLD_DELTAS_COLUMNS,
    build_audit_run_id,
    build_candidate_id,
)


REVIEWER_STATUS_VALUES = (
    "draft",
    "pending_review",
    "accepted",
    "rejected",
    "superseded",
    "rollback_required",
)

CANDIDATE_DECISION_VALUES = (
    "include",
    "skip",
    "block",
)


def get_reviewer_status_values() -> tuple[str, ...]:
    return REVIEWER_STATUS_VALUES


def validate_reviewer_status(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized not in REVIEWER_STATUS_VALUES:
        raise ValueError(f"Unsupported reviewer status: {status!r}")
    return normalized


def get_audit_retention_policy() -> dict[str, Any]:
    return {
        "policy_name": "csi_carry_forward_audit_retention",
        "automatic_cleanup": False,
        "rules": [
            "Keep audit run records permanently unless explicitly archived through a reviewed governance step.",
            "Do not delete candidate-level provenance while related canonical rows exist.",
            "Supersede rather than mutate accepted audit records.",
            "No automatic cleanup of audit evidence is allowed.",
        ],
        "archive_requires_review": True,
        "accepted_records_are_immutable": True,
    }


def build_sample_audit_run_payload(
    *,
    source_package_month: str = "November 2025",
    target_canonical_month: str = "December 2025",
    suffix: str = "workflow_preflight",
    reviewer_status: str = "pending_review",
    candidate_count: int = 2,
    include_count: int = 1,
    skip_count: int = 1,
    block_count: int = 0,
) -> dict[str, Any]:
    validated_reviewer_status = validate_reviewer_status(reviewer_status)
    audit_run_id = build_audit_run_id(source_package_month, target_canonical_month, suffix=suffix)
    return {
        "audit_run_id": audit_run_id,
        "created_at": "2026-05-07T00:00:00Z",
        "mode": "temp_reconcile",
        "source_package_month": source_package_month,
        "target_canonical_month": target_canonical_month,
        "source_package_month_key": _month_key(source_package_month),
        "target_canonical_month_key": _month_key(target_canonical_month),
        "carry_forward_reason": "previous_package_timestamp_spill_to_target_month",
        "status": "sample_preflight",
        "candidate_count": candidate_count,
        "include_count": include_count,
        "skip_count": skip_count,
        "block_count": block_count,
        "raw_matched_count": include_count,
        "silver_matched_count": include_count,
        "duplicate_raw_hash_groups": 0,
        "duplicate_silver_hash_groups": 0,
        "fact_machine_hour_row_delta": 0,
        "fact_machine_hour_good_qty_delta": 473257.0,
        "db_scope": "in_memory_preflight_only",
        "reviewer_status": validated_reviewer_status,
        "notes": "Sample B12.2 audit workflow payload; not a live DB migration record.",
    }


def build_sample_candidate_payload(
    *,
    audit_run_id: str,
    candidate_index: int = 1,
    decision: str = "include",
    source_row_hash: str | None = None,
) -> dict[str, Any]:
    normalized_decision = _validate_candidate_decision(decision)
    source_hash = source_row_hash or f"sample_source_hash_{candidate_index:03d}"
    stable_identity_key = [
        "PM1",
        f"2025-11-30 {candidate_index:02d}:00:00",
        f"2025-12-01 {candidate_index:02d}:30:00",
        f"ORDER-{candidate_index:03d}",
        "MATERIAL-A",
        str(100.0 + candidate_index),
    ]
    candidate_id = build_candidate_id(stable_identity_key, source_hash)
    return {
        "audit_run_id": audit_run_id,
        "candidate_id": candidate_id,
        "source_package_month": "November 2025",
        "canonical_event_month": "2025-12",
        "machine_id": stable_identity_key[0],
        "order_id": stable_identity_key[3],
        "material": stable_identity_key[4],
        "good_qty": 100.0 + candidate_index,
        "start_time": stable_identity_key[1],
        "end_time": stable_identity_key[2],
        "prep_end_time": f"2025-11-30 {candidate_index:02d}:45:00",
        "source_row_hash": source_hash,
        "stable_identity_key": json.dumps(stable_identity_key, ensure_ascii=True),
        "decision": normalized_decision,
        "decision_reason": _sample_decision_reason(normalized_decision),
        "existing_target_hash": source_hash if normalized_decision == "skip" else None,
        "existing_target_identity": 1 if normalized_decision == "skip" else 0,
        "inserted_raw": 1 if normalized_decision == "include" else 0,
        "matched_silver": 1 if normalized_decision == "include" else 0,
        "provenance_source_path": "source_data/2025_jul_2026_feb_collected/sample_csi.xls",
        "raw_payload_reference": f"sample_row_{candidate_index}",
    }


def build_sample_gold_delta_payload(
    *,
    audit_run_id: str,
    metric_name: str = "fact_machine_hour.good_qty",
    baseline_value: float = 100634237.0,
    reconciled_value: float = 101107494.0,
) -> dict[str, Any]:
    return {
        "audit_run_id": audit_run_id,
        "target_canonical_month": "December 2025",
        "metric_name": metric_name,
        "baseline_value": baseline_value,
        "reconciled_value": reconciled_value,
        "delta_value": reconciled_value - baseline_value,
        "notes": "Sample B12.2 Gold delta payload for workflow validation only.",
    }


def insert_audit_run(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    validate_reviewer_status(str(payload.get("reviewer_status", "")))
    _insert_payload(conn, "csi_carry_forward_audit_runs", AUDIT_RUNS_COLUMNS, payload)


def insert_candidate(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    _validate_candidate_decision(str(payload.get("decision", "")))
    _require_audit_run(conn, str(payload.get("audit_run_id", "")))
    _insert_payload(conn, "csi_carry_forward_candidates", CANDIDATES_COLUMNS, payload)


def insert_gold_delta(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    _require_audit_run(conn, str(payload.get("audit_run_id", "")))
    _insert_payload(conn, "csi_carry_forward_gold_deltas", GOLD_DELTAS_COLUMNS, payload)


def validate_audit_workflow_counts(conn: sqlite3.Connection, audit_run_id: str) -> dict[str, Any]:
    audit_row = conn.execute(
        """
        SELECT candidate_count, include_count, skip_count, block_count, reviewer_status
        FROM csi_carry_forward_audit_runs
        WHERE audit_run_id = ?
        """,
        (audit_run_id,),
    ).fetchone()
    if audit_row is None:
        raise ValueError(f"Audit run does not exist: {audit_run_id}")

    decision_counts = {
        decision: _count_rows(
            conn,
            "csi_carry_forward_candidates",
            "audit_run_id = ? AND decision = ?",
            (audit_run_id, decision),
        )
        for decision in CANDIDATE_DECISION_VALUES
    }
    candidate_count = _count_rows(
        conn,
        "csi_carry_forward_candidates",
        "audit_run_id = ?",
        (audit_run_id,),
    )
    gold_delta_count = _count_rows(
        conn,
        "csi_carry_forward_gold_deltas",
        "audit_run_id = ?",
        (audit_run_id,),
    )
    unresolved_candidate_count = _count_rows(
        conn,
        "csi_carry_forward_candidates",
        "audit_run_id = ? AND decision NOT IN ('include', 'skip', 'block')",
        (audit_run_id,),
    )
    expected = {
        "candidate_count": int(audit_row[0] or 0),
        "include_count": int(audit_row[1] or 0),
        "skip_count": int(audit_row[2] or 0),
        "block_count": int(audit_row[3] or 0),
    }
    actual = {
        "candidate_count": candidate_count,
        "include_count": decision_counts["include"],
        "skip_count": decision_counts["skip"],
        "block_count": decision_counts["block"],
    }
    mismatches = {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in expected
        if expected[key] != actual[key]
    }
    return {
        "audit_run_id": audit_run_id,
        "valid": not mismatches and unresolved_candidate_count == 0,
        "expected": expected,
        "actual": actual,
        "gold_delta_count": gold_delta_count,
        "unresolved_candidate_count": unresolved_candidate_count,
        "reviewer_status": str(audit_row[4]),
        "mismatches": mismatches,
        "referential_consistency": {
            "audit_run_exists": True,
            "candidate_rows_reference_existing_run": True,
            "gold_delta_rows_reference_existing_run": True,
        },
    }


def build_migration_preflight_checklist() -> tuple[dict[str, str], ...]:
    return (
        _check("db_backup_path_required", "A reviewed DB backup path is recorded before migration."),
        _check("backup_checksum_required", "A backup checksum is recorded and verified."),
        _check("dry_run_sql_diff_required", "A dry-run SQL diff is reviewed before applying migration SQL."),
        _check("row_count_baseline_required", "Pre-migration row-count baselines are recorded."),
        _check("duplicate_hash_baseline_required", "Duplicate source-hash baselines are recorded."),
        _check("rollback_procedure_required", "Rollback script or procedure is reviewed before migration."),
        _check("reviewer_approval_required", "Reviewer status is accepted before any promoted migration."),
        _check("app_runtime_smoke_required", "App/runtime smoke evidence is captured after a promoted migration."),
        _check("no_main_no_force_push_branch_rule", "Migration work stays off main and is never force-pushed."),
    )


def build_live_migration_abort_gates() -> tuple[dict[str, str], ...]:
    return (
        _check("missing_backup", "Abort if the approved backup is missing."),
        _check("failed_checksum", "Abort if the backup checksum cannot be verified."),
        _check("duplicate_source_hash_groups", "Abort if duplicate source-hash groups appear outside the plan."),
        _check("unresolved_candidate_decisions", "Abort if any candidate decision remains unresolved."),
        _check("unexpected_gold_deltas", "Abort if Gold deltas differ from the reviewed expectation."),
        _check("app_smoke_failure", "Abort if app/runtime smoke fails after migration rehearsal."),
        _check("unsafe_db_path", "Abort if the DB path is repo-local, original-runtime-local, or otherwise unsafe."),
        _check("reviewer_status_not_accepted", "Abort if reviewer status is not accepted."),
        _check("migration_touches_tables_outside_plan", "Abort if migration touches tables outside the reviewed plan."),
    )


def build_backup_rollback_requirements() -> tuple[dict[str, str], ...]:
    return (
        _check("backup_before_migration", "Copy the DB before migration and keep the backup outside Git."),
        _check("backup_checksum", "Record and verify a checksum for the pre-migration backup."),
        _check("restore_procedure", "Document the restore procedure before applying migration SQL."),
        _check("post_restore_validation", "Define row-count and schema validation after rollback."),
        _check("no_temp_promotion_without_review", "Do not promote any temp DB without a separate approval gate."),
    )


def _insert_payload(
    conn: sqlite3.Connection,
    table_name: str,
    columns: tuple[str, ...],
    payload: dict[str, Any],
) -> None:
    missing = [column for column in columns if column not in payload]
    if missing:
        raise ValueError(f"Payload for {table_name} is missing required keys: {missing}")
    _assert_no_destructive_sql(table_name)
    column_list = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})",
        tuple(payload[column] for column in columns),
    )
    conn.commit()


def _require_audit_run(conn: sqlite3.Connection, audit_run_id: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM csi_carry_forward_audit_runs WHERE audit_run_id = ?",
        (audit_run_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Candidate or Gold delta references missing audit run: {audit_run_id}")


def _count_rows(conn: sqlite3.Connection, table_name: str, where_sql: str, params: tuple[Any, ...]) -> int:
    _assert_no_destructive_sql(table_name)
    row = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {where_sql}", params).fetchone()
    return int(row[0])


def _check(check_id: str, description: str) -> dict[str, str]:
    return {"id": check_id, "description": description}


def _validate_candidate_decision(decision: str) -> str:
    normalized = str(decision or "").strip().lower()
    if normalized not in CANDIDATE_DECISION_VALUES:
        raise ValueError(f"Unsupported carry-forward candidate decision: {decision!r}")
    return normalized


def _sample_decision_reason(decision: str) -> str:
    if decision == "include":
        return "Sample include row with source hash evidence."
    if decision == "skip":
        return "Sample skip row with existing target duplicate evidence."
    return "Sample block row for unresolved evidence."


def _month_key(month_label: str) -> str:
    lowered = str(month_label).strip().lower()
    month_lookup = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }
    parts = lowered.split()
    if len(parts) == 2 and parts[0] in month_lookup and re.fullmatch(r"\d{4}", parts[1]):
        return f"{parts[1]}-{month_lookup[parts[0]]}"
    return lowered


def _assert_no_destructive_sql(sql_fragment: str) -> None:
    if re.search(r"\bdrop\s+table\b", sql_fragment, flags=re.IGNORECASE):
        raise ValueError("Audit workflow helpers must not generate destructive table-removal SQL.")


__all__ = [
    "CANDIDATE_DECISION_VALUES",
    "REVIEWER_STATUS_VALUES",
    "build_backup_rollback_requirements",
    "build_live_migration_abort_gates",
    "build_migration_preflight_checklist",
    "build_sample_audit_run_payload",
    "build_sample_candidate_payload",
    "build_sample_gold_delta_payload",
    "get_audit_retention_policy",
    "get_reviewer_status_values",
    "insert_audit_run",
    "insert_candidate",
    "insert_gold_delta",
    "validate_audit_workflow_counts",
    "validate_reviewer_status",
]
