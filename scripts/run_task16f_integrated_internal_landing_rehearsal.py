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

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.canonical_gold_reader import CanonicalGoldReader
from core.canonical_ml_reader import CanonicalMLReader
from core.canonical_optimization_reader import CanonicalOptimizationReader
from core.experimental_scheduling import get_active_saved_artifact_binding
from core.maintenance_evidence import MaintenanceEvidenceReader
from core.ml_predictor import MLPredictor
from core.runtime_mode import (
    DEMO_READONLY_RUNTIME_MODE,
    PILOT_REVIEW_RUNTIME_MODE,
    STANDARD_RUNTIME_MODE,
)
from core.runtime_paths import get_database_path


REHEARSAL_MONTH = "February 2026"
DB_FACT_SUMMARY_SQL = (
    "SELECT COUNT(*), MIN(substr(hour_ts, 1, 7)), MAX(substr(hour_ts, 1, 7)) "
    "FROM fact_machine_hour"
)
DB_MONTH_ROWCOUNT_SQL = (
    "SELECT COUNT(*) FROM fact_machine_hour WHERE hour_ts >= ? AND hour_ts < ?"
)


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


def _read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _json_default(value: object):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _month_bounds(month_year: str) -> tuple[str, str]:
    month_start = pd.to_datetime(month_year, format="%B %Y", errors="raise")
    next_month_start = month_start + pd.offsets.MonthBegin(1)
    return (
        month_start.strftime("%Y-%m-%dT00:00:00"),
        next_month_start.strftime("%Y-%m-%dT00:00:00"),
    )


def _db_snapshot(db_path: Path, month_year: str) -> dict[str, object]:
    month_start, next_month_start = _month_bounds(month_year)
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only = ON")
        fact_rows, min_month, max_month = conn.execute(DB_FACT_SUMMARY_SQL).fetchone()
        selected_month_rows = conn.execute(
            DB_MONTH_ROWCOUNT_SQL,
            (month_start, next_month_start),
        ).fetchone()[0]
    return {
        "fact_machine_hour_rows": int(fact_rows),
        "month_key_min": min_month,
        "month_key_max": max_month,
        "selected_month": month_year,
        "selected_month_rows": int(selected_month_rows),
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
    streamlit_stub.radio = lambda _label, options, index=0, *args, **kwargs: (
        options[index] if options else None
    )
    streamlit_stub.slider = lambda _label, min_value=None, max_value=None, value=None, *args, **kwargs: value
    streamlit_stub.checkbox = lambda *args, value=False, **kwargs: value
    streamlit_stub.file_uploader = lambda *args, **kwargs: None
    streamlit_stub.data_editor = lambda value, *args, **kwargs: value
    streamlit_stub.download_button = lambda *args, **kwargs: None
    streamlit_stub.button = lambda *args, **kwargs: False
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

    energy_stub = types.ModuleType("modules.energy_module")
    energy_stub.render_energy_module = _no_op
    stubs["modules.energy_module"] = energy_stub

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


def _import_app_shell_contract_module() -> object:
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

    app_spec = importlib.util.spec_from_file_location("task16f_rehearsal_app", REPO_ROOT / "app.py")
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


def _import_route_modules() -> dict[str, object]:
    _install_streamlit_stub()
    module_names = {
        "etl_module": "modules.etl_module",
        "unified_view_module": "modules.unified_view_module",
        "energy_module": "modules.energy_module",
        "optimization_module": "modules.optimization_module",
        "ml_module": "modules.ml_module",
        "maintenance_module": "modules.maintenance_module",
        "experimental_intelligence_lab_module": "modules.experimental_intelligence_lab_module",
    }
    imported: dict[str, object] = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for key, module_name in module_names.items():
            imported[key] = importlib.import_module(module_name)
    return imported


def _pick_rehearsal_month(available_months: list[str]) -> str:
    if REHEARSAL_MONTH in available_months:
        return REHEARSAL_MONTH
    if not available_months:
        raise RuntimeError("No canonical month is available for Task16F rehearsal.")
    return available_months[0]


def _compact_binding(binding: dict[str, object]) -> dict[str, object]:
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
        "predictor_instantiated_from_active_paths": binding.get(
            "predictor_instantiated_from_active_paths"
        ),
        "model_loaded": binding.get("model_loaded"),
        "preprocessor_loaded": binding.get("preprocessor_loaded"),
    }


