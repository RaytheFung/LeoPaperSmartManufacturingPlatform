"""
Canonical Optimization page backed by fact_machine_hour.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.canonical_ml_reader import CanonicalMLReader
from core.canonical_optimization_reader import CanonicalOptimizationReader
from core.intervention_preview import (
    build_intervention_preview_table,
    build_machine_intervention_preview,
)
from core.maintenance_evidence import MaintenanceEvidenceReader
from core.ml_predictor import MLPredictor
from core.ui_utils import (
    build_stat_card,
    build_surface_card,
    load_custom_css,
    render_surface_card,
    section_shell,
)


def render_optimization_module(db_path=None):
    """Render the canonical Optimization page."""
    try:
        try:
            load_custom_css()
        except Exception:
            pass

        reader = CanonicalOptimizationReader(db_path=db_path)
        maintenance_reader = MaintenanceEvidenceReader(db_path=db_path)

        st.title("🎯 Operational Decision Support")
        st.markdown(
            "Phase 1 rule-based decision support from canonical Gold only. "
            "This page surfaces machine opportunities, historical hour signals, and team context "
            "without claiming a constraint-aware optimization engine."
        )
        st.caption("Canonical Gold source: fact_machine_hour")

        available_months = reader.get_available_months()
        if not available_months:
            st.warning(
                "Canonical Gold is not available yet for Optimization. "
                "Run ETL for a month that materializes `fact_machine_hour`, then reload this page."
            )
            return

        selected_month = st.selectbox("Select month", available_months, index=0)
        summary_df = reader.build_machine_summary(selected_month)
        if summary_df.empty:
            st.warning(
                f"No canonical Gold machine summary is available for {selected_month}. "
                "This page does not fall back to legacy or synthetic data."
            )
            return

        metrics = reader.build_month_metrics(summary_df)
        _render_metrics(metrics)
        preview_payload = _build_model_preview_payload(selected_month, db_path=db_path)
        _render_canonical_summary(summary_df, selected_month, preview_payload, maintenance_reader)
        with st.expander("Context & Diagnostics: Historical Hour Signals", expanded=False):
            _render_schedule_tab(
                build_schedule_tab_payload(reader, selected_month),
                selected_month,
            )
        with st.expander("Supporting Evidence: Team Signals", expanded=False):
            _render_team_insights_tab(
                build_team_insights_tab_payload(reader, selected_month),
                selected_month,
            )

        _render_notes()
    except Exception as exc:
        st.error(f"Optimization page failed: {exc}")
        st.info("The canonical Optimization route did not fall back to legacy or synthetic data.")


def _render_metrics(metrics: dict[str, float | int | None]) -> None:
    cards = [
        build_stat_card(
            "Machines",
            metrics["machine_count_in_canonical_optimization_view"],
            compact=False,
            primary_decimals=0,
            full_decimals=0,
        ),
        build_stat_card(
            "Total Energy",
            metrics["total_energy_kwh"],
            unit="kWh",
            full_decimals=1,
        ),
        build_stat_card(
            "Total Good Qty",
            metrics["total_good_qty"],
            full_decimals=1,
        ),
        build_surface_card(
            "Avg Utilization Proxy",
            _format_percent(metrics["avg_utilization_proxy"]),
            "Observed production share across tracked canonical minutes in the selected month.",
        ),
    ]
    _render_card_grid(cards, columns=4)


def _render_canonical_summary(
    summary_df: pd.DataFrame,
    selected_month: str,
    preview_payload: dict[str, object],
    maintenance_reader: MaintenanceEvidenceReader,
) -> None:
    filtered_df = pd.DataFrame()
    with section_shell(
        "Opportunity Worklist",
        "Ranking is derived from machine-level `fact_machine_hour` aggregates for the selected month. "
        "Opportunity score = 40% energy intensity + 30% non-productive share + 15% maintenance recency + "
        "15% scrap rate. The worklist is the primary review surface; the chart below is secondary support only.",
        eyebrow="Primary Section",
    ):
        filtered_df, filter_summary = _render_opportunity_filters(summary_df, selected_month)
        st.caption(filter_summary)
        if filtered_df.empty:
            st.warning("No machines match the current support filters. Relax the thresholds to continue.")
            return

        worklist_df = _build_opportunity_worklist(filtered_df)
        st.dataframe(worklist_df, hide_index=True, use_container_width=True)

        top_df = filtered_df.head(10).copy()
        if not top_df.empty:
            st.caption(
                "Supporting visual: the same worklist ranked by opportunity score so the table and chart do not compete as separate primary summaries."
            )
            chart_df = top_df.sort_values("opportunity_score", ascending=True)
            fig = px.bar(
                chart_df,
                x="opportunity_score",
                y="machine_id",
                color="opportunity_flag",
                orientation="h",
                hover_data={
                    "avg_kwh_per_good_unit": ":.3f",
                    "scrap_rate": ":.3f",
                    "utilization_proxy": ":.3f",
                    "top_driver": True,
                },
                labels={"avg_kwh_per_good_unit": "Weighted kWh / Good Unit"},
                color_discrete_map={"High": "#d62728", "Medium": "#ff7f0e", "Low": "#2ca02c"},
                title="Opportunity score by worklist machine",
            )
            fig.update_layout(xaxis_title="Opportunity Score", yaxis_title="Machine", height=360)
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("Reference & Audit: Full scored machine table", expanded=False):
            display_df = _build_full_scored_machine_table(filtered_df)
            st.dataframe(display_df, hide_index=True, use_container_width=True)

    if filtered_df.empty:
        return
    _render_machine_drilldown(filtered_df, selected_month, preview_payload, maintenance_reader)


def _render_machine_drilldown(
    summary_df: pd.DataFrame,
    selected_month: str,
    preview_payload: dict[str, object],
    maintenance_reader: MaintenanceEvidenceReader,
) -> None:
    with section_shell(
        "Selected Machine Review",
        "The selected machine keeps the score decomposition tied to support fields, surfaces the model-backed scenario preview earlier, "
        "and separates supportive context from the primary review story. This remains prioritization support, not a scheduling solver.",
        eyebrow="Primary Section",
    ):
        preview_machine_ids = set()
        if preview_payload.get("available"):
            preview_machine_ids = set(
                preview_payload["prediction_df"]["machine_id"].dropna().astype(str).tolist()
            )
        default_index = 0
        for index, machine_id in enumerate(summary_df["machine_id"].tolist()):
            if str(machine_id) in preview_machine_ids:
                default_index = index
                break
        selected_machine = st.selectbox(
            "Inspect machine",
            options=summary_df["machine_id"].tolist(),
            index=default_index,
            key=f"optimization_machine_drilldown_{selected_month}",
        )
        selected_row = summary_df[summary_df["machine_id"] == selected_machine].iloc[0]
        drilldown = _build_machine_drilldown_snapshot(selected_row)

        _render_card_grid(_build_machine_summary_cards(drilldown), columns=4)

        note_col1, note_col2 = st.columns(2)
        with note_col1:
            with st.container(border=True):
                st.caption("Top Driver")
                st.write(str(drilldown["top_driver"]))
        with note_col2:
            with st.container(border=True):
                st.caption("Recommended Action")
                st.write(str(drilldown["recommended_action"]))

        _render_maintenance_context_block(
            selected_machine,
            maintenance_reader,
            description=(
                "Direct maintenance-table context reused from `🔧 Maintenance`. "
                "It adds compact evidence to the selected-machine review without re-scoring the worklist."
            ),
        )

        _render_model_backed_preview(selected_machine, preview_payload)

        st.markdown("##### Score Decomposition")
        st.caption("These normalized components explain why the current machine is ranking where it is.")
        decomposition_df = pd.DataFrame(
            [
                {"component": "Energy intensity", "score": selected_row["energy_intensity_component"]},
                {"component": "Non-productive share", "score": selected_row["nonproductive_component"]},
                {"component": "Maintenance recency", "score": selected_row["maintenance_recency_component"]},
                {"component": "Scrap rate", "score": selected_row["scrap_component"]},
            ]
        )
        decomposition_fig = px.bar(
            decomposition_df,
            x="score",
            y="component",
            orientation="h",
            title=f"Score decomposition for {selected_machine}",
            labels={"score": "Normalized component score", "component": "Component"},
        )
        st.plotly_chart(decomposition_fig, use_container_width=True)

        st.markdown("##### Supportive Context")
        st.caption("Observed productive vs non-productive hours are supportive context only and do not imply solver intelligence.")
        _render_card_grid(_build_machine_support_cards(drilldown), columns=2)
        hour_mix_df = pd.DataFrame(
            [
                {"hour_type": "Productive", "hours": drilldown["productive_hours"]},
                {"hour_type": "Non-Productive", "hours": drilldown["nonproductive_hours"]},
            ]
        )
        hour_mix_fig = px.bar(
            hour_mix_df,
            x="hours",
            y="hour_type",
            orientation="h",
            title=f"Observed productive vs non-productive hours for {selected_machine}",
            labels={"hours": "Hours", "hour_type": "Hour Type"},
            color="hour_type",
            color_discrete_map={"Productive": "#2ca02c", "Non-Productive": "#d62728"},
        )
        st.plotly_chart(hour_mix_fig, use_container_width=True)


def build_schedule_tab_payload(reader: CanonicalOptimizationReader, month_year: str) -> dict[str, object]:
    schedule_df = reader.build_schedule_summary(month_year)
    if schedule_df.empty:
        return {
            "blocked": True,
            "message": (
                f"No canonical scheduling summary is available for {month_year}. "
                "This tab blocks honestly instead of using legacy or synthetic scheduling output."
            ),
            "schedule_df": schedule_df,
        }
    return {
        "blocked": False,
        "message": None,
        "schedule_df": schedule_df,
    }


def build_team_insights_tab_payload(reader: CanonicalOptimizationReader, month_year: str) -> dict[str, object]:
    team_df = reader.build_team_insights(month_year)
    if team_df.empty:
        return {
            "blocked": True,
            "message": (
                f"No canonical team insights are available for {month_year}. "
                "This tab blocks honestly instead of using legacy or synthetic team analysis."
            ),
            "team_df": team_df,
        }
    return {
        "blocked": False,
        "message": None,
        "team_df": team_df,
    }


def _render_schedule_tab(payload: dict[str, object], selected_month: str) -> None:
    if payload["blocked"]:
        st.warning(str(payload["message"]))
        return

    schedule_df = payload["schedule_df"].copy()
    st.subheader(f"Historical Hour Signals for {selected_month}")
    st.caption(
        "These are descriptive hour-of-day signals derived from canonical machine-hour rows only. "
        "This tab does not claim constraint-aware scheduling; it highlights historically favorable "
        "or watch hours and exposes the support behind them."
    )

    recommended_df = schedule_df.head(3).copy()
    st.dataframe(
        recommended_df.loc[
            :,
            [
                "hour_of_day",
                "shift_label",
                "schedule_flag",
                "schedule_score",
                "top_driver",
                "avg_kwh_per_good_unit",
                "utilization_proxy",
                "total_good_qty",
            ],
        ].rename(
            columns={
                "hour_of_day": "Hour",
                "shift_label": "Shift",
                "schedule_flag": "Signal",
                "schedule_score": "Score",
                "top_driver": "Top Driver",
                "avg_kwh_per_good_unit": "Weighted kWh/Good Unit",
                "utilization_proxy": "Utilization Proxy",
                "total_good_qty": "Good Qty",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    chart_df = schedule_df.sort_values("schedule_score", ascending=True).copy()
    chart_df["hour_label"] = chart_df["hour_of_day"].apply(lambda value: f"{int(value):02d}:00")
    fig = px.bar(
        chart_df,
        x="schedule_score",
        y="hour_label",
        color="schedule_flag",
        orientation="h",
        title="Canonical Scheduling Score by Hour",
        hover_data={
            "shift_label": True,
            "avg_kwh_per_good_unit": ":.4f",
            "utilization_proxy": ":.3f",
            "total_good_qty": ":.1f",
            "eligible_rows": True,
        },
        labels={"avg_kwh_per_good_unit": "Weighted kWh / Good Unit"},
        color_discrete_map={"Preferred": "#2ca02c", "Watch": "#ff7f0e", "Avoid": "#d62728"},
    )
    fig.update_layout(xaxis_title="Scheduling Score", yaxis_title="Hour")
    st.plotly_chart(fig, use_container_width=True)

    display_df = schedule_df.copy()
    display_df["schedule_score"] = display_df["schedule_score"].round(4)
    display_df["avg_kwh_per_good_unit"] = display_df["avg_kwh_per_good_unit"].round(4)
    display_df["productive_hours"] = display_df["productive_hours"].round(2)
    display_df["nonproductive_hours"] = display_df["nonproductive_hours"].round(2)
    display_df["utilization_proxy"] = display_df["utilization_proxy"].round(4)
    display_df["total_energy_kwh"] = display_df["total_energy_kwh"].round(2)
    display_df["total_good_qty"] = display_df["total_good_qty"].round(2)
    st.dataframe(
        display_df.rename(
            columns={
                "hour_of_day": "Hour",
                "shift_label": "Shift",
                "eligible_rows": "Eligible Rows",
                "distinct_machines": "Distinct Machines",
                "total_energy_kwh": "Total Energy (kWh)",
                "total_good_qty": "Good Qty",
                "avg_kwh_per_good_unit": "Weighted kWh/Good Unit",
                "productive_hours": "Productive Hours",
                "nonproductive_hours": "Non-Productive Hours",
                "utilization_proxy": "Utilization Proxy",
                "schedule_score": "Scheduling Score",
                "schedule_flag": "Signal",
                "top_driver": "Top Driver",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def _render_team_insights_tab(payload: dict[str, object], selected_month: str) -> None:
    if payload["blocked"]:
        st.warning(str(payload["message"]))
        return

    team_df = payload["team_df"].copy()
    st.subheader(f"Canonical Team Signals for {selected_month}")
    st.caption(
        "Team-level signals are aggregated from canonical month-scoped machine-hour rows with "
        "named team leaders. Treat this section as appendix context because task/material mix is "
        "not fully normalized yet."
    )

    chart_df = team_df.head(10).sort_values("team_effectiveness_score", ascending=True).copy()
    fig = px.bar(
        chart_df,
        x="team_effectiveness_score",
        y="team_leader",
        color="team_band",
        orientation="h",
        title="Top Canonical Team Effectiveness Signals",
        hover_data={
            "avg_kwh_per_good_unit": ":.4f",
            "scrap_rate": ":.4f",
            "utilization_proxy": ":.3f",
            "total_good_qty": ":.1f",
            "distinct_machines": True,
        },
        labels={"avg_kwh_per_good_unit": "Weighted kWh / Good Unit"},
        color_discrete_map={"Strong": "#2ca02c", "Stable": "#ff7f0e", "Watch": "#d62728"},
    )
    fig.update_layout(xaxis_title="Team Effectiveness Score", yaxis_title="Team Leader")
    st.plotly_chart(fig, use_container_width=True)

    display_df = team_df.copy()
    display_df["team_effectiveness_score"] = display_df["team_effectiveness_score"].round(4)
    display_df["total_energy_kwh"] = display_df["total_energy_kwh"].round(2)
    display_df["total_good_qty"] = display_df["total_good_qty"].round(2)
    display_df["total_scrap_qty"] = display_df["total_scrap_qty"].round(2)
    display_df["avg_kwh_per_good_unit"] = display_df["avg_kwh_per_good_unit"].round(4)
    display_df["scrap_rate"] = display_df["scrap_rate"].round(4)
    display_df["productive_hours"] = display_df["productive_hours"].round(2)
    display_df["nonproductive_hours"] = display_df["nonproductive_hours"].round(2)
    display_df["utilization_proxy"] = display_df["utilization_proxy"].round(4)
    display_df["avg_hours_since_last_maintenance"] = display_df[
        "avg_hours_since_last_maintenance"
    ].round(2)
    st.dataframe(
        display_df.rename(
            columns={
                "team_leader": "Team Leader",
                "rows_with_team": "Rows With Team",
                "distinct_machines": "Distinct Machines",
                "production_rows": "Production Rows",
                "total_energy_kwh": "Total Energy (kWh)",
                "total_good_qty": "Good Qty",
                "total_scrap_qty": "Scrap Qty",
                "avg_kwh_per_good_unit": "Weighted kWh/Good Unit",
                "scrap_rate": "Scrap Rate",
                "productive_hours": "Productive Hours",
                "nonproductive_hours": "Non-Productive Hours",
                "utilization_proxy": "Utilization Proxy",
                "avg_hours_since_last_maintenance": "Avg Hours Since Maintenance",
                "team_effectiveness_score": "Team Score",
                "team_band": "Band",
                "top_driver": "Top Driver",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def _build_model_preview_payload(month_year: str, db_path=None) -> dict[str, object]:
    predictor = MLPredictor()
    if not (
        getattr(predictor, "loaded_model", False)
        and getattr(predictor, "loaded_preprocessor", False)
    ):
        return {
            "available": False,
            "reason": "Model-backed preview is unavailable because the active saved predictor artifacts are not loadable.",
        }

    reader = CanonicalMLReader(db_path=db_path)
    input_df = reader.build_month_input_dataframe(month_year, predictor=predictor)
    if input_df.empty:
        return {
            "available": False,
            "reason": f"Model-backed preview is unavailable because no canonical ML inputs are available for {month_year}.",
        }

    candidate_df = reader.build_prediction_candidates(input_df)
    if candidate_df.empty:
        return {
            "available": False,
            "reason": f"Model-backed preview is unavailable because no eligible canonical machine-hour seed rows exist for {month_year}.",
        }

    prediction_df, blocked_prediction_df = reader.build_prediction_dataframe(
        candidate_df,
        predictor=predictor,
    )
    if prediction_df.empty:
        return {
            "available": False,
            "reason": (
                f"Model-backed preview is unavailable because the active predictor did not return "
                f"saved-model results for {month_year}."
            ),
        }

    return {
        "available": True,
        "predictor": predictor,
        "candidate_df": candidate_df,
        "prediction_df": prediction_df,
        "blocked_prediction_df": blocked_prediction_df,
    }


def _render_model_backed_preview(
    machine_id: str,
    preview_payload: dict[str, object],
) -> None:
    with section_shell(
        "Model-Backed Intervention Preview",
        "This section reuses the active saved model on one real comparable machine-hour seed row. "
        "It is a scenario preview only, not an executed optimization plan or realized-savings engine.",
        eyebrow="Flagship Preview",
    ):
        if not preview_payload.get("available"):
            st.info(str(preview_payload.get("reason")))
            return

        preview = build_machine_intervention_preview(
            preview_payload["candidate_df"],
            preview_payload["prediction_df"],
            preview_payload["predictor"],
            machine_id,
        )
        if preview["blocked"]:
            st.info(str(preview["reason"]))
            return

        baseline = preview["baseline"]
        best_scenario = preview["best_supported_scenario"]
        highlight_cards = [
            build_stat_card(
                "Baseline kWh / Unit",
                baseline["predicted_efficiency"],
                unit="kWh / unit",
                compact=False,
                primary_decimals=4,
                full_decimals=6,
            ),
            build_surface_card(
                "Baseline Confidence",
                f"{float(baseline['confidence']):.2f}",
                f"Baseline top driver: {baseline['top_driver']}",
            ),
            build_surface_card(
                "Best Supported Scenario",
                "n/a" if best_scenario is None else str(best_scenario["scenario_name"]),
                "Based on the active saved model only. Unsupported paths remain visible and honest.",
            ),
            build_surface_card(
                "Best Delta @ Seed Volume",
                (
                    "n/a"
                    if best_scenario is None
                    else f"{float(best_scenario['estimated_kwh_change']):+.4f} kWh"
                ),
                (
                    "No supported scenario returned for the current machine."
                    if best_scenario is None
                    else f"{float(best_scenario['delta_vs_baseline']):+.4f} kWh / unit vs baseline"
                ),
            ),
        ]
        _render_card_grid(highlight_cards, columns=4)

        st.caption(
            f"Comparable seed row: {preview['seed_timestamp_label']} | support path: {preview['support_path']} | "
            f"current comparable production volume: {preview['seed_production_qty']:.1f}"
        )
        if preview["adapter_notes"]:
            st.caption(f"Adapter notes: {preview['adapter_notes']}")

        comparison_df = _build_preview_comparison_table(preview)
        if not comparison_df.empty:
            st.dataframe(comparison_df, hide_index=True, use_container_width=True)

        st.info(
            "Estimated kWh change is calculated at the seed row's current comparable machine-hour volume. "
            "Treat this as a model-backed preview from the active saved model only, not a realized saving or executed plan."
        )

        scenario_table = build_intervention_preview_table(preview)
        if not scenario_table.empty:
            scenario_table["Predicted kWh/Unit"] = scenario_table["Predicted kWh/Unit"].round(4)
            scenario_table["Delta vs Baseline"] = scenario_table["Delta vs Baseline"].round(4)
            scenario_table["Confidence"] = scenario_table["Confidence"].round(4)
            scenario_table["Est. kWh Change @ Seed Volume"] = scenario_table[
                "Est. kWh Change @ Seed Volume"
            ].round(4)
            with st.expander("Supporting Evidence: All template outcomes", expanded=False):
                st.dataframe(
                    scenario_table,
                    hide_index=True,
                    use_container_width=True,
                )


def _render_notes() -> None:
    with st.expander("Reference & Audit: Canonical Optimization Notes"):
        st.markdown(
            """
            - Selected month availability comes from distinct months present in `fact_machine_hour`.
            - Machine summaries aggregate `fact_machine_hour` by `canonical_machine_id` for the selected month only.
            - `Weighted kWh / Good Unit` uses safe rows only: total energy on rows with `good_qty > 0` divided by total `good_qty` on those same rows.
            - `utilization_proxy` = production_minutes / (production + setup + planned_stop + unplanned_stop + idle minutes).
            - Opportunity score = 40% energy intensity + 30% non-productive share + 15% maintenance recency + 15% scrap rate.
            - Historical Hour Signals are descriptive only; they are not a real scheduling engine.
            - This score is deterministic and explanatory. It is not an ML model and does not use legacy or synthetic fallback data.
            """
        )


def _render_maintenance_context_block(
    machine_id: str,
    maintenance_reader: MaintenanceEvidenceReader,
    *,
    description: str,
) -> None:
    with section_shell(
        "Maintenance Evidence Context",
        description,
        eyebrow="Evidence Chain",
    ):
        payload = maintenance_reader.build_machine_context_payload(machine_id)
        if not payload["available"]:
            st.info(str(payload["reason"]))
            return

        cards = [
            build_surface_card(
                "Days Since Last Maintenance",
                _format_optional_int(payload["days_since_last_maintenance"]),
                f"Latest stored maintenance: {payload['latest_maintenance_datetime_label']}",
            ),
            build_surface_card(
                "Total Events",
                f"{int(payload['total_events']):,}",
                "All stored matched maintenance events for this machine.",
            ),
            build_surface_card(
                "PM Ratio (All Time)",
                _format_optional_ratio(payload["pm_ratio_all_time"]),
                "PM rows divided by all stored matched events.",
            ),
            build_surface_card(
                "Recent Events Shown",
                f"{int(payload['recent_events_shown']):,}",
                payload["history_window_note"],
            ),
            build_surface_card(
                "Latest Work Order Type",
                str(payload["latest_work_order_type"]),
                f"Months covered: {int(payload['months_covered_count']):,}",
            ),
        ]
        _render_card_grid(cards, columns=5)


def _format_number(value: float | int | None, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.1f}{suffix}"


def _format_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:.1f}%"


def _format_optional_ratio(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _format_optional_int(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,}"


__all__ = ["render_optimization_module"]


def _render_card_grid(cards: list[dict[str, str]], *, columns: int) -> None:
    for start_index in range(0, len(cards), columns):
        row_cards = cards[start_index : start_index + columns]
        row_columns = st.columns(columns)
        for column, card in zip(row_columns, row_cards):
            with column:
                render_surface_card(card)


def _build_opportunity_worklist(summary_df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame()

    queue_df = summary_df.head(limit).copy()
    queue_df["recommended_action"] = queue_df.apply(_recommended_action, axis=1)
    queue_df["opportunity_score"] = queue_df["opportunity_score"].round(4)
    queue_df["eligible_rows"] = queue_df["eligible_rows"].fillna(0).astype(int)
    queue_df["total_good_qty"] = queue_df["total_good_qty"].round(1)
    queue_df["avg_kwh_per_good_unit"] = queue_df["avg_kwh_per_good_unit"].round(4)
    return queue_df.loc[
        :,
        [
            "machine_id",
            "machine_family",
            "opportunity_flag",
            "opportunity_score",
            "top_driver",
            "recommended_action",
            "eligible_rows",
            "total_good_qty",
            "avg_kwh_per_good_unit",
        ],
    ].rename(
        columns={
            "machine_id": "Machine",
            "machine_family": "Family",
            "opportunity_flag": "Priority",
            "opportunity_score": "Opportunity Score",
            "top_driver": "Top Driver",
            "recommended_action": "Recommended Action",
            "eligible_rows": "Eligible Rows",
            "total_good_qty": "Total Good Qty",
            "avg_kwh_per_good_unit": "Weighted kWh / Good Unit",
        }
    )


def _build_full_scored_machine_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    display_df = summary_df.loc[
        :,
        [
            "machine_id",
            "machine_family",
            "opportunity_flag",
            "opportunity_score",
            "top_driver",
            "eligible_rows",
            "total_energy_kwh",
            "total_good_qty",
            "scrap_rate",
            "avg_kwh_per_good_unit",
            "productive_hours",
            "nonproductive_hours",
            "utilization_proxy",
            "avg_hours_since_last_maintenance",
            "energy_intensity_component",
            "nonproductive_component",
            "maintenance_recency_component",
            "scrap_component",
        ],
    ].copy()
    display_df["eligible_rows"] = display_df["eligible_rows"].astype(int)
    display_df["opportunity_score"] = display_df["opportunity_score"].round(4)
    display_df["total_energy_kwh"] = display_df["total_energy_kwh"].round(2)
    display_df["total_good_qty"] = display_df["total_good_qty"].round(2)
    display_df["scrap_rate"] = display_df["scrap_rate"].round(4)
    display_df["avg_kwh_per_good_unit"] = display_df["avg_kwh_per_good_unit"].round(4)
    display_df["productive_hours"] = display_df["productive_hours"].round(2)
    display_df["nonproductive_hours"] = display_df["nonproductive_hours"].round(2)
    display_df["utilization_proxy"] = display_df["utilization_proxy"].round(4)
    display_df["avg_hours_since_last_maintenance"] = display_df[
        "avg_hours_since_last_maintenance"
    ].round(2)
    display_df["energy_intensity_component"] = display_df["energy_intensity_component"].round(4)
    display_df["nonproductive_component"] = display_df["nonproductive_component"].round(4)
    display_df["maintenance_recency_component"] = display_df["maintenance_recency_component"].round(4)
    display_df["scrap_component"] = display_df["scrap_component"].round(4)
    return display_df.rename(
        columns={
            "machine_id": "Machine",
            "machine_family": "Machine Family",
            "opportunity_flag": "Opportunity",
            "opportunity_score": "Score",
            "top_driver": "Top Driver",
            "eligible_rows": "Eligible Rows",
            "total_energy_kwh": "Total Energy (kWh)",
            "total_good_qty": "Good Qty",
            "scrap_rate": "Scrap Rate",
            "avg_kwh_per_good_unit": "Weighted kWh/Good Unit",
            "productive_hours": "Productive Hours",
            "nonproductive_hours": "Non-Productive Hours",
            "utilization_proxy": "Utilization Proxy",
            "avg_hours_since_last_maintenance": "Avg Hours Since Maintenance",
            "energy_intensity_component": "Energy Intensity Component",
            "nonproductive_component": "Non-Productive Component",
            "maintenance_recency_component": "Maintenance Recency Component",
            "scrap_component": "Scrap Component",
        }
    )


def _recommended_action(row: pd.Series) -> str:
    driver = str(row.get("top_driver") or "").lower()
    machine_id = row.get("machine_id")
    if "maintenance" in driver:
        return f"Inspect {machine_id} and verify whether maintenance recency is driving the score."
    if "non-productive" in driver:
        return f"Review setup/stop mix for {machine_id} and reduce avoidable non-productive hours."
    if "scrap" in driver:
        return f"Audit scrap-heavy runs on {machine_id} before chasing energy changes."
    return f"Review high energy intensity on {machine_id} against its closest cohort."


def _build_machine_summary_cards(drilldown: dict[str, object]) -> list[dict[str, str]]:
    return [
        build_surface_card(
            "Machine",
            str(drilldown["machine_id"]),
            f"Family {drilldown['machine_family']}",
        ),
        build_stat_card(
            "Opportunity Score",
            drilldown["opportunity_score"],
            compact=False,
            primary_decimals=4,
            full_decimals=4,
        ),
        build_stat_card(
            "Eligible Rows",
            drilldown["eligible_rows"],
            compact=False,
            primary_decimals=0,
            full_decimals=0,
        ),
        build_stat_card(
            "Total Good Qty",
            drilldown["total_good_qty"],
            full_decimals=1,
        ),
        build_stat_card(
            "Weighted kWh / Good Unit",
            drilldown["weighted_kwh_per_good_unit"],
            unit="kWh / good unit",
            compact=False,
            primary_decimals=4,
            full_decimals=6,
        ),
        build_surface_card(
            "Scrap Rate",
            _format_percent(drilldown["scrap_rate"]),
            "Observed within the selected canonical month.",
        ),
        build_surface_card(
            "Avg Hours Since Maintenance",
            (
                "N/A"
                if drilldown["avg_hours_since_last_maintenance"] is None
                else f"{float(drilldown['avg_hours_since_last_maintenance']):,.1f} h"
            ),
            "Month average on canonical machine-hour rows.",
        ),
    ]


def _build_machine_support_cards(drilldown: dict[str, object]) -> list[dict[str, str]]:
    return [
        build_stat_card(
            "Productive Hours",
            drilldown["productive_hours"],
            unit="h",
            compact=False,
            primary_decimals=1,
            full_decimals=1,
        ),
        build_stat_card(
            "Non-Productive Hours",
            drilldown["nonproductive_hours"],
            unit="h",
            compact=False,
            primary_decimals=1,
            full_decimals=1,
        ),
    ]


def _build_preview_comparison_table(preview: dict[str, object]) -> pd.DataFrame:
    if preview.get("blocked") or not preview.get("baseline"):
        return pd.DataFrame()

    baseline = preview["baseline"]
    rows = [
        {
            "Comparison Point": "Baseline",
            "Predicted kWh / Unit": round(float(baseline["predicted_efficiency"]), 4),
            "Delta vs Baseline": 0.0,
            "Confidence": round(float(baseline["confidence"]), 4),
            "Comparable kWh Change": 0.0,
            "Meaning": str(baseline["top_driver"]),
        }
    ]

    best_scenario = preview.get("best_supported_scenario")
    if best_scenario is not None:
        rows.append(
            {
                "Comparison Point": str(best_scenario["scenario_name"]),
                "Predicted kWh / Unit": round(float(best_scenario["predicted_efficiency"]), 4),
                "Delta vs Baseline": round(float(best_scenario["delta_vs_baseline"]), 4),
                "Confidence": round(float(best_scenario["confidence"]), 4),
                "Comparable kWh Change": round(float(best_scenario["estimated_kwh_change"]), 4),
                "Meaning": str(best_scenario["interpretation"]),
            }
        )

    return pd.DataFrame(rows)


def _render_opportunity_filters(summary_df: pd.DataFrame, selected_month: str) -> tuple[pd.DataFrame, str]:
    st.markdown("##### Support Toolbar")
    st.caption(
        "These controls affect only the ranking, worklist, and drill-down below. They do not create solver logic "
        "or normalize different machine families beyond the displayed support."
    )

    machine_family_values = sorted(
        {
            str(value)
            for value in summary_df["machine_family"].dropna().tolist()
            if str(value).strip()
        }
    )
    family_options = ["All families"] + machine_family_values
    max_eligible_rows = int(summary_df["eligible_rows"].fillna(0).max()) if not summary_df.empty else 0
    max_total_good_qty = float(summary_df["total_good_qty"].fillna(0.0).max()) if not summary_df.empty else 0.0
    good_qty_step = max(1.0, round(max_total_good_qty / 20.0, 1)) if max_total_good_qty > 0 else 1.0

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        selected_family = st.selectbox(
            "Machine family",
            options=family_options,
            index=0,
            key=f"optimization_family_filter_{selected_month}",
        )
    with filter_col2:
        min_eligible_rows = st.number_input(
            "Minimum eligible rows",
            min_value=0,
            max_value=max_eligible_rows,
            value=0,
            step=1,
            key=f"optimization_min_rows_{selected_month}",
        )
    with filter_col3:
        min_total_good_qty = st.number_input(
            "Minimum total good qty",
            min_value=0.0,
            max_value=max_total_good_qty,
            value=0.0,
            step=good_qty_step,
            key=f"optimization_min_good_qty_{selected_month}",
        )

    selected_family_filter = None if selected_family == "All families" else selected_family
    filtered_df = _apply_opportunity_filters(
        summary_df,
        machine_family=selected_family_filter,
        min_eligible_rows=int(min_eligible_rows),
        min_total_good_qty=float(min_total_good_qty),
    )
    filter_summary = (
        "Applied filters: "
        f"machine family = {selected_family_filter or 'all'} | "
        f"eligible rows >= {int(min_eligible_rows)} | "
        f"total good qty >= {float(min_total_good_qty):,.1f} | "
        f"remaining machines = {len(filtered_df):,} of {len(summary_df):,}"
    )
    return filtered_df, filter_summary


def _apply_opportunity_filters(
    summary_df: pd.DataFrame,
    machine_family: str | None = None,
    min_eligible_rows: int = 0,
    min_total_good_qty: float = 0.0,
) -> pd.DataFrame:
    filtered_df = summary_df.copy()
    if machine_family:
        filtered_df = filtered_df[
            filtered_df["machine_family"].fillna("").astype(str) == str(machine_family)
        ].copy()
    filtered_df = filtered_df[
        filtered_df["eligible_rows"].fillna(0).astype(float) >= float(min_eligible_rows)
    ].copy()
    filtered_df = filtered_df[
        filtered_df["total_good_qty"].fillna(0.0).astype(float) >= float(min_total_good_qty)
    ].copy()
    return filtered_df.reset_index(drop=True)


def _build_machine_drilldown_snapshot(row: pd.Series) -> dict[str, object]:
    return {
        "machine_id": row.get("machine_id"),
        "machine_family": row.get("machine_family") if pd.notna(row.get("machine_family")) else "n/a",
        "opportunity_score": float(row.get("opportunity_score", 0.0)),
        "top_driver": row.get("top_driver") or "No strong canonical opportunity signal",
        "eligible_rows": int(float(row.get("eligible_rows", 0) or 0)),
        "total_good_qty": float(row.get("total_good_qty", 0.0) or 0.0),
        "productive_hours": float(row.get("productive_hours", 0.0) or 0.0),
        "nonproductive_hours": float(row.get("nonproductive_hours", 0.0) or 0.0),
        "weighted_kwh_per_good_unit": (
            None if pd.isna(row.get("avg_kwh_per_good_unit")) else float(row.get("avg_kwh_per_good_unit"))
        ),
        "scrap_rate": None if pd.isna(row.get("scrap_rate")) else float(row.get("scrap_rate")),
        "avg_hours_since_last_maintenance": (
            None
            if pd.isna(row.get("avg_hours_since_last_maintenance"))
            else float(row.get("avg_hours_since_last_maintenance"))
        ),
        "recommended_action": _recommended_action(row),
    }
