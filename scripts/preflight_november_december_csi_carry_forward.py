#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.november_december_carry_forward_preflight import (
    build_november_december_csi_carry_forward_preflight,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build read-only November-to-December CSI carry-forward preflight evidence.",
    )
    parser.add_argument("--data-root", type=Path, default=None, help="Optional extension source-data root.")
    parser.add_argument("--source-package-db-path", type=Path, default=None, help="Optional read-only November DB.")
    parser.add_argument("--current-package-db-path", type=Path, default=None, help="Optional read-only December DB.")
    parser.add_argument("--json", action="store_true", help="Print full structured JSON.")
    args = parser.parse_args(argv)

    preflight = build_november_december_csi_carry_forward_preflight(
        data_root=args.data_root,
        source_package_db_path=args.source_package_db_path,
        current_package_db_path=args.current_package_db_path,
    )
    if args.json:
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
    else:
        _print_text_report(preflight)
    return 0


def _print_text_report(preflight: dict[str, Any]) -> None:
    identity = preflight["candidate_identity_evidence"]
    hash_evidence = preflight["source_row_hash_bronze_evidence"]
    overlap = preflight["current_december_overlap_check"]
    workbook_overlap = overlap["workbook_level_overlap"]
    bronze_overlap = overlap["bronze_db_overlap"]

    print("November-to-December CSI Carry-Forward Preflight")
    print(f"data_root: {preflight['data_root']}")
    print(f"source_package: {preflight['source_package_month']}")
    print(f"target_month: {preflight['target_month']}")
    print(f"candidate_count: {identity['candidate_count']}")
    print(f"candidate_count_matches_b10_1: {identity['candidate_count_matches_b10_1']}")
    print(f"distinct_machine_count: {identity['distinct_machine_count']}")
    print(f"distinct_order_count: {identity['distinct_order_count']}")
    print(f"good_qty_sum: {identity['good_qty_sum']}")
    print(f"timestamp_range: {identity['min_event_timestamp']} -> {identity['max_event_timestamp']}")
    print(f"canonical_month_distribution: {identity['canonical_month_distribution']}")
    print(f"duplicate_stable_identity_group_count: {identity['duplicate_stable_identity_group_count']}")
    print(f"source_row_hash_available_directly_in_workbook: {identity['source_row_hash_available_directly_in_workbook']}")
    print(f"source_row_hash_bronze_status: {hash_evidence['status']}")
    print(f"source_row_hash_available: {hash_evidence['source_row_hash_available']}")
    print(f"workbook_overlap_status: {workbook_overlap['status']}")
    print(f"workbook_overlap_candidate_count: {workbook_overlap['candidate_overlap_count']}")
    print(f"bronze_overlap_status: {bronze_overlap['status']}")
    print(f"strongest_available_overlap_evidence: {overlap['strongest_available_evidence']}")
    print(f"proof_gaps: {preflight['proof_gaps']}")


if __name__ == "__main__":
    raise SystemExit(main())
