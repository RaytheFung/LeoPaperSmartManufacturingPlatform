#!/usr/bin/env python3
"""Temp-only CSI carry-forward audit workflow rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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

from core.csi_carry_forward_audit_schema import (
    create_carry_forward_audit_schema,
    validate_carry_forward_audit_schema,
)
from core.csi_carry_forward_audit_workflow import (
    build_backup_rollback_requirements,
    build_live_migration_abort_gates,
    build_migration_preflight_checklist,
    build_sample_audit_run_payload,
    build_sample_candidate_payload,
    build_sample_gold_delta_payload,
    insert_audit_run,
    insert_candidate,
    insert_gold_delta,
    validate_audit_workflow_counts,
)


ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"
TEMP_ROOT = Path("/tmp")
DEFAULT_REHEARSAL_DIR = TEMP_ROOT / "leopaper_stage_b12_3_audit_workflow"
DEFAULT_TEMP_DB_PATH = DEFAULT_REHEARSAL_DIR / "audit_workflow_rehearsal.db"
DEFAULT_BACKUP_DB_PATH = DEFAULT_REHEARSAL_DIR / "audit_workflow_rehearsal.backup.db"
DEFAULT_RESTORE_DB_PATH = DEFAULT_REHEARSAL_DIR / "audit_workflow_rehearsal.restored.db"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a temp-only CSI carry-forward audit workflow rehearsal.",
    )
    parser.add_argument("--temp-db-path", type=Path, default=DEFAULT_TEMP_DB_PATH)
    parser.add_argument("--backup-db-path", type=Path, default=DEFAULT_BACKUP_DB_PATH)
    parser.add_argument("--restore-db-path", type=Path, default=DEFAULT_RESTORE_DB_PATH)
    args = parser.parse_args(argv)

    try:
        evidence = run_csi_carry_forward_audit_workflow_rehearsal(
            temp_db_path=args.temp_db_path,
            backup_db_path=args.backup_db_path,
            restore_db_path=args.restore_db_path,
        )
    except Exception as exc:
        payload = {
            "status": "error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
        return 1

    print(json.dumps(evidence, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if evidence.get("status") == "success" else 2


def run_csi_carry_forward_audit_workflow_rehearsal(
    *,
    temp_db_path: str | Path = DEFAULT_TEMP_DB_PATH,
    backup_db_path: str | Path = DEFAULT_BACKUP_DB_PATH,
    restore_db_path: str | Path = DEFAULT_RESTORE_DB_PATH,
) -> dict[str, Any]:
    started_at = _utc_now()
    started_perf = time.perf_counter()
    temp_db = validate_temp_only_db_path(temp_db_path)
    backup_db = validate_temp_only_db_path(backup_db_path)
    restore_db = validate_temp_only_db_path(restore_db_path)
    _assert_distinct_paths(temp_db, backup_db, restore_db)

    temp_db.parent.mkdir(parents=True, exist_ok=True)
    backup_db.parent.mkdir(parents=True, exist_ok=True)
    restore_db.parent.mkdir(parents=True, exist_ok=True)

    temp_checksum_before = _sha256_file(temp_db) if temp_db.exists() else None
    for path in (temp_db, backup_db, restore_db):
        if path.exists():
            path.unlink()

    audit_run_id = ""
    with sqlite3.connect(temp_db) as conn:
        schema_create = create_carry_forward_audit_schema(conn)
        audit_payload = build_sample_audit_run_payload(
            source_package_month="November 2025",
            target_canonical_month="December 2025",
            suffix="b12_3_temp_rehearsal",
            reviewer_status="accepted",
            candidate_count=3,
            include_count=2,
            skip_count=1,
            block_count=0,
        )
        audit_run_id = str(audit_payload["audit_run_id"])
        insert_audit_run(conn, audit_payload)
        candidate_payloads = [
            build_sample_candidate_payload(audit_run_id=audit_run_id, candidate_index=1, decision="include"),
            build_sample_candidate_payload(audit_run_id=audit_run_id, candidate_index=2, decision="include"),
            build_sample_candidate_payload(audit_run_id=audit_run_id, candidate_index=3, decision="skip"),
        ]
        for payload in candidate_payloads:
            insert_candidate(conn, payload)
        gold_payload = build_sample_gold_delta_payload(audit_run_id=audit_run_id)
        insert_gold_delta(conn, gold_payload)
        schema_validation = validate_carry_forward_audit_schema(conn)
        count_validation = validate_audit_workflow_counts(conn, audit_run_id)

    temp_checksum_after = _sha256_file(temp_db)
    shutil.copy2(temp_db, backup_db)
    backup_checksum = _sha256_file(backup_db)
    backup_checksum_matches_temp = backup_checksum == temp_checksum_after

    shutil.copy2(backup_db, restore_db)
    restore_checksum = _sha256_file(restore_db)
    with sqlite3.connect(restore_db) as conn:
        restore_schema_validation = validate_carry_forward_audit_schema(conn)
        restore_count_validation = validate_audit_workflow_counts(conn, audit_run_id)

    abort_gate_ids = [item["id"] for item in build_live_migration_abort_gates()]
    checklist_ids = [item["id"] for item in build_migration_preflight_checklist()]
    rollback_requirement_ids = [item["id"] for item in build_backup_rollback_requirements()]
    duration_seconds = round(time.perf_counter() - started_perf, 3)

    return {
        "status": "success",
        "started_at_utc": started_at,
        "ended_at_utc": _utc_now(),
        "duration_seconds": duration_seconds,
        "temp_db_boundary": {
            "temp_db_path": str(temp_db),
            "backup_db_path": str(backup_db),
            "restore_db_path": str(restore_db),
            "inside_repo": _path_is_relative_to(temp_db, REPO_ROOT.resolve()),
            "inside_original_runtime_repo": _path_is_relative_to(temp_db, ORIGINAL_RUNTIME_REPO_ROOT.resolve()),
            "writes_live_db": False,
            "promotes_temp_db": False,
        },
        "audit_schema_applied": schema_create,
        "sample_audit_records": {
            "audit_run_id": audit_run_id,
            "source_package_month": "November 2025",
            "target_canonical_month": "December 2025",
            "reviewer_status": "accepted",
            "candidate_records_inserted": 3,
            "include_decisions": 2,
            "skip_decisions": 1,
            "block_decisions": 0,
            "gold_delta_records_inserted": 1,
        },
        "schema_validation": schema_validation,
        "workflow_count_validation": count_validation,
        "backup_checksum_evidence": {
            "temp_checksum_before": temp_checksum_before,
            "temp_checksum_after": temp_checksum_after,
            "backup_checksum": backup_checksum,
            "backup_checksum_matches_temp": backup_checksum_matches_temp,
        },
        "rollback_restore_evidence": {
            "restore_checksum": restore_checksum,
            "restore_checksum_matches_backup": restore_checksum == backup_checksum,
            "restore_schema_valid": restore_schema_validation["valid"],
            "restore_workflow_counts_valid": restore_count_validation["valid"],
        },
        "preflight_checklist_ids": checklist_ids,
        "abort_gate_ids": abort_gate_ids,
        "backup_rollback_requirement_ids": rollback_requirement_ids,
        "runtime_behavior_impact": {
            "runs_etl": False,
            "runs_backfill": False,
            "runs_materialization": False,
            "runs_reconciliation": False,
            "changes_runtime_predicates": False,
            "changes_source_discovery_policy": False,
            "streamlit_control": False,
            "live_db_migration": False,
        },
    }


def validate_temp_only_db_path(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve(strict=False)
    temp_root = TEMP_ROOT.resolve(strict=False)
    if resolved.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError(f"Rehearsal DB path must use a SQLite DB suffix: {resolved}")
    if not _path_is_relative_to(resolved, temp_root):
        raise ValueError(f"Rehearsal DB path must be under temp root {temp_root}: {resolved}")
    if _path_is_relative_to(resolved, REPO_ROOT.resolve()):
        raise ValueError(f"Refusing DB path inside GitHub-safe repo: {resolved}")
    if _path_is_relative_to(resolved, ORIGINAL_RUNTIME_REPO_ROOT.resolve()):
        raise ValueError(f"Refusing DB path inside original runtime repo: {resolved}")
    return resolved


def verify_backup_checksum(source_db_path: str | Path, backup_db_path: str | Path) -> dict[str, Any]:
    source = validate_temp_only_db_path(source_db_path)
    backup = validate_temp_only_db_path(backup_db_path)
    if not source.exists():
        raise FileNotFoundError(f"Source DB does not exist: {source}")
    if not backup.exists():
        raise FileNotFoundError(f"Backup DB does not exist: {backup}")
    source_checksum = _sha256_file(source)
    backup_checksum = _sha256_file(backup)
    return {
        "source_db_path": str(source),
        "backup_db_path": str(backup),
        "source_checksum": source_checksum,
        "backup_checksum": backup_checksum,
        "matches": source_checksum == backup_checksum,
    }


def validate_restored_audit_db(restored_db_path: str | Path, audit_run_id: str) -> dict[str, Any]:
    restored = validate_temp_only_db_path(restored_db_path)
    if not restored.exists():
        raise FileNotFoundError(f"Restored DB does not exist: {restored}")
    with sqlite3.connect(restored) as conn:
        schema_validation = validate_carry_forward_audit_schema(conn)
        workflow_validation = validate_audit_workflow_counts(conn, audit_run_id)
    return {
        "restored_db_path": str(restored),
        "schema_valid": schema_validation["valid"],
        "workflow_counts_valid": workflow_validation["valid"],
    }


def _assert_distinct_paths(*paths: Path) -> None:
    if len({path.resolve(strict=False) for path in paths}) != len(paths):
        raise ValueError("Temp, backup, and restore DB paths must be distinct.")


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
