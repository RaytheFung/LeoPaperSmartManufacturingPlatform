"""Read-only preflight plans for future historical backfill rehearsals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.source_manifest_discovery import get_manifest_month_source_files
from modules.etl_module import ETLPipelineModule
from scripts.compare_source_discovery_modes import build_source_discovery_compare_diagnostics


_JULY_2025_RATIONALE = (
    "July 2025 is the first accepted extension month, has complete Energy/CSI/MES "
    "source-family status, and avoids the later accepted-month flag and quarantine "
    "complexity documented for August 2025 and February 2026."
)

_TEMP_DB_PATH_RECOMMENDATIONS = {
    "July 2025": "/tmp/leopaper_stage_b6_july_rehearsal/july_rehearsal.db",
    "August 2025": "/tmp/leopaper_stage_b8_2_august_rehearsal/august_rehearsal.db",
}

_PLANNED_EXECUTION_STEPS = [
    "Confirm the selected month remains accepted and source-discovery compare diagnostics pass.",
    "Create a temp-only DB copy outside the Git working tree in the future rehearsal task.",
    "Run ETLPipelineModule.run_historical_canonical_backfill() for the selected month against the temp DB only.",
    "Capture extracted Energy/CSI/MES row counts after month scoping.",
    "Capture machine mapping counts and partial-match counts.",
    "Capture ETL staging, Bronze, Silver, Gold, and fact_machine_hour row counts.",
    "Capture aggregate energy, good-quantity, scrap-quantity, source-flag, and quarantine checks.",
    "Run downstream regression tests and unsafe-file scans before any evidence is staged.",
]

_PLANNED_WRITE_SURFACES = [
    "temp DB copy only",
    "ETL staging tables on temp DB",
    "Bronze raw tables on temp DB",
    "Silver month partitions on temp DB",
    "Gold fact_machine_hour month partition on temp DB",
]

_ABORT_CRITERIA = [
    "DB path is not temp-only or is inside the Git working tree.",
    "Repo-local manufacturing_data.db or another live/shared DB would be written.",
    "Source payload comparison mismatches for the selected month.",
    "March 2026 becomes accepted or is included in any target-month output.",
    "Extracted, mapping, ETL staging, Bronze, Silver, or Gold row counts materially diverge.",
    "Canonical materialization writes outside the temp DB.",
    "Runtime exceeds the declared safe threshold.",
    "Downstream regression tests fail.",
    "Raw DB, raw Excel, generated etl_outputs, model artifacts, or local env folders would be staged.",
]

_REQUIRED_POST_RUN_EVIDENCE = [
    "source payload summary and compare diagnostic result",
    "extracted Energy/CSI/MES row counts after month scoping",
    "machine mapping counts and partial-match counts",
    "ETL staging row counts",
    "Bronze/Silver/Gold row counts",
    "fact_machine_hour month row count",
    "duplicate source_row_hash group counts for target-month raw and silver surfaces",
    "aggregate kWh, good quantity, scrap quantity, and quantity-basis checks",
    "source flag and quarantine consistency checks",
    "runtime duration and stage timing",
    "temp DB path proof plus live/repo DB non-write proof",
    "post-run regression tests and unsafe-file scans",
]

_AUGUST_REQUIRED_POST_RUN_EVIDENCE = [
    "source payload summary and compare diagnostic result",
    "extracted Energy/CSI/MES row counts after August month scoping",
    "machine mapping counts and partial-match counts",
    "ETL staging row counts for August 2025",
    "Bronze/Silver row counts for August raw_energy_hourly, raw_csi_event, raw_mes_report, energy_meter_hour, csi_job_event, and mes_report_event",
    "Gold fact_machine_hour August row count",
    "duplicate source_row_hash group counts for August raw_csi_event and csi_job_event",
    "B7.3 spill identity capture under August raw and silver scope",
    "aggregate kWh, good quantity, scrap quantity, and quantity-basis checks",
    "runtime duration and stage timing",
    "temp DB path proof plus live/repo DB non-write proof",
    "post-run regression tests and unsafe-file scans",
]

_AUGUST_ISOLATION_PRUNE_SURFACES = [
    {
        "surface": "etl_runs",
        "scope": "month_processed = 'August 2025'",
        "reason": "ETL run ledger rows are month-scoped by month_processed.",
    },
    {
        "surface": "etl_energy_data",
        "scope": "month_year = 'August 2025'",
        "reason": "ETL Energy staging is month-scoped by month_year.",
    },
    {
        "surface": "etl_csi_data",
        "scope": "month_year = 'August 2025'",
        "reason": "ETL CSI staging is month-scoped by month_year.",
    },
    {
        "surface": "etl_mes_data",
        "scope": "month_year = 'August 2025'",
        "reason": "ETL MES staging is month-scoped by month_year.",
    },
    {
        "surface": "raw_energy_hourly",
        "scope": "substr(raw_timestamp, 1, 7) = '2025-08'",
        "reason": "Bronze Energy is month-scoped by raw_timestamp.",
    },
    {
        "surface": "raw_csi_event",
        "scope": "current raw CSI canonical month expression = '2025-08'",
        "reason": "Bronze CSI must use the same first-available timestamp rule documented in B7.2/B7.3.",
    },
    {
        "surface": "raw_mes_report",
        "scope": "substr(json_extract(raw_payload_json, '$.\"報工時間\"'), 1, 7) = '2025-08'",
        "reason": "Bronze MES is month-scoped by report timestamp in raw_payload_json.",
    },
    {
        "surface": "energy_meter_hour",
        "scope": "substr(hour_ts, 1, 7) = '2025-08'",
        "reason": "Silver Energy is month-scoped by hour_ts.",
    },
    {
        "surface": "csi_job_event",
        "scope": "current silver CSI canonical month expression = '2025-08'",
        "reason": "Silver CSI must preserve the B7.2/B7.3 canonical month rule.",
    },
    {
        "surface": "mes_report_event",
        "scope": "substr(report_ts, 1, 7) = '2025-08'",
        "reason": "Silver MES is month-scoped by report_ts.",
    },
    {
        "surface": "fact_machine_hour",
        "scope": "substr(hour_ts, 1, 7) = '2025-08'",
        "reason": "Gold fact table is month-scoped by hour_ts.",
    },
    {
        "surface": "machine_monthly_presence",
        "scope": "month_year = 'August 2025'",
        "reason": "Machine presence is explicitly month-scoped by month_year.",
    },
]

_AUGUST_SPILL_TRACEABILITY_REQUIREMENT = {
    "required": True,
    "source_stage": "B7.3",
    "required_check": "Run the B7.3 spill identity traceability check after a future August temp-only rehearsal.",
    "expected_spill_identity_count": 235,
    "required_raw_unmatched_count": 0,
    "required_silver_unmatched_count": 0,
    "identity_key": "machine_id + start_time + end_time + prep_end_time + order_id + material + good_qty",
    "proof_path": (
        "Match July-package spill identities into August canonical raw CSI rows, then use matched "
        "raw source_row_hash values to prove August canonical silver traceability."
    ),
}

_PROOF_GAPS = [
    "ETL output equivalence is not proven by this preflight plan.",
    "Canonical Silver/Gold materialization equivalence is not proven by this preflight plan.",
    "Runtime duration is not proven until a temp-only rehearsal executes.",
    "Month-scoping behavior for real workbook spill rows is not proven until execution.",
]


def build_historical_backfill_preflight_plan(
    month_label: str = "July 2025",
    data_root: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a read-only plan for a future temp-only backfill rehearsal.

    The helper performs source-discovery checks only. It does not load raw Excel
    content, run ETL, instantiate canonical materialization, connect to SQLite,
    copy a database, or write files.
    """
    normalized_month_label = _normalize_month_label(month_label)
    manifest_spec = get_manifest_month_source_files(normalized_month_label)
    compare_diagnostics = build_source_discovery_compare_diagnostics(
        month_labels=[manifest_spec["month_label"]],
        data_root=data_root,
        pipeline=ETLPipelineModule(initialize_schema=False),
    )
    compare_row = compare_diagnostics["rows"][0]
    blocked = _is_blocked_month(manifest_spec, compare_row)

    plan = {
        "target_month": manifest_spec["month_label"],
        "target_month_key": manifest_spec["month_key"],
        "accepted_for_rehearsal": not blocked,
        "blocked": blocked,
        "blocked_reason": _blocked_reason(manifest_spec, compare_row) if blocked else None,
        "source_discovery_default_policy": "auto / manifest-backed",
        "source_discovery_policy": (
            "Stage B5 auto policy uses manifest-backed discovery for accepted extension months; "
            "March 2026 remains blocked."
        ),
        "default_resolver_mode": "auto",
        "explicit_legacy_resolver_available": True,
        "compare_diagnostic_available": True,
        "compare_diagnostic_status": _build_compare_diagnostic_status(compare_row, blocked),
        "source_payload_summary": _build_source_payload_summary(manifest_spec, compare_row),
        "source_payload_equivalence_status": _equivalence_status(compare_row, blocked),
        "expected_source_files": _build_expected_source_files(manifest_spec, data_root),
        "missing_source_files": _build_missing_source_files(manifest_spec, data_root),
        "expected_source_families": dict(manifest_spec["family_status"]),
        "planned_execution_steps": list(_PLANNED_EXECUTION_STEPS),
        "planned_write_surfaces": list(_PLANNED_WRITE_SURFACES),
        "temp_db_required": True,
        "planned_temp_db_path": _planned_temp_db_path(manifest_spec["month_label"], db_path),
        "planned_isolation_prune_surfaces": _planned_isolation_prune_surfaces(manifest_spec["month_label"]),
        "spill_row_traceability_requirement": _spill_traceability_requirement(manifest_spec["month_label"]),
        "live_db_write_allowed": False,
        "repo_db_write_allowed": False,
        "raw_file_staging_allowed": False,
        "generated_output_staging_allowed": False,
        "model_artifact_change_allowed": False,
        "rollback_boundary": (
            "No rollback is required for this read-only preflight. Future rehearsal rollback "
            "must discard the temp DB and prove no live or repo DB was written."
        ),
        "abort_criteria": list(_ABORT_CRITERIA),
        "required_post_run_evidence": _required_post_run_evidence(manifest_spec["month_label"]),
        "proof_gaps": list(_PROOF_GAPS),
        "july_2025_candidate_rationale": _JULY_2025_RATIONALE,
    }
    if blocked:
        plan["planned_execution_steps"] = [
            "Do not run a rehearsal for this month.",
            "Keep March 2026 blocked unless a later approved scope explicitly reopens it.",
        ]
        plan["planned_write_surfaces"] = []
    return plan


