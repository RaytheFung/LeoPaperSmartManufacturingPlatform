#!/usr/bin/env python3
from __future__ import annotations

import builtins
import hashlib
import importlib
import importlib.util
import json
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime_paths import get_database_path


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha1": _sha1(path) if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
    }


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __call__(self, *args, **kwargs):
        return None

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class _SidebarStub(_NullContext):
    def caption(self, *args, **kwargs):
        return None

    def selectbox(self, _label, options, index=0, *args, **kwargs):
        return options[index] if options else None


def _install_streamlit_stub() -> None:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}
    streamlit_stub.query_params = {}
    streamlit_stub.sidebar = _SidebarStub()
    streamlit_stub.cache_data = lambda func=None, **kwargs: (lambda inner: inner) if func is None else func
    streamlit_stub.set_page_config = lambda *args, **kwargs: None
    streamlit_stub.stop = lambda: None
    streamlit_stub.columns = lambda spec, *args, **kwargs: [
        _NullContext() for _ in range(spec if isinstance(spec, int) else len(spec))
    ]
    streamlit_stub.tabs = lambda labels, *args, **kwargs: [_NullContext() for _ in labels]
    streamlit_stub.expander = lambda *args, **kwargs: _NullContext()
    streamlit_stub.spinner = lambda *args, **kwargs: _NullContext()
    streamlit_stub.container = lambda *args, **kwargs: _NullContext()
    streamlit_stub.selectbox = lambda _label, options, index=0, *args, **kwargs: (
        options[index] if options else None
    )
    streamlit_stub.radio = lambda _label, options, index=0, *args, **kwargs: (
        options[index] if options else None
    )
    streamlit_stub.button = lambda *args, **kwargs: False
    streamlit_stub.download_button = lambda *args, **kwargs: None
    streamlit_stub.number_input = lambda *args, value=0, **kwargs: value

    for attr_name in (
        "title",
        "header",
        "subheader",
        "markdown",
        "caption",
        "info",
        "warning",
        "error",
        "success",
        "write",
        "metric",
        "dataframe",
        "plotly_chart",
    ):
        setattr(streamlit_stub, attr_name, lambda *args, **kwargs: None)

    sys.modules["streamlit"] = streamlit_stub


def _build_route_module_stubs() -> dict[str, types.ModuleType]:
    def _no_op(*args, **kwargs):
        return None

    stubs: dict[str, types.ModuleType] = {}

    etl_stub = types.ModuleType("modules.etl_module")
    etl_stub.render_etl_page = _no_op
    stubs["modules.etl_module"] = etl_stub

    unified_stub = types.ModuleType("modules.unified_view_module")
    unified_stub._build_unified_value_card_payload = lambda *args, **kwargs: {}
    unified_stub._render_unified_audit_card = _no_op
    unified_stub._render_unified_value_card = _no_op
    unified_stub.render_unified_view_page = _no_op
    stubs["modules.unified_view_module"] = unified_stub

    maintenance_stub = types.ModuleType("modules.maintenance_module")
    maintenance_stub.render_maintenance_page = _no_op
    stubs["modules.maintenance_module"] = maintenance_stub

    experimental_stub = types.ModuleType("modules.experimental_intelligence_lab_module")
    experimental_stub.render_experimental_intelligence_lab = _no_op
    stubs["modules.experimental_intelligence_lab_module"] = experimental_stub

    ml_stub = types.ModuleType("modules.ml_module")
    ml_stub.render_ml_module = _no_op
    stubs["modules.ml_module"] = ml_stub

    optimization_stub = types.ModuleType("modules.optimization_module")
    optimization_stub.render_optimization_module = _no_op
    stubs["modules.optimization_module"] = optimization_stub

    return stubs


def _import_app_with_blocked_legacy_loader_imports():
    _install_streamlit_stub()
    route_stubs = _build_route_module_stubs()
    original_modules: dict[str, types.ModuleType | None] = {}
    for module_name, stub in route_stubs.items():
        original_modules[module_name] = sys.modules.get(module_name)
        sys.modules[module_name] = stub

    blocked_import_names = {
        "core.enhanced_etl_solution_CURRENT",
        "modules.euvg_module",
    }
    original_import = builtins.__import__

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in blocked_import_names:
            raise RuntimeError(f"blocked legacy loader import during app import: {name}")
        return original_import(name, globals, locals, fromlist, level)

    app_spec = importlib.util.spec_from_file_location("task16c_smoke_app", REPO_ROOT / "app.py")
    if app_spec is None or app_spec.loader is None:
        raise RuntimeError("Could not build an import spec for app.py")
    app_module = importlib.util.module_from_spec(app_spec)

    try:
        builtins.__import__ = _guarded_import
        app_spec.loader.exec_module(app_module)
    finally:
        builtins.__import__ = original_import
        for module_name, original_module in original_modules.items():
            if original_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original_module

    return app_module


