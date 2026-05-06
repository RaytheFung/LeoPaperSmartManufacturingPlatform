#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import traceback
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_materializer import CanonicalMaterializer
from core.november_december_hash_gap_decision import (
    BLOCK_UNRESOLVED,
    HASH_RESOLVED,
    SKIP_DUE_EXISTING_DUPLICATE,
    STABLE_IDENTITY_FALLBACK_SAFE,
    build_november_december_hash_gap_decision,
    normalize_timestamp_for_gap_match,
)
from core.runtime_paths import get_extended_raw_dataset_root
from modules.etl_module import ETLPipelineModule
from scripts.audit_july_csi_spill_rows import RAW_CSI_CANONICAL_MONTH_EXPR, SILVER_CSI_CANONICAL_MONTH_EXPR
from scripts.compare_source_discovery_modes import build_source_discovery_compare_diagnostics


SOURCE_PACKAGE_MONTH = "November 2025"
SOURCE_PACKAGE_MONTH_KEY = "2025-11"
TARGET_MONTH = "December 2025"
TARGET_MONTH_KEY = "2025-12"
DEFAULT_TARGET_DB_PATH = Path("/tmp/leopaper_stage_b10_5_nov_dec_reconciliation/nov_dec_reconciliation.db")
ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"
ORIGINAL_RUNTIME_DB_PATH = ORIGINAL_RUNTIME_REPO_ROOT / "manufacturing_data.db"
APPROVED_INCLUDE_COUNT = 135
APPROVED_SKIP_COUNT = 7
APPROVED_BLOCK_COUNT = 0


DECEMBER_PRUNE_RULES = {
    "etl_runs": {
        "where": "month_processed = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_processed"},
        "reason": "ETL run ledger rows are month-scoped by month_processed.",
    },
    "etl_energy_data": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "ETL Energy staging is month-scoped by month_year.",
    },
    "etl_csi_data": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "ETL CSI staging is month-scoped by month_year.",
    },
    "etl_mes_data": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "ETL MES staging is month-scoped by month_year.",
    },
    "raw_energy_hourly": {
        "where": "substr(raw_timestamp, 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"raw_timestamp"},
        "reason": "Bronze Energy is month-scoped by raw_timestamp.",
    },
    "raw_csi_event": {
        "where": f"{RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"raw_start_time", "raw_end_time", "raw_prep_end_time", "raw_payload_json"},
        "reason": "Bronze CSI uses the current first-available timestamp canonical month expression.",
    },
    "raw_mes_report": {
        "where": "substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"raw_payload_json"},
        "reason": "Bronze MES is month-scoped by report timestamp in raw_payload_json.",
    },
    "raw_maintenance_txn": {
        "where": "substr(raw_transaction_date, 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"raw_transaction_date"},
        "reason": "Bronze maintenance is month-scoped by transaction timestamp.",
    },
    "energy_meter_hour": {
        "where": "substr(hour_ts, 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"hour_ts"},
        "reason": "Silver Energy is month-scoped by hour_ts.",
    },
    "csi_job_event": {
        "where": f"{SILVER_CSI_CANONICAL_MONTH_EXPR} = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"prod_start_ts", "prod_end_ts", "prep_end_ts", "shift_date"},
        "reason": "Silver CSI uses the current first-available timestamp canonical month expression.",
    },
    "mes_report_event": {
        "where": "substr(report_ts, 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"report_ts"},
        "reason": "Silver MES is month-scoped by report_ts.",
    },
    "maintenance_txn_event": {
        "where": "substr(txn_ts, 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"txn_ts"},
        "reason": "Silver maintenance is month-scoped by txn_ts.",
    },
    "fact_machine_hour": {
        "where": "substr(hour_ts, 1, 7) = ?",
        "params": (TARGET_MONTH_KEY,),
        "required_columns": {"hour_ts"},
        "reason": "Gold fact table is month-scoped by hour_ts.",
    },
    "machine_monthly_presence": {
        "where": "month_year = ?",
        "params": (TARGET_MONTH,),
        "required_columns": {"month_year"},
        "reason": "Machine presence is explicitly month-scoped by month_year.",
    },
}