def _find_machine_with_maintenance_history(
    page_df: pd.DataFrame,
    evidence_reader: MaintenanceEvidenceReader,
    *,
    as_of: pd.Timestamp,
) -> dict[str, object]:
    if page_df.empty:
        return {
            "blocked": True,
            "message": "The selected canonical month slice is empty, so no maintenance evidence lookup is possible.",
        }

    machine_priority = (
        page_df.groupby("machine_id", dropna=False)
        .size()
        .sort_values(ascending=False)
        .index.tolist()
    )
    for machine_id in machine_priority:
        if machine_id is None or str(machine_id).strip() == "":
            continue
        evidence = evidence_reader.build_machine_evidence(
            str(machine_id),
            recent_window_limit=10,
            as_of=as_of,
        )
        if evidence.get("machine_has_history"):
            return {
                "blocked": False,
                "machine_id": str(machine_id),
                "all_time_event_count": int(evidence["all_time_event_count"]),
                "recent_window_event_count": int(evidence["recent_window_event_count"]),
                "pm_ratio_all_time": evidence["pm_ratio_all_time"],
                "pm_ratio_recent_window": evidence["pm_ratio_recent_window"],
                "latest_maintenance_datetime_label": evidence["latest_maintenance_datetime_label"],
                "months_covered_count": int(evidence["months_covered_count"]),
                "history_window_note": evidence["history_window_note"],
            }

    return {
        "blocked": True,
        "message": (
            "No machine from the selected canonical month slice returned linked maintenance history "
            "through the read-only evidence helper."
        ),
    }


