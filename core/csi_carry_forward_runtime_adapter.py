"""Read-only CSI carry-forward runtime preflight adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from core.csi_carry_forward_config import (
    CarryForwardConfig,
    CarryForwardMode,
    assert_no_live_db_mode,
    assert_supported_boundary,
    validate_carry_forward_mode,
    validate_temp_db_path,
)


PreflightBuilder = Callable[..., dict[str, Any]]


def build_carry_forward_runtime_preflight(
    config: CarryForwardConfig | Mapping[str, object] | str | None,
    source_package_month: str | None = None,
    target_canonical_month: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized = _normalize_config(
        config,
        source_package_month=source_package_month,
        target_canonical_month=target_canonical_month,
        db_path=db_path,
    )
    return maybe_build_preflight_only_result(
        normalized,
        normalized.source_package_month,
        normalized.target_canonical_month,
        db_path=normalized.target_db_path,
    )


def summarize_carry_forward_runtime_policy(
    config: CarryForwardConfig | Mapping[str, object] | str | None,
) -> dict[str, Any]:
    normalized = _normalize_config(config)
    return {
        "mode": normalized.mode,
        "enabled": normalized.mode != CarryForwardMode.DISABLED,
        "disabled_by_default": normalized.mode == CarryForwardMode.DISABLED,
        "source_package_month": normalized.source_package_month,
        "target_canonical_month": normalized.target_canonical_month,
        "allow_live_db": normalized.allow_live_db,
        "allowed_boundaries": [
            {"source_package_month": source, "target_canonical_month": target}
            for source, target in normalized.allowed_boundaries
        ],
        "active_runtime_wiring": False,
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "runs_reconciliation": False,
        "writes_db": False,
        "streamlit_control": False,
    }


def assert_carry_forward_runtime_not_live(
    config: CarryForwardConfig | Mapping[str, object] | str | None,
) -> None:
    normalized = _normalize_config(config)
    assert_no_live_db_mode(normalized.mode)
    if normalized.allow_live_db:
        raise ValueError("Carry-forward live DB mode is not available.")


def maybe_build_preflight_only_result(
    config: CarryForwardConfig | Mapping[str, object] | str | None,
    source_package_month: str | None,
    target_canonical_month: str | None,
    db_path: str | Path | None = None,
    preflight_builder: PreflightBuilder | None = None,
) -> dict[str, Any]:
    normalized = _normalize_config(
        config,
        source_package_month=source_package_month,
        target_canonical_month=target_canonical_month,
        db_path=db_path,
    )
    assert_carry_forward_runtime_not_live(normalized)

    if normalized.mode == CarryForwardMode.DISABLED:
        return _disabled_result(normalized)

    source, target = assert_supported_boundary(
        normalized.source_package_month,
        normalized.target_canonical_month,
        allowlist=normalized.allowed_boundaries,
    )

    if normalized.mode == CarryForwardMode.TEMP_RECONCILE:
        target_db = validate_temp_db_path(normalized.target_db_path) if normalized.target_db_path else None
        if target_db is None:
            raise ValueError("temp_reconcile mode requires an explicit target DB path.")
        return _temp_reconcile_guard_result(normalized, source, target, target_db)

    if normalized.mode != CarryForwardMode.PREFLIGHT_ONLY:
        raise ValueError(f"Unsupported carry-forward adapter mode: {normalized.mode}")

    if db_path is not None:
        validate_temp_db_path(db_path)

    if preflight_builder is not None:
        helper_result = preflight_builder(
            source_package_month=source,
            target_canonical_month=target,
            db_path=db_path,
        )
        return _preflight_result(normalized, source, target, helper_result, helper_called=True)

    if (source, target) == ("November 2025", "December 2025"):
        from core.november_december_carry_forward_preflight import (
            build_november_december_csi_carry_forward_preflight,
        )

        helper_result = build_november_december_csi_carry_forward_preflight(
            source_package_month=source,
            target_month=target,
        )
        return _preflight_result(normalized, source, target, helper_result, helper_called=True)

    if (source, target) == ("July 2025", "August 2025") and db_path is not None:
        from core.csi_carry_forward_preflight import build_csi_carry_forward_preflight

        helper_result = build_csi_carry_forward_preflight(target_month=target, db_path=db_path)
        return _preflight_result(normalized, source, target, helper_result, helper_called=True)

    return _preflight_result(
        normalized,
        source,
        target,
        {
            "status": "not_run",
            "reason": (
                "The July 2025 -> August 2025 preflight helper requires an explicit existing temp DB path; "
                "the adapter did not inspect source files or open a DB."
            ),
            "writes_db": False,
            "runs_etl": False,
            "runs_backfill": False,
            "runs_materialization": False,
        },
        helper_called=False,
    )


def _normalize_config(
    config: CarryForwardConfig | Mapping[str, object] | str | None,
    *,
    source_package_month: str | None = None,
    target_canonical_month: str | None = None,
    db_path: str | Path | None = None,
) -> CarryForwardConfig:
    if isinstance(config, CarryForwardConfig):
        return CarryForwardConfig(
            mode=config.mode,
            source_package_month=source_package_month or config.source_package_month,
            target_canonical_month=target_canonical_month or config.target_canonical_month,
            target_db_path=db_path or config.target_db_path,
            allow_live_db=config.allow_live_db,
            allowed_boundaries=config.allowed_boundaries,
        )
    if isinstance(config, Mapping):
        mode = str(config.get("mode", config.get("carry_forward_mode", CarryForwardMode.DISABLED)))
        return CarryForwardConfig(
            mode=mode,
            source_package_month=source_package_month or _optional_string(config.get("source_package_month")),
            target_canonical_month=target_canonical_month
            or _optional_string(config.get("target_canonical_month", config.get("target_month"))),
            target_db_path=db_path or config.get("target_db_path"),
            allow_live_db=bool(config.get("allow_live_db", False)),
        )
    mode = validate_carry_forward_mode(str(config or CarryForwardMode.DISABLED))
    return CarryForwardConfig(
        mode=mode,
        source_package_month=source_package_month,
        target_canonical_month=target_canonical_month,
        target_db_path=db_path,
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _disabled_result(config: CarryForwardConfig) -> dict[str, Any]:
    return {
        "status": "disabled",
        "mode": config.mode,
        "enabled": False,
        "message": "CSI carry-forward is disabled; adapter returned no-op policy evidence.",
        "helper_called": False,
        "requires_db_path": False,
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "runs_reconciliation": False,
        "writes_db": False,
        "changes_runtime_predicates": False,
        "changes_source_discovery_policy": False,
        "active_runtime_wiring": False,
    }


def _preflight_result(
    config: CarryForwardConfig,
    source: str,
    target: str,
    helper_result: dict[str, Any],
    *,
    helper_called: bool,
) -> dict[str, Any]:
    return {
        "status": "preflight_only",
        "mode": config.mode,
        "enabled": True,
        "source_package_month": source,
        "target_canonical_month": target,
        "helper_called": helper_called,
        "preflight": helper_result,
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "runs_reconciliation": False,
        "writes_db": False,
        "changes_runtime_predicates": False,
        "changes_source_discovery_policy": False,
        "active_runtime_wiring": False,
    }


def _temp_reconcile_guard_result(
    config: CarryForwardConfig,
    source: str,
    target: str,
    target_db: Path,
) -> dict[str, Any]:
    return {
        "status": "guarded_not_executed",
        "mode": config.mode,
        "enabled": True,
        "source_package_month": source,
        "target_canonical_month": target,
        "target_db_path": str(target_db),
        "message": "temp_reconcile is not executable through active runtime in Stage B11.3.",
        "requires_explicit_temp_db_path": True,
        "helper_called": False,
        "runs_etl": False,
        "runs_backfill": False,
        "runs_materialization": False,
        "runs_reconciliation": False,
        "writes_db": False,
        "changes_runtime_predicates": False,
        "changes_source_discovery_policy": False,
        "active_runtime_wiring": False,
    }


__all__ = [
    "assert_carry_forward_runtime_not_live",
    "build_carry_forward_runtime_preflight",
    "maybe_build_preflight_only_result",
    "summarize_carry_forward_runtime_policy",
]