GLOBAL_OR_AMBIGUOUS_TABLE_REASONS = {
    "machine_inventory": "Global inventory state; no conservative December partition deletion predicate is defined.",
    "three_way_matches": "Global mapping state; first/last matched dates do not make row deletion safely month-scoped.",
    "unified_view": "Derived/global legacy surface; no conservative December delete predicate is defined.",
    "ml_models": "Model metadata/artifact table; model artifacts must not be modified.",
    "sqlite_sequence": "SQLite internal sequence table.",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a temp-only November-to-December CSI carry-forward reconciliation rehearsal.",
    )
    parser.add_argument("--target-db-path", type=Path, required=True)
    parser.add_argument("--original-db-path", type=Path, default=ORIGINAL_RUNTIME_DB_PATH)
    parser.add_argument("--data-root", type=Path, default=get_extended_raw_dataset_root())
    parser.add_argument("--source-package-month", default=SOURCE_PACKAGE_MONTH)
    parser.add_argument("--target-month", default=TARGET_MONTH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        evidence = run_november_december_csi_carry_forward_reconciliation(
            target_db_path=args.target_db_path,
            original_db_path=args.original_db_path,
            data_root=args.data_root,
            source_package_month=args.source_package_month,
            target_month=args.target_month,
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


def run_november_december_csi_carry_forward_reconciliation(
    *,
    target_db_path: str | Path,
    original_db_path: str | Path = ORIGINAL_RUNTIME_DB_PATH,
    data_root: str | Path = get_extended_raw_dataset_root(),
    source_package_month: str = SOURCE_PACKAGE_MONTH,
    target_month: str = TARGET_MONTH,
    dry_run: bool = False,
) -> dict[str, Any]:
    _validate_boundary(source_package_month, target_month)
    target_db = _validate_existing_target_db_path(Path(target_db_path))
    original_db = Path(original_db_path).expanduser().resolve(strict=False)
    source_root = Path(data_root).expanduser().resolve(strict=False)
    if not original_db.exists():
        raise FileNotFoundError(f"Original runtime DB does not exist: {original_db}")

    started_at = _utc_now()
    started_perf = time.perf_counter()
    original_before = _file_stat(original_db)
    target_before_mutation = {**_file_stat(target_db), "sha256": _sha256_file(target_db)}
    approved_plan = build_approved_november_december_plan(db_path=target_db, data_root=source_root)
    validate_approved_plan_counts(approved_plan)
    pre_isolation_counts = summarize_december_temp_db(target_db)

    if dry_run:
        original_after = _file_stat(original_db)
        return {
            "status": "dry_run",
            "source_package_month": source_package_month,
            "target_month": target_month,
            "target_month_key": TARGET_MONTH_KEY,
            "target_db_path": str(target_db),
            "approved_plan": public_approved_plan(approved_plan),
            "pre_isolation_counts": pre_isolation_counts,
            "safety_evidence": {
                "dry_run": True,
                "target_db_inside_github_safe_repo": _path_is_relative_to(target_db, REPO_ROOT),
                "target_db_inside_original_runtime_repo": _path_is_relative_to(target_db, ORIGINAL_RUNTIME_REPO_ROOT),
                "original_runtime_db_unchanged_by_size_mtime": _same_size_and_mtime(original_before, original_after),
                "writes_target_db": False,
            },
        }

    isolation_evidence = isolate_december_baseline_partitions(target_db)
    december_backfill_evidence = run_december_baseline_backfill(target_db, source_root)
    baseline_counts = summarize_december_temp_db(target_db)
    baseline_duplicates = inspect_december_duplicate_evidence(target_db)
    insertion_evidence = apply_approved_carry_forward_plan(
        target_db_path=target_db,
        approved_plan=approved_plan,
    )
    materialization_evidence = CanonicalMaterializer(target_db).materialize_backfill_month(TARGET_MONTH)
    after_counts = summarize_december_temp_db(target_db)
    after_duplicates = inspect_december_duplicate_evidence(target_db)
    traceability_evidence = build_carry_forward_traceability(target_db, approved_plan["include_source_hashes"])
    baseline_comparison = compare_december_counts(baseline_counts, after_counts, approved_plan)
    target_after = {**_file_stat(target_db), "sha256": _sha256_file(target_db)}
    original_after = _file_stat(original_db)
    duration_seconds = round(time.perf_counter() - started_perf, 3)

    status = _result_status(insertion_evidence, traceability_evidence, after_duplicates, baseline_comparison)
    return {
        "status": status,
        "source_package_month": source_package_month,
        "source_package_month_key": SOURCE_PACKAGE_MONTH_KEY,
        "target_month": target_month,
        "target_month_key": TARGET_MONTH_KEY,
        "started_at_utc": started_at,
        "ended_at_utc": _utc_now(),
        "duration_seconds": duration_seconds,
        "target_db_path": str(target_db),
        "data_root": str(source_root),
        "original_runtime_db_evidence": {
            "before": original_before,
            "after": original_after,
        },
        "target_db_evidence": {
            "before_mutation": target_before_mutation,
            "after_reconciliation": target_after,
        },
        "approved_plan": public_approved_plan(approved_plan),
        "pre_isolation_counts": pre_isolation_counts,
        "isolation_evidence": isolation_evidence,
        "december_baseline_backfill_evidence": december_backfill_evidence,
        "baseline_counts": baseline_counts,
        "baseline_duplicate_evidence": baseline_duplicates,
        "reconciliation_evidence": insertion_evidence,
        "materialization_evidence": materialization_evidence,
        "counts_after_reconciliation": after_counts,
        "duplicate_prevention_evidence": after_duplicates,
        "carry_forward_traceability": traceability_evidence,
        "baseline_comparison": baseline_comparison,
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
            "modifies_model_artifacts": False,
        },
    }


def build_approved_november_december_plan(
    *,
    db_path: str | Path,
    data_root: str | Path | None = None,
) -> dict[str, Any]:
    db = _validate_existing_target_db_path(Path(db_path))
    decision = build_november_december_hash_gap_decision(db_path=db, data_root=data_root)
    source_relative = str(decision["source_csi_file_relative"])
    include_raw_rows = _load_source_package_december_raw_rows(db, source_relative)
    include_hashes = sorted(
        {
            str(row["source_row_hash"])
            for row in include_raw_rows
            if row.get("source_row_hash") is not None and str(row["source_row_hash"]).strip()
        }
    )
    skip_candidates = [
        row
        for row in decision["hash_gap_candidates"]
        if row["classification"] == SKIP_DUE_EXISTING_DUPLICATE
    ]
    block_candidates = [
        row
        for row in decision["hash_gap_candidates"]
        if row["classification"] == BLOCK_UNRESOLVED
    ]
    fallback_candidates = [
        row
        for row in decision["hash_gap_candidates"]
        if row["classification"] == STABLE_IDENTITY_FALLBACK_SAFE
    ]
    hash_resolved_candidates = [
        row
        for row in decision["hash_gap_candidates"]
        if row["classification"] == HASH_RESOLVED
    ]
    include_identity_keys = {_raw_identity_key(row) for row in include_raw_rows}
    duplicate_include_identity_groups = _duplicate_group_count(include_identity_keys, [_raw_identity_key(row) for row in include_raw_rows])

    return {
        "candidate_count": int(decision["candidate_count"]),
        "include_count": len(include_raw_rows),
        "skip_count": len(skip_candidates),
        "block_count": len(block_candidates),
        "hash_proven_include_count": int(decision["include_skip_block_plan"]["hash_proven_include_count"]),
        "hash_resolved_include_count": len(hash_resolved_candidates),
        "stable_identity_fallback_include_count": len(fallback_candidates),
        "include_raw_rows": include_raw_rows,
        "include_source_hashes": include_hashes,
        "skip_candidates": skip_candidates,
        "block_candidates": block_candidates,
        "hash_resolved_candidates": hash_resolved_candidates,
        "source_csi_file_relative": source_relative,
        "target_csi_file_relative": str(decision["target_csi_file_relative"]),
        "root_cause_classification": decision["root_cause_classification"],
        "fallback_policy_decision": decision["fallback_policy_decision"],
        "duplicate_include_identity_group_count": duplicate_include_identity_groups,
        "source_package_month": SOURCE_PACKAGE_MONTH,
        "canonical_event_month": TARGET_MONTH_KEY,
        "carry_forward_reason": "previous_package_timestamp_spill_to_target_month",
    }


def validate_approved_plan_counts(
    plan: dict[str, Any],
    *,
    expected_include_count: int = APPROVED_INCLUDE_COUNT,
    expected_skip_count: int = APPROVED_SKIP_COUNT,
    expected_block_count: int = APPROVED_BLOCK_COUNT,
) -> None:
    mismatches = []
    for key, expected in (
        ("include_count", expected_include_count),
        ("skip_count", expected_skip_count),
        ("block_count", expected_block_count),
    ):
        actual = int(plan.get(key) or 0)
        if actual != expected:
            mismatches.append(f"{key} expected {expected} got {actual}")
    if mismatches:
        raise ValueError("Approved include/skip/block plan mismatch: " + "; ".join(mismatches))
    if int(plan.get("stable_identity_fallback_include_count") or 0) != 0:
        raise ValueError("Stable-identity fallback rows are not approved for B10.5 execution.")
    if int(plan.get("duplicate_include_identity_group_count") or 0) != 0:
        raise ValueError("Approved include rows contain duplicate stable identity groups.")
    if len(plan.get("include_source_hashes") or []) != expected_include_count:
        raise ValueError("Approved include source_row_hash count does not match include count.")


def public_approved_plan(plan: dict[str, Any]) -> dict[str, Any]:
    include_rows = plan.get("include_raw_rows") or []
    return {
        "total_candidates": plan["candidate_count"],
        "include_count": plan["include_count"],
        "skip_count": plan["skip_count"],
        "block_count": plan["block_count"],
        "hash_proven_include_count": plan["hash_proven_include_count"],
        "hash_resolved_include_count": plan["hash_resolved_include_count"],
        "stable_identity_fallback_include_count": plan["stable_identity_fallback_include_count"],
        "source_package_month": plan["source_package_month"],
        "canonical_event_month": plan["canonical_event_month"],
        "carry_forward_reason": plan["carry_forward_reason"],
        "source_csi_file_relative": plan["source_csi_file_relative"],
        "target_csi_file_relative": plan["target_csi_file_relative"],
        "root_cause_classification": plan["root_cause_classification"],
        "fallback_policy_decision": plan["fallback_policy_decision"],
        "include_source_hash_count": len(plan["include_source_hashes"]),
        "include_affected_machine_count": len({_normalize_key_value(row.get("raw_machine_id_or_label")) for row in include_rows}),
        "include_affected_order_count": len({_normalize_key_value(row.get("raw_order_id")) for row in include_rows}),
        "include_good_qty_sum": _numeric_sum(include_rows, "raw_good_qty"),
        "skip_reasons": [
            {
                "stable_identity_key": row["stable_identity_key"],
                "reason": row["reason"],
                "target_hashes": row["target_hashes"],
            }
            for row in plan["skip_candidates"]
        ],
        "hash_resolved_gap_reasons": [
            {
                "stable_identity_key": row["stable_identity_key"],
                "reason": row["reason"],
                "source_hashes": row["source_hashes"],
            }
            for row in plan["hash_resolved_candidates"]
        ],
    }


def apply_approved_carry_forward_plan(
    *,
    target_db_path: str | Path,
    approved_plan: dict[str, Any],
    dry_run: bool = False,
    expected_include_count: int = APPROVED_INCLUDE_COUNT,
    expected_skip_count: int = APPROVED_SKIP_COUNT,
    expected_block_count: int = APPROVED_BLOCK_COUNT,
) -> dict[str, Any]:
    target_db = _validate_existing_target_db_path(Path(target_db_path))
    include_rows = list(approved_plan.get("include_raw_rows") or [])
    validate_approved_plan_counts(
        approved_plan,
        expected_include_count=expected_include_count,
        expected_skip_count=expected_skip_count,
        expected_block_count=expected_block_count,
    )

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    try:
        target_columns = _table_columns(conn, "raw_csi_event")
        existing_raw_hashes = _existing_source_hashes(conn, "raw_csi_event", RAW_CSI_CANONICAL_MONTH_EXPR)
        existing_silver_hashes = _existing_source_hashes(conn, "csi_job_event", SILVER_CSI_CANONICAL_MONTH_EXPR)
        existing_identity_keys = _existing_raw_identity_keys(conn)
        duplicate_source_hashes = sorted(
            {
                str(row["source_row_hash"])
                for row in include_rows
                if row.get("source_row_hash") in existing_raw_hashes or row.get("source_row_hash") in existing_silver_hashes
            }
        )
        duplicate_identity_keys = sorted(
            {
                "|".join(_raw_identity_key(row))
                for row in include_rows
                if _raw_identity_key(row) in existing_identity_keys
            }
        )
        if duplicate_source_hashes or duplicate_identity_keys:
            raise ValueError(
                "Approved include rows overlap existing December baseline: "
                f"duplicate_hashes={len(duplicate_source_hashes)} duplicate_identities={len(duplicate_identity_keys)}"
            )

        if not dry_run:
            _insert_raw_rows(conn, include_rows, target_columns)
            conn.commit()

        return {
            "status": "dry_run" if dry_run else "inserted",
            "raw_rows_planned": len(include_rows),
            "raw_rows_inserted": 0 if dry_run else len(include_rows),
            "skipped_existing_duplicate_count": int(approved_plan["skip_count"]),
            "unresolved_candidate_count": int(approved_plan["block_count"]),
            "source_package_month": SOURCE_PACKAGE_MONTH,
            "canonical_event_month": TARGET_MONTH_KEY,
            "carry_forward_reason": "previous_package_timestamp_spill_to_target_month",
            "duplicate_source_hashes_blocked": len(duplicate_source_hashes),
            "duplicate_identity_keys_blocked": len(duplicate_identity_keys),
        }
    finally:
        conn.close()


def run_december_baseline_backfill(target_db: Path, data_root: Path) -> dict[str, Any]:
    pipeline = ETLPipelineModule(db_path=target_db)
    source_default = pipeline.resolve_historical_month_sources(TARGET_MONTH, data_root=data_root)
    compare_diagnostic = build_source_discovery_compare_diagnostics(
        month_labels=[TARGET_MONTH],
        data_root=data_root,
        pipeline=ETLPipelineModule(db_path=target_db, initialize_schema=False),
    )
    captured_stdout = StringIO()
    exception_payload = None
    try:
        with redirect_stdout(captured_stdout):
            result = pipeline.run_historical_canonical_backfill([TARGET_MONTH], data_root=data_root)
    except Exception as exc:
        result = {"status": "exception", "message": str(exc)}
        exception_payload = {
            "error_type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    return {
        "result": result,
        "source_discovery_mode": source_default.get("source_discovery_mode", "legacy"),
        "source_readiness": source_default.get("backfill_readiness"),
        "compare_diagnostic": compare_diagnostic,
        "exception": exception_payload,
        "captured_stdout": _sanitize_captured_stdout(captured_stdout.getvalue().splitlines()),
    }


def isolate_december_baseline_partitions(db_path: str | Path) -> dict[str, Any]:
    db = _validate_existing_target_db_path(Path(db_path))
    conn = sqlite3.connect(db)
    try:
        inspected = inspect_db_tables(conn)
        pruned: dict[str, Any] = {}
        skipped: dict[str, Any] = {}
        for table_name in sorted(inspected):
            columns = set(inspected[table_name])
            pre_total_count = _count_all_table_rows(conn, table_name)
            if table_name not in DECEMBER_PRUNE_RULES:
                skipped[table_name] = {
                    "columns": inspected[table_name],
                    "pre_total_row_count": pre_total_count,
                    "post_total_row_count": pre_total_count,
                    "reason": GLOBAL_OR_AMBIGUOUS_TABLE_REASONS.get(
                        table_name,
                        "No conservative December-specific delete predicate is defined for this table.",
                    ),
                }
                continue

            rule = DECEMBER_PRUNE_RULES[table_name]
            missing_columns = sorted(set(rule["required_columns"]) - columns)
            if missing_columns:
                skipped[table_name] = {
                    "columns": inspected[table_name],
                    "pre_total_row_count": pre_total_count,
                    "post_total_row_count": pre_total_count,
                    "reason": "Required columns are missing for conservative December pruning: " + ", ".join(missing_columns),
                }
                continue

            pre_count = _count_table_rows(conn, table_name, rule["where"], rule["params"])
            conn.execute(f"DELETE FROM {_quote_identifier(table_name)} WHERE {rule['where']}", rule["params"])
            post_count = _count_table_rows(conn, table_name, rule["where"], rule["params"])
            pruned[table_name] = {
                "delete_condition": rule["where"],
                "params": list(rule["params"]),
                "pre_prune_december_count": pre_count,
                "post_prune_december_count": post_count,
                "pre_total_row_count": pre_total_count,
                "post_total_row_count": _count_all_table_rows(conn, table_name),
                "deleted_rows": pre_count - post_count if isinstance(pre_count, int) and isinstance(post_count, int) else None,
                "reason": rule["reason"],
            }
        conn.commit()
        return {
            "tables_inspected": inspected,
            "tables_pruned": pruned,
            "tables_skipped": skipped,
        }
    finally:
        conn.close()


def summarize_december_temp_db(db_path: str | Path) -> dict[str, Any]:
    db = _validate_existing_target_db_path(Path(db_path))
    table_specs = {
        "raw_csi_event": {
            "count_sql": f"SELECT COUNT(*) AS row_count FROM raw_csi_event WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
            "params": (TARGET_MONTH_KEY,),
            "range_sql": f"SELECT MIN(raw_start_time) AS min_raw_start_time, MAX(raw_end_time) AS max_raw_end_time, SUM(raw_good_qty) AS raw_good_qty_sum FROM raw_csi_event WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
        },
        "csi_job_event": {
            "count_sql": f"SELECT COUNT(*) AS row_count FROM csi_job_event WHERE {SILVER_CSI_CANONICAL_MONTH_EXPR} = ?",
            "params": (TARGET_MONTH_KEY,),
            "range_sql": f"SELECT MIN(prod_start_ts) AS min_prod_start_ts, MAX(prod_end_ts) AS max_prod_end_ts, SUM(good_qty) AS good_qty_sum FROM csi_job_event WHERE {SILVER_CSI_CANONICAL_MONTH_EXPR} = ?",
        },
        "fact_machine_hour": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ?",
            "params": (TARGET_MONTH_KEY,),
            "range_sql": "SELECT MIN(hour_ts) AS min_hour_ts, MAX(hour_ts) AS max_hour_ts, SUM(good_qty) AS good_qty_sum, SUM(energy_total_kwh) AS energy_total_kwh_sum FROM fact_machine_hour WHERE substr(hour_ts, 1, 7) = ?",
        },
        "etl_csi_data": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM etl_csi_data WHERE month_year = ?",
            "params": (TARGET_MONTH,),
            "range_sql": "SELECT MIN(start_time) AS min_start_time, MAX(end_time) AS max_end_time, SUM(good_qty) AS good_qty_sum FROM etl_csi_data WHERE month_year = ?",
        },
        "raw_energy_hourly": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM raw_energy_hourly WHERE substr(raw_timestamp, 1, 7) = ?",
            "params": (TARGET_MONTH_KEY,),
        },
        "raw_mes_report": {
            "count_sql": "SELECT COUNT(*) AS row_count FROM raw_mes_report WHERE substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = ?",
            "params": (TARGET_MONTH_KEY,),
        },
    }
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        existing_tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        result: dict[str, Any] = {}
        for table_name, spec in table_specs.items():
            if table_name not in existing_tables:
                result[table_name] = {"present": False}
                continue
            table_result: dict[str, Any] = {"present": True}
            table_result["december_row_count"] = _query_one(conn, spec["count_sql"], spec.get("params", ()))
            if spec.get("range_sql"):
                table_result["range_and_aggregate"] = _query_one(conn, spec["range_sql"], spec.get("params", ()))
            result[table_name] = table_result
        return result
    finally:
        conn.close()


