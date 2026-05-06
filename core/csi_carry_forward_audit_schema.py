"""SQLite schema blueprint for CSI carry-forward audit provenance."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any


CSI_CARRY_FORWARD_AUDIT_RUNS_TABLE = "csi_carry_forward_audit_runs"
CSI_CARRY_FORWARD_CANDIDATES_TABLE = "csi_carry_forward_candidates"
CSI_CARRY_FORWARD_GOLD_DELTAS_TABLE = "csi_carry_forward_gold_deltas"

AUDIT_RUNS_COLUMNS = (
    "audit_run_id",
    "created_at",
    "mode",
    "source_package_month",
    "target_canonical_month",
    "source_package_month_key",
    "target_canonical_month_key",
    "carry_forward_reason",
    "status",
    "candidate_count",
    "include_count",
    "skip_count",
    "block_count",
    "raw_matched_count",
    "silver_matched_count",
    "duplicate_raw_hash_groups",
    "duplicate_silver_hash_groups",
    "fact_machine_hour_row_delta",
    "fact_machine_hour_good_qty_delta",
    "db_scope",
    "reviewer_status",
    "notes",
)
CANDIDATES_COLUMNS = (
    "audit_run_id",
    "candidate_id",
    "source_package_month",
    "canonical_event_month",
    "machine_id",
    "order_id",
    "material",
    "good_qty",
    "start_time",
    "end_time",
    "prep_end_time",
    "source_row_hash",
    "stable_identity_key",
    "decision",
    "decision_reason",
    "existing_target_hash",
    "existing_target_identity",
    "inserted_raw",
    "matched_silver",
    "provenance_source_path",
    "raw_payload_reference",
)
GOLD_DELTAS_COLUMNS = (
    "audit_run_id",
    "target_canonical_month",
    "metric_name",
    "baseline_value",
    "reconciled_value",
    "delta_value",
    "notes",
)

AUDIT_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS csi_carry_forward_audit_runs (
    audit_run_id TEXT PRIMARY KEY,
    created_at TEXT,
    mode TEXT,
    source_package_month TEXT,
    target_canonical_month TEXT,
    source_package_month_key TEXT,
    target_canonical_month_key TEXT,
    carry_forward_reason TEXT,
    status TEXT,
    candidate_count INTEGER,
    include_count INTEGER,
    skip_count INTEGER,
    block_count INTEGER,
    raw_matched_count INTEGER,
    silver_matched_count INTEGER,
    duplicate_raw_hash_groups INTEGER,
    duplicate_silver_hash_groups INTEGER,
    fact_machine_hour_row_delta INTEGER,
    fact_machine_hour_good_qty_delta REAL,
    db_scope TEXT,
    reviewer_status TEXT,
    notes TEXT
);
""".strip()

CANDIDATES_DDL = """
CREATE TABLE IF NOT EXISTS csi_carry_forward_candidates (
    audit_run_id TEXT,
    candidate_id TEXT,
    source_package_month TEXT,
    canonical_event_month TEXT,
    machine_id TEXT,
    order_id TEXT,
    material TEXT,
    good_qty REAL,
    start_time TEXT,
    end_time TEXT,
    prep_end_time TEXT,
    source_row_hash TEXT,
    stable_identity_key TEXT,
    decision TEXT,
    decision_reason TEXT,
    existing_target_hash TEXT,
    existing_target_identity INTEGER,
    inserted_raw INTEGER,
    matched_silver INTEGER,
    provenance_source_path TEXT,
    raw_payload_reference TEXT,
    PRIMARY KEY(audit_run_id, candidate_id)
);
""".strip()

GOLD_DELTAS_DDL = """
CREATE TABLE IF NOT EXISTS csi_carry_forward_gold_deltas (
    audit_run_id TEXT,
    target_canonical_month TEXT,
    metric_name TEXT,
    baseline_value REAL,
    reconciled_value REAL,
    delta_value REAL,
    notes TEXT,
    PRIMARY KEY(audit_run_id, metric_name)
);
""".strip()

