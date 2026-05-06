"""Read-only CSI boundary-month source-package inventory helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.data_contracts import load_source_manifest
from core.runtime_paths import get_extended_raw_dataset_root
from core.source_manifest_discovery import (
    month_key_to_label,
    resolve_manifest_month_sources,
)


DEFAULT_MONTH_KEYS = (
    "2025-07",
    "2025-08",
    "2025-09",
    "2025-10",
    "2025-11",
    "2025-12",
    "2026-01",
    "2026-02",
)

CSI_CANONICAL_TIMESTAMP_COLUMNS = {
    "start": "工程開始時間",
    "end": "工程結束時間",
    "prep_end": "準備結束時間",
    "shift_date": "班次內日期",
}
CSI_IDENTITY_COLUMNS = {
    "machine": "機台編號",
    "order": "作业",
    "material": "物料",
    "good_qty": "正品數量",
}
SOURCE_ROW_HASH_COLUMNS = ("source_row_hash", "source_hash", "raw_source_row_hash")


@dataclass(frozen=True)
class InventoryRunConfig:
    data_root: Path
    month_keys: tuple[str, ...] = DEFAULT_MONTH_KEYS


def build_csi_boundary_candidate_inventory(
    data_root: str | Path | None = None,
    month_keys: tuple[str, ...] | list[str] = DEFAULT_MONTH_KEYS,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inventory accepted extension CSI packages without DB writes or ETL.

    The helper reads only CSI source workbooks resolved through the source
    manifest. It does not create databases, run ETL/backfill/materialization, or
    mutate source files.
    """
    root = Path(data_root) if data_root is not None else get_extended_raw_dataset_root()
    root = root.expanduser().resolve(strict=False)
    config = InventoryRunConfig(data_root=root, month_keys=tuple(month_keys))
    source_manifest = manifest if manifest is not None else load_source_manifest()

    package_rows = []
    for month_key in config.month_keys:
        package_rows.append(_inspect_month_package(month_key, config.data_root, source_manifest))

    resolved_packages = [row for row in package_rows if row["status"] == "resolved"]
    unresolved_packages = [row for row in package_rows if row["status"] != "resolved"]
    candidate_rows = [
        row
        for row in resolved_packages
        if row["boundary_candidate_count"] and row["boundary_candidate_count"] > 0
    ]
    recommendation = _select_recommended_candidate(candidate_rows, resolved_packages)

    return {
        "purpose": "CSI boundary-month candidate inventory across accepted extension source packages.",
        "data_root": str(config.data_root),
        "month_keys": list(config.month_keys),
        "uses_manifest_source_discovery": True,
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "writes_db": False,
        "source_packages": package_rows,
        "resolved_package_count": len(resolved_packages),
        "unresolved_package_count": len(unresolved_packages),
        "total_rows": sum(row["total_rows"] or 0 for row in resolved_packages),
        "total_boundary_candidate_count": sum(
            row["boundary_candidate_count"] or 0 for row in resolved_packages
        ),
        "total_forward_spill_count": sum(row["forward_spill_count"] or 0 for row in resolved_packages),
        "total_backward_spill_count": sum(row["backward_spill_count"] or 0 for row in resolved_packages),
        "total_other_out_of_range_count": sum(
            row["other_out_of_range_count"] or 0 for row in resolved_packages
        ),
        "unresolved_packages": unresolved_packages,
        "recommended_b10_2_target_boundary": recommendation,
    }


def canonical_csi_event_month(row: dict[str, Any]) -> str | None:
    """Return the first available CSI canonical event month as YYYY-MM."""
    for column in (
        CSI_CANONICAL_TIMESTAMP_COLUMNS["start"],
        CSI_CANONICAL_TIMESTAMP_COLUMNS["end"],
        CSI_CANONICAL_TIMESTAMP_COLUMNS["prep_end"],
        CSI_CANONICAL_TIMESTAMP_COLUMNS["shift_date"],
    ):
        month_key = _month_key_from_value(row.get(column))
        if month_key:
            return month_key
    return None


def classify_boundary_direction(source_month_key: str, canonical_month_key: str | None) -> str:
    if not canonical_month_key or canonical_month_key == source_month_key:
        return "same_month"
    source_period = pd.Period(source_month_key, freq="M")
    canonical_period = pd.Period(canonical_month_key, freq="M")
    delta = canonical_period.ordinal - source_period.ordinal
    if delta == 1:
        return "forward_spill_to_next_month"
    if delta == -1:
        return "backward_spill_to_previous_month"
    return "other_out_of_range"