def inspect_december_duplicate_evidence(db_path: str | Path) -> dict[str, Any]:
    db = _validate_existing_target_db_path(Path(db_path))
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        raw_rows = _fetch_month_rows(conn, "raw_csi_event", RAW_CSI_CANONICAL_MONTH_EXPR)
        silver_rows = _fetch_month_rows(conn, "csi_job_event", SILVER_CSI_CANONICAL_MONTH_EXPR)
        return {
            "raw_csi_event": {
                "source_hash_duplicate_group_count": _source_hash_duplicate_group_count(raw_rows),
                "stable_identity_duplicate_group_count": _stable_identity_duplicate_group_count(
                    raw_rows,
                    _raw_identity_key,
                ),
            },
            "csi_job_event": {
                "source_hash_duplicate_group_count": _source_hash_duplicate_group_count(silver_rows),
                "stable_identity_duplicate_group_count": _stable_identity_duplicate_group_count(
                    silver_rows,
                    _silver_identity_key,
                ),
            },
        }
    finally:
        conn.close()


def build_carry_forward_traceability(db_path: str | Path, include_source_hashes: list[str]) -> dict[str, Any]:
    db = _validate_existing_target_db_path(Path(db_path))
    expected_hashes = set(include_source_hashes)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        raw_rows = _fetch_month_rows(conn, "raw_csi_event", RAW_CSI_CANONICAL_MONTH_EXPR)
        silver_rows = _fetch_month_rows(conn, "csi_job_event", SILVER_CSI_CANONICAL_MONTH_EXPR)
        raw_hashes = _source_hash_set(raw_rows)
        silver_hashes = _source_hash_set(silver_rows)
        raw_missing = sorted(expected_hashes - raw_hashes)
        silver_missing = sorted(expected_hashes - silver_hashes)
        return {
            "expected_include_count": len(expected_hashes),
            "raw_matched_count": len(expected_hashes) - len(raw_missing),
            "raw_unmatched_count": len(raw_missing),
            "silver_matched_count": len(expected_hashes) - len(silver_missing),
            "silver_unmatched_count": len(silver_missing),
            "raw_missing_hashes": raw_missing[:20],
            "silver_missing_hashes": silver_missing[:20],
        }
    finally:
        conn.close()


