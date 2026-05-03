from __future__ import annotations

import pandas as pd


REQUIRED_INTERVENTION_FIELDS = [
    "machine_id",
    "team_leader",
    "material_code",
    "hours_since_last_maintenance",
    "task_difficulty",
    "production_qty",
    "team_size",
    "hour_of_day",
    "is_weekend",
    "month",
    "last_maintenance_type",
    "maintenance_intensity_30d",
    "cumulative_maintenance_count",
]

SCENARIO_TEMPLATE_ORDER = [
    "Maintenance Refresh",
    "Crew Support +1",
    "Combined Support",
]


def candidate_support_label(row: pd.Series) -> str:
    adapter_notes = str(row.get("adapter_notes") or "")
    if "preprocessor_default" in adapter_notes:
        return "Defaulted row"
    if adapter_notes.strip():
        return "Adapted row"
    return "Direct canonical row"


def run_intervention_prediction(
    seed_row: pd.Series,
    overrides: dict[str, object],
    predictor,
) -> dict[str, object]:
    scenario = seed_row.copy()
    for field_name, value in overrides.items():
        scenario[field_name] = value

    missing_fields = []
    for field_name in REQUIRED_INTERVENTION_FIELDS:
        value = scenario.get(field_name)
        if value is None or pd.isna(value):
            missing_fields.append(field_name)
    if missing_fields:
        return {
            "blocked": True,
            "reason": "Scenario blocked because the seed row is missing required supported inputs: "
            + ", ".join(missing_fields),
        }

    prediction = predictor.predict_efficiency(
        machine_id=str(scenario["machine_id"]),
        team_leader=str(scenario["team_leader"]),
        material_code=str(scenario["material_code"]),
        hours_since_maintenance=float(scenario["hours_since_last_maintenance"]),
        task_difficulty=str(scenario["task_difficulty"]),
        production_qty=float(scenario["production_qty"]),
        team_size=float(scenario["team_size"]),
        hour_of_day=int(scenario["hour_of_day"]),
        is_weekend=bool(scenario["is_weekend"]),
        month=int(scenario["month"]),
        last_maintenance_type=str(scenario["last_maintenance_type"]),
        maintenance_intensity_30d=float(scenario["maintenance_intensity_30d"]),
        cumulative_maintenance_count=float(scenario["cumulative_maintenance_count"]),
    )
    if prediction.get("source") != "model":
        return {
            "blocked": True,
            "reason": "Scenario blocked because the active predictor did not return a saved-model result.",
        }
    return {"blocked": False, "prediction": prediction, "scenario": scenario}


def build_machine_intervention_preview(
    candidate_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    predictor,
    machine_id: object,
) -> dict[str, object]:
    if candidate_df.empty:
        return {
            "blocked": True,
            "reason": "No eligible canonical seed rows are available for intervention preview.",
        }

    machine_text = _clean_text(machine_id)
    if machine_text is None:
        return {
            "blocked": True,
            "reason": "No machine is selected for intervention preview.",
        }

    seed_matches = candidate_df[
        candidate_df["machine_id"].fillna("").astype(str) == machine_text
    ].copy()
    if seed_matches.empty:
        return {
            "blocked": True,
            "reason": (
                f"No saved-model intervention preview is available for {machine_text} because "
                "the current month has no eligible canonical machine-hour seed row for that machine."
            ),
        }

    seed_row = seed_matches.sort_values(["datetime", "machine_id"], ascending=[False, True]).iloc[0]
    baseline_matches = pd.DataFrame()
    if not prediction_df.empty:
        baseline_matches = prediction_df[
            prediction_df["machine_id"].fillna("").astype(str) == machine_text
        ].copy()
    baseline_row = (
        baseline_matches.sort_values(["datetime", "machine_id"], ascending=[False, True]).iloc[0]
        if not baseline_matches.empty
        else None
    )
    return build_seed_row_intervention_preview(
        seed_row,
        predictor,
        baseline_row=baseline_row,
    )


