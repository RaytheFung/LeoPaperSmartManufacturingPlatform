#!/usr/bin/env python3
from __future__ import annotations

import builtins
import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import sqlite3
import sys
import types
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.experimental_maintenance_prototype import build_predictive_maintenance_prototype
from core.experimental_scheduling import get_active_saved_artifact_binding, get_available_months, run_constraint_aware_scheduling
from core.runtime_mode import DEMO_READONLY_RUNTIME_MODE, PILOT_REVIEW_RUNTIME_MODE, STANDARD_RUNTIME_MODE
from core.runtime_paths import get_database_path


def _hash_path(path: Path, algorithm: str) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.new(algorithm)
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(path: Path, algorithm: str) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "algorithm": algorithm,
        "digest": _hash_path(path, algorithm),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
    }


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
        "fact_machine_hour_rows": int(fact_rows),
        "month_key_min": min_month,
        "month_key_max": max_month,
    }


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __call__(self, *args, **kwargs):
        return None

    def __getattr__(self, _name):
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
    streamlit_stub.slider = lambda _label, min_value=None, max_value=None, value=None, *args, **kwargs: value
    streamlit_stub.checkbox = lambda *args, value=False, **kwargs: value
    streamlit_stub.file_uploader = lambda *args, **kwargs: None
    streamlit_stub.data_editor = lambda value, *args, **kwargs: value
    streamlit_stub.download_button = lambda *args, **kwargs: None
    streamlit_stub.button = lambda *args, **kwargs: False

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


def _build_app_dependency_stubs() -> dict[str, types.ModuleType]:
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


def _import_app_and_experimental_module() -> tuple[object, object]:
    _install_streamlit_stub()
    app_dependency_stubs = _build_app_dependency_stubs()
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

    app_spec = importlib.util.spec_from_file_location("task16e_smoke_app", REPO_ROOT / "app.py")
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

    experimental_module = importlib.import_module("modules.experimental_intelligence_lab_module")
    return app_module, experimental_module


def _read_route_wording_contract() -> dict[str, object]:
    source = (REPO_ROOT / "modules" / "experimental_intelligence_lab_module.py").read_text(encoding="utf-8")
    return {
        "stale_task4l_wording_absent": "Task 4L" not in source,
        "internal_landing_flagship_wording_present": "Internal-landing experimental flagship lane" in source,
        "active_saved_live_artifacts_wording_present": "active saved live artifacts" in source,
        "no_solver_claim_wording_present": "No solver claim." in source,
        "no_predictive_maintenance_claim_wording_present": (
            "No predictive-maintenance production claim." in source
        ),
    }


def _compact_artifact_binding(binding: dict[str, object]) -> dict[str, object]:
    return {
        "task_tag": binding.get("task_tag"),
        "artifact_version_id": binding.get("artifact_version_id"),
        "selected_model": binding.get("selected_model"),
        "active_db_path": binding.get("active_db_path"),
        "model_path": binding.get("model_path"),
        "preprocessor_path": binding.get("preprocessor_path"),
        "model_provenance_path": binding.get("model_provenance_path"),
        "preprocessor_provenance_path": binding.get("preprocessor_provenance_path"),
        "paths_use_repo_models_dir": binding.get("paths_use_repo_models_dir"),
        "predictor_instantiated_from_active_paths": binding.get("predictor_instantiated_from_active_paths"),
        "model_loaded": binding.get("model_loaded"),
        "preprocessor_loaded": binding.get("preprocessor_loaded"),
    }