def compare_december_counts(
    baseline_counts: dict[str, Any],
    after_counts: dict[str, Any],
    approved_plan: dict[str, Any],
) -> dict[str, Any]:
    comparison = {
        "raw_csi_event_december_row_count": _count_delta(baseline_counts, after_counts, "raw_csi_event"),
        "csi_job_event_december_row_count": _count_delta(baseline_counts, after_counts, "csi_job_event"),
        "fact_machine_hour_december_row_count": _count_delta(baseline_counts, after_counts, "fact_machine_hour"),
        "csi_good_qty_sum": _aggregate_delta(baseline_counts, after_counts, "csi_job_event", "good_qty_sum"),
        "fact_machine_hour_good_qty_sum": _aggregate_delta(
            baseline_counts,
            after_counts,
            "fact_machine_hour",
            "good_qty_sum",
        ),
        "affected_machine_count": len(
            {_normalize_key_value(row.get("raw_machine_id_or_label")) for row in approved_plan["include_raw_rows"]}
        ),
        "affected_order_count": len({_normalize_key_value(row.get("raw_order_id")) for row in approved_plan["include_raw_rows"]}),
        "approved_include_good_qty_sum": _numeric_sum(approved_plan["include_raw_rows"], "raw_good_qty"),
    }
    return comparison


