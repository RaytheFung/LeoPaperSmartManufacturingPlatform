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

from core.november_december_hash_gap_decision import build_november_december_hash_gap_decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve November-to-December source-row-hash gaps with read-only evidence.",
    )
    parser.add_argument("--db-path", type=Path, required=True, help="Explicit read-only DB path to inspect.")
    parser.add_argument("--data-root", type=Path, default=None, help="Optional extension source-data root.")
    parser.add_argument("--json", action="store_true", help="Print full structured JSON.")
    args = parser.parse_args(argv)

    decision = build_november_december_hash_gap_decision(
        db_path=args.db_path,
        data_root=args.data_root,
    )
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        _print_text_report(decision)
    return 0


def _print_text_report(decision: dict[str, Any]) -> None:
    gap = decision["source_hash_gap_reproduction"]
    attempts = decision["alternative_matching_attempts"]
    plan = decision["include_skip_block_plan"]
    fallback = decision["fallback_policy_decision"]
    safety = decision["b10_5_execution_safety_decision"]

    print("November-to-December Source-Hash Gap Decision")
    print(f"db_path: {decision['db_evidence_source']['db_path']}")
    print(f"opened_read_only: {decision['db_evidence_source']['opened_read_only']}")
    print(f"candidate_count: {decision['candidate_count']}")
    print(f"source_hash_gap_count: {gap['source_hash_gap_count']}")
    print(f"gap_count_matches_b10_3: {gap['gap_count_matches_b10_3']}")
    print(f"root_cause_classification: {decision['root_cause_classification']}")
    print(f"hash_resolved_count: {attempts['null_equivalent_identity_hash_resolved_count']}")
    print(f"stable_identity_fallback_safe_count: {attempts['stable_identity_fallback_safe_count']}")
    print(f"skip_due_existing_duplicate_count: {attempts['skip_due_existing_duplicate_count']}")
    print(f"block_unresolved_count: {attempts['block_unresolved_count']}")
    print(f"fallback_policy: {fallback['fallback_policy']}")
    print(f"include_skip_block_plan: {plan}")
    print(f"safe_for_b10_5_temp_reconciliation: {safety['safe_for_b10_5_temp_reconciliation']}")
    print(f"safety_reason: {safety['reason']}")


if __name__ == "__main__":
    raise SystemExit(main())