def _normalize_month_label(month_label: str) -> str:
    cleaned = str(month_label or "").strip()
    if not cleaned:
        raise ValueError("month_label must be a non-empty month label.")
    return cleaned


def _is_blocked_month(manifest_spec: dict[str, Any], compare_row: dict[str, Any]) -> bool:
    return (
        manifest_spec.get("canonical_scope_status") != "accepted"
        or manifest_spec.get("backfill_readiness") == "blocked"
        or bool(compare_row.get("expected_blocked"))
    )


def _blocked_reason(manifest_spec: dict[str, Any], compare_row: dict[str, Any]) -> str:
    errors = compare_row.get("errors") or {}
    messages = [
        str(error_payload.get("message"))
        for error_payload in errors.values()
        if isinstance(error_payload, dict) and error_payload.get("message")
    ]
    if messages:
        return " ".join(messages)
    return (
        f"{manifest_spec['month_label']} is not accepted for rehearsal: "
        f"canonical_scope_status={manifest_spec.get('canonical_scope_status')}, "
        f"backfill_readiness={manifest_spec.get('backfill_readiness')}."
    )


def _build_source_payload_summary(
    manifest_spec: dict[str, Any],
    compare_row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "month_label": manifest_spec["month_label"],
        "month_key": manifest_spec["month_key"],
        "canonical_scope_status": manifest_spec["canonical_scope_status"],
        "backfill_readiness": manifest_spec["backfill_readiness"],
        "family_status": dict(manifest_spec["family_status"]),
        "legacy_status": compare_row.get("legacy_status"),
        "manifest_status": compare_row.get("manifest_status"),
        "matches": bool(compare_row.get("matches")),
        "difference_count": len(compare_row.get("differences") or []),
        "expected_blocked": bool(compare_row.get("expected_blocked")),
        "ok": bool(compare_row.get("ok")),
        "notes": list(manifest_spec.get("notes") or []),
    }