def build_seed_row_intervention_preview(
    seed_row: pd.Series,
    predictor,
    baseline_row: pd.Series | None = None,
) -> dict[str, object]:
    support_path = candidate_support_label(seed_row)
    baseline = _resolve_baseline(seed_row, predictor, baseline_row=baseline_row)
    preview = {
        "blocked": False,
        "reason": None,
        "seed_machine_id": _clean_text(seed_row.get("machine_id")) or "n/a",
        "seed_timestamp": seed_row.get("datetime"),
        "seed_timestamp_label": _format_timestamp_label(seed_row.get("datetime")),
        "seed_task_difficulty": _clean_text(seed_row.get("task_difficulty")) or "unknown",
        "seed_team_leader": _clean_text(seed_row.get("team_leader")) or "unknown",
        "seed_material_code": _clean_text(seed_row.get("material_code")) or "unknown",
        "seed_production_qty": _float_or_zero(seed_row.get("production_qty")),
        "seed_team_size": _float_or_none(seed_row.get("team_size")),
        "seed_hours_since_last_maintenance": _float_or_none(
            seed_row.get("hours_since_last_maintenance")
        ),
        "support_path": support_path,
        "adapter_notes": str(seed_row.get("adapter_notes") or "").strip(),
        "baseline": None,
        "scenarios": [],
        "best_supported_scenario": None,
    }
    if baseline["blocked"]:
        preview["blocked"] = True
        preview["reason"] = baseline["reason"]
        return preview

    preview["baseline"] = baseline
    baseline_efficiency = float(baseline["predicted_efficiency"])
    scenario_specs = _build_scenario_template_specs(seed_row)

    scenario_rows = []
    for spec in scenario_specs:
        if spec["blocked"]:
            scenario_rows.append(
                {
                    "scenario_name": spec["name"],
                    "status": "unsupported",
                    "predicted_efficiency": None,
                    "delta_vs_baseline": None,
                    "confidence": None,
                    "estimated_kwh_change": None,
                    "top_driver": None,
                    "interpretation": None,
                    "override_summary": spec["override_summary"],
                    "reason": spec["reason"],
                }
            )
            continue

        scenario_result = run_intervention_prediction(seed_row, spec["overrides"], predictor)
        if scenario_result["blocked"]:
            scenario_rows.append(
                {
                    "scenario_name": spec["name"],
                    "status": "unsupported",
                    "predicted_efficiency": None,
                    "delta_vs_baseline": None,
                    "confidence": None,
                    "estimated_kwh_change": None,
                    "top_driver": None,
                    "interpretation": None,
                    "override_summary": spec["override_summary"],
                    "reason": scenario_result["reason"],
                }
            )
            continue

        prediction = scenario_result["prediction"]
        delta_vs_baseline = float(prediction["efficiency"]) - baseline_efficiency
        scenario_rows.append(
            {
                "scenario_name": spec["name"],
                "status": "supported",
                "predicted_efficiency": float(prediction["efficiency"]),
                "delta_vs_baseline": delta_vs_baseline,
                "confidence": float(prediction["confidence"]),
                "estimated_kwh_change": delta_vs_baseline * preview["seed_production_qty"],
                "top_driver": _top_driver_from_prediction(prediction),
                "interpretation": _scenario_interpretation(
                    spec["name"],
                    delta_vs_baseline,
                    baseline_efficiency,
                ),
                "override_summary": spec["override_summary"],
                "reason": None,
            }
        )

    preview["scenarios"] = scenario_rows
    preview["best_supported_scenario"] = _best_supported_scenario(scenario_rows)
    return preview