def _load_source_package_december_raw_rows(db_path: Path, source_relative: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in conn.execute(
                f"SELECT * FROM raw_csi_event WHERE {RAW_CSI_CANONICAL_MONTH_EXPR} = ?",
                (TARGET_MONTH_KEY,),
            ).fetchall()
        ]
    finally:
        conn.close()
    selected = [row for row in rows if _source_file_matches(row.get("source_file"), source_relative)]
    selected.sort(key=lambda row: (_raw_identity_key(row), str(row.get("source_row_hash") or "")))
    return selected


def _insert_raw_rows(conn: sqlite3.Connection, rows: list[dict[str, Any]], target_columns: list[str]) -> None:
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


def _fetch_month_rows(conn: sqlite3.Connection, table_name: str, month_expr: str) -> list[dict[str, Any]]:
    if table_name not in _existing_tables(conn):
        return []
    rows = conn.execute(
        f"SELECT * FROM {_quote_identifier(table_name)} WHERE {month_expr} = ?",
        (TARGET_MONTH_KEY,),
    ).fetchall()
    return [dict(row) for row in rows]


def _existing_source_hashes(conn: sqlite3.Connection, table_name: str, month_expr: str) -> set[str]:
    if table_name not in _existing_tables(conn):
        return set()
    columns = _table_columns(conn, table_name)
    if "source_row_hash" not in columns:
        return set()
    return {
        str(row[0])
        for row in conn.execute(
            f"SELECT source_row_hash FROM {_quote_identifier(table_name)} WHERE {month_expr} = ?",
            (TARGET_MONTH_KEY,),
        ).fetchall()
        if row[0] is not None and str(row[0]).strip()
    }