def _bool(value: object) -> bool:
    return bool(value)


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

    app_module = _import_app_shell_contract_module()
    route_modules = _import_route_modules()
    model_manifest = _read_json(model_provenance_path)
    preprocessor_manifest = _read_json(preprocessor_provenance_path)

    gold_reader = CanonicalGoldReader(db_path=str(db_path))
    rehearsal_month = _pick_rehearsal_month(gold_reader.get_available_months())
    month_start_label, next_month_start_label = _month_bounds(rehearsal_month)
    selected_month_end = pd.Timestamp(next_month_start_label) - pd.Timedelta(seconds=1)

    with contextlib.redirect_stdout(io.StringIO()):
        page_df = gold_reader.read_month_page_dataframe(rehearsal_month)
        overview_metrics = gold_reader.build_month_metrics(page_df) if not page_df.empty else {}

        energy_snapshot = route_modules["energy_module"].build_energy_route_snapshot(
            db_path=str(db_path),
            selected_month=rehearsal_month,
        )

        optimization_reader = CanonicalOptimizationReader(db_path=str(db_path))
        optimization_summary_df = optimization_reader.build_machine_summary(rehearsal_month)
        schedule_payload = route_modules["optimization_module"].build_schedule_tab_payload(
            optimization_reader,
            rehearsal_month,
        )
        team_payload = route_modules["optimization_module"].build_team_insights_tab_payload(
            optimization_reader,
            rehearsal_month,
        )

        predictor = MLPredictor(
            model_path=str(model_path),
            preprocessor_path=str(preprocessor_path),
        )
        ml_reader = CanonicalMLReader(db_path=str(db_path))
        ml_input_df = ml_reader.build_month_input_dataframe(rehearsal_month, predictor=predictor)
        ml_candidate_df = ml_reader.build_prediction_candidates(ml_input_df)
        ml_prediction_df, ml_blocked_df = ml_reader.build_prediction_dataframe(
            ml_candidate_df,
            predictor=predictor,
        )
        ml_predictor_status = ml_reader.get_predictor_status(predictor)

        maintenance_reader = MaintenanceEvidenceReader(db_path=str(db_path))
        maintenance_coverage = maintenance_reader.build_coverage_snapshot()
        maintenance_evidence = _find_machine_with_maintenance_history(
            page_df,
            maintenance_reader,
            as_of=selected_month_end,
        )

        experimental_snapshot = route_modules[
            "experimental_intelligence_lab_module"
        ].build_experimental_lab_route_snapshot(
            rehearsal_month,
            runtime_mode=PILOT_REVIEW_RUNTIME_MODE,
            db_path=str(db_path),
            queue_size=3,
            max_jobs_per_machine=1,
            horizon_days=14,
        )

    etl_availability_df = route_modules["etl_module"]._build_extension_source_availability_dataframe()
    if rehearsal_month in route_modules["etl_module"].EXTENSION_MONTH_SOURCE_MAPPINGS:
        selected_etl_source_mapping = route_modules["etl_module"]._resolve_extension_source_mapping(
            rehearsal_month,
        )
        etl_missing_files = [
            path_value
            for path_value in (
                *selected_etl_source_mapping["energy_files"],
                selected_etl_source_mapping["csi_file"],
                selected_etl_source_mapping["mes_file"],
            )
            if path_value and not Path(path_value).exists()
        ]
    else:
        selected_etl_source_mapping = {
            "dataset_root": None,
            "energy_files": [],
            "csi_file": None,
            "mes_file": None,
            "family_status": {},
            "backfill_readiness": "not_mapped",
            "notes": [
                "The selected rehearsal month is not part of the ETL extension source-mapping table.",
            ],
        }
        etl_missing_files = []

    active_binding = _compact_binding(
        experimental_snapshot.get("active_artifact_binding")
        or get_active_saved_artifact_binding()
    )
    experimental_scheduling = experimental_snapshot.get("scheduling") or {}
    experimental_maintenance = experimental_snapshot.get("maintenance") or {}

    after = {
        "database": _fingerprint(db_path, "sha1"),
        "model": _fingerprint(model_path, "sha256"),
        "preprocessor": _fingerprint(preprocessor_path, "sha256"),
        "model_provenance": _fingerprint(model_provenance_path, "sha256"),
        "preprocessor_provenance": _fingerprint(preprocessor_provenance_path, "sha256"),
    }

    visibility_by_mode = {
        STANDARD_RUNTIME_MODE: app_module.get_app_shell_contract(STANDARD_RUNTIME_MODE),
        DEMO_READONLY_RUNTIME_MODE: app_module.get_app_shell_contract(DEMO_READONLY_RUNTIME_MODE),
        PILOT_REVIEW_RUNTIME_MODE: app_module.get_app_shell_contract(PILOT_REVIEW_RUNTIME_MODE),
    }

    etl_result = {
        "module_imported": True,
        "runtime_mode_rehearsed": PILOT_REVIEW_RUNTIME_MODE,
        "route_visible_in_pilot_review": "🔄 ETL Pipeline"
        in visibility_by_mode[PILOT_REVIEW_RUNTIME_MODE]["visible_pages"],
        "historical_source_months_listed": int(len(etl_availability_df)),
        "selected_month_source_mapping": {
            "month": rehearsal_month,
            "dataset_root": selected_etl_source_mapping["dataset_root"],
            "family_status": selected_etl_source_mapping["family_status"],
            "backfill_readiness": selected_etl_source_mapping["backfill_readiness"],
            "notes": selected_etl_source_mapping["notes"],
            "missing_files": etl_missing_files,
        },
        "route_scope_rehearsal_status": "limited_read_only",
        "limitation": (
            "The ETL upload/process/backfill path is intentionally not exercised in Task16F because it mutates the DB. "
            "Only route import plus month/source availability contract were rehearsed honestly."
        ),
    }

    overview_result = {
        "module_imported": True,
        "available_month_count": int(len(gold_reader.get_available_months())),
        "selected_month": rehearsal_month,
        "rows_loaded": int(len(page_df)),
        "distinct_machines": overview_metrics.get("distinct_machines"),
        "weighted_kwh_per_good_unit": overview_metrics.get("weighted_kwh_per_good_unit"),
        "canonical_read_path": "CanonicalGoldReader.read_month_page_dataframe",
        "fallback_used": False,
    }

    top_optimization_machine = None
    if not optimization_summary_df.empty:
        top_optimization_machine = str(optimization_summary_df.iloc[0]["machine_id"])

    energy_result = {
        "module_imported": True,
        "selected_month": energy_snapshot.get("selected_month"),
        "rows_loaded": energy_snapshot.get("rows_loaded"),
        "total_energy_kwh": energy_snapshot.get("total_energy_kwh"),
        "weighted_kwh_per_good_unit": energy_snapshot.get("weighted_kwh_per_good_unit"),
        "canonical_read_path": "modules.energy_module.build_energy_route_snapshot -> CanonicalEnergyReader",
        "fallback_used": bool(energy_snapshot.get("fallback_used")),
        "legacy_energy_fallback_used": False,
    }

    optimization_result = {
        "module_imported": True,
        "selected_month": rehearsal_month,
        "machine_summary_rows": int(len(optimization_summary_df)),
        "top_machine": top_optimization_machine,
        "schedule_payload_blocked": bool(schedule_payload.get("blocked")),
        "schedule_rows": int(len(schedule_payload.get("schedule_df", pd.DataFrame()))),
        "team_payload_blocked": bool(team_payload.get("blocked")),
        "team_rows": int(len(team_payload.get("team_df", pd.DataFrame()))),
        "route_aligned_helpers": [
            "CanonicalOptimizationReader.build_machine_summary",
            "modules.optimization_module.build_schedule_tab_payload",
            "modules.optimization_module.build_team_insights_tab_payload",
        ],
    }

    ml_result = {
        "module_imported": True,
        "selected_month": rehearsal_month,
        "input_rows": int(len(ml_input_df)),
        "candidate_rows": int(len(ml_candidate_df)),
        "prediction_rows": int(len(ml_prediction_df)),
        "blocked_after_predictor_gate_rows": int(len(ml_blocked_df)),
        "predictor_loaded_model": bool(getattr(predictor, "loaded_model", False)),
        "predictor_loaded_preprocessor": bool(getattr(predictor, "loaded_preprocessor", False)),
        "predictor_status": ml_predictor_status,
        "active_binding": {
            "task_tag": model_manifest.get("task_tag"),
            "artifact_version_id": model_manifest.get("artifact_version_id"),
            "selected_model": model_manifest.get("selected_model"),
        },
        "canonical_read_path": "CanonicalMLReader + active MLPredictor",
    }

    maintenance_result = {
        "module_imported": True,
        "coverage_snapshot": {
            "maintenance_records_available": bool(maintenance_coverage["maintenance_records_available"]),
            "records_stored": int(maintenance_coverage["records_stored"]),
            "integrated_machine_count": int(maintenance_coverage["integrated_machine_count"]),
            "months_covered_count": int(maintenance_coverage["months_covered_count"]),
            "latest_month": maintenance_coverage["latest_month"],
            "latest_maintenance_datetime_label": maintenance_coverage[
                "latest_maintenance_datetime_label"
            ],
        },
        "selected_month_evidence": maintenance_evidence,
        "limitation": (
            "Task16F rehearses only the read-only evidence surface. Upload/integration controls stay out of scope "
            "because they would mutate maintenance tables."
        ),
    }

    experimental_result = {
        "module_imported": True,
        "runtime_mode_rehearsed": PILOT_REVIEW_RUNTIME_MODE,
        "selected_month": experimental_snapshot.get("selected_month"),
        "route_exposed": bool(experimental_snapshot.get("route_exposed")),
        "active_artifact_binding": active_binding,
        "scheduling": experimental_scheduling,
        "maintenance": experimental_maintenance,
        "scope_summary": experimental_snapshot.get("scope_summary"),
        "non_defended_boundary": (
            "Internal-landing experimental flagship lane only. Read-only. Non-defended for production claims."
        ),
    }

    route_results = {
        "etl_pipeline": etl_result,
        "canonical_operations_overview": overview_result,
        "energy_analysis": energy_result,
        "operational_decision_support": optimization_result,
        "efficiency_prediction_and_governance": ml_result,
        "maintenance": maintenance_result,
        "experimental_intelligence_lab": experimental_result,
    }

    hard_blockers: list[str] = []
    if db_path != expected_db_path:
        hard_blockers.append(
            f"Runtime DB path resolved to `{db_path}` instead of repo-local `{expected_db_path}`."
        )
    if not _bool(visibility_by_mode[PILOT_REVIEW_RUNTIME_MODE]["visible_pages"]):
        hard_blockers.append("Pilot-review visible page contract could not be resolved from app.py.")
    if len(page_df) <= 0:
        hard_blockers.append(
            f"Canonical Operations Overview could not load a real `{rehearsal_month}` slice from `fact_machine_hour`."
        )
    if bool(energy_result["fallback_used"]) or not energy_result["rows_loaded"]:
        hard_blockers.append(
            f"Energy Analysis could not build a real canonical `{rehearsal_month}` summary without fallback."
        )
    if optimization_result["machine_summary_rows"] <= 0 or optimization_result["schedule_payload_blocked"]:
        hard_blockers.append(
            f"Operational Decision Support could not build the real `{rehearsal_month}` machine/schedule payload."
        )
    if (
        ml_result["prediction_rows"] <= 0
        or not ml_result["predictor_loaded_model"]
        or not ml_result["predictor_loaded_preprocessor"]
    ):
        hard_blockers.append(
            f"Efficiency Prediction & Governance could not load the active Task14F artifacts or produce real `{rehearsal_month}` predictions."
        )
    if maintenance_result["coverage_snapshot"]["records_stored"] <= 0:
        hard_blockers.append("Maintenance evidence tables are not available for a read-only rehearsal.")
    if maintenance_result["selected_month_evidence"].get("blocked"):
        hard_blockers.append(
            "Maintenance route could not prove one selected-month machine evidence read through the read-only helper."
        )
    if (
        not experimental_result["route_exposed"]
        or experimental_result["scheduling"] is None
        or experimental_result["maintenance"] is None
        or experimental_result["scheduling"]["blocked"]
        or experimental_result["maintenance"]["blocked"]
    ):
        hard_blockers.append(
            f"Experimental Intelligence Lab could not complete the integrated `{rehearsal_month}` pilot-review rehearsal."
        )
    if not all(
        before[key]["digest"] == after[key]["digest"]
        for key in before
    ):
        hard_blockers.append("DB or live artifact fingerprints changed during the rehearsal.")

    soft_debt = [
        etl_result["limitation"],
        maintenance_result["limitation"],
        (
            "The integrated rehearsal proves route-aligned read paths and shell exposure contracts only; "
            "it does not replace a human whole-platform interaction pass in a live Streamlit session."
        ),
    ]
    explicit_non_defended_limits = [
        "Experimental scheduling remains a read-only prototype, not a live scheduling engine or solver.",
        "Experimental scheduling default provenance remains real-seeded synthetic unless a narrow real-input pilot queue is uploaded.",
        (
            "Experimental maintenance remains a weak-label-model-or-fallback evidence prototype, "
            "not a production predictive-maintenance recommendation engine."
        ),
        (
            "Experimental maintenance-event observation horizon remains bounded by stored maintenance records through "
            f"`{experimental_maintenance.get('maintenance_event_horizon_end') or 'unknown'}`."
        ),
    ]

    internal_use_handoff = {
        "recommended_runtime_mode": PILOT_REVIEW_RUNTIME_MODE,
        "exact_launch_command": (
            "SMART_MFG_RUNTIME_MODE=pilot_review ./.conda311/bin/streamlit run app.py "
            "--server.port 8502 --server.address 0.0.0.0 --server.headless true"
        ),
        "route_order": [
            "🔄 ETL Pipeline",
            "📊 Canonical Operations Overview",
            "⚡ Energy Analysis",
            "🎯 Operational Decision Support",
            "🤖 Efficiency Prediction & Governance",
            "🔧 Maintenance",
            "🧪 Experimental Intelligence Lab",
        ],
        "selected_month": rehearsal_month,
        "manual_verification_checklist": {
            "🔄 ETL Pipeline": (
                "Confirm pilot-review hides upload/process controls, the Jul 2025 -> Mar 2026 source-availability table renders, "
                "and no page action offers DB mutation."
            ),
            "📊 Canonical Operations Overview": (
                f"Keep `{rehearsal_month}` selected and confirm real canonical month cards plus table output render from `fact_machine_hour`."
            ),
            "⚡ Energy Analysis": (
                f"Keep `{rehearsal_month}` selected and confirm canonical energy KPI, attribution coverage, and machine-attention views render without any EUVG/unified_view fallback messaging."
            ),
            "🎯 Operational Decision Support": (
                f"Keep `{rehearsal_month}` selected and confirm the worklist, schedule-tab payload, and team-insights payload all render as canonical read-only decision support."
            ),
            "🤖 Efficiency Prediction & Governance": (
                f"Keep `{rehearsal_month}` selected and confirm active saved-model status, prediction rows, blocked-reason surfaces, and Scenario Lab all stay read-only."
            ),
            "🔧 Maintenance": (
                "Confirm coverage cards, machine evidence lookup, and supporting maintenance-age energy context render; upload/integration controls must stay hidden in pilot_review."
            ),
            "🧪 Experimental Intelligence Lab": (
                f"Keep `{rehearsal_month}` selected and confirm route snapshot, scheduling payload provenance, maintenance prototype mode, and export/provenance messaging all remain explicit and non-defended."
            ),
        },
        "boundaries_to_keep_visible": [
            "Repo-local runtime DB path remains `manufacturing_data.db`.",
            "Active saved artifact bundle remains `Task 14F / 20260419_181842 / random_forest`.",
            "Experimental lane stays read-only and non-defended.",
            "Experimental scheduling provenance must stay explicit.",
            "Experimental maintenance-event horizon note must stay explicit for late-anchor months.",
        ],
        "do_not_claim": [
            "Do not claim a live solver or production scheduling engine.",
            "Do not claim production predictive-maintenance status.",
            "Do not claim that pilot_review rehearses ETL processing, DB writes, retraining, or artifact promotion.",
            "Do not claim that experimental outputs are defended production truth.",
        ],
    }

    payload = {
        "task": "Task16F",
        "passed": len(hard_blockers) == 0,
        "selected_month": rehearsal_month,
        "runtime_paths": {
            "resolved_db_path": str(db_path),
            "expected_repo_local_db_path": str(expected_db_path),
            "repo_local_path_match": db_path == expected_db_path,
        },
        "db_snapshot": _db_snapshot(db_path, rehearsal_month),
        "active_live_state": {
            "model_manifest": {
                "task_tag": model_manifest.get("task_tag"),
                "artifact_version_id": model_manifest.get("artifact_version_id"),
                "selected_model": model_manifest.get("selected_model"),
                "active_db_path": model_manifest.get("active_db_path"),
            },
            "preprocessor_manifest": {
                "task_tag": preprocessor_manifest.get("task_tag"),
                "artifact_version_id": preprocessor_manifest.get("artifact_version_id"),
                "selected_model": preprocessor_manifest.get("selected_model"),
                "active_db_path": preprocessor_manifest.get("active_db_path"),
            },
        },
        "route_visibility_by_mode": {
            runtime_mode: {
                "visible_pages": contract["visible_pages"],
                "loader_dependent_visible_pages": contract["loader_dependent_visible_pages"],
            }
            for runtime_mode, contract in visibility_by_mode.items()
        },
        "route_results": route_results,
        "blocker_map": {
            "hard_blockers_before_internal_use_testing": hard_blockers,
            "soft_non_blocking_debt": soft_debt,
            "explicit_non_defended_prototype_limits": explicit_non_defended_limits,
        },
        "internal_use_test_handoff": internal_use_handoff,
        "sql_probes": [
            DB_FACT_SUMMARY_SQL,
            f"{DB_MONTH_ROWCOUNT_SQL}  -- params: ({month_start_label}, {next_month_start_label})",
        ],
        "route_module_checks_run": [
            "app.py import boundary with blocked legacy loader imports",
            "modules.etl_module import",
            "modules.unified_view_module import",
            "modules.energy_module import + build_energy_route_snapshot",
            "modules.optimization_module import + build_schedule_tab_payload + build_team_insights_tab_payload",
            "modules.ml_module import + CanonicalMLReader + MLPredictor",
            "modules.maintenance_module import + MaintenanceEvidenceReader coverage/evidence read",
            "modules.experimental_intelligence_lab_module import + build_experimental_lab_route_snapshot in pilot_review",
        ],
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
                before["preprocessor_provenance"]["digest"]
                == after["preprocessor_provenance"]["digest"]
            ),
            "db_write_path_executed": False,
            "etl_or_materialization_executed": False,
            "retraining_executed": False,
            "artifact_promotion_executed": False,
        },
    }

    print(json.dumps(payload, indent=2, ensure_ascii=True, default=_json_default))


if __name__ == "__main__":
    main()
