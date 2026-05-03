import builtins
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


def _build_app_import_stubs():
    def _no_op(*args, **kwargs):
        return None

    stubs = {}

    etl_stub = types.ModuleType("modules.etl_module")
    etl_stub.render_etl_page = _no_op
    stubs["modules.etl_module"] = etl_stub

    unified_stub = types.ModuleType("modules.unified_view_module")
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


def _load_app_module():
    _install_streamlit_stub()
    route_stubs = _build_app_import_stubs()
    original_modules = {}
    for module_name, stub in route_stubs.items():
        original_modules[module_name] = sys.modules.get(module_name)
        sys.modules[module_name] = stub

    original_import = builtins.__import__

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"core.enhanced_etl_solution_CURRENT", "modules.euvg_module"}:
            raise AssertionError(f"legacy loader import reached during app import: {name}")
        return original_import(name, globals, locals, fromlist, level)

    spec = importlib.util.spec_from_file_location("task16d_test_app", REPO_ROOT / "app.py")
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


def _load_energy_module():
    _install_streamlit_stub()
    original_unified_module = sys.modules.get("modules.unified_view_module")
    unified_stub = types.ModuleType("modules.unified_view_module")
    unified_stub._build_unified_value_card_payload = lambda *args, **kwargs: {}
    unified_stub._render_unified_audit_card = lambda *args, **kwargs: None
    unified_stub._render_unified_value_card = lambda *args, **kwargs: None
    unified_stub.render_unified_view_page = lambda *args, **kwargs: None
    sys.modules["modules.unified_view_module"] = unified_stub

    spec = importlib.util.spec_from_file_location(
        "task16d_test_energy_module",
        REPO_ROOT / "modules" / "energy_module.py",
    )
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        if original_unified_module is None:
            sys.modules.pop("modules.unified_view_module", None)
        else:
            sys.modules["modules.unified_view_module"] = original_unified_module
    return module


class EnergyRouteContractTests(unittest.TestCase):
    def test_app_energy_route_now_delegates_to_module(self):
        app_module = _load_app_module()

        with patch.object(app_module, "render_energy_module", return_value=None) as render_patch:
            app_module.show_energy_analysis_page()
            render_patch.assert_called_once_with(runtime_mode=app_module.runtime_mode)

    def test_app_source_no_longer_contains_inline_energy_page_body(self):
        source = (REPO_ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn("render_energy_module(runtime_mode=runtime_mode)", source)
        self.assertNotIn("CanonicalEnergyReader()", source)
        self.assertNotIn("def _build_energy_month_cards", source)
        self.assertNotIn("def _build_energy_attribution_cards", source)
        self.assertNotIn("def _build_energy_machine_context_cards", source)
        self.assertNotIn("def _select_energy_attention_view", source)

    def test_energy_module_can_build_real_canonical_snapshot_without_fallback(self):
        energy_module = _load_energy_module()

        snapshot = energy_module.build_energy_route_snapshot()

        self.assertGreater(snapshot["available_month_count"], 0)
        self.assertIsNotNone(snapshot["selected_month"])
        self.assertGreater(snapshot["rows_loaded"], 0)
        self.assertFalse(snapshot["fallback_used"])
        self.assertIsNotNone(snapshot["total_energy_kwh"])


if __name__ == "__main__":
    unittest.main()