def _build_compare_diagnostic_status(compare_row: dict[str, Any], blocked: bool) -> dict[str, Any]:
    return {
        "status": _equivalence_status(compare_row, blocked),
        "ok": bool(compare_row.get("ok")),
        "legacy_status": compare_row.get("legacy_status"),
        "manifest_status": compare_row.get("manifest_status"),
        "matches": bool(compare_row.get("matches")),
        "difference_count": len(compare_row.get("differences") or []),
        "expected_blocked": bool(compare_row.get("expected_blocked")),
        "backfill_readiness": compare_row.get("backfill_readiness"),
    }


def _equivalence_status(compare_row: dict[str, Any], blocked: bool) -> str:
    if blocked:
        return "blocked"
    if compare_row.get("ok") and compare_row.get("matches"):
        return "match"
    return "review_required"


def _build_expected_source_files(
    manifest_spec: dict[str, Any],
    data_root: str | Path | None,
) -> dict[str, Any]:
    def resolve(relative_path: str | None) -> str | None:
        if relative_path is None:
            return None
        if data_root is None:
            return relative_path
        return str(Path(data_root) / relative_path)

    return {
        "data_root": str(Path(data_root)) if data_root is not None else manifest_spec["scope_id"],
        "energy_files": [resolve(path) for path in manifest_spec["energy_files"]],
        "csi_file": resolve(manifest_spec.get("csi_file")),
        "mes_file": resolve(manifest_spec.get("mes_file")),
    }


