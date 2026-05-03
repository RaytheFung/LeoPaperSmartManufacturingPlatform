import builtins
import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _install_streamlit_stub():
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


def _build_route_module_stubs():
    def _no_op(*args, **kwargs):
        return None

    stubs = {}

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

    energy_stub = types.ModuleType("modules.energy_module")
    energy_stub.render_energy_module = _no_op
    stubs["modules.energy_module"] = energy_stub

    return stubs


def _load_app_module(*, block_legacy_loader_imports=False):
    _install_streamlit_stub()
    route_stubs = _build_route_module_stubs()
    original_modules = {}
    for module_name, stub in route_stubs.items():
        original_modules[module_name] = sys.modules.get(module_name)
        sys.modules[module_name] = stub

    original_import = builtins.__import__

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if block_legacy_loader_imports and name in {
            "core.enhanced_etl_solution_CURRENT",
            "modules.euvg_module",
        }:
            raise AssertionError(f"legacy loader import reached during app import: {name}")
        return original_import(name, globals, locals, fromlist, level)

    spec = importlib.util.spec_from_file_location("task16c_test_app", REPO_ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    try:
        builtins.__import__ = _guarded_import
        spec.loader.exec_module(module)
    finally:
        builtins.__import__ = original_import
        for module_name, original_module in original_modules.items():
            if original_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original_module
    return module


class AppLegacyQuarantineTests(unittest.TestCase):
    def test_quarantine_module_imports_cleanly_and_declares_boundary(self):
        _install_streamlit_stub()
        module = importlib.import_module("modules.dormant_legacy_app_helpers")

        self.assertEqual(
            module.DORMANT_LEGACY_HELPER_NAMES,
            (
                "load_data",
                "show_overview_page",
                "show_etl_page",
                "show_team_performance_page",
                "show_optimization_page",
            ),
        )
        self.assertIn("Dormant", module.MODULE_BOUNDARY_NOTE)
        self.assertIn("non-routed", module.MODULE_BOUNDARY_NOTE)

    def test_app_wrappers_delegate_to_quarantine_helpers(self):
        module = _load_app_module(block_legacy_loader_imports=True)

        with patch.object(module, "_load_dormant_legacy_data", return_value=("etl", "euvg", "view")):
            self.assertEqual(module.load_data(), ("etl", "euvg", "view"))

        with patch.object(module, "_show_dormant_legacy_etl_page", return_value="etl-page") as etl_patch:
            self.assertEqual(module.show_etl_page("etl"), "etl-page")
            etl_patch.assert_called_once_with("etl")

        with patch.object(
            module, "_show_dormant_legacy_overview_page", return_value="overview-page"
        ) as overview_patch:
            self.assertEqual(module.show_overview_page("etl", "euvg", "view"), "overview-page")
            overview_patch.assert_called_once_with("etl", "euvg", "view")


if __name__ == "__main__":
    unittest.main()
