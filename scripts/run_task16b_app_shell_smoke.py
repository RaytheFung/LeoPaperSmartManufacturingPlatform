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

from core.runtime_capabilities import get_visible_pages
from core.runtime_mode import DEMO_READONLY_RUNTIME_MODE, PILOT_REVIEW_RUNTIME_MODE, STANDARD_RUNTIME_MODE
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


def _import_app_without_legacy_loader_imports() -> object:
    _install_streamlit_stub()
    app_dependency_stubs = _build_route_module_stubs()
    original_modules: dict[str, types.ModuleType | None] = {}
    for module_name, stub in app_dependency_stubs.items():
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

    app_spec = importlib.util.spec_from_file_location("task16b_smoke_app", REPO_ROOT / "app.py")
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

    app_module = _import_app_without_legacy_loader_imports()

    route_imports = {}
    for module_name in (
        "modules.unified_view_module",
        "modules.ml_module",
        "modules.optimization_module",
        "modules.maintenance_module",
        "modules.experimental_intelligence_lab_module",
    ):
        route_imports[module_name] = importlib.import_module(module_name).__name__

    standard_contract = app_module.get_app_shell_contract(STANDARD_RUNTIME_MODE)
    demo_contract = app_module.get_app_shell_contract(DEMO_READONLY_RUNTIME_MODE)
    pilot_contract = app_module.get_app_shell_contract(PILOT_REVIEW_RUNTIME_MODE)

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
        "app_shell": {
            "defended_core_routes": app_module.get_defended_core_route_labels(),
            "experimental_bonus_route": app_module.get_experimental_bonus_route_label(),
            "standard_visible_pages": standard_contract["visible_pages"],
            "demo_readonly_visible_pages": demo_contract["visible_pages"],
            "pilot_review_visible_pages": pilot_contract["visible_pages"],
            "standard_loader_dependent_visible_pages": standard_contract["loader_dependent_visible_pages"],
            "demo_loader_dependent_visible_pages": demo_contract["loader_dependent_visible_pages"],
            "pilot_loader_dependent_visible_pages": pilot_contract["loader_dependent_visible_pages"],
            "dormant_legacy_helpers": app_module.get_dormant_legacy_helper_names(),
            "visible_pages_match_runtime_capabilities": (
                standard_contract["visible_pages"] == get_visible_pages(STANDARD_RUNTIME_MODE)
                and demo_contract["visible_pages"] == get_visible_pages(DEMO_READONLY_RUNTIME_MODE)
                and pilot_contract["visible_pages"] == get_visible_pages(PILOT_REVIEW_RUNTIME_MODE)
            ),
        },
        "imports": {
            "app.py": getattr(app_module, "__name__", "task16b_smoke_app"),
            "route_modules": route_imports,
        },
        "legacy_loader_isolation": {
            "blocked_legacy_loader_imports_during_app_import": True,
            "defended_core_routes_use_legacy_loader": any(
                app_module.route_uses_dormant_legacy_loader(page_label)
                for page_label in app_module.get_defended_core_route_labels()
            ),
            "experimental_route_uses_legacy_loader": app_module.route_uses_dormant_legacy_loader(
                app_module.get_experimental_bonus_route_label()
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
        and payload["app_shell"]["visible_pages_match_runtime_capabilities"]
        and not payload["app_shell"]["standard_loader_dependent_visible_pages"]
        and not payload["app_shell"]["demo_loader_dependent_visible_pages"]
        and not payload["app_shell"]["pilot_loader_dependent_visible_pages"]
        and not payload["legacy_loader_isolation"]["defended_core_routes_use_legacy_loader"]
        and not payload["legacy_loader_isolation"]["experimental_route_uses_legacy_loader"]
        and payload["write_safety"]["database_fingerprint_unchanged"]
        and payload["write_safety"]["model_fingerprint_unchanged"]
        and payload["write_safety"]["preprocessor_fingerprint_unchanged"]
        and payload["write_safety"]["model_provenance_fingerprint_unchanged"]
        and payload["write_safety"]["preprocessor_provenance_fingerprint_unchanged"]
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
