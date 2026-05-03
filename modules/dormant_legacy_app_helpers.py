"""Dormant historical compatibility helpers extracted from app.py.

This module is dormant, non-routed, historical compatibility only, and is not
defended-core runtime truth. The current defended-core and experimental sidebar
routes do not dispatch into these helpers during normal execution.
"""

from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.runtime_paths import get_data_dir


MODULE_BOUNDARY_NOTE = (
    "Dormant, non-routed, historical compatibility only. "
    "Not defended-core runtime truth."
)

DORMANT_LEGACY_HELPER_NAMES = (
    "load_data",
    "show_overview_page",
    "show_etl_page",
    "show_team_performance_page",
    "show_optimization_page",
)


@st.cache_data
def load_data():
    """Load legacy June ETL/EUVG data for dormant helper paths only."""

    try:
        from core.enhanced_etl_solution_CURRENT import EnhancedSmartManufacturingETL
        from modules.euvg_module import EnhancedUnifiedViewGenerator

        etl = EnhancedSmartManufacturingETL()
        data_dir = get_data_dir()

        energy_files = [str(data_dir / "能耗、費用報表June(1-30).xlsx")]
        csi_file = str(data_dir / "CSI印刷心電圖報表June.xlsx")
        mes_file = str(data_dir / "MES生產數據JunePrinter.xlsx")
        mappings_file = data_dir / "june_enhanced_manufacturing_mappings_LATEST.json"

        etl.extract_all_sources(energy_files, csi_file, mes_file)

        if mappings_file.exists():
            with open(mappings_file, "r", encoding="utf-8") as file_obj:
                mappings_data = json.load(file_obj)
                etl.state.machine_mapping = mappings_data
        else:
            etl.aggregate_energy_data()
            etl.create_comprehensive_mapping()

        euvg = EnhancedUnifiedViewGenerator(etl)
        if "three_way_matches" in etl.machine_mapping:
            euvg.three_way_matches = etl.machine_mapping["three_way_matches"]
        else:
            st.error("No three-way matches found in ETL mapping!")
            return None, None, None

        unified_view = euvg.create_unified_hourly_view()
        enhanced_view = euvg.add_engineered_features()
        return etl, euvg, enhanced_view

    except Exception as exc:
        st.error(f"Error loading data: {exc}")
        st.error("Please ensure all data files are in the 'data' folder")
        return None, None, None


