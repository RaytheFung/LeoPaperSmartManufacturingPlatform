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

from modules.etl_module import ETLPipelineModule


EXTENSION_MONTH_LABELS = [
    "July 2025",
    "August 2025",
    "September 2025",
    "October 2025",
    "November 2025",
    "December 2025",
    "January 2026",
    "February 2026",
    "March 2026",
]
EXPECTED_BLOCKED_MONTHS = {"March 2026"}


def build_source_discovery_compare_diagnostics(
    month_labels: list[str] | tuple[str, ...] = tuple(EXTENSION_MONTH_LABELS),
    data_root: str | Path | None = None,
    pipeline: ETLPipelineModule | None = None,
) -> dict[str, Any]:
    resolver = pipeline or ETLPipelineModule(initialize_schema=False)
    rows = []
    for month_label in month_labels:
        expected_blocked = month_label in EXPECTED_BLOCKED_MONTHS
        try:
            payload = resolver.resolve_historical_month_sources(
                month_label,
                data_root=data_root,
                discovery_mode="compare",
            )
            equivalence = payload.get("manifest_equivalence", {})
            legacy_error = equivalence.get("legacy_error")
            manifest_error = equivalence.get("manifest_error")
            row = {
                "month_label": month_label,
                "backfill_readiness": payload.get("backfill_readiness"),
                "legacy_status": "blocked" if _is_blocked_error(legacy_error) else "resolved",
                "manifest_status": "blocked" if _is_blocked_error(manifest_error) else "resolved",
                "matches": bool(equivalence.get("matches")),
                "differences": equivalence.get("differences", []),
                "expected_blocked": expected_blocked,
                "errors": {
                    "legacy": legacy_error,
                    "manifest": manifest_error,
                },
            }
        except Exception as exc:
            row = {
                "month_label": month_label,
                "backfill_readiness": None,
                "legacy_status": "error",
                "manifest_status": "error",
                "matches": False,
                "differences": [],
                "expected_blocked": expected_blocked,
                "errors": {
                    "diagnostic": {
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                },
            }
        row["ok"] = _row_is_ok(row)
        rows.append(row)

    accepted_rows = [row for row in rows if not row["expected_blocked"]]
    blocked_rows = [row for row in rows if row["expected_blocked"]]
    success = all(row["ok"] for row in rows)
    return {
        "success": success,
        "data_root": str(Path(data_root)) if data_root is not None else "default",
        "month_count": len(rows),
        "accepted_month_count": len(accepted_rows),
        "expected_blocked_month_count": len(blocked_rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare legacy and manifest source discovery without running ETL.",
    )
    parser.add_argument("--data-root", type=Path, default=None, help="Optional extension source-data root.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON instead of text.")
    args = parser.parse_args(argv)

    diagnostics = build_source_discovery_compare_diagnostics(data_root=args.data_root)
    if args.json:
        print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    else:
        _print_text_report(diagnostics)
    return 0 if diagnostics["success"] else 1


def _row_is_ok(row: dict[str, Any]) -> bool:
    if row["expected_blocked"]:
        return (
            row["backfill_readiness"] == "blocked"
            and row["legacy_status"] == "blocked"
            and row["manifest_status"] == "blocked"
        )
    return (
        row["matches"]
        and row["legacy_status"] == "resolved"
        and row["manifest_status"] == "resolved"
        and not row["differences"]
    )


def _is_blocked_error(error_payload: Any) -> bool:
    return bool(isinstance(error_payload, dict) and error_payload.get("blocked"))


def _print_text_report(diagnostics: dict[str, Any]) -> None:
    print("Source Discovery Compare Diagnostic")
    print(f"data_root: {diagnostics['data_root']}")
    print(f"months_checked: {diagnostics['month_count']}")
    print("")
    for row in diagnostics["rows"]:
        status = "OK" if row["ok"] else "FAIL"
        if row["expected_blocked"]:
            summary = "expected blocked"
        elif row["matches"]:
            summary = "legacy and manifest match"
        else:
            summary = "legacy and manifest differ or errored"
        print(
            f"- {row['month_label']}: {status}; {summary}; "
            f"legacy={row['legacy_status']}; manifest={row['manifest_status']}; "
            f"readiness={row['backfill_readiness']}"
        )
        for difference in row["differences"]:
            print(f"  difference: {difference}")
        for mode_name, error_payload in row["errors"].items():
            if error_payload:
                print(f"  {mode_name}_error: {error_payload['message']}")
    print("")
    print(f"overall: {'PASS' if diagnostics['success'] else 'FAIL'}")


if __name__ == "__main__":
    raise SystemExit(main())