def _existing_raw_identity_keys(conn: sqlite3.Connection) -> set[tuple[str, ...]]:
    return {_raw_identity_key(row) for row in _fetch_month_rows(conn, "raw_csi_event", RAW_CSI_CANONICAL_MONTH_EXPR)}


def _raw_identity_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_key_value(row.get("raw_machine_id_or_label")),
        normalize_timestamp_for_gap_match(row.get("raw_start_time")),
        normalize_timestamp_for_gap_match(row.get("raw_end_time")),
        normalize_timestamp_for_gap_match(row.get("raw_prep_end_time")),
        _normalize_key_value(row.get("raw_order_id")),
        _normalize_key_value(row.get("raw_material")),
        _normalize_key_value(row.get("raw_good_qty")),
    )


def _silver_identity_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        _normalize_key_value(row.get("raw_machine_id_or_label")),
        normalize_timestamp_for_gap_match(row.get("prod_start_ts")),
        normalize_timestamp_for_gap_match(row.get("prod_end_ts")),
        normalize_timestamp_for_gap_match(row.get("prep_end_ts")),
        _normalize_key_value(row.get("order_id")),
        _normalize_key_value(row.get("material_code")),
        _normalize_key_value(row.get("good_qty")),
    )


def _source_hash_duplicate_group_count(rows: list[dict[str, Any]]) -> int:
    counts = Counter(str(row["source_row_hash"]) for row in rows if row.get("source_row_hash"))
    return sum(1 for count in counts.values() if count > 1)