def build_intervention_preview_table(preview: dict[str, object]) -> pd.DataFrame:
    rows = []
    for scenario in preview.get("scenarios") or []:
        rows.append(
            {
                "Scenario": scenario["scenario_name"],
                "Status": "Supported" if scenario["status"] == "supported" else "Unsupported",
                "Supported Change": scenario["override_summary"],
                "Predicted kWh/Unit": (
                    pd.NA
                    if scenario["predicted_efficiency"] is None
                    else float(scenario["predicted_efficiency"])
                ),
                "Delta vs Baseline": (
                    pd.NA
                    if scenario["delta_vs_baseline"] is None
                    else float(scenario["delta_vs_baseline"])
                ),
                "Confidence": (
                    pd.NA
                    if scenario["confidence"] is None
                    else float(scenario["confidence"])
                ),
                "Est. kWh Change @ Seed Volume": (
                    pd.NA
                    if scenario["estimated_kwh_change"] is None
                    else float(scenario["estimated_kwh_change"])
                ),
                "Interpretation": scenario["interpretation"],
                "Blocked Reason": scenario["reason"],
            }
        )
    return pd.DataFrame(rows)


def _resolve_baseline(
    seed_row: pd.Series,
    predictor,
    baseline_row: pd.Series | None = None,
) -> dict[str, object]:
    if baseline_row is not None:
        predicted_efficiency = _float_or_none(baseline_row.get("predicted_efficiency"))
        confidence = _float_or_none(baseline_row.get("confidence"))
        if predicted_efficiency is not None and confidence is not None:
            return {
                "blocked": False,
                "predicted_efficiency": predicted_efficiency,
                "confidence": confidence,
                "top_driver": _clean_text(baseline_row.get("top_driver")) or "No dominant driver returned",
            }

    baseline_result = run_intervention_prediction(seed_row, {}, predictor)
    if baseline_result["blocked"]:
        return {
            "blocked": True,
            "reason": "Baseline preview is unavailable because the active predictor could not return a saved-model result for the real seed row.",
        }

    prediction = baseline_result["prediction"]
    return {
        "blocked": False,
        "predicted_efficiency": float(prediction["efficiency"]),
        "confidence": float(prediction["confidence"]),
        "top_driver": _top_driver_from_prediction(prediction),
    }


def _build_scenario_template_specs(seed_row: pd.Series) -> list[dict[str, object]]:
    maintenance_spec = _build_maintenance_refresh_spec(seed_row)
    crew_spec = _build_crew_support_spec(seed_row)
    combined_spec = _build_combined_support_spec(maintenance_spec, crew_spec)
    return [maintenance_spec, crew_spec, combined_spec]


def _build_maintenance_refresh_spec(seed_row: pd.Series) -> dict[str, object]:
    hours_since_last_maintenance = _float_or_none(seed_row.get("hours_since_last_maintenance"))
    if hours_since_last_maintenance is None:
        return {
            "name": "Maintenance Refresh",
            "blocked": True,
            "reason": "Maintenance refresh is unsupported because the seed row has no maintenance-recency value.",
            "override_summary": "hours_since_last_maintenance unavailable",
        }

    reduction = max(12.0, hours_since_last_maintenance * 0.25)
    target_hours = max(0.0, hours_since_last_maintenance - reduction)
    if target_hours >= hours_since_last_maintenance:
        return {
            "name": "Maintenance Refresh",
            "blocked": True,
            "reason": "Maintenance refresh is unsupported because the seed row is already at the lowest supported maintenance-recency bound.",
            "override_summary": (
                f"hours_since_last_maintenance {hours_since_last_maintenance:.1f} -> "
                f"{target_hours:.1f}"
            ),
        }

    return {
        "name": "Maintenance Refresh",
        "blocked": False,
        "overrides": {"hours_since_last_maintenance": float(target_hours)},
        "override_summary": (
            f"hours_since_last_maintenance {hours_since_last_maintenance:.1f} -> "
            f"{target_hours:.1f}"
        ),
    }