def main() -> None:
    db_path = get_database_path().resolve()
    model_path = (REPO_ROOT / "models" / "production_efficiency_model.pkl").resolve()
    preprocessor_path = (REPO_ROOT / "models" / "production_preprocessor.pkl").resolve()
    model_provenance_path = (REPO_ROOT / "models" / "production_efficiency_model.provenance.json").resolve()
    preprocessor_provenance_path = (REPO_ROOT / "models" / "production_preprocessor.provenance.json").resolve()

    before = {
        "database": _fingerprint(db_path),
        "model": _fingerprint(model_path),
        "preprocessor": _fingerprint(preprocessor_path),
        "model_provenance": _fingerprint(model_provenance_path),
        "preprocessor_provenance": _fingerprint(preprocessor_provenance_path),
    }

    app_module = _import_app_with_blocked_legacy_loader_imports()
    quarantine_module = importlib.import_module("modules.dormant_legacy_app_helpers")

    after = {
        "database": _fingerprint(db_path),
        "model": _fingerprint(model_path),
        "preprocessor": _fingerprint(preprocessor_path),
        "model_provenance": _fingerprint(model_provenance_path),
        "preprocessor_provenance": _fingerprint(preprocessor_provenance_path),
    }

    payload = {
        "runtime_paths": {
            "resolved_db_path": str(db_path),
            "expected_repo_local_db_path": str((REPO_ROOT / "manufacturing_data.db").resolve()),
            "repo_local_path_match": db_path == (REPO_ROOT / "manufacturing_data.db").resolve(),
        },
        "app_import_boundary": {
            "app_imported": True,
            "blocked_legacy_loader_imports_during_app_import": True,
            "defended_core_route_helpers_available": {
                "get_defended_core_route_labels": hasattr(app_module, "get_defended_core_route_labels"),
                "get_experimental_bonus_route_label": hasattr(
                    app_module, "get_experimental_bonus_route_label"
                ),
                "get_dormant_legacy_helper_names": hasattr(
                    app_module, "get_dormant_legacy_helper_names"
                ),
                "route_uses_dormant_legacy_loader": hasattr(
                    app_module, "route_uses_dormant_legacy_loader"
                ),
            },
        },
        "quarantine_module": {
            "module_name": quarantine_module.__name__,
            "module_boundary_note": getattr(quarantine_module, "MODULE_BOUNDARY_NOTE", None),
            "dormant_helper_names": list(getattr(quarantine_module, "DORMANT_LEGACY_HELPER_NAMES", [])),
            "load_data_imported": hasattr(quarantine_module, "load_data"),
            "show_overview_page_imported": hasattr(quarantine_module, "show_overview_page"),
            "show_etl_page_imported": hasattr(quarantine_module, "show_etl_page"),
            "show_team_performance_page_imported": hasattr(
                quarantine_module, "show_team_performance_page"
            ),
            "show_optimization_page_imported": hasattr(
                quarantine_module, "show_optimization_page"
            ),
        },
        "fingerprints_before": before,
        "fingerprints_after": after,
        "write_safety": {
            "database_fingerprint_unchanged": before["database"]["sha1"] == after["database"]["sha1"],
            "model_fingerprint_unchanged": before["model"]["sha1"] == after["model"]["sha1"],
            "preprocessor_fingerprint_unchanged": before["preprocessor"]["sha1"] == after["preprocessor"]["sha1"],
            "model_provenance_fingerprint_unchanged": (
                before["model_provenance"]["sha1"] == after["model_provenance"]["sha1"]
            ),
            "preprocessor_provenance_fingerprint_unchanged": (
                before["preprocessor_provenance"]["sha1"] == after["preprocessor_provenance"]["sha1"]
            ),
            "db_write_path_executed": False,
            "etl_or_materialization_executed": False,
        },
    }
    payload["passed"] = (
        payload["runtime_paths"]["repo_local_path_match"]
        and all(payload["app_import_boundary"]["defended_core_route_helpers_available"].values())
        and payload["quarantine_module"]["module_name"] == "modules.dormant_legacy_app_helpers"
        and payload["quarantine_module"]["load_data_imported"]
        and payload["quarantine_module"]["show_overview_page_imported"]
        and payload["quarantine_module"]["show_etl_page_imported"]
        and payload["quarantine_module"]["show_team_performance_page_imported"]
        and payload["quarantine_module"]["show_optimization_page_imported"]
        and payload["write_safety"]["database_fingerprint_unchanged"]
        and payload["write_safety"]["model_fingerprint_unchanged"]
        and payload["write_safety"]["preprocessor_fingerprint_unchanged"]
        and payload["write_safety"]["model_provenance_fingerprint_unchanged"]
        and payload["write_safety"]["preprocessor_provenance_fingerprint_unchanged"]
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