def _build_missing_source_files(
    manifest_spec: dict[str, Any],
    data_root: str | Path | None,
) -> list[str]:
    if data_root is None:
        return []
    expected = _build_expected_source_files(manifest_spec, data_root)
    paths = [
        *expected["energy_files"],
        *([expected["csi_file"]] if expected.get("csi_file") else []),
        *([expected["mes_file"]] if expected.get("mes_file") else []),
    ]
    return [str(path) for path in paths if path and not Path(path).exists()]


def _planned_temp_db_path(month_label: str, db_path: str | Path | None) -> str:
    if db_path is not None:
        return str(Path(db_path))
    return _TEMP_DB_PATH_RECOMMENDATIONS.get(month_label, "/tmp/leopaper_historical_backfill_rehearsal/temp_rehearsal.db")


def _planned_isolation_prune_surfaces(month_label: str) -> list[dict[str, str]]:
    if month_label == "August 2025":
        return [dict(item) for item in _AUGUST_ISOLATION_PRUNE_SURFACES]
    return []


def _spill_traceability_requirement(month_label: str) -> dict[str, Any]:
    if month_label == "August 2025":
        return dict(_AUGUST_SPILL_TRACEABILITY_REQUIREMENT)
    return {
        "required": False,
        "reason": "No August spill identity capture requirement applies to this month.",
    }


def _required_post_run_evidence(month_label: str) -> list[str]:
    if month_label == "August 2025":
        return list(_AUGUST_REQUIRED_POST_RUN_EVIDENCE)
    return list(_REQUIRED_POST_RUN_EVIDENCE)