def _source_hash_set(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row["source_row_hash"]) for row in rows if row.get("source_row_hash")}


def _stable_identity_duplicate_group_count(rows: list[dict[str, Any]], key_builder: Any) -> int:
    counts = Counter(key_builder(row) for row in rows)
    return sum(1 for count in counts.values() if count > 1)


def _duplicate_group_count(unique_keys: set[tuple[str, ...]], keys: list[tuple[str, ...]]) -> int:
    if len(unique_keys) == len(keys):
        return 0
    counts = Counter(keys)
    return sum(1 for count in counts.values() if count > 1)


def _source_file_matches(source_file: object, expected_relative_path: str) -> bool:
    if source_file is None:
        return False
    source_text = str(source_file).replace("\\", "/")
    expected_text = expected_relative_path.replace("\\", "/")
    return source_text.endswith(expected_text) or Path(source_text).name == Path(expected_text).name


def _count_delta(before: dict[str, Any], after: dict[str, Any], table_name: str) -> dict[str, Any]:
    before_value = _count_metric(before, table_name)
    after_value = _count_metric(after, table_name)
    return {"before": before_value, "after": after_value, "delta": _numeric_delta(after_value, before_value)}


def _aggregate_delta(
    before: dict[str, Any],
    after: dict[str, Any],
    table_name: str,
    metric_name: str,
) -> dict[str, Any]:
    before_value = _aggregate_metric(before, table_name, metric_name)
    after_value = _aggregate_metric(after, table_name, metric_name)
    return {"before": before_value, "after": after_value, "delta": _numeric_delta(after_value, before_value)}


