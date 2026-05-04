from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.data_contracts import load_source_manifest, validate_manifest_shape


_SOURCE_FILE_MAP_KEY = "month_source_files"
_REQUIRED_MONTH_SOURCE_FIELDS = {
    "scope_id",
    "canonical_scope_status",
    "energy_files",
    "csi_file",
    "mes_file",
    "family_status",
    "backfill_readiness",
    "notes",
}
_SOURCE_DOMAINS = ("energy", "csi", "mes")
_CANONICAL_SCOPE_STATUSES = {"accepted", "blocked_out_of_scope"}
_BACKFILL_READINESS_VALUES = {"ready", "ready_with_flags", "blocked"}
_FAMILY_STATUS_VALUES = {"complete", "partial", "blocked"}


def month_label_to_key(month_label: str) -> str:
    cleaned_label = str(month_label or "").strip()
    if len(cleaned_label) == 7 and cleaned_label[4] == "-":
        _parse_month_key(cleaned_label)
        return cleaned_label
    try:
        return datetime.strptime(cleaned_label, "%B %Y").strftime("%Y-%m")
    except ValueError as exc:
        raise ValueError(f"Invalid month label: {month_label}") from exc


def month_key_to_label(month_key: str) -> str:
    return _parse_month_key(month_key).strftime("%B %Y")