def _inspect_month_package(
    month_key: str,
    data_root: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    month_label = month_key_to_label(month_key)
    base_row = {
        "source_package_month": month_label,
        "source_package_month_key": month_key,
        "status": "unresolved",
        "csi_file": None,
        "relative_csi_file": None,
        "total_rows": None,
        "same_month_count": None,
        "boundary_candidate_count": None,
        "forward_spill_count": None,
        "backward_spill_count": None,
        "other_out_of_range_count": None,
        "source_row_hash_available_directly": None,
        "source_row_hash_note": None,
        "identity_fields_available": None,
        "affected_machine_count": None,
        "affected_order_count": None,
        "good_qty_sum": None,
        "min_event_timestamp": None,
        "max_event_timestamp": None,
        "canonical_month_distribution": {},
        "direction_distribution": {},
        "candidate_target_month_distribution": {},
        "candidate_duplicate_identity_group_count": None,
        "candidate_duplicate_identity_row_count": None,
        "top_machine_summary": [],
        "top_order_summary": [],
        "error": None,
    }
    try:
        sources = resolve_manifest_month_sources(month_key, data_root=data_root, manifest=manifest)
        csi_file = sources.get("csi_file")
        if not csi_file:
            raise ValueError(f"No CSI source file is defined for {month_label}.")
        csi_path = _validate_source_path(csi_file, data_root)
        df = _read_csi_source_file(csi_path)
        return _summarize_source_dataframe(base_row, df, month_key, csi_path, data_root)
    except Exception as exc:
        base_row["error"] = {
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        }
        return base_row


def _read_csi_source_file(path: Path) -> pd.DataFrame:
    read_kwargs: dict[str, Any] = {}
    if path.suffix.lower() == ".xls":
        read_kwargs["engine"] = "xlrd"
    return pd.read_excel(path, **read_kwargs)


def _summarize_source_dataframe(
    base_row: dict[str, Any],
    df: pd.DataFrame,
    month_key: str,
    csi_path: Path,
    data_root: Path,
) -> dict[str, Any]:
    _require_timestamp_columns(df)
    working = df.copy()
    canonical_months = [canonical_csi_event_month(row) for row in working.to_dict("records")]
    directions = [classify_boundary_direction(month_key, month) for month in canonical_months]
    working["_canonical_event_month"] = canonical_months
    working["_boundary_direction"] = directions

    candidate_mask = working["_boundary_direction"] != "same_month"
    candidates = working.loc[candidate_mask].copy()
    direction_counter = Counter(directions)
    canonical_counter = Counter(str(month) for month in canonical_months if month)
    candidate_target_counter = Counter(
        str(month) for month in candidates["_canonical_event_month"].tolist() if month
    )
    duplicate_summary = _candidate_duplicate_identity_summary(candidates)
    timestamp_values = _candidate_timestamp_values(candidates)
    hash_columns = [column for column in SOURCE_ROW_HASH_COLUMNS if column in working.columns]

    base_row.update(
        {
            "status": "resolved",
            "csi_file": str(csi_path),
            "relative_csi_file": str(csi_path.relative_to(data_root)),
            "total_rows": int(len(working)),
            "same_month_count": int(direction_counter.get("same_month", 0)),
            "boundary_candidate_count": int(len(candidates)),
            "forward_spill_count": int(direction_counter.get("forward_spill_to_next_month", 0)),
            "backward_spill_count": int(direction_counter.get("backward_spill_to_previous_month", 0)),
            "other_out_of_range_count": int(direction_counter.get("other_out_of_range", 0)),
            "source_row_hash_available_directly": bool(hash_columns),
            "source_row_hash_note": (
                f"direct columns present: {', '.join(hash_columns)}"
                if hash_columns
                else "not present in source workbook; compute from Bronze/raw payload later if needed"
            ),
            "identity_fields_available": _identity_fields_available(working),
            "affected_machine_count": _distinct_count(candidates, CSI_IDENTITY_COLUMNS["machine"]),
            "affected_order_count": _distinct_count(candidates, CSI_IDENTITY_COLUMNS["order"]),
            "good_qty_sum": _numeric_sum(candidates, CSI_IDENTITY_COLUMNS["good_qty"]),
            "min_event_timestamp": min(timestamp_values).isoformat(sep=" ") if timestamp_values else None,
            "max_event_timestamp": max(timestamp_values).isoformat(sep=" ") if timestamp_values else None,
            "canonical_month_distribution": dict(sorted(canonical_counter.items())),
            "direction_distribution": dict(sorted(direction_counter.items())),
            "candidate_target_month_distribution": dict(sorted(candidate_target_counter.items())),
            "candidate_duplicate_identity_group_count": duplicate_summary["group_count"],
            "candidate_duplicate_identity_row_count": duplicate_summary["row_count"],
            "top_machine_summary": _top_group_summary(candidates, CSI_IDENTITY_COLUMNS["machine"]),
            "top_order_summary": _top_group_summary(candidates, CSI_IDENTITY_COLUMNS["order"]),
        }
    )
    return base_row


def _require_timestamp_columns(df: pd.DataFrame) -> None:
    missing = [
        column
        for column in CSI_CANONICAL_TIMESTAMP_COLUMNS.values()
        if column not in df.columns
    ]
    if missing:
        raise ValueError("CSI source is missing required timestamp columns: " + ", ".join(missing))


def _validate_source_path(path_value: str, data_root: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        resolved = path.expanduser().resolve(strict=False)
    else:
        resolved = (data_root / path).expanduser().resolve(strict=False)
    root = data_root.expanduser().resolve(strict=False)
    if not _path_is_relative_to(resolved, root):
        raise ValueError(f"Resolved CSI source path escapes data_root: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"CSI source file not found: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"CSI source path is not a file: {resolved}")
    return resolved


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _month_key_from_value(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.strftime("%Y-%m")


def _identity_fields_available(df: pd.DataFrame) -> dict[str, bool]:
    return {
        logical_name: column in df.columns
        for logical_name, column in CSI_IDENTITY_COLUMNS.items()
    }


def _distinct_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns or df.empty:
        return 0
    return int(df[column].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique())


def _numeric_sum(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _candidate_timestamp_values(df: pd.DataFrame) -> list[pd.Timestamp]:
    values: list[pd.Timestamp] = []
    if df.empty:
        return values
    for column in CSI_CANONICAL_TIMESTAMP_COLUMNS.values():
        if column not in df.columns:
            continue
        parsed = pd.to_datetime(df[column], errors="coerce")
        values.extend([value for value in parsed.tolist() if not pd.isna(value)])
    return values


def _top_group_summary(df: pd.DataFrame, group_column: str, limit: int = 5) -> list[dict[str, Any]]:
    if df.empty or group_column not in df.columns:
        return []
    qty_column = CSI_IDENTITY_COLUMNS["good_qty"]
    order_column = CSI_IDENTITY_COLUMNS["order"]
    rows = []
    for group_value, group_df in df.groupby(group_column, dropna=True):
        row = {
            group_column: str(group_value),
            "row_count": int(len(group_df)),
            "good_qty_sum": _numeric_sum(group_df, qty_column),
        }
        if order_column in group_df.columns:
            row["distinct_order_count"] = _distinct_count(group_df, order_column)
        rows.append(row)
    rows.sort(key=lambda item: (item["good_qty_sum"], item["row_count"], str(item[group_column])), reverse=True)
    return rows[:limit]


def _candidate_duplicate_identity_summary(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {"group_count": 0, "row_count": 0}
    required_columns = [
        CSI_IDENTITY_COLUMNS["machine"],
        CSI_CANONICAL_TIMESTAMP_COLUMNS["start"],
        CSI_CANONICAL_TIMESTAMP_COLUMNS["end"],
        CSI_CANONICAL_TIMESTAMP_COLUMNS["prep_end"],
        CSI_IDENTITY_COLUMNS["order"],
        CSI_IDENTITY_COLUMNS["material"],
        CSI_IDENTITY_COLUMNS["good_qty"],
    ]
    if any(column not in df.columns for column in required_columns):
        return {"group_count": 0, "row_count": 0}
    normalized = df[required_columns].fillna("").astype(str).apply(lambda col: col.str.strip())
    grouped = normalized.groupby(required_columns, dropna=False).size()
    duplicate_groups = grouped[grouped > 1]
    return {
        "group_count": int(len(duplicate_groups)),
        "row_count": int(duplicate_groups.sum()) if not duplicate_groups.empty else 0,
    }


def _select_recommended_candidate(
    candidate_rows: list[dict[str, Any]],
    resolved_packages: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_month_keys = {row["source_package_month_key"] for row in resolved_packages}
    scored = []
    for row in candidate_rows:
        target_distribution = row.get("candidate_target_month_distribution") or {}
        for target_month_key, count in target_distribution.items():
            direction = classify_boundary_direction(row["source_package_month_key"], target_month_key)
            if direction != "forward_spill_to_next_month":
                continue
            if target_month_key not in accepted_month_keys:
                continue
            identity_fields = row.get("identity_fields_available") or {}
            stable_identity_available = all(identity_fields.values())
            if not stable_identity_available:
                continue
            scored.append(
                {
                    "source_package_month": row["source_package_month"],
                    "source_package_month_key": row["source_package_month_key"],
                    "target_canonical_month": month_key_to_label(target_month_key),
                    "target_canonical_month_key": target_month_key,
                    "candidate_count": int(count),
                    "direction": direction,
                    "source_package_and_target_package_accepted": True,
                    "stable_identity_fields_available": stable_identity_available,
                    "source_row_hash_available_directly": bool(row["source_row_hash_available_directly"]),
                    "candidate_duplicate_identity_group_count": int(
                        row.get("candidate_duplicate_identity_group_count") or 0
                    ),
                    "candidate_duplicate_identity_row_count": int(row.get("candidate_duplicate_identity_row_count") or 0),
                    "reason": (
                        "Selected as the clear forward spill with the lowest duplicate-identity complexity, accepted "
                        "source and target packages, complete stable identity fields, and then the lowest count."
                    ),
                }
            )

    if not scored:
        return {
            "status": "no_recommendation",
            "reason": "No clear accepted-package forward spill candidate with stable identity fields was found.",
        }
    scored.sort(
        key=lambda item: (
            item["candidate_duplicate_identity_group_count"],
            item["candidate_count"],
            item["source_package_month_key"],
        )
    )
    recommendation = dict(scored[0])
    recommendation["status"] = "recommended"
    return recommendation


__all__ = [
    "CSI_CANONICAL_TIMESTAMP_COLUMNS",
    "DEFAULT_MONTH_KEYS",
    "build_csi_boundary_candidate_inventory",
    "canonical_csi_event_month",
    "classify_boundary_direction",
]