def _build_crew_support_spec(seed_row: pd.Series) -> dict[str, object]:
    team_size = _float_or_none(seed_row.get("team_size"))
    if team_size is None or team_size <= 0:
        return {
            "name": "Crew Support +1",
            "blocked": True,
            "reason": "Crew support is unsupported because the seed row has no positive team-size value.",
            "override_summary": "team_size unavailable",
        }

    current_team_size = max(1, int(round(team_size)))
    next_team_size = current_team_size + 1
    return {
        "name": "Crew Support +1",
        "blocked": False,
        "overrides": {"team_size": float(next_team_size)},
        "override_summary": f"team_size {current_team_size:d} -> {next_team_size:d}",
    }


def _build_combined_support_spec(
    maintenance_spec: dict[str, object],
    crew_spec: dict[str, object],
) -> dict[str, object]:
    blocked_reasons = [
        spec["reason"]
        for spec in (maintenance_spec, crew_spec)
        if spec.get("blocked")
    ]
    if blocked_reasons:
        return {
            "name": "Combined Support",
            "blocked": True,
            "reason": "Combined support is unsupported because "
            + "; ".join(blocked_reasons),
            "override_summary": (
                f"{maintenance_spec.get('override_summary', '')}; "
                f"{crew_spec.get('override_summary', '')}"
            ).strip("; "),
        }

    overrides = {}
    overrides.update(maintenance_spec.get("overrides", {}))
    overrides.update(crew_spec.get("overrides", {}))
    return {
        "name": "Combined Support",
        "blocked": False,
        "overrides": overrides,
        "override_summary": (
            f"{maintenance_spec.get('override_summary', '')}; "
            f"{crew_spec.get('override_summary', '')}"
        ).strip("; "),
    }


def _best_supported_scenario(
    scenario_rows: list[dict[str, object]],
) -> dict[str, object] | None:
    supported_rows = [
        row for row in scenario_rows if row.get("status") == "supported"
    ]
    if not supported_rows:
        return None
    return min(
        supported_rows,
        key=lambda row: (
            float(row.get("delta_vs_baseline") or 0.0),
            float(row.get("predicted_efficiency") or 0.0),
        ),
    )


def _scenario_interpretation(
    scenario_name: str,
    delta_vs_baseline: float,
    baseline_efficiency: float,
) -> str:
    neutral_threshold = max(0.001, abs(baseline_efficiency) * 0.05)
    if abs(delta_vs_baseline) <= neutral_threshold:
        if scenario_name == "Crew Support +1":
            return "Crew support shows limited incremental benefit."
        if scenario_name == "Maintenance Refresh":
            return "Maintenance refresh shows limited incremental benefit."
        return "Combined support shows limited incremental benefit."

    if delta_vs_baseline < 0:
        if scenario_name == "Maintenance Refresh":
            return "Maintenance refresh lowers predicted energy intensity."
        if scenario_name == "Crew Support +1":
            return "Crew support lowers predicted energy intensity."
        return "Combined support lowers predicted energy intensity most in this comparable row."

    if scenario_name == "Maintenance Refresh":
        return "Maintenance refresh raises predicted energy intensity in this comparable row."
    if scenario_name == "Crew Support +1":
        return "Crew support raises predicted energy intensity in this comparable row."
    return "Combined support raises predicted energy intensity in this comparable row."


def _top_driver_from_prediction(prediction: dict[str, object]) -> str:
    impacts = prediction.get("feature_impacts") or {}
    if not isinstance(impacts, dict) or not impacts:
        return "No dominant driver returned"
    label, narrative = next(iter(impacts.items()))
    return f"{label}: {narrative}"


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or_zero(value: object) -> float:
    converted = _float_or_none(value)
    return 0.0 if converted is None else float(converted)


def _format_timestamp_label(value: object) -> str:
    if value is None:
        return "n/a"
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return str(value)
    return timestamp.strftime("%Y-%m-%d %H:%M")
