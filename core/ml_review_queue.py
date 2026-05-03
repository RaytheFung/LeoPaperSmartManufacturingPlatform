from __future__ import annotations

import pandas as pd

from core.canonical_ml_reader import (
    MISSING_POSITIVE_GOOD_QTY_INSUFFICIENT_CONTEXT_REASON,
    MISSING_POSITIVE_GOOD_QTY_NONPRODUCTIVE_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON,
)
from core.intervention_preview import (
    build_seed_row_intervention_preview,
    candidate_support_label,
)


SUPPORT_PATH_WEIGHTS = {
    "Direct canonical row": 1.0,
    "Adapted row": 0.85,
    "Defaulted row": 0.65,
}

COVERAGE_BUCKET_ORDER = [
    "Direct canonical row",
    "Adapted row",
    "Defaulted row",
    "Blocked row",
]

COVERAGE_BUCKET_LABELS = {
    "Direct canonical row": "Direct canonical",
    "Adapted row": "Adapted",
    "Defaulted row": "Defaulted",
    "Blocked row": "Blocked",
}

REVIEW_QUEUE_COLUMNS = [
    "machine_id",
    "machine_family",
    "support_path",
    "support_weight",
    "predicted_efficiency",
    "comparable_baseline",
    "baseline_basis",
    "baseline_peer_count",
    "severity_gap",
    "estimated_excess_kwh",
    "confidence",
    "review_priority_score",
    "top_driver",
    "preview_available",
    "best_supported_scenario",
    "recommended_review_note",
]

BLOCKED_REASON_METADATA = {
    MISSING_POSITIVE_GOOD_QTY_NONPRODUCTIVE_REASON: {
        "label": "Nonproductive-state rows with no good_qty expected",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows already tagged as nonproductive states such as setup or stop time. "
            "They stay blocked and are separated from production-state quantity gaps."
        ),
    },
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON: {
        "label": "Production-state rows with zero good_qty",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows still tagged as production but carrying zero good_qty. "
            "This parent bucket remains only as a conservative fallback when no narrower subreason is supportable."
        ),
    },
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON: {
        "label": "Production-state rows with contradictory stop / idle minutes",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows still labeled as production even though the same row carries stop or idle minute evidence. "
            "They remain blocked and are reported as likely state-label contradictions."
        ),
    },
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON: {
        "label": "Production-state rows with pure-production zero good_qty",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows with production-only minute evidence plus order/material/task context, but still zero good_qty. "
            "They remain blocked and are reported as likely quantity-overlay gaps."
        ),
    },
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON: {
        "label": "Production-state rows with order / material context conflict",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows carrying quantity-alignment evidence such as material misalignment. "
            "They remain blocked and are reported as likely order/material context conflicts."
        ),
    },
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON: {
        "label": "Production-state rows with source-quality / anomaly evidence",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows carrying anomaly or no-positive-production-basis evidence. "
            "They remain blocked and are reported as source-quality / anomaly cases."
        ),
    },
    MISSING_POSITIVE_GOOD_QTY_INSUFFICIENT_CONTEXT_REASON: {
        "label": "Rows with no usable quantity context",
        "family": "Missing / non-positive good_qty",
        "description": (
            "Rows without enough state context to call them productive or nonproductive honestly. "
            "They remain blocked rather than being inferred."
        ),
    },
    "missing_positive_good_qty": {
        "label": "Missing / non-positive good_qty",
        "family": "Missing / non-positive good_qty",
        "description": "Legacy aggregate bucket kept only for backward-compatible reporting.",
    },
    "missing_machine_id": {
        "label": "Missing machine ID",
        "family": "Core canonical fields",
        "description": "The canonical machine key is missing, so the row cannot be scored safely.",
    },
    "missing_timestamp": {
        "label": "Missing timestamp",
        "family": "Core canonical fields",
        "description": "The hour timestamp is missing or unreadable.",
    },
    "missing_hours_since_last_maintenance": {
        "label": "Missing maintenance recency",
        "family": "Maintenance context",
        "description": "The row is missing hours_since_last_maintenance, so maintenance-aware features cannot be built.",
    },
    "missing_positive_energy_total_kwh": {
        "label": "Missing / non-positive energy_total_kwh",
        "family": "Training-only energy contract",
        "description": "Training keeps rows blocked when energy_total_kwh is absent or non-positive.",
    },
    "unmapped_task_name": {
        "label": "Unmapped task name",
        "family": "Task-difficulty mapping",
        "description": "The task label cannot be mapped into the supported task-difficulty families.",
    },
    "predictor_artifacts_unavailable": {
        "label": "Predictor artifacts unavailable",
        "family": "Predictor gate",
        "description": "The saved model or preprocessor could not be loaded for model-backed inference.",
    },
    "predictor_returned_non_model_source": {
        "label": "Predictor returned non-model source",
        "family": "Predictor gate",
        "description": "The predictor did not return a model-backed result, so the row remains blocked.",
    },
}