def main() -> None:
    warnings.filterwarnings(
        "ignore",
        message="The behavior of DataFrame concatenation with empty or all-NA entries is deprecated.*",
        category=FutureWarning,
    )
    db_path = get_database_path().resolve()
    expected_db_path = (REPO_ROOT / "manufacturing_data.db").resolve()
    model_path = (REPO_ROOT / "models" / "production_efficiency_model.pkl").resolve()
    preprocessor_path = (REPO_ROOT / "models" / "production_preprocessor.pkl").resolve()
    model_provenance_path = (REPO_ROOT / "models" / "production_efficiency_model.provenance.json").resolve()
    preprocessor_provenance_path = (REPO_ROOT / "models" / "production_preprocessor.provenance.json").resolve()

    before = {
        "database": _fingerprint(db_path, "sha1"),
        "model": _fingerprint(model_path, "sha256"),
        "preprocessor": _fingerprint(preprocessor_path, "sha256"),
        "model_provenance": _fingerprint(model_provenance_path, "sha256"),
        "preprocessor_provenance": _fingerprint(preprocessor_provenance_path, "sha256"),
    }

    app_module, experimental_module = _import_app_and_experimental_module()
    wording_contract = _read_route_wording_contract()
    standard_contract = app_module.get_app_shell_contract(STANDARD_RUNTIME_MODE)
    demo_contract = app_module.get_app_shell_contract(DEMO_READONLY_RUNTIME_MODE)
    pilot_contract = app_module.get_app_shell_contract(PILOT_REVIEW_RUNTIME_MODE)

    available_months = get_available_months(db_path=str(db_path))
    if not available_months:
        raise RuntimeError("No canonical month slice is available for the experimental lane smoke.")
    selected_month = available_months[0]

    with contextlib.redirect_stdout(io.StringIO()):
        route_snapshot = experimental_module.build_experimental_lab_route_snapshot(
            selected_month,
            runtime_mode=STANDARD_RUNTIME_MODE,
            db_path=str(db_path),
            queue_size=3,
            max_jobs_per_machine=1,
            horizon_days=14,
        )
        scheduling_payload = run_constraint_aware_scheduling(
            selected_month,
            queue_size=3,
            max_jobs_per_machine=1,
            db_path=str(db_path),
        )
        maintenance_payload = build_predictive_maintenance_prototype(
            selected_month,
            horizon_days=14,
            db_path=str(db_path),
        )
    active_binding = _compact_artifact_binding(get_active_saved_artifact_binding())

    after = {
        "database": _fingerprint(db_path, "sha1"),
        "model": _fingerprint(model_path, "sha256"),
        "preprocessor": _fingerprint(preprocessor_path, "sha256"),
        "model_provenance": _fingerprint(model_provenance_path, "sha256"),
        "preprocessor_provenance": _fingerprint(preprocessor_provenance_path, "sha256"),
    }

    payload = {
        "runtime_paths": {
            "resolved_db_path": str(db_path),
            "expected_repo_local_db_path": str(expected_db_path),
            "repo_local_path_match": db_path == expected_db_path,
        },
        "app_import_boundary": {
            "app_imported": True,
            "experimental_module_imported": getattr(experimental_module, "__name__", None)
            == "modules.experimental_intelligence_lab_module",
            "blocked_legacy_loader_imports_during_app_import": True,
        },
        "route_visibility": {
            "standard_visible_pages": standard_contract["visible_pages"],
            "demo_readonly_visible_pages": demo_contract["visible_pages"],
            "pilot_review_visible_pages": pilot_contract["visible_pages"],
            "standard_route_exposed": "🧪 Experimental Intelligence Lab" in standard_contract["visible_pages"],
            "demo_route_exposed": "🧪 Experimental Intelligence Lab" in demo_contract["visible_pages"],
            "pilot_route_exposed": "🧪 Experimental Intelligence Lab" in pilot_contract["visible_pages"],
        },
        "route_wording_contract": wording_contract,
        "db_snapshot": _db_snapshot(db_path),
        "selected_month": selected_month,
        "route_snapshot": {
            "runtime_mode": route_snapshot["runtime_mode"],
            "route_exposed": route_snapshot["route_exposed"],
            "resolved_db_path": route_snapshot["resolved_db_path"],
            "selected_month": route_snapshot["selected_month"],
            "scope_summary": route_snapshot["scope_summary"],
            "active_artifact_binding": _compact_artifact_binding(
                route_snapshot.get("active_artifact_binding") or {}
            ),
            "scheduling": route_snapshot["scheduling"],
            "maintenance": route_snapshot["maintenance"],
        },
        "scheduling_payload": {
            "blocked": bool(scheduling_payload.get("blocked")),
            "queue_rows": int(len(scheduling_payload.get("queue_df"))),
            "assigned_rows": int(len(scheduling_payload.get("optimized_schedule_df"))),
            "queue_provenance": scheduling_payload.get("provenance_label"),
            "queue_generation_rule": scheduling_payload.get("queue_generation_rule"),
            "active_artifact_binding": _compact_artifact_binding(
                scheduling_payload.get("active_artifact_binding") or {}
            ),
        },
        "maintenance_payload": {
            "blocked": bool(maintenance_payload.get("blocked")),
            "prototype_mode": maintenance_payload.get("prototype_mode"),
            "risk_rows": int(len(maintenance_payload.get("risk_table_df", []))),
            "maintenance_event_horizon_end": maintenance_payload.get("maintenance_event_horizon_end"),
            "prototype_note": maintenance_payload.get("prototype_note"),
        },
        "active_saved_artifact_binding": active_binding,
        "fingerprints_before": before,
        "fingerprints_after": after,
        "write_safety": {
            "database_fingerprint_unchanged": before["database"]["digest"] == after["database"]["digest"],
            "model_fingerprint_unchanged": before["model"]["digest"] == after["model"]["digest"],
            "preprocessor_fingerprint_unchanged": before["preprocessor"]["digest"] == after["preprocessor"]["digest"],
            "model_provenance_fingerprint_unchanged": (
                before["model_provenance"]["digest"] == after["model_provenance"]["digest"]
            ),
            "preprocessor_provenance_fingerprint_unchanged": (
                before["preprocessor_provenance"]["digest"] == after["preprocessor_provenance"]["digest"]
            ),
            "db_write_path_executed": False,
            "etl_or_materialization_executed": False,
            "retraining_executed": False,
            "artifact_promotion_executed": False,
        },
    }
    payload["passed"] = all(
        [
            payload["runtime_paths"]["repo_local_path_match"],
            payload["app_import_boundary"]["app_imported"],
            payload["app_import_boundary"]["experimental_module_imported"],
            payload["route_visibility"]["standard_route_exposed"],
            not payload["route_visibility"]["demo_route_exposed"],
            payload["route_visibility"]["pilot_route_exposed"],
            wording_contract["stale_task4l_wording_absent"],
            route_snapshot["route_exposed"],
            not route_snapshot["scheduling"]["blocked"],
            route_snapshot["scheduling"]["queue_provenance"] == "Real-seeded synthetic queue",
            not route_snapshot["maintenance"]["blocked"],
            route_snapshot["maintenance"]["prototype_mode"] in {"Weak-label model", "Fallback evidence score"},
            scheduling_payload["active_artifact_binding"]["predictor_instantiated_from_active_paths"],
            scheduling_payload["active_artifact_binding"]["model_loaded"],
            scheduling_payload["active_artifact_binding"]["preprocessor_loaded"],
            payload["write_safety"]["database_fingerprint_unchanged"],
            payload["write_safety"]["model_fingerprint_unchanged"],
            payload["write_safety"]["preprocessor_fingerprint_unchanged"],
            payload["write_safety"]["model_provenance_fingerprint_unchanged"],
            payload["write_safety"]["preprocessor_provenance_fingerprint_unchanged"],
        ]
    )
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
