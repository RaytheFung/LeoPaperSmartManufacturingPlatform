from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.canonical_energy_reader import CanonicalEnergyReader
from core.ui_utils import build_stat_card, build_surface_card, render_surface_card, section_shell
from modules.unified_view_module import (
    _build_unified_value_card_payload,
    _render_unified_audit_card,
    _render_unified_value_card,
)


def build_energy_route_snapshot(
    *,
    db_path=None,
    selected_month: str | None = None,
) -> dict[str, object]:
    reader = CanonicalEnergyReader(db_path=db_path)
    available_months = reader.get_available_months()
    resolved_month = selected_month or (available_months[0] if available_months else None)
    energy_df = (
        reader.read_month_energy_dataframe(resolved_month)
        if resolved_month is not None
        else reader.read_month_energy_dataframe("January 1900")
    )
    summary = reader.build_month_summary(energy_df) if not energy_df.empty else {}
    return {
        "available_month_count": len(available_months),
        "selected_month": resolved_month,
        "rows_loaded": int(len(energy_df)),
        "total_energy_kwh": summary.get("total_energy_kwh"),
        "weighted_kwh_per_good_unit": summary.get("weighted_kwh_per_good_unit"),
        "fallback_used": False,
    }


def render_energy_module(db_path=None, runtime_mode: str = "standard") -> None:
    st.header("⚡ Energy Analysis Dashboard")
    reader = CanonicalEnergyReader(db_path=db_path)
    st.caption(
        "Canonical Gold source: fact_machine_hour. State-attributed energy uses canonical "
        "minute shares when available and falls back to canonical row state; residual energy-only "
        "hours remain explicitly unallocated."
    )

    available_months = reader.get_available_months()
    if not available_months:
        st.warning(
            "Canonical Gold is not available yet for Energy Analysis. "
            "This route no longer falls back to EUVG or unified_view."
        )
        return

    selected_month = st.selectbox("Select month", available_months, index=0)
    energy_df = reader.read_month_energy_dataframe(selected_month)
    if energy_df.empty:
        st.warning(
            f"No canonical energy rows are available for {selected_month}. "
            "This route does not fall back to EUVG or unified_view."
        )
        return

    summary = reader.build_month_summary(energy_df)
    trust_df = reader.build_attribution_trust_summary(energy_df)
    attribution_overview = reader.build_attribution_coverage_summary(energy_df)
    breakdown_df = reader.build_energy_breakdown(energy_df)
    machine_summary = reader.build_machine_energy_summary(
        energy_df,
        min_row_count=5,
        min_total_good_qty=1000.0,
    )

    energy_cards = _build_energy_month_cards(summary)
    first_row = st.columns(2)
    second_row = st.columns(2)
    for column, card in zip(first_row, energy_cards[:2]):
        with column:
            _render_unified_value_card(card)
    for column, card in zip(second_row, energy_cards[2:]):
        with column:
            _render_unified_value_card(card)
    st.caption(
        "Displayed efficiency KPI = sum(energy_total_kwh) / sum(good_qty) on positive-good-qty "
        "canonical rows in the selected month."
    )

    with section_shell(
        "Attribution Coverage & Residual Energy",
        "This section is current-month composition only. It shows how much of the month's energy is state-attributed, "
        "how much remains residual, and how many positive-energy rows are covered.",
        eyebrow="Primary Section",
    ):
        attribution_cards = _build_energy_attribution_cards(attribution_overview)
        attribution_columns = st.columns(3)
        for column, card in zip(attribution_columns, attribution_cards):
            with column:
                _render_unified_audit_card(card)
        if not trust_df.empty:
            trust_display_df = trust_df.copy()
            trust_display_df["energy_kwh"] = trust_display_df["energy_kwh"].round(2)
            trust_display_df["energy_share"] = trust_display_df["energy_share"].apply(_format_ratio)
            with st.expander("Reference & Audit: Detailed attribution categories", expanded=False):
                st.dataframe(
                    trust_display_df.rename(
                        columns={
                            "attribution_label": "Attribution Category",
                            "meaning": "Meaning",
                            "row_count": "Rows",
                            "energy_kwh": "Energy (kWh)",
                            "energy_share": "Share of Month Energy",
                        }
                    )[
                        [
                            "Attribution Category",
                            "Meaning",
                            "Rows",
                            "Energy (kWh)",
                            "Share of Month Energy",
                        ]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

    with section_shell(
        "Energy Mix & Machine Attention",
        "Keep one primary energy story and one decision-oriented machine review area on the main surface. "
        "Detailed or lower-priority context stays below as disclosures.",
        eyebrow="Primary Section",
    ):
        story_col, attention_col = st.columns([1.1, 0.9])
        with story_col:
            st.markdown("#### Where Energy Goes")
            if breakdown_df.empty:
                st.info("No positive canonical energy rows are available for the selected month.")
            else:
                breakdown_display_df = breakdown_df.copy()
                total_energy = breakdown_display_df["energy_kwh"].sum()
                breakdown_display_df["energy_share"] = (
                    breakdown_display_df["energy_kwh"] / total_energy if total_energy > 0 else 0.0
                )
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=breakdown_df["energy_bucket"],
                            values=breakdown_df["energy_kwh"],
                            textposition="inside",
                            textinfo="percent+label",
                            hovertemplate=(
                                "<b>%{label}</b><br>Energy: %{value:,.2f} kWh"
                                "<br>Share of month energy: %{percent}<extra></extra>"
                            ),
                        )
                    ]
                )
                fig.update_layout(title=f"Energy Mix by Operating State in {selected_month}", showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    breakdown_display_df.assign(
                        energy_kwh=breakdown_display_df["energy_kwh"].round(2),
                        energy_share=breakdown_display_df["energy_share"].apply(_format_ratio),
                    ).rename(
                        columns={
                            "energy_bucket": "Energy Bucket",
                            "energy_kwh": "Energy (kWh)",
                            "energy_share": "Share of Month Energy",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

        with attention_col:
            st.markdown("#### Machines to Review First")
            st.caption(
                "Support filter: at least 5 positive-good rows and 1,000 total good qty in the selected month."
            )
            if machine_summary.empty:
                st.info("No machines meet the tightened support rule for the attention views.")
            else:
                attention_view = st.radio(
                    "Attention view",
                    ["Highest energy load", "Highest weighted kWh / Good Unit", "Most efficient"],
                    horizontal=True,
                )
                attention_config = _select_energy_attention_view(machine_summary, attention_view)
                attention_df = attention_config["dataframe"]
                attention_chart_df = attention_df.sort_values(
                    [attention_config["metric_column"], "machine_id"],
                    ascending=[True, True],
                )
                fig = px.bar(
                    attention_chart_df,
                    x=attention_config["metric_column"],
                    y="machine_id",
                    orientation="h",
                    title=attention_config["title"],
                    hover_data={
                        "row_count": True,
                        "total_good_qty": ":,.0f",
                        "total_energy_kwh": ":,.1f",
                        "weighted_kwh_per_good_unit": ":,.4f",
                    },
                    labels={
                        "machine_id": "Machine ID",
                        "row_count": "Eligible Rows",
                        "total_good_qty": "Good Qty",
                        "total_energy_kwh": "Energy (kWh)",
                        "weighted_kwh_per_good_unit": "Weighted kWh / Good Unit",
                        attention_config["metric_column"]: attention_config["metric_label"],
                    },
                )
                st.plotly_chart(fig, use_container_width=True)
                focus_machine = st.selectbox("Selected machine context", attention_df["machine_id"], index=0)
                focus_row = attention_df.loc[attention_df["machine_id"] == focus_machine].iloc[0]
                st.markdown("##### Selected machine context")
                focus_cards = _build_energy_machine_context_cards(focus_row, attention_view)
                first_focus_row = st.columns(2)
                second_focus_row = st.columns(2)
                for column, card in zip(first_focus_row + second_focus_row, focus_cards):
                    with column:
                        render_surface_card(card)

    with st.expander("Context & Diagnostics: Daily Energy Attribution Over Time", expanded=False):
        st.caption(
            "Daily stacks show how the selected month's energy composition moves across days. "
            "This is descriptive only and does not imply a causal explanation."
        )
        daily_energy = reader.build_daily_state_energy(energy_df)
        if daily_energy.empty:
            st.info("No daily canonical energy series is available for the selected month.")
        else:
            daily_anomalies = reader.build_daily_energy_anomalies(daily_energy)
            fig = go.Figure()
            for column in daily_energy.columns[1:]:
                if daily_energy[column].fillna(0.0).sum() <= 0:
                    continue
                fig.add_trace(
                    go.Scatter(
                        x=daily_energy["date"],
                        y=daily_energy[column],
                        name=column,
                        stackgroup="one",
                    )
                )
            if not daily_anomalies.empty:
                fig.add_trace(
                    go.Scatter(
                        x=daily_anomalies["date"],
                        y=daily_anomalies["total_energy_kwh"],
                        mode="markers",
                        name="Daily anomaly",
                        marker=dict(color="#d62728", size=10, symbol="diamond"),
                        hovertemplate=(
                            "<b>%{x}</b><br>Total energy: %{y:,.1f} kWh"
                            "<br>Anomaly type: %{text}<extra></extra>"
                        ),
                        text=daily_anomalies["direction"],
                    )
                )
            fig.update_layout(
                title=f"Daily Canonical Energy Attribution for {selected_month}",
                xaxis_title="Date",
                yaxis_title="Energy (kWh)",
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)
            if not daily_anomalies.empty:
                st.caption(
                    "Daily anomaly markers use an IQR rule on total daily energy and highlight days "
                    "that sit materially outside the month’s normal range."
                )

    with st.expander("Supporting Evidence: Maintenance Context", expanded=False):
        st.caption(
            "Observed only. This curve is a contextual appendix and does not imply a causal maintenance threshold or policy rule."
        )
        maintenance_curve = reader.build_maintenance_efficiency_curve(month_year=selected_month)
        if maintenance_curve.empty:
            st.info("Not enough supported rows are available to build the maintenance-age efficiency curve.")
        else:
            curve_fig = px.line(
                maintenance_curve,
                x="bucket",
                y="weighted_kwh_per_good_unit",
                markers=True,
                hover_data={
                    "row_count": True,
                    "total_good_qty": ":,.0f",
                    "total_energy_kwh": ":,.1f",
                },
                title=f"Observed weighted energy intensity by maintenance-age bucket in {selected_month}",
                labels={
                    "bucket": "Hours Since Maintenance",
                    "weighted_kwh_per_good_unit": "Weighted kWh / Good Unit",
                },
            )
            st.plotly_chart(curve_fig, use_container_width=True)

    with section_shell(
        "Hourly Energy Pattern",
        "Primary view uses total energy by hour because it preserves the clearest operational contrast. "
        "Average-per-row hourly energy is kept as a secondary reference.",
        eyebrow="Primary Section",
    ):
        hourly_pattern = reader.build_hourly_energy_profile(energy_df)
        if hourly_pattern.empty:
            st.info("No canonical hourly energy pattern is available for the selected month.")
        else:
            total_fig = go.Figure()
            total_fig.add_trace(
                go.Bar(
                    x=hourly_pattern["hour_of_day"],
                    y=hourly_pattern["total_energy_kwh"],
                    name="Total Energy",
                    customdata=hourly_pattern[["row_count"]],
                    hovertemplate=(
                        "Hour %{x}:00<br>Total Energy (kWh): %{y:,.1f}"
                        "<br>Rows: %{customdata[0]}<extra></extra>"
                    ),
                )
            )
            total_fig.update_layout(
                title=f"Total Energy by Hour in {selected_month}",
                xaxis_title="Hour of Day",
                yaxis_title="Total Energy (kWh)",
            )
            st.plotly_chart(total_fig, use_container_width=True)
            with st.expander("Reference & Audit: Average energy per canonical row by hour", expanded=False):
                avg_fig = go.Figure()
                avg_fig.add_trace(
                    go.Bar(
                        x=hourly_pattern["hour_of_day"],
                        y=hourly_pattern["avg_energy_kwh"],
                        name="Average Energy",
                        customdata=hourly_pattern[["row_count"]],
                        hovertemplate=(
                            "Hour %{x}:00<br>Average Energy (kWh): %{y:,.1f}"
                            "<br>Rows: %{customdata[0]}<extra></extra>"
                        ),
                    )
                )
                avg_fig.update_layout(
                    title=f"Average Energy per Canonical Row by Hour in {selected_month}",
                    xaxis_title="Hour of Day",
                    yaxis_title="Average Energy (kWh)",
                )
                st.plotly_chart(avg_fig, use_container_width=True)


def _format_ratio(value):
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _build_energy_month_cards(summary):
    return [
        _build_unified_value_card_payload(
            "Total Energy",
            summary.get("total_energy_kwh"),
            unit="kWh",
            full_decimals=1,
        ),
        _build_unified_value_card_payload(
            "Good Quantity",
            summary.get("total_good_qty"),
            unit="pcs",
            full_decimals=1,
        ),
        _build_unified_value_card_payload(
            "Weighted kWh / Good Unit",
            summary.get("weighted_kwh_per_good_unit"),
            unit="kWh / good unit",
            compact=False,
            primary_decimals=4,
            full_decimals=6,
        ),
        _build_unified_value_card_payload(
            "Distinct Machines",
            summary.get("distinct_machines"),
            unit="machines",
            full_decimals=0,
        ),
    ]


def _build_energy_attribution_cards(attribution_overview):
    total_energy = attribution_overview.get("total_energy_kwh", 0.0) or 0.0
    positive_rows = int(attribution_overview.get("positive_energy_rows", 0) or 0)
    attributed_rows = int(attribution_overview.get("attributed_positive_energy_rows", 0) or 0)
    return [
        {
            "label": "Attributed Energy",
            "primary": _format_ratio(attribution_overview.get("attributed_energy_share")),
            "secondary": (
                f"{attribution_overview.get('attributed_energy_kwh', 0.0):,.1f} / {total_energy:,.1f} kWh"
            ),
            "description": "Energy assigned to a specific operating state through minute-share attribution or machine-state fallback.",
        },
        {
            "label": "Residual / Unallocated Energy",
            "primary": _format_ratio(attribution_overview.get("residual_energy_share")),
            "secondary": (
                f"{attribution_overview.get('residual_energy_kwh', 0.0):,.1f} / {total_energy:,.1f} kWh"
            ),
            "description": "Positive energy that remains energy-only or otherwise unattributed in the current month slice.",
        },
        {
            "label": "State-Attributed Positive-Energy Rows",
            "primary": _format_ratio(attribution_overview.get("attributed_positive_energy_row_share")),
            "secondary": f"{attributed_rows:,} / {positive_rows:,} positive-energy rows",
            "description": "Rows with positive energy that were mapped into a specific operating state instead of staying residual.",
        },
    ]


def _build_energy_machine_context_cards(focus_row, attention_view):
    return [
        build_stat_card(
            "Month Energy",
            focus_row.get("total_energy_kwh"),
            unit="kWh",
            full_decimals=1,
        ),
        build_stat_card(
            "Weighted kWh / Good Unit",
            focus_row.get("weighted_kwh_per_good_unit"),
            unit="kWh / good unit",
            compact=False,
            primary_decimals=4,
            full_decimals=6,
        ),
        build_stat_card(
            "Eligible Rows",
            focus_row.get("row_count"),
            compact=False,
            primary_decimals=0,
            full_decimals=0,
        ),
        build_surface_card(
            "Attention View",
            attention_view,
            "Affects the ranking, selected-machine context, and review ordering only.",
        ),
    ]


def _select_energy_attention_view(machine_summary, attention_view, limit=10):
    config_map = {
        "Highest energy load": {
            "metric_column": "total_energy_kwh",
            "metric_label": "Energy (kWh)",
            "title": "Highest Energy Load Machines",
            "sort_columns": ["total_energy_kwh", "weighted_kwh_per_good_unit", "machine_id"],
            "ascending": [False, False, True],
        },
        "Highest weighted kWh / Good Unit": {
            "metric_column": "weighted_kwh_per_good_unit",
            "metric_label": "Weighted kWh / Good Unit",
            "title": "Highest Weighted kWh / Good Unit",
            "sort_columns": ["weighted_kwh_per_good_unit", "total_energy_kwh", "machine_id"],
            "ascending": [False, False, True],
        },
        "Most efficient": {
            "metric_column": "weighted_kwh_per_good_unit",
            "metric_label": "Weighted kWh / Good Unit",
            "title": "Most Efficient Machines",
            "sort_columns": ["weighted_kwh_per_good_unit", "total_good_qty", "machine_id"],
            "ascending": [True, False, True],
        },
    }
    config = dict(config_map.get(attention_view, config_map["Highest energy load"]))
    config["dataframe"] = (
        machine_summary.sort_values(config["sort_columns"], ascending=config["ascending"])
        .head(limit)
        .reset_index(drop=True)
    )
    return config


__all__ = ["build_energy_route_snapshot", "render_energy_module"]