def build_inference_coverage_summary(input_df: pd.DataFrame) -> pd.DataFrame:
    if input_df.empty:
        return pd.DataFrame(columns=["support_path", "coverage_bucket", "rows", "share"])

    notes = input_df["adapter_notes"].fillna("").astype(str)
    blocked_mask = input_df["eligible_for_inference"] == 0
    defaulted_mask = (~blocked_mask) & notes.str.contains("preprocessor_default", na=False)
    adapted_mask = (~blocked_mask) & (~defaulted_mask) & notes.ne("")
    direct_mask = (~blocked_mask) & (~defaulted_mask) & (~adapted_mask)

    bucket_masks = {
        "Direct canonical row": direct_mask,
        "Adapted row": adapted_mask,
        "Defaulted row": defaulted_mask,
        "Blocked row": blocked_mask,
    }
    total_rows = len(input_df)
    rows = []
    for support_path in COVERAGE_BUCKET_ORDER:
        row_count = int(bucket_masks[support_path].sum())
        rows.append(
            {
                "support_path": support_path,
                "coverage_bucket": COVERAGE_BUCKET_LABELS[support_path],
                "rows": row_count,
                "share": (row_count / total_rows) if total_rows else 0.0,
            }
        )
    return pd.DataFrame(rows)


def collect_blocked_rows(
    input_df: pd.DataFrame,
    blocked_prediction_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    blocked_frames = []
    blocked_input_df = input_df[input_df["eligible_for_inference"] == 0].copy() if not input_df.empty else pd.DataFrame()
    if not blocked_input_df.empty:
        blocked_frames.append(blocked_input_df)
    if blocked_prediction_df is not None and not blocked_prediction_df.empty:
        blocked_frames.append(blocked_prediction_df.copy())

    if not blocked_frames:
        return pd.DataFrame()

    blocked_df = pd.concat(blocked_frames, ignore_index=True, sort=False)
    sort_columns = [column for column in ["datetime", "machine_id"] if column in blocked_df.columns]
    if sort_columns:
        blocked_df = blocked_df.sort_values(sort_columns)
    dedupe_columns = [
        column
        for column in ["machine_id", "hour_ts", "blocked_reason"]
        if column in blocked_df.columns
    ]
    if dedupe_columns:
        blocked_df = blocked_df.drop_duplicates(subset=dedupe_columns, keep="first")
    return blocked_df.reset_index(drop=True)


def build_blocked_reason_summary(blocked_df: pd.DataFrame) -> pd.DataFrame:
    if blocked_df.empty:
        return pd.DataFrame(
            columns=[
                "blocked_reason",
                "blocked_reason_label",
                "blocked_reason_family",
                "blocked_reason_description",
                "row_count",
                "share",
            ]
        )

    summary_df = (
        blocked_df.assign(blocked_reason=blocked_df["blocked_reason"].fillna("unknown"))
        .groupby("blocked_reason", dropna=False)
        .size()
        .reset_index(name="row_count")
        .sort_values(["row_count", "blocked_reason"], ascending=[False, True])
        .reset_index(drop=True)
    )
    total_rows = int(summary_df["row_count"].sum())
    summary_df["share"] = summary_df["row_count"] / total_rows if total_rows else 0.0
    metadata_df = summary_df["blocked_reason"].apply(describe_blocked_reason).apply(pd.Series)
    summary_df["blocked_reason_label"] = metadata_df["label"]
    summary_df["blocked_reason_family"] = metadata_df["family"]
    summary_df["blocked_reason_description"] = metadata_df["description"]
    return summary_df


def describe_blocked_reason(blocked_reason: object) -> dict[str, str]:
    normalized_reason = str(blocked_reason or "unknown")
    metadata = BLOCKED_REASON_METADATA.get(normalized_reason)
    if metadata is not None:
        return metadata
    return {
        "label": normalized_reason,
        "family": "Other blocked rows",
        "description": "No curated description is available for this blocked reason yet.",
    }


def build_model_review_queue(
    candidate_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    *,
    predictor=None,
    min_family_peer_count: int = 3,
    min_difficulty_peer_count: int = 5,
) -> pd.DataFrame:
    if candidate_df.empty or prediction_df.empty:
        return pd.DataFrame(columns=REVIEW_QUEUE_COLUMNS)

    seed_df = candidate_df.drop_duplicates(subset=["machine_id", "datetime"]).copy()
    merged_df = seed_df.merge(
        prediction_df.loc[
            :,
            [
                "machine_id",
                "datetime",
                "predicted_efficiency",
                "confidence",
                "top_driver",
            ],
        ],
        on=["machine_id", "datetime"],
        how="inner",
    )
    if merged_df.empty:
        return pd.DataFrame(columns=REVIEW_QUEUE_COLUMNS)

    merged_df["machine_family"] = merged_df["machine_id"].fillna("").astype(str).str.split("-").str[0]
    merged_df["support_path"] = merged_df.apply(candidate_support_label, axis=1)
    merged_df["support_weight"] = (
        merged_df["support_path"].map(SUPPORT_PATH_WEIGHTS).fillna(SUPPORT_PATH_WEIGHTS["Defaulted row"])
    )

    review_rows = []
    for row_index, row in merged_df.iterrows():
        baseline_value, baseline_basis, baseline_peer_count = _resolve_comparable_baseline(
            merged_df,
            row_index,
            min_family_peer_count=min_family_peer_count,
            min_difficulty_peer_count=min_difficulty_peer_count,
        )
        predicted_efficiency = _float_or_zero(row.get("predicted_efficiency"))
        production_qty = _float_or_zero(row.get("production_qty"))
        confidence = max(0.0, min(_float_or_zero(row.get("confidence")), 1.0))
        support_weight = _float_or_zero(row.get("support_weight"))
        severity_gap = max(predicted_efficiency - baseline_value, 0.0)
        estimated_excess_kwh = severity_gap * production_qty
        review_priority_score = estimated_excess_kwh * confidence * support_weight
        preview_summary = _build_preview_summary(row, predictor)

        review_rows.append(
            {
                "machine_id": row.get("machine_id"),
                "machine_family": row.get("machine_family"),
                "support_path": row.get("support_path"),
                "support_weight": support_weight,
                "predicted_efficiency": predicted_efficiency,
                "comparable_baseline": baseline_value,
                "baseline_basis": baseline_basis,
                "baseline_peer_count": baseline_peer_count,
                "severity_gap": severity_gap,
                "estimated_excess_kwh": estimated_excess_kwh,
                "confidence": confidence,
                "review_priority_score": review_priority_score,
                "top_driver": row.get("top_driver"),
                "preview_available": preview_summary["preview_available"],
                "best_supported_scenario": preview_summary["best_supported_scenario"],
                "recommended_review_note": _recommended_review_note(
                    top_driver=row.get("top_driver"),
                    support_path=row.get("support_path"),
                    severity_gap=severity_gap,
                    preview_available=preview_summary["preview_available"],
                    best_supported_scenario=preview_summary["best_supported_scenario"],
                ),
            }
        )

    queue_df = pd.DataFrame(review_rows)
    if queue_df.empty:
        return pd.DataFrame(columns=REVIEW_QUEUE_COLUMNS)

    queue_df = queue_df.sort_values(
        [
            "review_priority_score",
            "estimated_excess_kwh",
            "confidence",
            "predicted_efficiency",
            "machine_id",
        ],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    return queue_df.loc[:, REVIEW_QUEUE_COLUMNS].copy()


def _resolve_comparable_baseline(
    merged_df: pd.DataFrame,
    row_index: int,
    *,
    min_family_peer_count: int,
    min_difficulty_peer_count: int,
) -> tuple[float, str, int]:
    row = merged_df.loc[row_index]
    peer_df = merged_df.drop(index=row_index)

    family_peer_df = peer_df[
        (peer_df["machine_family"] == row.get("machine_family"))
        & (peer_df["task_difficulty"] == row.get("task_difficulty"))
    ]
    if len(family_peer_df) >= min_family_peer_count:
        return (
            float(family_peer_df["predicted_efficiency"].median()),
            "Family + task-difficulty peer median",
            int(len(family_peer_df)),
        )

    difficulty_peer_df = peer_df[peer_df["task_difficulty"] == row.get("task_difficulty")]
    if len(difficulty_peer_df) >= min_difficulty_peer_count:
        return (
            float(difficulty_peer_df["predicted_efficiency"].median()),
            "Task-difficulty peer median",
            int(len(difficulty_peer_df)),
        )

    return (
        float(merged_df["predicted_efficiency"].median()),
        "Selected-month median fallback",
        int(len(merged_df)),
    )


def _build_preview_summary(row: pd.Series, predictor) -> dict[str, object]:
    if predictor is None:
        return {"preview_available": False, "best_supported_scenario": None}

    baseline_row = pd.Series(
        {
            "predicted_efficiency": row.get("predicted_efficiency"),
            "confidence": row.get("confidence"),
            "top_driver": row.get("top_driver"),
        }
    )
    preview = build_seed_row_intervention_preview(row, predictor, baseline_row=baseline_row)
    if preview.get("blocked"):
        return {"preview_available": False, "best_supported_scenario": None}

    supported_rows = [
        scenario for scenario in (preview.get("scenarios") or []) if scenario.get("status") == "supported"
    ]
    if not supported_rows:
        return {"preview_available": False, "best_supported_scenario": None}

    best_scenario = preview.get("best_supported_scenario") or {}
    return {
        "preview_available": True,
        "best_supported_scenario": best_scenario.get("scenario_name"),
    }


def _recommended_review_note(
    *,
    top_driver: object,
    support_path: object,
    severity_gap: float,
    preview_available: bool,
    best_supported_scenario: object,
) -> str:
    if severity_gap <= 0:
        return "Monitor only; this machine is within the current comparable baseline."

    driver_text = str(top_driver or "").lower()
    note_parts = []
    if "maintenance" in driver_text:
        note_parts.append("Validate maintenance recency against comparable peers.")
    elif "task" in driver_text:
        note_parts.append("Check task mix against same-difficulty peers.")
    elif "production" in driver_text:
        note_parts.append("Validate production scale against comparable peer rows.")
    else:
        note_parts.append("Inspect the current machine-hour evidence before escalation.")

    if str(support_path or "") != "Direct canonical row":
        note_parts.append("Confirm adapted/defaulted inputs before operational follow-up.")

    if preview_available:
        if best_supported_scenario:
            note_parts.append(f"Scenario Lab is available ({best_supported_scenario}).")
        else:
            note_parts.append("Scenario Lab is available.")
    else:
        note_parts.append("Scenario Lab has no supported template on the current seed row.")

    return " ".join(note_parts)


def _float_or_zero(value: object) -> float:
    try:
        if value is None or pd.isna(value):
            return 0.0
    except TypeError:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "COVERAGE_BUCKET_LABELS",
    "COVERAGE_BUCKET_ORDER",
    "REVIEW_QUEUE_COLUMNS",
    "SUPPORT_PATH_WEIGHTS",
    "build_blocked_reason_summary",
    "build_inference_coverage_summary",
    "build_model_review_queue",
    "collect_blocked_rows",
    "describe_blocked_reason",
]
