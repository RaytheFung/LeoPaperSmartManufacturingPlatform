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

from core.november_december_overlap_proof import build_november_december_overlap_proof


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prove November-to-December CSI overlap against read-only Bronze/Silver DB evidence.",
    )
    parser.add_argument("--db-path", type=Path, required=True, help="Explicit read-only DB path to inspect.")
    parser.add_argument("--data-root", type=Path, default=None, help="Optional extension source-data root.")
    parser.add_argument("--json", action="store_true", help="Print full structured JSON.")
    args = parser.parse_args(argv)

    proof = build_november_december_overlap_proof(
        db_path=args.db_path,
        data_root=args.data_root,
    )
    if args.json:
        print(json.dumps(proof, ensure_ascii=False, indent=2))
    else:
        _print_text_report(proof)
    return 0


def _print_text_report(proof: dict[str, Any]) -> None:
    candidate = proof["candidate_identity_reproduction"]
    workbook = proof["workbook_level_overlap_reproduction"]
    bronze = proof["bronze_raw_silver_overlap_proof"]
    plan = proof["include_skip_unresolved_plan"]
    hash_evidence = proof["source_row_hash_evidence"]
    safety = proof["b10_4_execution_safety_decision"]

    print("November-to-December CSI Bronze/Hash Overlap Proof")
    print(f"db_path: {proof['db_evidence_source']['db_path']}")
    print(f"opened_read_only: {proof['db_evidence_source']['opened_read_only']}")
    print(f"candidate_count: {candidate['candidate_count']}")
    print(f"candidate_count_matches_b10_2: {candidate['candidate_count_matches_b10_2']}")
    print(f"workbook_overlap_count: {workbook['overlap_count']}")
    print(f"workbook_overlap_count_matches_b10_2: {workbook['overlap_count_matches_b10_2']}")
    print(f"raw_december_canonical_row_count: {bronze['raw_december_canonical_row_count']}")
    print(f"silver_december_canonical_row_count: {bronze['silver_december_canonical_row_count']}")
    print(f"raw_source_package_candidate_scope_row_count: {bronze['raw_source_package_candidate_scope_row_count']}")
    print(f"raw_current_package_target_scope_row_count: {bronze['raw_current_package_target_scope_row_count']}")
    print(f"seven_overlap_summary: {proof['seven_overlap_classification']['summary']}")
    print(f"include_count: {plan['include_count']}")
    print(f"skip_count: {plan['skip_count']}")
    print(f"unresolved_count: {plan['unresolved_count']}")
    print(f"source_row_hash_available_for_all_candidates: {hash_evidence['source_row_hash_available_for_all_candidates']}")
    print(f"safe_for_b10_4_temp_reconciliation: {safety['safe_for_b10_4_temp_reconciliation']}")
    print(f"safety_reason: {safety['reason']}")


if __name__ == "__main__":
    raise SystemExit(main())
