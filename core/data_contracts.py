from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_DIR = _REPO_ROOT / "config"
_DEFAULT_SOURCE_MANIFEST = _CONFIG_DIR / "source_manifest.v1.json"
_DEFAULT_DATA_QUALITY_RULES = _CONFIG_DIR / "data_quality_rules.v1.json"
_MONTH_KEY_RE = re.compile(r"^20\d{2}-(0[1-9]|1[0-2])$")
_REQUIRED_SOURCE_FAMILIES = {
    "energy_hourly_report_v1",
    "csi_monthly_xlsx_v1",
    "csi_monthly_xls_variant_v1",
    "mes_monthly_report_v1",
    "maintenance_transaction_v1",
    "energy_daily_report_v1",
    "energy_tariff_aggregate_v1",
}
_REQUIRED_DQ_RULE_SECTIONS = {
    "accepted_sentinel_anomalies",
    "partial_energy_month_flags",
    "unresolved_quarantine_ids",
    "quantity_overlay_anomaly_types",
    "allowed_energy_scope_statuses",
    "accepted_month_range",
}


def get_config_dir() -> Path:
    return _CONFIG_DIR


def load_source_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest = _load_json_file(path or _DEFAULT_SOURCE_MANIFEST)
    validate_manifest_shape(manifest)
    return manifest


def load_data_quality_rules(path: str | Path | None = None) -> dict[str, Any]:
    rules = _load_json_file(path or _DEFAULT_DATA_QUALITY_RULES)
    validate_data_quality_rules_shape(rules)
    return rules


def get_accepted_canonical_months(manifest: dict[str, Any] | None = None) -> list[str]:
    source_manifest = manifest if manifest is not None else load_source_manifest()
    validate_manifest_shape(source_manifest)
    return list(source_manifest["accepted_canonical_months"])


def get_source_scope_for_month(
    month_key: str,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_month_key(month_key, "month_key")
    source_manifest = manifest if manifest is not None else load_source_manifest()
    validate_manifest_shape(source_manifest)
    for scope in source_manifest["source_scopes"]:
        if month_key in scope["accepted_months"]:
            return dict(scope)
    raise ValueError(f"No accepted source scope is defined for canonical month {month_key}.")


def validate_manifest_shape(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("Source manifest must be a JSON object.")
    if manifest.get("schema_version") != "source_manifest.v1":
        raise ValueError("Source manifest schema_version must be source_manifest.v1.")

    families = manifest.get("source_families")
    if not isinstance(families, dict):
        raise ValueError("Source manifest source_families must be an object.")
    missing_families = sorted(_REQUIRED_SOURCE_FAMILIES - set(families))
    if missing_families:
        raise ValueError(
            "Source manifest is missing required source families: "
            + ", ".join(missing_families)
        )

    accepted_months = manifest.get("accepted_canonical_months")
    if not isinstance(accepted_months, list) or not accepted_months:
        raise ValueError("Source manifest accepted_canonical_months must be a non-empty list.")
    for month_key in accepted_months:
        _validate_month_key(month_key, "accepted_canonical_months")
    if accepted_months != sorted(accepted_months):
        raise ValueError("Source manifest accepted_canonical_months must be sorted.")

    scopes = manifest.get("source_scopes")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("Source manifest source_scopes must be a non-empty list.")

    scoped_months: list[str] = []
    for scope in scopes:
        _validate_source_scope(scope)
        scoped_months.extend(scope["accepted_months"])
    if sorted(scoped_months) != accepted_months:
        raise ValueError(
            "Source manifest scoped accepted_months must exactly match accepted_canonical_months."
        )

    _reject_absolute_paths(manifest, "source_manifest")


def validate_data_quality_rules_shape(rules: dict[str, Any]) -> None:
    if not isinstance(rules, dict):
        raise ValueError("Data-quality rules must be a JSON object.")
    if rules.get("schema_version") != "data_quality_rules.v1":
        raise ValueError("Data-quality rules schema_version must be data_quality_rules.v1.")

    missing_sections = sorted(_REQUIRED_DQ_RULE_SECTIONS - set(rules))
    if missing_sections:
        raise ValueError(
            "Data-quality rules are missing required sections: "
            + ", ".join(missing_sections)
        )

    month_range = rules["accepted_month_range"]
    if not isinstance(month_range, dict):
        raise ValueError("Data-quality rules accepted_month_range must be an object.")
    _validate_month_key(month_range.get("start_month"), "accepted_month_range.start_month")
    _validate_month_key(month_range.get("end_month"), "accepted_month_range.end_month")
    excluded = month_range.get("excluded_by_default", [])
    if not isinstance(excluded, list):
        raise ValueError("accepted_month_range.excluded_by_default must be a list.")
    for month_key in excluded:
        _validate_month_key(month_key, "accepted_month_range.excluded_by_default")

    for section_name in (
        "accepted_sentinel_anomalies",
        "partial_energy_month_flags",
        "unresolved_quarantine_ids",
        "quantity_overlay_anomaly_types",
        "allowed_energy_scope_statuses",
    ):
        if not isinstance(rules[section_name], list):
            raise ValueError(f"Data-quality rules {section_name} must be a list.")


def _load_json_file(path: str | Path) -> dict[str, Any]:
    json_path = Path(path)
    try:
        with json_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {json_path}: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot read JSON config {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON config {json_path} must contain an object.")
    return data


def _validate_source_scope(scope: Any) -> None:
    if not isinstance(scope, dict):
        raise ValueError("Each source scope must be an object.")
    for field_name in ("scope_id", "root_folder", "accepted_months", "expected_folders"):
        if field_name not in scope:
            raise ValueError(f"Source scope is missing required field {field_name}.")
    if not isinstance(scope["scope_id"], str) or not scope["scope_id"].strip():
        raise ValueError("Source scope scope_id must be a non-empty string.")
    if not isinstance(scope["root_folder"], str) or not scope["root_folder"].strip():
        raise ValueError("Source scope root_folder must be a non-empty relative string.")
    if not isinstance(scope["accepted_months"], list) or not scope["accepted_months"]:
        raise ValueError("Source scope accepted_months must be a non-empty list.")
    for month_key in scope["accepted_months"]:
        _validate_month_key(month_key, f"{scope['scope_id']}.accepted_months")
    if scope["accepted_months"] != sorted(scope["accepted_months"]):
        raise ValueError(f"Source scope {scope['scope_id']} accepted_months must be sorted.")
    if not isinstance(scope["expected_folders"], dict) or not scope["expected_folders"]:
        raise ValueError("Source scope expected_folders must be a non-empty object.")


def _validate_month_key(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not _MONTH_KEY_RE.match(value):
        raise ValueError(f"{field_name} must contain month keys in YYYY-MM format.")


def _reject_absolute_paths(value: Any, field_name: str) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            _reject_absolute_paths(child_value, f"{field_name}.{key}")
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            _reject_absolute_paths(child_value, f"{field_name}[{index}]")
    elif isinstance(value, str):
        if Path(value).is_absolute():
            raise ValueError(f"{field_name} must not contain absolute local paths.")


__all__ = [
    "get_accepted_canonical_months",
    "get_config_dir",
    "get_source_scope_for_month",
    "load_data_quality_rules",
    "load_source_manifest",
    "validate_data_quality_rules_shape",
    "validate_manifest_shape",
]
