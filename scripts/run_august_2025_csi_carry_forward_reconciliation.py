#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_materializer import CanonicalMaterializer
from core.csi_carry_forward_preflight import (
    ETL_CSI_CANONICAL_MONTH_EXPR,
    RAW_CSI_CANONICAL_MONTH_EXPR,
    TARGET_MONTH,
    TARGET_MONTH_KEY,
    build_csi_carry_forward_preflight,
)
from core.runtime_paths import get_extended_raw_dataset_root
from scripts.audit_august_csi_spill_traceability import build_traceability_audit
from scripts.run_august_2025_temp_backfill_rehearsal import (
    AUGUST_MONTH_KEY,
    DEFAULT_TEMP_DB_PATH as B8_2_BASELINE_DB_PATH,
    ORIGINAL_RUNTIME_DB_PATH,
    ORIGINAL_RUNTIME_REPO_ROOT,
    inspect_august_source_hash_duplicates,
    run_august_temp_backfill_rehearsal,
    summarize_august_temp_db,
)


DEFAULT_TARGET_DB_PATH = Path("/tmp/leopaper_stage_b9_2_carry_forward/august_carry_forward.db")
DEFAULT_CANDIDATE_SOURCE_DB_PATH = Path("/tmp/leopaper_stage_b6_4_july_isolation/july_isolation.db")
PREVIOUS_PACKAGE_MONTH = "July 2025"
RAW_IDENTITY_FIELDS = [
    "raw_machine_id_or_label",
    "raw_start_time",
    "raw_end_time",
    "raw_prep_end_time",
    "raw_order_id",
    "raw_material",
    "raw_good_qty",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a temp-only August 2025 CSI carry-forward reconciliation rehearsal.",
    )
    parser.add_argument("--target-db-path", type=Path, required=True)
    parser.add_argument("--candidate-source-db-path", type=Path, default=DEFAULT_CANDIDATE_SOURCE_DB_PATH)
    parser.add_argument("--baseline-db-path", type=Path, default=B8_2_BASELINE_DB_PATH)
    parser.add_argument("--original-db-path", type=Path, default=ORIGINAL_RUNTIME_DB_PATH)
    parser.add_argument("--data-root", type=Path, default=get_extended_raw_dataset_root())
    parser.add_argument("--month", default=TARGET_MONTH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        evidence = run_august_csi_carry_forward_reconciliation(
            target_db_path=args.target_db_path,
            candidate_source_db_path=args.candidate_source_db_path,
            baseline_db_path=args.baseline_db_path,
            original_db_path=args.original_db_path,
            data_root=args.data_root,
            month=args.month,
            dry_run=args.dry_run,
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
    return 0 if evidence.get("status") in {"success", "dry_run"} else 2


def run_august_csi_carry_forward_reconciliation(
    *,
    target_db_path: str | Path,
    candidate_source_db_path: str | Path = DEFAULT_CANDIDATE_SOURCE_DB_PATH,
    baseline_db_path: str | Path = B8_2_BASELINE_DB_PATH,
    original_db_path: str | Path = ORIGINAL_RUNTIME_DB_PATH,
    data_root: str | Path = get_extended_raw_dataset_root(),
    month: str = TARGET_MONTH,
    dry_run: bool = False,
) -> dict[str, Any]:
    _validate_target_month(month)
    target_db = _resolve_target_db_path(target_db_path)
    candidate_source_db = _validate_existing_db_path(Path(candidate_source_db_path), "candidate source DB")
    baseline_db = _validate_existing_db_path(Path(baseline_db_path), "baseline DB") if baseline_db_path else None
    original_db = Path(original_db_path).expanduser().resolve()
    source_root = Path(data_root).expanduser().resolve(strict=False)
    if not original_db.exists():
        raise FileNotFoundError(f"Original runtime DB does not exist: {original_db}")

    started_at = _utc_now()
    started_perf = time.perf_counter()
    original_before = _file_stat(original_db)
    preflight = build_csi_carry_forward_preflight(
        db_path=candidate_source_db,
        current_package_db_path=baseline_db,
    )
    baseline_counts = summarize_august_temp_db(baseline_db) if baseline_db else None
    baseline_duplicates = inspect_august_source_hash_duplicates(baseline_db) if baseline_db else None

    if dry_run:
        original_after = _file_stat(original_db)
        return {
            "status": "dry_run",
            "target_month": month,
            "target_month_key": TARGET_MONTH_KEY,
            "target_db_path": str(target_db),
            "candidate_source_db_path": str(candidate_source_db),
            "baseline_db_path": str(baseline_db) if baseline_db else None,
            "candidate_evidence": _candidate_evidence(preflight),
            "baseline_counts": baseline_counts,
            "baseline_duplicates": baseline_duplicates,
            "safety_evidence": {
                "dry_run": True,
                "target_db_created": target_db.exists(),
                "original_runtime_db_unchanged_by_size_mtime": _same_size_and_mtime(original_before, original_after),
                "writes_target_db": False,
            },
        }

    target_db.parent.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        target_db.unlink()
    shutil.copy2(original_db, target_db)
    target_before_mutation = {**_file_stat(target_db), "sha256": _sha256_file(target_db)}

    august_run_evidence = run_august_temp_backfill_rehearsal(
        temp_db_path=target_db,
        data_root=source_root,
        month=month,
        original_db_path=original_db,
    )
    before_reconcile_counts = summarize_august_temp_db(target_db)
    before_reconcile_preflight = build_csi_carry_forward_preflight(
        db_path=candidate_source_db,
        current_package_db_path=target_db,
    )
    reconciliation = reconcile_csi_carry_forward_candidates(
        target_db_path=target_db,
        candidate_source_db_path=candidate_source_db,
    )
    materialization_evidence = _refresh_august_materialization(target_db)
    after_reconcile_counts = summarize_august_temp_db(target_db)
    after_traceability = build_traceability_audit(target_db)
    after_duplicates = inspect_august_source_hash_duplicates(target_db)
    target_after = {**_file_stat(target_db), "sha256": _sha256_file(target_db)}
    original_after = _file_stat(original_db)
    duration_seconds = round(time.perf_counter() - started_perf, 3)

    return {
        "status": _result_status(reconciliation, after_traceability),
        "target_month": month,
        "target_month_key": TARGET_MONTH_KEY,
        "started_at_utc": started_at,
        "ended_at_utc": _utc_now(),
        "duration_seconds": duration_seconds,
        "target_db_path": str(target_db),
        "candidate_source_db_path": str(candidate_source_db),
        "baseline_db_path": str(baseline_db) if baseline_db else None,
        "original_runtime_db_evidence": {
            "before": original_before,
            "after": original_after,
        },
        "target_db_evidence": {
            "before_mutation": target_before_mutation,
            "after_reconciliation": target_after,
        },
        "candidate_evidence": _candidate_evidence(preflight),
        "august_backfill_evidence": {
            "status": august_run_evidence.get("status"),
            "rehearsal_result": august_run_evidence.get("rehearsal_result"),
            "isolation_evidence": august_run_evidence.get("isolation_evidence"),
            "spill_traceability_before_carry_forward": august_run_evidence.get("spill_traceability_evidence", {}).get(
                "traceability_result"
            ),
        },
        "before_reconcile_overlap": before_reconcile_preflight["current_package_overlap_summary"],
        "reconciliation_evidence": reconciliation,
        "materialization_evidence": materialization_evidence,
        "after_reconcile_traceability": after_traceability.get("traceability_result", {}),
        "duplicate_prevention_evidence": {
            "baseline_duplicates": baseline_duplicates,
            "after_duplicates": after_duplicates,
            "candidate_duplicate_identity_groups": preflight["duplicate_risk_summary"][
                "candidate_duplicate_identity_group_count"
            ],
        },
        "b8_2_baseline_comparison": _compare_august_counts(baseline_counts, after_reconcile_counts),
        "counts_before_reconcile": before_reconcile_counts,
        "counts_after_reconcile": after_reconcile_counts,
        "safety_evidence": {
            "target_db_inside_github_safe_repo": _path_is_relative_to(target_db, REPO_ROOT),
            "target_db_inside_original_runtime_repo": _path_is_relative_to(target_db, ORIGINAL_RUNTIME_REPO_ROOT),
            "original_runtime_db_unchanged_by_size_mtime": _same_size_and_mtime(original_before, original_after),
            "writes_target_db": True,
            "writes_original_runtime_db": False,
            "runs_march_2026": False,
            "changes_runtime_predicates": False,
            "changes_source_discovery_policy": False,
            "promotes_temp_db": False,
        },
    }


def reconcile_csi_carry_forward_candidates(
    *,
    target_db_path: str | Path,
    candidate_source_db_path: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    target_db = _resolve_target_db_path(target_db_path)
    candidate_source_db = _validate_existing_db_path(Path(candidate_source_db_path), "candidate source DB")
    if not target_db.exists():
        raise FileNotFoundError(f"Target DB does not exist: {target_db}")

    candidate_rows = _load_candidate_raw_rows(candidate_source_db)
    candidate_key_counts = Counter(row["identity_key"] for row in candidate_rows)
    duplicate_candidate_identity_groups = sum(1 for count in candidate_key_counts.values() if count > 1)

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    try:
        target_raw_columns = _table_columns(conn, "raw_csi_event")
        existing_hashes = _existing_source_hashes(conn)
        existing_identity_keys = _existing_raw_identity_keys(conn)
        rows_to_insert: list[dict[str, Any]] = []
        skipped_existing_hash = []
        skipped_existing_identity = []

        for row in candidate_rows:
            source_hash = row.get("source_row_hash")
            identity_key = row["identity_key"]
            if source_hash in existing_hashes:
                skipped_existing_hash.append(source_hash)
                continue
            if identity_key in existing_identity_keys:
                skipped_existing_identity.append(source_hash)
                continue
            rows_to_insert.append(row)
            if source_hash:
                existing_hashes.add(source_hash)
            existing_identity_keys.add(identity_key)

        if not dry_run:
            _insert_raw_rows(conn, rows_to_insert, target_raw_columns)
            conn.commit()

        return {
            "candidate_count": len(candidate_rows),
            "duplicate_candidate_identity_group_count": duplicate_candidate_identity_groups,
            "raw_rows_inserted": 0 if dry_run else len(rows_to_insert),
            "raw_rows_planned": len(rows_to_insert),
            "skipped_existing_source_hash_count": len(skipped_existing_hash),
            "skipped_existing_identity_count": len(skipped_existing_identity),
            "dry_run": dry_run,
            "source_files_used": [
                {"source_file": source_file, "row_count": count}
                for source_file, count in Counter(str(row.get("source_file")) for row in rows_to_insert).most_common()
            ],
            "provenance_marker": "source_file retains the previous-package July source path; no runtime schema change was made.",
        }
    finally:
        conn.close()


def _load_candidate_raw_rows(candidate_source_db: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(candidate_source_db)
    conn.row_factory = sqlite3.Row
    try:
        candidate_rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                    machine_id,
                    start_time,
                    end_time,
                    setup_end AS prep_end_time,
                    order_id,
                    material,
                    good_qty
                FROM etl_csi_data
                WHERE month_year = ?
                  AND {ETL_CSI_CANONICAL_MONTH_EXPR} = ?
                """,
                (PREVIOUS_PACKAGE_MONTH, TARGET_MONTH_KEY),
            ).fetchall()
        ]
        raw_rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT *
                FROM raw_csi_event
                WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?
                """,
                (TARGET_MONTH_KEY,),
            ).fetchall()
        ]
    finally:
        conn.close()

    raw_by_key: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in raw_rows:
        raw_by_key.setdefault(_raw_identity_key(row), []).append(row)

    selected_rows = []
    missing_identity_count = 0
    for candidate in candidate_rows:
        identity_key = _candidate_identity_key(candidate)
        matches = raw_by_key.get(identity_key, [])
        if not matches:
            missing_identity_count += 1
            continue
        selected = sorted(matches, key=_source_file_preference)[0]
        selected["identity_key"] = identity_key
        selected_rows.append(selected)

    if missing_identity_count:
        raise ValueError(f"Candidate raw source rows are missing for {missing_identity_count} identities.")
    return selected_rows


def _refresh_august_materialization(target_db: Path) -> dict[str, Any]:
    materializer = CanonicalMaterializer(target_db)
    return materializer.materialize_backfill_month(TARGET_MONTH)


def _candidate_evidence(preflight: dict[str, Any]) -> dict[str, Any]:
    summary = preflight["candidate_identity_summary"]
    hash_evidence = preflight["source_row_hash_evidence"]
    return {
        "candidate_count": preflight["candidate_count"],
        "distinct_machine_count": summary["distinct_machine_count"],
        "distinct_order_count": summary["distinct_order_count"],
        "good_qty_sum": summary["good_qty_sum"],
        "min_start_time": summary["min_start_time"],
        "max_end_time": summary["max_end_time"],
        "source_row_hash_available": preflight["source_row_hash_available"],
        "identity_hash_method": {
            "identity_key": "machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty",
            "hash_method": "match previous-package ETL identity to raw_csi_event, then carry source_row_hash through silver materialization",
        },
        "raw_hash_matched_candidate_count": hash_evidence["previous_package_raw_hash_matched_candidate_count"],
        "silver_matched_candidate_count": hash_evidence["previous_package_silver_matched_candidate_count"],
    }


def _compare_august_counts(
    baseline_counts: dict[str, Any] | None,
    after_counts: dict[str, Any],
) -> dict[str, Any]:
    if baseline_counts is None:
        return {"status": "not_available", "reason": "Baseline DB was not available."}

    comparisons = {}
    for table_name in ("raw_csi_event", "csi_job_event", "fact_machine_hour"):
        baseline_row_count = _count_metric(baseline_counts, table_name)
        after_row_count = _count_metric(after_counts, table_name)
        comparisons[f"{table_name}_august_row_count"] = {
            "baseline": baseline_row_count,
            "after": after_row_count,
            "delta": _numeric_delta(after_row_count, baseline_row_count),
        }

    baseline_csi_good_qty = _aggregate_metric(baseline_counts, "csi_job_event", "good_qty_sum")
    after_csi_good_qty = _aggregate_metric(after_counts, "csi_job_event", "good_qty_sum")
    baseline_fact_good_qty = _aggregate_metric(baseline_counts, "fact_machine_hour", "good_qty_sum")
    after_fact_good_qty = _aggregate_metric(after_counts, "fact_machine_hour", "good_qty_sum")
    comparisons["csi_job_event_good_qty_sum"] = {
        "baseline": baseline_csi_good_qty,
        "after": after_csi_good_qty,
        "delta": _numeric_delta(after_csi_good_qty, baseline_csi_good_qty),
    }
    comparisons["fact_machine_hour_good_qty_sum"] = {
        "baseline": baseline_fact_good_qty,
        "after": after_fact_good_qty,
        "delta": _numeric_delta(after_fact_good_qty, baseline_fact_good_qty),
    }
    return comparisons


def _count_metric(counts: dict[str, Any], table_name: str) -> Any:
    return counts.get(table_name, {}).get("august_row_count", {}).get("row_count")


def _aggregate_metric(counts: dict[str, Any], table_name: str, metric_name: str) -> Any:
    return counts.get(table_name, {}).get("range_and_aggregate", {}).get(metric_name)


def _numeric_delta(after: Any, before: Any) -> Any:
    if after is None or before is None:
        return None
    return after - before


def _existing_source_hashes(conn: sqlite3.Connection) -> set[Any]:
    if "source_row_hash" not in _table_columns(conn, "raw_csi_event"):
        return set()
    return {
        row[0]
        for row in conn.execute(
            f"SELECT source_row_hash FROM raw_csi_event WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
            (TARGET_MONTH_KEY,),
        ).fetchall()
        if row[0] is not None
    }


def _existing_raw_identity_keys(conn: sqlite3.Connection) -> set[tuple[str, ...]]:
    rows = conn.execute(
        f"SELECT * FROM raw_csi_event WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
        (TARGET_MONTH_KEY,),
    ).fetchall()
    return {_raw_identity_key(dict(row)) for row in rows}


def _insert_raw_rows(
    conn: sqlite3.Connection,
    rows: list[dict[str, Any]],
    target_columns: list[str],
) -> None:
    if not rows:
        return
    insert_columns = [
        column
        for column in target_columns
        if column in rows[0] and column not in {"identity_key", "id"}
    ]
    column_sql = ", ".join(_quote_identifier(column) for column in insert_columns)
    placeholder_sql = ", ".join("?" for _ in insert_columns)
    conn.executemany(
        f"INSERT INTO raw_csi_event ({column_sql}) VALUES ({placeholder_sql})",
        [tuple(row.get(column) for column in insert_columns) for row in rows],
    )


def _candidate_identity_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_key_value(row.get("machine_id")),
        _normalize_key_value(row.get("start_time")),
        _normalize_key_value(row.get("end_time")),
        _normalize_key_value(row.get("prep_end_time")),
        _normalize_key_value(row.get("order_id")),
        _normalize_key_value(row.get("material")),
        _normalize_key_value(row.get("good_qty")),
    )


def _raw_identity_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_key_value(row.get("raw_machine_id_or_label")),
        _normalize_key_value(row.get("raw_start_time")),
        _normalize_key_value(row.get("raw_end_time")),
        _normalize_key_value(row.get("raw_prep_end_time")),
        _normalize_key_value(row.get("raw_order_id")),
        _normalize_key_value(row.get("raw_material")),
        _normalize_key_value(row.get("raw_good_qty")),
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


def _source_file_preference(row: dict[str, Any]) -> tuple[int, str]:
    source_file = str(row.get("source_file") or "")
    if source_file.startswith("source_data/"):
        return (0, source_file)
    if not source_file.startswith("/"):
        return (1, source_file)
    return (2, source_file)


def _result_status(reconciliation: dict[str, Any], traceability: dict[str, Any]) -> str:
    trace_result = traceability.get("traceability_result", {})
    if (
        reconciliation.get("raw_rows_inserted") == reconciliation.get("candidate_count")
        and trace_result.get("raw_august_unmatched_spill_row_count") == 0
        and trace_result.get("silver_august_unmatched_spill_row_count") == 0
    ):
        return "success"
    return "partial_error"


def _validate_target_month(month: str) -> None:
    if str(month).strip() != TARGET_MONTH:
        raise ValueError(f"Refusing non-August target month: {month}")


def _resolve_target_db_path(db_path: str | Path) -> Path:
    resolved = Path(db_path).expanduser().resolve(strict=False)
    if _path_is_relative_to(resolved, REPO_ROOT):
        raise ValueError(f"Refusing DB path inside repo: {resolved}")
    if _path_is_relative_to(resolved, ORIGINAL_RUNTIME_REPO_ROOT):
        raise ValueError(f"Refusing DB path inside original runtime repo: {resolved}")
    if resolved.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError(f"Target DB path must use a DB suffix: {resolved}")
    return resolved


def _validate_existing_db_path(db_path: Path, label: str) -> Path:
    resolved = db_path.expanduser().resolve()
    if _path_is_relative_to(resolved, REPO_ROOT):
        raise ValueError(f"Refusing {label} path inside repo: {resolved}")
    if _path_is_relative_to(resolved, ORIGINAL_RUNTIME_REPO_ROOT):
        raise ValueError(f"Refusing {label} path inside original runtime repo: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"{label} is not a file: {resolved}")
    return resolved


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [str(row["name"]) for row in conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()]


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
    import hashlib

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