def show_overview_page(etl, euvg, unified_view):
    """Display the dormant overview metrics and key insights helper."""

    st.header("📊 Manufacturing Analytics Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_machines = len(euvg.three_way_matches) if hasattr(euvg, "three_way_matches") else 0
        total_mes = etl.machine_mapping.get("mapping_stats", {}).get("mes_machines", 88)
        coverage_pct = (total_machines / total_mes * 100) if total_mes > 0 else 0
        st.metric("Three-way Matches", f"{total_machines}/{total_mes}", f"{coverage_pct:.1f}%")

    with col2:
        total_energy = unified_view["energy_kwh"].sum()
        st.metric("Total Energy (June)", f"{total_energy:,.0f} kWh")

    with col3:
        total_production = unified_view["production_qty"].sum()
        st.metric("Total Production", f"{total_production:,.0f} units")

    with col4:
        avg_efficiency = unified_view["kwh_per_unit"].mean()
        st.metric("Avg Efficiency", f"{avg_efficiency:.2f} kWh/unit")

    st.subheader("Energy Attribution Breakdown")
    energy_color_map = {
        "Setup Energy": "#3498db",
        "Production Energy": "#2ecc71",
        "Idle Energy": "#e74c3c",
        "Maintenance Energy": "#f39c12",
    }

    energy_cols = ["setup_energy", "production_energy", "idle_energy", "maintenance_energy"]
    energy_breakdown = {}
    for column in energy_cols:
        if column in unified_view.columns:
            energy_breakdown[column.replace("_", " ").title()] = unified_view[column].sum()

    if energy_breakdown:
        fig = px.pie(
            values=list(energy_breakdown.values()),
            names=list(energy_breakdown.keys()),
            title="Where Does Energy Go?",
            color_discrete_map=energy_color_map,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Daily Production Trend")
    daily_stats = unified_view.groupby(pd.Grouper(key="datetime", freq="D")).agg(
        {"production_qty": "sum", "energy_kwh": "sum"}
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily_stats["datetime"],
            y=daily_stats["production_qty"],
            name="Production Quantity",
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily_stats["datetime"],
            y=daily_stats["energy_kwh"],
            name="Energy Consumption",
            yaxis="y2",
            line=dict(color="red"),
        )
    )
    fig.update_layout(
        title="Daily Production vs Energy Consumption",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Production Quantity", side="left"),
        yaxis2=dict(title="Energy (kWh)", side="right", overlaying="y"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


def show_etl_page(etl):
    """Display the dormant ETL pipeline status helper."""

    st.header("🔄 ETL Pipeline Status")
    stats = etl.machine_mapping.get("mapping_stats", {})

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Data Volume")
        st.write(f"- Energy Records: {stats.get('energy_original_rows', 0):,}")
        st.write(f"- Energy Machines: {stats.get('energy_unique_machines', 0)}")
        st.write(f"- CSI Machines: {stats.get('csi_machines', 0)}")
        st.write(f"- MES Machines: {stats.get('mes_machines', 0)}")

    with col2:
        st.subheader("Matching Results")
        st.write(f"- Three-way Matches: {stats.get('three_way_matches', 0)}")
        st.write(f"- MES Coverage: {stats.get('mes_coverage_percent', 'N/A')}")

    st.subheader("Three-way Machine Matches")
    if "three_way_matches" in etl.machine_mapping:
        matches_df = pd.DataFrame(etl.machine_mapping["three_way_matches"])
        display_cols = ["machine_id", "csi", "mes", "total_kwh"]
        if all(column in matches_df.columns for column in display_cols):
            st.dataframe(matches_df[display_cols].round(2), use_container_width=True)
        else:
            st.dataframe(matches_df, use_container_width=True)


def show_team_performance_page(euvg, unified_view):
    """Display the dormant team-performance analysis helper."""

    st.header("👥 Team Performance Analysis")

    if unified_view is None or unified_view.empty:
        st.info("Unified view data not available. Please run the ETL pipeline first.")
        return

    required_columns = {"kwh_per_unit", "production_qty", "datetime"}
    missing_columns = required_columns - set(unified_view.columns)
    if missing_columns:
        st.warning(f"Unified view is missing required columns: {', '.join(sorted(missing_columns))}.")
        return

    analysis_df = unified_view.copy()
    mask = analysis_df["kwh_per_unit"].between(0.3, 10, inclusive="both")
    mask &= analysis_df["production_qty"] > 0
    if "is_near_zero_output" in analysis_df.columns:
        mask &= analysis_df["is_near_zero_output"] == 0
    analysis_df = analysis_df.loc[mask].copy()

    if analysis_df.empty:
        st.info("No qualifying production records found (after quality filters).")
        return

    analysis_df["month_period"] = analysis_df["datetime"].dt.to_period("M")
    if analysis_df["month_period"].empty:
        st.info("No month information available in the unified view.")
        return

    month_options = sorted(analysis_df["month_period"].unique())
    selected_month = st.selectbox(
        "Select month",
        month_options,
        index=len(month_options) - 1,
        format_func=lambda period: str(period),
    )

    analysis_df = analysis_df[analysis_df["month_period"] == selected_month].copy()
    if analysis_df.empty:
        st.info("No qualifying production records for the selected month.")
        return

    month_label = str(selected_month)
    analysis_df["task_type"] = (
        analysis_df["task_type"].fillna("Unknown")
        if "task_type" in analysis_df.columns
        else "Unknown"
    )
    analysis_df["team_leader"] = (
        analysis_df["team_leader"].fillna("Unknown")
        if "team_leader" in analysis_df.columns
        else "Unknown"
    )
    if "team_composition" in analysis_df.columns:
        analysis_df["team_composition"] = analysis_df["team_composition"].fillna(
            analysis_df["team_leader"]
        )

    config_col1, config_col2 = st.columns(2)
    leader_task_min = config_col1.number_input(
        "Minimum samples per leader × task",
        min_value=1,
        value=20,
        step=1,
        help="Only show leader-task combinations with at least this many qualifying hours.",
    )
    team_comp_min = config_col2.number_input(
        "Minimum samples per team composition × task",
        min_value=1,
        value=10,
        step=1,
        help="Only show team composition-task combinations with at least this many qualifying hours.",
    )

    st.subheader("Leader × Task Efficiency")
    leader_task_columns = [
        "task_type",
        "team_leader",
        "avg_kwh_per_unit",
        "median_kwh_per_unit",
        "sample_size",
        "total_production",
        "last_observed",
    ]
    leader_task_group = pd.DataFrame(columns=leader_task_columns)
    if "team_leader" in analysis_df.columns:
        raw_leader_task = (
            analysis_df.groupby(["task_type", "team_leader"], dropna=False)
            .agg(
                avg_kwh_per_unit=("kwh_per_unit", "mean"),
                median_kwh_per_unit=("kwh_per_unit", "median"),
                sample_size=("kwh_per_unit", "count"),
                total_production=("production_qty", "sum"),
                last_observed=("datetime", "max"),
            )
            .reset_index()
        )
        if not raw_leader_task.empty:
            leader_task_group = raw_leader_task[
                (raw_leader_task["sample_size"] >= leader_task_min)
                & (raw_leader_task["team_leader"] != "Unknown")
                & (raw_leader_task["task_type"] != "Unknown")
            ].sort_values("avg_kwh_per_unit")

    if leader_task_group.empty:
        st.info("No leader × task combinations meet the minimum sample threshold yet.")
    else:
        st.dataframe(
            leader_task_group.head(25).round({"avg_kwh_per_unit": 3, "median_kwh_per_unit": 3}),
            use_container_width=True,
            hide_index=True,
        )

        best_leader_chart = leader_task_group.nsmallest(15, "avg_kwh_per_unit")
        fig = px.bar(
            best_leader_chart,
            x="team_leader",
            y="avg_kwh_per_unit",
            color="task_type",
            title="Top Leader × Task Combinations (Lower kWh/unit is better)",
            labels={
                "avg_kwh_per_unit": "Avg kWh/unit",
                "team_leader": "Team Leader",
                "task_type": "Task",
            },
        )
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    if hasattr(euvg, "team_performance_analysis") and euvg.team_performance_analysis:
        team_analysis = euvg.team_performance_analysis
        st.subheader("🏆 Top Performing Teams")

        if "best_teams" in team_analysis and team_analysis["best_teams"]:
            top_teams_df = pd.DataFrame(team_analysis["best_teams"])
            display_cols = ["team_name", "avg_kwh_per_unit", "productivity", "primary_task"]
            available_cols = [column for column in display_cols if column in top_teams_df.columns]
            if available_cols:
                st.dataframe(top_teams_df[available_cols].round(2), use_container_width=True)

        st.subheader("Team Efficiency by Task Type")
        if "detailed_metrics" in team_analysis:
            team_task_data = []
            for team_name, metrics in team_analysis["detailed_metrics"].items():
                if isinstance(metrics, dict):
                    team_task_data.append(
                        {
                            "Team": team_name[:30] + "..." if len(team_name) > 30 else team_name,
                            "Efficiency": metrics.get("avg_kwh_per_unit", 0),
                            "Task Type": metrics.get("primary_task", "Unknown"),
                            "Hours Worked": metrics.get("total_hours", 0),
                        }
                    )

            if team_task_data:
                team_task_df = pd.DataFrame(team_task_data)
                team_task_df = team_task_df[team_task_df["Efficiency"] > 0]
                if len(team_task_df) > 0:
                    fig = px.scatter(
                        team_task_df,
                        x="Hours Worked",
                        y="Efficiency",
                        color="Task Type",
                        hover_data=["Team"],
                        title="Team Efficiency vs Experience",
                        labels={"Efficiency": "kWh per Unit (Lower is Better)"},
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("Team Efficiency Ranking")
                    top_20_teams = team_task_df.nsmallest(20, "Efficiency")
                    if len(top_20_teams) > 0:
                        fig = px.bar(
                            top_20_teams,
                            x="Team",
                            y="Efficiency",
                            color="Task Type",
                            title="Top 20 Teams by Efficiency",
                        )
                        fig.update_xaxis(tickangle=45)
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Team performance analysis artifacts not available. Live analytics below use unified view data."
            )

    team_comp_columns = [
        "task_type",
        "team_composition",
        "avg_kwh_per_unit",
        "median_kwh_per_unit",
        "sample_size",
        "total_production",
        "last_observed",
        "median_team_size",
    ]
    team_comp_group = pd.DataFrame(columns=team_comp_columns)
    if "team_composition" in analysis_df.columns:
        st.subheader("Team Composition × Task Efficiency")
        comp_df = analysis_df[analysis_df["team_composition"].notna()]
        comp_df = comp_df[comp_df["team_composition"] != "Unknown"]

        if comp_df.empty:
            st.info("No team composition data available after filtering.")
        else:
            aggregation_kwargs = dict(
                avg_kwh_per_unit=("kwh_per_unit", "mean"),
                median_kwh_per_unit=("kwh_per_unit", "median"),
                sample_size=("kwh_per_unit", "count"),
                total_production=("production_qty", "sum"),
                last_observed=("datetime", "max"),
            )
            if "team_size" in comp_df.columns:
                aggregation_kwargs["median_team_size"] = ("team_size", "median")

            team_comp_group = (
                comp_df.groupby(["task_type", "team_composition"], dropna=False)
                .agg(**aggregation_kwargs)
                .reset_index()
            )
            team_comp_group = team_comp_group[
                (team_comp_group["sample_size"] >= team_comp_min)
                & (team_comp_group["task_type"] != "Unknown")
            ].sort_values("avg_kwh_per_unit")

            if team_comp_group.empty:
                st.info("No team composition × task combinations meet the minimum sample threshold yet.")
            else:
                st.dataframe(
                    team_comp_group.head(25).round(
                        {"avg_kwh_per_unit": 3, "median_kwh_per_unit": 3}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                best_team_comp_chart = team_comp_group.nsmallest(15, "avg_kwh_per_unit")
                fig = px.bar(
                    best_team_comp_chart,
                    x="team_composition",
                    y="avg_kwh_per_unit",
                    color="task_type",
                    title="Top Team Composition × Task Combinations",
                    labels={
                        "avg_kwh_per_unit": "Avg kWh/unit",
                        "team_composition": "Team Composition",
                    },
                )
                fig.update_layout(xaxis_tickangle=-35)
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Insights Report")
    avg_efficiency = analysis_df["kwh_per_unit"].dropna().mean()
    summary_rows = [
        ("Month", month_label),
        ("Hours analyzed", f"{len(analysis_df):,}"),
        ("Total production (units)", f"{analysis_df['production_qty'].sum():,.0f}"),
        ("Average kWh/unit", f"{avg_efficiency:.3f}" if not np.isnan(avg_efficiency) else "N/A"),
        ("Unique machines", analysis_df["machine_id"].nunique()),
        ("Unique leaders", analysis_df["team_leader"].nunique()),
        ("Unique tasks", analysis_df["task_type"].nunique()),
    ]

    if not leader_task_group.empty:
        best_combo = leader_task_group.iloc[0]
        summary_rows.append(("Top leader × task", f"{best_combo['team_leader']} ({best_combo['task_type']})"))
        summary_rows.append(("Top leader × task kWh/unit", f"{best_combo['avg_kwh_per_unit']:.3f}"))
        worst_combo = leader_task_group.iloc[-1]
        summary_rows.append(
            (
                "Largest improvement (leader × task)",
                f"{worst_combo['team_leader']} ({worst_combo['task_type']})",
            )
        )
        summary_rows.append(("Improvement kWh/unit", f"{worst_combo['avg_kwh_per_unit']:.3f}"))

    if not team_comp_group.empty:
        best_team = team_comp_group.iloc[0]
        summary_rows.append(
            ("Top team composition", f"{best_team['team_composition']} ({best_team['task_type']})")
        )
        summary_rows.append(("Top team kWh/unit", f"{best_team['avg_kwh_per_unit']:.3f}"))

    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    if not leader_task_group.empty:
        opportunities_df = leader_task_group.nlargest(
            min(len(leader_task_group), 15), "avg_kwh_per_unit"
        ).reset_index(drop=True)
    else:
        opportunities_df = pd.DataFrame(
            columns=[
                "task_type",
                "team_leader",
                "avg_kwh_per_unit",
                "median_kwh_per_unit",
                "sample_size",
                "total_production",
                "last_observed",
            ]
        )

    maintenance_df = pd.DataFrame(
        columns=["machine_id", "maintenance_energy", "energy_kwh", "hours", "maintenance_ratio"]
    )
    if {"maintenance_energy", "energy_kwh"}.issubset(analysis_df.columns):
        maintenance_summary = (
            analysis_df.groupby("machine_id")
            .agg(
                maintenance_energy=("maintenance_energy", "sum"),
                energy_kwh=("energy_kwh", "sum"),
                hours=("machine_id", "count"),
            )
            .reset_index()
        )
        maintenance_summary["maintenance_ratio"] = np.where(
            maintenance_summary["energy_kwh"] > 0,
            maintenance_summary["maintenance_energy"] / maintenance_summary["energy_kwh"],
            np.nan,
        )
        maintenance_df = maintenance_summary.sort_values("maintenance_energy", ascending=False).head(15)

    detail_columns = [
        "datetime",
        "machine_id",
        "team_leader",
        "team_composition",
        "task_type",
        "production_qty",
        "energy_kwh",
        "kwh_per_unit",
        "maintenance_energy",
        "is_near_zero_output",
    ]
    detail_cols_present = [column for column in detail_columns if column in analysis_df.columns]
    detail_df = analysis_df[detail_cols_present].copy()
    if "datetime" in detail_df.columns:
        detail_df["datetime"] = detail_df["datetime"].astype(str)
    if "kwh_per_unit" in detail_df.columns:
        detail_df["kwh_per_unit"] = detail_df["kwh_per_unit"].round(3)

    insights_buffer = io.BytesIO()
    with pd.ExcelWriter(insights_buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        leader_task_group.to_excel(writer, index=False, sheet_name="Leader_Task")
        team_comp_group.to_excel(writer, index=False, sheet_name="Team_Composition")
        opportunities_df.to_excel(writer, index=False, sheet_name="Opportunities")
        maintenance_df.to_excel(writer, index=False, sheet_name="Maintenance_Hotspots")
        detail_df.to_excel(writer, index=False, sheet_name="Detail")

    insights_buffer.seek(0)
    st.download_button(
        label=f"Download {month_label} Insights (XLSX)",
        data=insights_buffer.getvalue(),
        file_name=f"monthly_insights_{month_label}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def show_optimization_page(euvg, unified_view):
    """Display the dormant optimization helper."""

    st.header("🎯 Production Optimization")
    st.subheader("Material Transition Costs")

    if "material_transition" in unified_view.columns:
        transitions = unified_view[unified_view["material_transition"] == 1]
        if len(transitions) > 0 and "setup_energy" in transitions.columns:
            transition_energy = transitions.groupby("material_code")["setup_energy"].mean()
            if len(transition_energy) > 0:
                fig = px.bar(
                    transition_energy.sort_values(ascending=False).head(10).reset_index(),
                    x="material_code",
                    y="setup_energy",
                    title="Average Setup Energy by Material",
                )
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Intelligent Scheduling")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(
            """
        The intelligent scheduler optimizes production sequences to:
        - Minimize material transitions
        - Reduce setup times
        - Maximize machine utilization
        - Balance workload across teams
        """
        )

    with col2:
        if st.button("Generate Optimized Schedule", type="primary"):
            pending_orders = [
                {"order_id": "J250001", "material_code": "MAT001", "quantity": 1000},
                {"order_id": "J250002", "material_code": "MAT002", "quantity": 1500},
                {"order_id": "J250003", "material_code": "MAT001", "quantity": 800},
                {"order_id": "J250004", "material_code": "MAT003", "quantity": 1200},
                {"order_id": "J250005", "material_code": "MAT002", "quantity": 900},
            ]

            if hasattr(euvg, "scheduler"):
                optimized = euvg.scheduler.optimize_production_sequence(pending_orders)
                st.success("✅ Optimized sequence minimizes material transitions!")
                st.subheader("Optimized Production Sequence")

                opt_df = pd.DataFrame(optimized)
                opt_df["Sequence"] = range(1, len(opt_df) + 1)
                st.dataframe(
                    opt_df[["Sequence", "order_id", "material_code", "quantity"]],
                    use_container_width=True,
                )

                st.subheader("Estimated Savings")
                original_transitions = len({order["material_code"] for order in pending_orders}) - 1
                optimized_transitions = 0
                prev_material = None
                for order in optimized:
                    if prev_material and order["material_code"] != prev_material:
                        optimized_transitions += 1
                    prev_material = order["material_code"]

                avg_setup_energy = 50
                energy_saved = (original_transitions - optimized_transitions) * avg_setup_energy

                savings_col1, savings_col2 = st.columns(2)
                with savings_col1:
                    reduction_pct = (
                        (original_transitions - optimized_transitions) / original_transitions * 100
                        if original_transitions > 0
                        else 0
                    )
                    st.metric(
                        "Reduced Transitions",
                        f"{original_transitions} → {optimized_transitions}",
                        f"-{reduction_pct:.0f}%",
                    )
                with savings_col2:
                    energy_pct = (
                        energy_saved / (original_transitions * avg_setup_energy) * 100
                        if original_transitions > 0
                        else 0
                    )
                    st.metric("Energy Saved", f"{energy_saved:.0f} kWh", f"-{energy_pct:.0f}%")


__all__ = [
    "DORMANT_LEGACY_HELPER_NAMES",
    "MODULE_BOUNDARY_NOTE",
    "load_data",
    "show_etl_page",
    "show_optimization_page",
    "show_overview_page",
    "show_team_performance_page",
]
