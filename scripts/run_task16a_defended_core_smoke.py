#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_gold_reader import CanonicalGoldReader
from core.canonical_ml_reader import CanonicalMLReader
from core.canonical_optimization_reader import CanonicalOptimizationReader
from core.ml_predictor import MLPredictor
from core.runtime_paths import get_database_path


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(path: Path, *, include_sha1: bool = True) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha1": _sha1(path) if include_sha1 and path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
    }


def _pick_post_june_month(months: list[str]) -> str:
    for month_label in months:
        month_key = Path(month_label.replace(" ", "_")).name
        parsed = __import__("datetime").datetime.strptime(month_label, "%B %Y")
        if parsed.year > 2025 or (parsed.year == 2025 and parsed.month >= 7):
            return month_label
    raise ValueError("No post-June canonical month is available for the Task16A smoke.")


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

    def selectbox(self, *args, **kwargs):
        return "🔄 ETL Pipeline"


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
    streamlit_stub.selectbox = lambda *args, **kwargs: "🔄 ETL Pipeline"

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


def _import_app_and_modules() -> dict[str, object]:
    _install_streamlit_stub()

    imported = {}
    for module_name in (
        "modules.ml_module",
        "modules.optimization_module",
        "modules.maintenance_module",
    ):
        imported[module_name] = importlib.import_module(module_name).__name__

    def _no_op(*args, **kwargs):
        return None

    app_dependency_stubs: dict[str, types.ModuleType] = {}

    etl_stub = types.ModuleType("modules.etl_module")
    etl_stub.render_etl_page = _no_op
    app_dependency_stubs["modules.etl_module"] = etl_stub

    unified_stub = types.ModuleType("modules.unified_view_module")
    unified_stub._build_unified_value_card_payload = _no_op
    unified_stub._render_unified_audit_card = _no_op
    unified_stub._render_unified_value_card = _no_op
    unified_stub.render_unified_view_page = _no_op
    app_dependency_stubs["modules.unified_view_module"] = unified_stub

    maintenance_stub = types.ModuleType("modules.maintenance_module")
    maintenance_stub.render_maintenance_page = _no_op
    app_dependency_stubs["modules.maintenance_module"] = maintenance_stub

    experimental_stub = types.ModuleType("modules.experimental_intelligence_lab_module")
    experimental_stub.render_experimental_intelligence_lab = _no_op
    app_dependency_stubs["modules.experimental_intelligence_lab_module"] = experimental_stub

    ml_stub = types.ModuleType("modules.ml_module")
    ml_stub.render_ml_module = _no_op
    app_dependency_stubs["modules.ml_module"] = ml_stub

    optimization_stub = types.ModuleType("modules.optimization_module")
    optimization_stub.render_optimization_module = _no_op
    app_dependency_stubs["modules.optimization_module"] = optimization_stub

    euvg_stub = types.ModuleType("modules.euvg_module")
    euvg_stub.EnhancedUnifiedViewGenerator = object
    app_dependency_stubs["modules.euvg_module"] = euvg_stub

    original_modules: dict[str, types.ModuleType | None] = {}
    for module_name, stub in app_dependency_stubs.items():
        original_modules[module_name] = sys.modules.get(module_name)
        sys.modules[module_name] = stub

    app_spec = importlib.util.spec_from_file_location("task16a_smoke_app", REPO_ROOT / "app.py")
    if app_spec is None or app_spec.loader is None:
        raise RuntimeError("Could not build an import spec for app.py")
    app_module = importlib.util.module_from_spec(app_spec)
    try:
        app_spec.loader.exec_module(app_module)
    finally:
        for module_name, original_module in original_modules.items():
            if original_module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = original_module
    imported["app.py"] = getattr(app_module, "__name__", "task16a_smoke_app")
    return imported


def _db_snapshot(db_path: Path) -> dict[str, object]:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only = ON")
        fact_rows, min_month, max_month = conn.execute(
            """
            SELECT COUNT(*), MIN(substr(hour_ts, 1, 7)), MAX(substr(hour_ts, 1, 7))
            FROM fact_machine_hour
            """
        ).fetchone()
    return {
        "db_path": str(db_path),
        "fact_machine_hour_rows": int(fact_rows),
        "month_key_min": min_month,
        "month_key_max": max_month,
    }


def main() -> None:
    db_path = get_database_path().resolve()
    model_path = (REPO_ROOT / "models" / "production_efficiency_model.pkl").resolve()
    preprocessor_path = (REPO_ROOT / "models" / "production_preprocessor.pkl").resolve()

    before = {
        "database": _fingerprint(db_path, include_sha1=False),
        "model": _fingerprint(model_path),
        "preprocessor": _fingerprint(preprocessor_path),
    }

    gold_reader = CanonicalGoldReader()
    gold_months = gold_reader.get_available_months()
    post_june_month = _pick_post_june_month(gold_months)

    ml_reader = CanonicalMLReader()
    predictor = MLPredictor()
    ml_fact_df = ml_reader._read_month_fact_dataframe(post_june_month)

    optimization_reader = CanonicalOptimizationReader()
    optimization_months = optimization_reader.get_available_months()

    imported_modules = _import_app_and_modules()

    after = {
        "database": _fingerprint(db_path, include_sha1=False),
        "model": _fingerprint(model_path),
        "preprocessor": _fingerprint(preprocessor_path),
    }

    payload = {
        "db_snapshot": _db_snapshot(db_path),
        "runtime_paths": {
            "resolved_db_path": str(db_path),
            "expected_repo_local_db_path": str((REPO_ROOT / "manufacturing_data.db").resolve()),
            "repo_local_path_match": db_path == (REPO_ROOT / "manufacturing_data.db").resolve(),
        },
        "canonical_gold": {
            "available_month_count": len(gold_months),
            "latest_month": gold_months[0] if gold_months else None,
            "post_june_month": post_june_month,
        },
        "canonical_ml": {
            "post_june_month": post_june_month,
            "fact_rows": int(len(ml_fact_df)),
        },
        "canonical_optimization": {
            "available_month_count": len(optimization_months),
            "post_june_month": post_june_month,
        },
        "predictor": {
            "loaded_model": bool(predictor.loaded_model),
            "loaded_preprocessor": bool(predictor.loaded_preprocessor),
            "feature_column_count": len(predictor.feature_columns or []),
        },
        "imports": {
            "imported_modules": imported_modules,
        },
        "fingerprints_before": before,
        "fingerprints_after": after,
        "write_safety": {
            "database_fingerprint_unchanged": (
                before["database"]["size_bytes"] == after["database"]["size_bytes"]
                and before["database"]["mtime_ns"] == after["database"]["mtime_ns"]
            ),
            "model_fingerprint_unchanged": before["model"]["sha1"] == after["model"]["sha1"],
            "preprocessor_fingerprint_unchanged": before["preprocessor"]["sha1"] == after["preprocessor"]["sha1"],
            "db_write_path_executed": False,
        },
        "passed": (
            db_path == (REPO_ROOT / "manufacturing_data.db").resolve()
            and len(gold_months) > 0
            and len(ml_fact_df) > 0
            and len(optimization_months) > 0
            and predictor.loaded_model
            and predictor.loaded_preprocessor
            and before["database"]["size_bytes"] == after["database"]["size_bytes"]
            and before["database"]["mtime_ns"] == after["database"]["mtime_ns"]
            and before["model"]["sha1"] == after["model"]["sha1"]
            and before["preprocessor"]["sha1"] == after["preprocessor"]["sha1"]
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
