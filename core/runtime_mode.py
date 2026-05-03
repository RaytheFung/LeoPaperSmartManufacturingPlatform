from __future__ import annotations

import os
from collections.abc import Mapping


STANDARD_RUNTIME_MODE = "standard"
DEMO_READONLY_RUNTIME_MODE = "demo_readonly"
PILOT_REVIEW_RUNTIME_MODE = "pilot_review"
RUNTIME_MODE_ENV_VAR = "SMART_MFG_RUNTIME_MODE"
VALID_RUNTIME_MODES = {
    STANDARD_RUNTIME_MODE,
    DEMO_READONLY_RUNTIME_MODE,
    PILOT_REVIEW_RUNTIME_MODE,
}


def normalize_runtime_mode(value: object) -> str:
    if value is None:
        return STANDARD_RUNTIME_MODE
    normalized = str(value).strip().lower()
    if normalized in VALID_RUNTIME_MODES:
        return normalized
    return STANDARD_RUNTIME_MODE


def resolve_runtime_mode(
    *,
    session_state: Mapping[str, object] | None = None,
    query_params: Mapping[str, object] | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    if session_state is not None:
        override = session_state.get("runtime_mode")
        if override is not None:
            return normalize_runtime_mode(override)

    if query_params is not None:
        for key in ("runtime_mode", "mode"):
            value = query_params.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                value = value[0] if value else None
            return normalize_runtime_mode(value)

    source_env = env if env is not None else os.environ
    return normalize_runtime_mode(source_env.get(RUNTIME_MODE_ENV_VAR))


def is_demo_readonly_mode(
    *,
    session_state: Mapping[str, object] | None = None,
    query_params: Mapping[str, object] | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    return (
        resolve_runtime_mode(
            session_state=session_state,
            query_params=query_params,
            env=env,
        )
        == DEMO_READONLY_RUNTIME_MODE
    )


def get_runtime_mode_label(runtime_mode: str) -> str:
    normalized = normalize_runtime_mode(runtime_mode)
    if normalized == DEMO_READONLY_RUNTIME_MODE:
        return "Demo Read-Only Mode"
    if normalized == PILOT_REVIEW_RUNTIME_MODE:
        return "Pilot Review Mode"
    return "Standard Mode"


def get_runtime_mode_summary(runtime_mode: str) -> str:
    normalized = normalize_runtime_mode(runtime_mode)
    if normalized == DEMO_READONLY_RUNTIME_MODE:
        return (
            "Write-capable controls are hidden or disabled. Read-only analytics remain available."
        )
    if normalized == PILOT_REVIEW_RUNTIME_MODE:
        return (
            "Defended-core write controls stay hidden while pilot-review experimental inputs, exports, and provenance surfaces remain available."
        )
    return "Operational controls are available on the current shell."


__all__ = [
    "DEMO_READONLY_RUNTIME_MODE",
    "PILOT_REVIEW_RUNTIME_MODE",
    "RUNTIME_MODE_ENV_VAR",
    "STANDARD_RUNTIME_MODE",
    "VALID_RUNTIME_MODES",
    "get_runtime_mode_label",
    "get_runtime_mode_summary",
    "is_demo_readonly_mode",
    "normalize_runtime_mode",
    "resolve_runtime_mode",
]
