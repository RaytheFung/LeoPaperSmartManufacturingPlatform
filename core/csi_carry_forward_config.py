"""Disabled-by-default CSI carry-forward configuration guardrails."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNTIME_REPO_ROOT = REPO_ROOT.parent / "LeoPaperSmartManufacturingPlatform"


class CarryForwardMode:
    DISABLED = "disabled"
    PREFLIGHT_ONLY = "preflight_only"
    TEMP_RECONCILE = "temp_reconcile"


DEFAULT_CARRY_FORWARD_MODE = CarryForwardMode.DISABLED
ALLOWED_CARRY_FORWARD_MODES = frozenset(
    {
        CarryForwardMode.DISABLED,
        CarryForwardMode.PREFLIGHT_ONLY,
        CarryForwardMode.TEMP_RECONCILE,
    }
)
DEFAULT_ALLOWED_BOUNDARIES = (
    ("July 2025", "August 2025"),
    ("November 2025", "December 2025"),
)
DB_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3"})


@dataclass(frozen=True)
class CarryForwardConfig:
    mode: str = DEFAULT_CARRY_FORWARD_MODE
    source_package_month: str | None = None
    target_canonical_month: str | None = None
    target_db_path: str | Path | None = None
    allow_live_db: bool = False
    allowed_boundaries: tuple[tuple[str, str], ...] = field(default_factory=lambda: DEFAULT_ALLOWED_BOUNDARIES)

    def __post_init__(self) -> None:
        validated_mode = validate_carry_forward_mode(self.mode)
        object.__setattr__(self, "mode", validated_mode)
        assert_no_live_db_mode(validated_mode)
        if self.allow_live_db:
            raise ValueError("Carry-forward live DB mode is not available.")
        if validated_mode != CarryForwardMode.DISABLED:
            assert_explicit_target_month(self.target_canonical_month)
            _assert_explicit_source_package_month(self.source_package_month)
            assert_supported_boundary(
                self.source_package_month,
                self.target_canonical_month,
                allowlist=self.allowed_boundaries,
            )
        if validated_mode == CarryForwardMode.TEMP_RECONCILE:
            if self.target_db_path is None:
                raise ValueError("temp_reconcile mode requires an explicit target DB path.")
            validate_temp_db_path(self.target_db_path)


def build_default_carry_forward_config() -> CarryForwardConfig:
    return CarryForwardConfig()


def validate_carry_forward_mode(mode: str | None) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized not in ALLOWED_CARRY_FORWARD_MODES:
        raise ValueError(
            f"Unsupported carry-forward mode {mode!r}; expected disabled, preflight_only, or temp_reconcile."
        )
    return normalized


def is_carry_forward_enabled(config: CarryForwardConfig | Mapping[str, object] | str | None) -> bool:
    mode = _extract_mode(config)
    return validate_carry_forward_mode(mode) != CarryForwardMode.DISABLED


def require_disabled_by_default(config: CarryForwardConfig | Mapping[str, object] | str | None) -> None:
    mode = _extract_mode(config)
    if validate_carry_forward_mode(mode) != DEFAULT_CARRY_FORWARD_MODE:
        raise ValueError("Carry-forward must default to disabled.")


def validate_temp_db_path(
    path: str | Path,
    repo_root: str | Path | None = None,
    original_runtime_root: str | Path | None = None,
) -> Path:
    resolved = Path(path).expanduser().resolve(strict=False)
    resolved_repo_root = Path(repo_root).expanduser().resolve(strict=False) if repo_root else REPO_ROOT
    resolved_runtime_root = (
        Path(original_runtime_root).expanduser().resolve(strict=False)
        if original_runtime_root
        else ORIGINAL_RUNTIME_REPO_ROOT
    )

    if _path_is_relative_to(resolved, resolved_repo_root):
        raise ValueError(f"Refusing DB path inside repo: {resolved}")
    if _path_is_relative_to(resolved, resolved_runtime_root):
        raise ValueError(f"Refusing DB path inside original runtime repo: {resolved}")
    if resolved.suffix.lower() not in DB_SUFFIXES:
        raise ValueError(f"Carry-forward temp DB path must use a DB suffix: {resolved}")
    return resolved


def assert_no_live_db_mode(mode: str | None) -> None:
    normalized = str(mode or "").strip().lower()
    if normalized in {"live", "live_db", "shared_db", "production", "promote"}:
        raise ValueError("Carry-forward live DB mode is not available.")
    validate_carry_forward_mode(normalized)


def assert_explicit_target_month(month_label: str | None) -> str:
    normalized = str(month_label or "").strip()
    if not normalized:
        raise ValueError("Carry-forward target month must be explicit.")
    return normalized


def assert_supported_boundary(
    source_package_month: str | None,
    target_canonical_month: str | None,
    allowlist: tuple[tuple[str, str], ...] | None = None,
) -> tuple[str, str]:
    source = _assert_explicit_source_package_month(source_package_month)
    target = assert_explicit_target_month(target_canonical_month)
    allowed = allowlist if allowlist is not None else DEFAULT_ALLOWED_BOUNDARIES
    if (source, target) not in allowed:
        raise ValueError(f"Unsupported CSI carry-forward boundary: {source} -> {target}")
    return source, target


def _extract_mode(config: CarryForwardConfig | Mapping[str, object] | str | None) -> str:
    if config is None:
        return DEFAULT_CARRY_FORWARD_MODE
    if isinstance(config, CarryForwardConfig):
        return config.mode
    if isinstance(config, Mapping):
        value = config.get("mode", config.get("carry_forward_mode", DEFAULT_CARRY_FORWARD_MODE))
        return str(value)
    return str(config)


def _assert_explicit_source_package_month(month_label: str | None) -> str:
    normalized = str(month_label or "").strip()
    if not normalized:
        raise ValueError("Carry-forward source package month must be explicit.")
    return normalized


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


__all__ = [
    "ALLOWED_CARRY_FORWARD_MODES",
    "CarryForwardConfig",
    "CarryForwardMode",
    "DEFAULT_ALLOWED_BOUNDARIES",
    "DEFAULT_CARRY_FORWARD_MODE",
    "assert_explicit_target_month",
    "assert_no_live_db_mode",
    "assert_supported_boundary",
    "build_default_carry_forward_config",
    "is_carry_forward_enabled",
    "require_disabled_by_default",
    "validate_carry_forward_mode",
    "validate_temp_db_path",
]