EXPECTED_SCHEMA_COLUMNS = {
    CSI_CARRY_FORWARD_AUDIT_RUNS_TABLE: AUDIT_RUNS_COLUMNS,
    CSI_CARRY_FORWARD_CANDIDATES_TABLE: CANDIDATES_COLUMNS,
    CSI_CARRY_FORWARD_GOLD_DELTAS_TABLE: GOLD_DELTAS_COLUMNS,
}


def get_carry_forward_audit_schema_statements() -> tuple[str, ...]:
    """Return the non-destructive audit/provenance schema DDL statements."""
    return (AUDIT_RUNS_DDL, CANDIDATES_DDL, GOLD_DELTAS_DDL)


def create_carry_forward_audit_schema(conn: sqlite3.Connection, dry_run: bool = False) -> dict[str, Any]:
    """Create the audit schema on a caller-supplied connection, or parse only.

    `dry_run=True` validates the DDL against an in-memory database and leaves
    the supplied connection untouched.
    """
    statements = get_carry_forward_audit_schema_statements()
    _assert_safe_schema_statements(statements)

    target_conn = sqlite3.connect(":memory:") if dry_run else conn
    close_target = dry_run
    try:
        for statement in statements:
            target_conn.execute(statement)
        if not dry_run:
            conn.commit()
        validation = validate_carry_forward_audit_schema(target_conn)
    finally:
        if close_target:
            target_conn.close()

    return {
        "dry_run": dry_run,
        "created_tables": list(EXPECTED_SCHEMA_COLUMNS),
        "statement_count": len(statements),
        "valid": validation["valid"],
    }


def validate_carry_forward_audit_schema(conn: sqlite3.Connection) -> dict[str, Any]:
    """Validate required audit tables and columns on a SQLite connection."""
    tables: dict[str, dict[str, Any]] = {}
    valid = True
    for table_name, expected_columns in EXPECTED_SCHEMA_COLUMNS.items():
        actual_columns = _table_columns(conn, table_name)
        missing_columns = [column for column in expected_columns if column not in actual_columns]
        table_valid = not missing_columns
        valid = valid and table_valid
        tables[table_name] = {
            "exists": bool(actual_columns),
            "valid": table_valid,
            "expected_columns": list(expected_columns),
            "actual_columns": actual_columns,
            "missing_columns": missing_columns,
        }
    return {"valid": valid, "tables": tables}


def build_candidate_id(stable_identity_key: object, source_row_hash: str | None = None) -> str:
    """Build a deterministic candidate identifier from stable identity evidence."""
    payload = {
        "stable_identity_key": _normalize_identity_value(stable_identity_key),
        "source_row_hash": str(source_row_hash or "").strip(),
    }
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
    return f"cfcand_{digest[:32]}"


def build_audit_run_id(
    source_package_month: str,
    target_canonical_month: str,
    suffix: str | None = None,
) -> str:
    """Build a deterministic audit-run identifier for a carry-forward boundary."""
    source = _slug(source_package_month)
    target = _slug(target_canonical_month)
    parts = ["cfaudit", source, "to", target]
    if suffix:
        parts.append(_slug(suffix))
    return "_".join(parts)


def _assert_safe_schema_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        if re.search(r"\bdrop\s+table\b", statement, flags=re.IGNORECASE):
            raise ValueError("Carry-forward audit schema must not contain DROP TABLE statements.")


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row[1]) for row in rows]


def _normalize_identity_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _normalize_identity_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize_identity_value(item) for item in value]
    if value is None:
        return None
    return str(value).strip()


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return normalized.strip("_")


__all__ = [
    "AUDIT_RUNS_COLUMNS",
    "AUDIT_RUNS_DDL",
    "CANDIDATES_COLUMNS",
    "CANDIDATES_DDL",
    "CSI_CARRY_FORWARD_AUDIT_RUNS_TABLE",
    "CSI_CARRY_FORWARD_CANDIDATES_TABLE",
    "CSI_CARRY_FORWARD_GOLD_DELTAS_TABLE",
    "EXPECTED_SCHEMA_COLUMNS",
    "GOLD_DELTAS_COLUMNS",
    "GOLD_DELTAS_DDL",
    "build_audit_run_id",
    "build_candidate_id",
    "create_carry_forward_audit_schema",
    "get_carry_forward_audit_schema_statements",
    "validate_carry_forward_audit_schema",
]
