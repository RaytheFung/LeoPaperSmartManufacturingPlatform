from __future__ import annotations

from copy import deepcopy

from core.runtime_mode import (
    DEMO_READONLY_RUNTIME_MODE,
    PILOT_REVIEW_RUNTIME_MODE,
    STANDARD_RUNTIME_MODE,
    normalize_runtime_mode,
)


_BASE_PAGES = [
    "🔄 ETL Pipeline",
    "📊 Canonical Operations Overview",
    "⚡ Energy Analysis",
    "🎯 Operational Decision Support",
    "🤖 Efficiency Prediction & Governance",
    "🔧 Maintenance",
]

_EXPERIMENTAL_ROUTE = "🧪 Experimental Intelligence Lab"

_RUNTIME_CAPABILITY_MATRIX = {
    STANDARD_RUNTIME_MODE: {
        "visible_pages": [*_BASE_PAGES, _EXPERIMENTAL_ROUTE],
        "suppress_write_controls": False,
        "experimental_route_exposed": True,
        "experimental_real_input_upload": True,
        "experimental_exports": True,
        "experimental_manual_stress_test": True,
        "experimental_profile_label": "Internal experimental access",
    },
    DEMO_READONLY_RUNTIME_MODE: {
        "visible_pages": list(_BASE_PAGES),
        "suppress_write_controls": True,
        "experimental_route_exposed": False,
        "experimental_real_input_upload": False,
        "experimental_exports": False,
        "experimental_manual_stress_test": False,
        "experimental_profile_label": "Defended-core read-only demo shell",
    },
    PILOT_REVIEW_RUNTIME_MODE: {
        "visible_pages": [*_BASE_PAGES, _EXPERIMENTAL_ROUTE],
        "suppress_write_controls": True,
        "experimental_route_exposed": True,
        "experimental_real_input_upload": True,
        "experimental_exports": True,
        "experimental_manual_stress_test": True,
        "experimental_profile_label": "Pilot-review experimental access",
    },
}


def get_runtime_capabilities(runtime_mode: str) -> dict[str, object]:
    normalized = normalize_runtime_mode(runtime_mode)
    capabilities = deepcopy(_RUNTIME_CAPABILITY_MATRIX[normalized])
    capabilities["runtime_mode"] = normalized
    return capabilities


def get_visible_pages(runtime_mode: str) -> list[str]:
    return list(get_runtime_capabilities(runtime_mode)["visible_pages"])


def suppress_write_controls(runtime_mode: str) -> bool:
    return bool(get_runtime_capabilities(runtime_mode)["suppress_write_controls"])


def experimental_route_is_exposed(runtime_mode: str) -> bool:
    return bool(get_runtime_capabilities(runtime_mode)["experimental_route_exposed"])


def experimental_real_input_upload_is_allowed(runtime_mode: str) -> bool:
    return bool(get_runtime_capabilities(runtime_mode)["experimental_real_input_upload"])


def experimental_exports_are_allowed(runtime_mode: str) -> bool:
    return bool(get_runtime_capabilities(runtime_mode)["experimental_exports"])


def experimental_manual_stress_test_is_allowed(runtime_mode: str) -> bool:
    return bool(get_runtime_capabilities(runtime_mode)["experimental_manual_stress_test"])


__all__ = [
    "experimental_exports_are_allowed",
    "experimental_manual_stress_test_is_allowed",
    "experimental_real_input_upload_is_allowed",
    "experimental_route_is_exposed",
    "get_runtime_capabilities",
    "get_visible_pages",
    "suppress_write_controls",
]
