#!/usr/bin/env python3
"""Run repeatable historical canonical Silver/Gold backfill on the shared DB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_materializer import CanonicalMaterializer
from core.runtime_paths import get_database_path
from modules.etl_module import ETLPipelineModule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "months",
        nargs="+",
        help='Month labels to backfill, for example "January 2025" "February 2025".',
    )
    parser.add_argument(
        "--db-path",
        default=str(get_database_path()),
        help="SQLite database path. Defaults to the shared runtime DB.",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help=(
            "Optional historical dataset root override. "
            "When omitted, month-based defaults are used: repo Jan-Jun data for legacy months "
            "and the sibling Task13 extension package for Jul 2025 onward."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pipeline = ETLPipelineModule(db_path=args.db_path)
    materializer = CanonicalMaterializer(db_path=args.db_path)

    before = materializer.summarize_month_coverage()
    result = pipeline.run_historical_canonical_backfill(args.months, data_root=args.data_root)
    after = materializer.summarize_month_coverage()

    print(
        json.dumps(
            {
                "db_path": args.db_path,
                "data_root": args.data_root,
                "before": before,
                "result": result,
                "after": after,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