def get_manifest_month_source_files(
    month_key_or_label: str,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_manifest = manifest if manifest is not None else load_source_manifest()
    _validate_month_source_file_map(source_manifest)
    month_key = month_label_to_key(month_key_or_label)
    month_map = source_manifest[_SOURCE_FILE_MAP_KEY]
    if month_key not in month_map:
        raise ValueError(f"No manifest source file map is defined for {month_key}.")
    spec = dict(month_map[month_key])
    spec["month_key"] = month_key
    spec["month_label"] = month_key_to_label(month_key)
    return spec


def build_manifest_source_availability_dataframe(
    data_root: str | Path,
    manifest: dict[str, Any] | None = None,
) -> pd.DataFrame:
    source_manifest = manifest if manifest is not None else load_source_manifest()
    _validate_month_source_file_map(source_manifest)
    rows = []
    for month_key in sorted(source_manifest[_SOURCE_FILE_MAP_KEY]):
        spec = get_manifest_month_source_files(month_key, source_manifest)
        resolved = _resolve_spec_paths(spec, data_root)
        file_candidates = [
            *resolved["energy_files"],
            *([resolved["csi_file"]] if resolved.get("csi_file") else []),
            *([resolved["mes_file"]] if resolved.get("mes_file") else []),
        ]
        missing_files = [path for path in file_candidates if path and not Path(path).exists()]
        readiness = _display_readiness(
            spec["backfill_readiness"],
            blocked=bool(missing_files) or spec["backfill_readiness"] == "blocked",
        )
        rows.append(
            {
                "Month": spec["month_label"],
                "Energy": spec["family_status"]["energy"].title(),
                "CSI": spec["family_status"]["csi"].title(),
                "MES": spec["family_status"]["mes"].title(),
                "Backfill Readiness": readiness,
                "Notes": " | ".join(spec["notes"]) or "none",
                "Missing Files": " | ".join(str(path) for path in missing_files) or "none",
            }
        )
    return pd.DataFrame(rows)


def resolve_manifest_month_sources(
    month_key_or_label: str,
    data_root: str | Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_manifest = manifest if manifest is not None else load_source_manifest()
    spec = get_manifest_month_source_files(month_key_or_label, source_manifest)
    if spec["canonical_scope_status"] != "accepted" or spec["backfill_readiness"] == "blocked":
        raise ValueError(
            "Manifest source discovery blocks "
            f"{spec['month_label']}: canonical scope status is {spec['canonical_scope_status']}."
        )
    resolved = _resolve_spec_paths(spec, data_root)
    missing_files = [
        path
        for path in [
            *resolved["energy_files"],
            *([resolved["csi_file"]] if resolved.get("csi_file") else []),
            *([resolved["mes_file"]] if resolved.get("mes_file") else []),
        ]
        if data_root is not None and path and not Path(path).exists()
    ]
    if missing_files:
        raise ValueError(
            "Manifest source discovery cannot resolve "
            f"{spec['month_label']} because files are missing: "
            + ", ".join(str(path) for path in missing_files)
        )
    return {
        "dataset_root": str(Path(data_root)) if data_root is not None else spec["scope_id"],
        "energy_files": [str(path) for path in resolved["energy_files"]],
        "csi_file": str(resolved["csi_file"]) if resolved.get("csi_file") else None,
        "mes_file": str(resolved["mes_file"]) if resolved.get("mes_file") else None,
        "family_status": dict(spec["family_status"]),
        "backfill_readiness": spec["backfill_readiness"],
        "notes": list(spec["notes"]),
        "month_key": spec["month_key"],
        "month_label": spec["month_label"],
        "canonical_scope_status": spec["canonical_scope_status"],
    }


def compare_manifest_to_legacy_extension_mapping(
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from modules.etl_module import EXTENSION_MONTH_SOURCE_MAPPINGS

    source_manifest = manifest if manifest is not None else load_source_manifest()
    differences = []
    checked_months = []
    for month_label, legacy_spec in EXTENSION_MONTH_SOURCE_MAPPINGS.items():
        checked_months.append(month_label)
        manifest_spec = get_manifest_month_source_files(month_label, source_manifest)
        legacy_readiness = _legacy_readiness(legacy_spec["family_status"])
        comparisons = {
            "energy_files": legacy_spec["energy_files"] == manifest_spec["energy_files"],
            "csi_file": legacy_spec.get("csi_file") == manifest_spec.get("csi_file"),
            "mes_file": legacy_spec.get("mes_file") == manifest_spec.get("mes_file"),
            "family_status": legacy_spec["family_status"] == manifest_spec["family_status"],
            "backfill_readiness": legacy_readiness == manifest_spec["backfill_readiness"],
        }
        failed = sorted(name for name, matched in comparisons.items() if not matched)
        if failed:
            differences.append({"month": month_label, "fields": failed})
    return {
        "matches": not differences,
        "checked_months": checked_months,
        "differences": differences,
    }


def _resolve_spec_paths(spec: dict[str, Any], data_root: str | Path | None) -> dict[str, Any]:
    base = Path(data_root) if data_root is not None else None

    def _resolve(relative_path: str | None) -> Path | str | None:
        if relative_path is None:
            return None
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Manifest source file paths must be non-empty relative strings.")
        path = Path(relative_path)
        if path.is_absolute():
            raise ValueError("Manifest source file paths must be relative.")
        if base is None:
            return relative_path
        resolved_path = base / path
        if not _path_is_relative_to(resolved_path.resolve(strict=False), base.resolve(strict=False)):
            raise ValueError("Resolved manifest source file paths must stay under data_root.")
        return resolved_path

    return {
        "energy_files": [_resolve(path) for path in spec["energy_files"]],
        "csi_file": _resolve(spec.get("csi_file")),
        "mes_file": _resolve(spec.get("mes_file")),
    }


def _validate_month_source_file_map(manifest: dict[str, Any]) -> None:
    validate_manifest_shape(manifest)
    month_map = manifest.get(_SOURCE_FILE_MAP_KEY)
    if not isinstance(month_map, dict) or not month_map:
        raise ValueError("Source manifest month_source_files must be a non-empty object.")
    accepted_months = set(manifest["accepted_canonical_months"])
    for month_key, spec in month_map.items():
        _parse_month_key(month_key)
        if not isinstance(spec, dict):
            raise ValueError(f"month_source_files.{month_key} must be an object.")
        missing_fields = sorted(_REQUIRED_MONTH_SOURCE_FIELDS - set(spec))
        if missing_fields:
            raise ValueError(
                f"month_source_files.{month_key} is missing required fields: "
                + ", ".join(missing_fields)
            )
        if spec["canonical_scope_status"] not in _CANONICAL_SCOPE_STATUSES:
            raise ValueError(
                f"month_source_files.{month_key}.canonical_scope_status must be one of "
                + ", ".join(sorted(_CANONICAL_SCOPE_STATUSES))
            )
        if spec["canonical_scope_status"] == "accepted" and month_key not in accepted_months:
            raise ValueError(f"month_source_files.{month_key} is accepted but not in accepted_canonical_months.")
        if not isinstance(spec["energy_files"], list) or not spec["energy_files"]:
            raise ValueError(f"month_source_files.{month_key}.energy_files must be a non-empty list.")
        if spec["backfill_readiness"] not in _BACKFILL_READINESS_VALUES:
            raise ValueError(
                f"month_source_files.{month_key}.backfill_readiness must be one of "
                + ", ".join(sorted(_BACKFILL_READINESS_VALUES))
            )
        if not isinstance(spec["family_status"], dict):
            raise ValueError(f"month_source_files.{month_key}.family_status must be an object.")
        for domain in _SOURCE_DOMAINS:
            if domain not in spec["family_status"]:
                raise ValueError(f"month_source_files.{month_key}.family_status is missing {domain}.")
            if spec["family_status"][domain] not in _FAMILY_STATUS_VALUES:
                raise ValueError(
                    f"month_source_files.{month_key}.family_status.{domain} must be one of "
                    + ", ".join(sorted(_FAMILY_STATUS_VALUES))
                )
        if not isinstance(spec["notes"], list):
            raise ValueError(f"month_source_files.{month_key}.notes must be a list.")
        _resolve_spec_paths(spec, data_root=None)


def _legacy_readiness(family_status: dict[str, str]) -> str:
    if all(status == "complete" for status in family_status.values()):
        return "ready"
    if any(status == "blocked" for status in family_status.values()):
        return "blocked"
    return "ready_with_flags"


def _display_readiness(backfill_readiness: str, *, blocked: bool) -> str:
    if blocked:
        return "Blocked"
    if backfill_readiness == "ready_with_flags":
        return "Ready with Flags"
    if backfill_readiness == "ready":
        return "Ready"
    return str(backfill_readiness).replace("_", " ").title()


def _parse_month_key(month_key: str) -> datetime:
    try:
        return datetime.strptime(str(month_key or "").strip(), "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"Invalid month key: {month_key}") from exc


def _path_is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


__all__ = [
    "build_manifest_source_availability_dataframe",
    "compare_manifest_to_legacy_extension_mapping",
    "get_manifest_month_source_files",
    "month_key_to_label",
    "month_label_to_key",
    "resolve_manifest_month_sources",
]