def _count_metric(counts: dict[str, Any], table_name: str) -> Any:
    return counts.get(table_name, {}).get("december_row_count", {}).get("row_count")


def _aggregate_metric(counts: dict[str, Any], table_name: str, metric_name: str) -> Any:
    return counts.get(table_name, {}).get("range_and_aggregate", {}).get(metric_name)


def _numeric_delta(after: Any, before: Any) -> Any:
    if after is None or before is None:
        return None
    return after - before


def _numeric_sum(rows: list[dict[str, Any]], field_name: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(field_name)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric != numeric:
            continue
        total += numeric
    return total


def _sanitize_captured_stdout(lines: list[str]) -> list[str]:
    replacements = {
        "🎉": "SUCCESS:",
        "📊": "INFO:",
    }
    sanitized = []
    for line in lines:
        clean = line
        for source, replacement in replacements.items():
            clean = clean.replace(source, replacement)
        sanitized.append(clean)
    return sanitized


def _result_status(
    insertion: dict[str, Any],
    traceability: dict[str, Any],
    duplicates: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    duplicate_free = (
        duplicates["raw_csi_event"]["source_hash_duplicate_group_count"] == 0
        and duplicates["csi_job_event"]["source_hash_duplicate_group_count"] == 0
        and duplicates["raw_csi_event"]["stable_identity_duplicate_group_count"] == 0
        and duplicates["csi_job_event"]["stable_identity_duplicate_group_count"] == 0
    )
    expected_delta = comparison["raw_csi_event_december_row_count"]["delta"] == APPROVED_INCLUDE_COUNT
    if (
        insertion.get("raw_rows_inserted") == APPROVED_INCLUDE_COUNT
        and traceability.get("raw_unmatched_count") == 0
        and traceability.get("silver_unmatched_count") == 0
        and duplicate_free
        and expected_delta
    ):
        return "success"
    return "partial_error"


def _validate_boundary(source_package_month: str, target_month: str) -> None:
    if str(source_package_month).strip() != SOURCE_PACKAGE_MONTH or str(target_month).strip() != TARGET_MONTH:
        raise ValueError(
            "Only November 2025 -> December 2025 is supported by the Stage B10.5 reconciliation helper."
        )


def _validate_existing_target_db_path(db_path: Path) -> Path:
    resolved = db_path.expanduser().resolve(strict=False)
    if _path_is_relative_to(resolved, REPO_ROOT):
        raise ValueError(f"Refusing DB path inside repo: {resolved}")
    if _path_is_relative_to(resolved, ORIGINAL_RUNTIME_REPO_ROOT):
        raise ValueError(f"Refusing DB path inside original runtime repo: {resolved}")
    if resolved.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError(f"Target DB path must use a DB suffix: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"Target DB path does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Target DB path is not a file: {resolved}")
    return resolved


def inspect_db_tables(conn: sqlite3.Connection) -> dict[str, list[str]]:
    return {
        table_name: _table_columns(conn, table_name)
        for table_name in sorted(_existing_tables(conn))
    }


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [
        str(row["name"])
        if isinstance(row, sqlite3.Row)
        else str(row[1])
        for row in conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()
    ]


def _count_all_table_rows(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}").fetchone()[0])


def _count_table_rows(conn: sqlite3.Connection, table_name: str, where_sql: str, params: tuple[Any, ...]) -> int:
    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM {_quote_identifier(table_name)} WHERE {where_sql}",
            params,
        ).fetchone()[0]
    )


def _query_one(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}


def _normalize_key_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
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


def _path_is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(base.resolve(strict=False))
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
