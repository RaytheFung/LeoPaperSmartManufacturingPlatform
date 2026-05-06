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

from core.csi_boundary_inventory import DEFAULT_MONTH_KEYS, build_csi_boundary_candidate_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inventory CSI boundary-month candidates from accepted extension source packages.",
    )
    parser.add_argument("--data-root", type=Path, default=None, help="Optional extension source-data root.")
    parser.add_argument(
        "--months",
        nargs="+",
        default=list(DEFAULT_MONTH_KEYS),
        help="Month keys to inspect, for example 2025-07 2025-08.",
    )
    parser.add_argument("--json", action="store_true", help="Print full structured JSON.")
    args = parser.parse_args(argv)

    inventory = build_csi_boundary_candidate_inventory(
        data_root=args.data_root,
        month_keys=tuple(args.months),
    )
    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
    else:
        _print_text_report(inventory)
    return 0 if inventory["unresolved_package_count"] == 0 else 1


def _print_text_report(inventory: dict[str, Any]) -> None:
    print("CSI Boundary Candidate Inventory")
    print(f"data_root: {inventory['data_root']}")
    print(f"resolved_package_count: {inventory['resolved_package_count']}")
    print(f"unresolved_package_count: {inventory['unresolved_package_count']}")
    print(f"total_rows: {inventory['total_rows']}")
    print(f"total_boundary_candidate_count: {inventory['total_boundary_candidate_count']}")
    print(f"total_forward_spill_count: {inventory['total_forward_spill_count']}")
    print(f"total_backward_spill_count: {inventory['total_backward_spill_count']}")
    print(f"total_other_out_of_range_count: {inventory['total_other_out_of_range_count']}")
    print("")
    print("Packages:")
    for row in inventory["source_packages"]:
        if row["status"] != "resolved":
            error = row.get("error") or {}
            print(
                f"- {row['source_package_month']}: unresolved; "
                f"{error.get('error_type')}: {error.get('message')}"
            )
            continue
        print(
            f"- {row['source_package_month']}: rows={row['total_rows']}; "
            f"boundary={row['boundary_candidate_count']}; "
            f"forward={row['forward_spill_count']}; "
            f"backward={row['backward_spill_count']}; "
            f"other={row['other_out_of_range_count']}; "
            f"targets={row['candidate_target_month_distribution']}"
        )
    print("")
    print("Recommended B10.2 target:")
    print(json.dumps(inventory["recommended_b10_2_target_boundary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
