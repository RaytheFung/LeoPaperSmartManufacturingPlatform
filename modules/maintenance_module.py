"""
Maintenance evidence page backed by existing maintenance tables.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from core.canonical_energy_reader import CanonicalEnergyReader
from core.maintenance_evidence import (
    RECENT_HISTORY_LIMIT,
    MaintenanceEvidenceReader,
    format_maintenance_timestamp,
)
from core.maintenance_integration import integrate_maintenance_with_etl
from core.runtime_capabilities import suppress_write_controls
from core.runtime_mode import normalize_runtime_mode
from core.runtime_paths import get_database_path
from core.ui_utils import (
    build_stat_card,
    build_surface_card,
    load_custom_css,
    render_surface_card,
    section_shell,
)


def render_maintenance_page(db_path=None, runtime_mode: str = "standard"):
    """Render the maintenance evidence page."""
    try:
        load_custom_css()
    except Exception:
        pass

    db_path = str(db_path or get_database_path())
    evidence_reader = MaintenanceEvidenceReader(db_path)
    canonical_energy_reader = CanonicalEnergyReader(db_path)
    snapshot = evidence_reader.build_coverage_snapshot()
    read_only_runtime = suppress_write_controls(runtime_mode)

    st.title("🔧 Maintenance Evidence & Coverage")
    st.markdown(
        "Read-only maintenance evidence from the existing maintenance tables. "
        "This page shows storage coverage, machine-level history, and supporting operational visuals "
        "without claiming a predictive-maintenance model, solver, or scheduling engine."
    )
    st.caption(
        "Primary evidence comes from `maintenance_records` and related maintenance tables. "
        "Compact maintenance context is reused on `🤖 Efficiency Prediction & Governance` and "
        "`🎯 Operational Decision Support` without changing their ranking logic."
    )
    if read_only_runtime:
        st.info(
            "Demo read-only mode is active. Evidence and browse surfaces stay available, while upload/integration controls are hidden."
            if normalize_runtime_mode(runtime_mode) == "demo_readonly"
            else "Pilot review mode is active. Evidence and browse surfaces stay available, while upload/integration controls are hidden."
        )

    _render_status_banner(snapshot, runtime_mode=runtime_mode)
    _render_coverage_snapshot(snapshot)
    _render_machine_evidence_lookup(evidence_reader)
    _render_supporting_visuals(evidence_reader)

    with st.expander(
        "Supporting Evidence: Observed Energy Intensity vs Maintenance Age",
        expanded=False,
    ):
        _render_energy_context(canonical_energy_reader)

    if snapshot["legacy_risk_rows"] > 0:
        with st.expander(
            "Reference & Audit: Legacy/Admin Maintenance Risk View",
            expanded=False,
        ):
            _render_legacy_risk_reference(db_path)

    with st.expander("Admin / Details", expanded=False):
        if read_only_runtime:
            st.caption(
                "Browse stays available in demo read-only mode. Upload/integration controls are hidden to keep the shell read-only."
                if normalize_runtime_mode(runtime_mode) == "demo_readonly"
                else "Browse stays available in pilot review mode. Upload/integration controls are hidden to keep defended-core surfaces read-only."
            )
            _render_browse_records_tab(evidence_reader, db_path)
        else:
            st.caption(
                "Upload and raw browsing stay available for operational work, but the reviewer-facing "
                "story is the evidence contract above."
            )
            upload_tab, browse_tab = st.tabs(["📤 Upload & Integration", "🔍 Browse Records"])
            with upload_tab:
                _render_upload_and_integration_controls(db_path, snapshot)
            with browse_tab:
                _render_browse_records_tab(evidence_reader, db_path)


def _render_status_banner(snapshot: dict[str, object], *, runtime_mode: str = "standard") -> None:
    total_records = int(snapshot["records_stored"])
    integrated_machines = int(snapshot["integrated_machine_count"])
    total_three_way_matches = int(snapshot["total_three_way_matches"])
    months_covered_count = int(snapshot["months_covered_count"])
    read_only_runtime = suppress_write_controls(runtime_mode)

    if total_records <= 0:
        if read_only_runtime:
            st.warning(
                "No maintenance records are stored yet. Demo read-only mode keeps upload/integration controls hidden."
                if normalize_runtime_mode(runtime_mode) == "demo_readonly"
                else "No maintenance records are stored yet. Pilot review mode keeps upload/integration controls hidden."
            )
        else:
            st.warning(
                "No maintenance records are stored yet. Upload records in `Admin / Details` to start "
                "evidence coverage."
            )
    elif integrated_machines <= 0:
        st.warning(
            "Maintenance records are stored, but no machine-linked evidence is currently available "
            "on the canonical machine set."
        )
    else:
        if total_three_way_matches > 0:
            coverage_text = (
                f"{integrated_machines} of {total_three_way_matches} canonical machines have linked history"
            )
        else:
            coverage_text = f"{integrated_machines} canonical machines have linked history"
        st.success(
            f"Maintenance evidence is available from stored records across {months_covered_count} months. "
            f"{coverage_text}."
        )

    st.caption(
        "Legacy maintenance-risk outputs and the maintenance-age energy curve remain supporting evidence only. "
        "They do not change the page-level coverage status."
    )


def _render_coverage_snapshot(snapshot: dict[str, object]) -> None:
    with section_shell(
        "Maintenance Coverage Snapshot",
        (
            "Current storage and linkage coverage from the existing maintenance tables. "
            "These cards make stored scope explicit before any machine-level lookup."
        ),
        eyebrow="First-Screen Evidence",
    ):
        months_secondary = "No stored month labels yet."
        if snapshot["months_covered_count"] > 0:
            months_secondary = (
                f"{snapshot['earliest_month']} -> {snapshot['latest_month']}"
                if snapshot["earliest_month"] and snapshot["latest_month"]
                else "Chronological month-year parsing applied to stored labels."
            )

        coverage_ratio = snapshot["integration_coverage_ratio"]
        coverage_primary = "n/a"
        coverage_secondary = "No canonical machine denominator is available."
        if coverage_ratio is not None:
            coverage_primary = f"{float(coverage_ratio) * 100:.1f}%"
            coverage_secondary = (
                f"{int(snapshot['integrated_machine_count']):,} of "
                f"{int(snapshot['total_three_way_matches']):,} canonical machines currently have matched history."
            )

        cards = [
            build_stat_card(
                "Stored Records",
                snapshot["records_stored"],
                compact=False,
                primary_decimals=0,
                full_decimals=0,
                none_secondary="No maintenance rows are stored yet.",
            ),
            build_stat_card(
                "Matched Records",
                snapshot["matched_records_stored"],
                compact=False,
                primary_decimals=0,
                full_decimals=0,
                none_secondary="No machine-linked maintenance rows are stored yet.",
            ),
            build_stat_card(
                "Integrated Machines",
                snapshot["integrated_machine_count"],
                compact=False,
                primary_decimals=0,
                full_decimals=0,
                none_secondary="No canonical machines currently have linked maintenance history.",
            ),
            build_surface_card(
                "Canonical Coverage",
                coverage_primary,
                coverage_secondary,
            ),
            build_surface_card(
                "Months Covered",
                f"{int(snapshot['months_covered_count']):,}",
                months_secondary,
            ),
            build_surface_card(
                "Latest Stored Event",
                str(snapshot["latest_maintenance_datetime_label"]),
                "Latest stored maintenance transaction across all current maintenance rows.",
            ),
        ]
        _render_card_grid(cards, columns=3)


def _render_machine_evidence_lookup(evidence_reader: MaintenanceEvidenceReader) -> None:
    machine_catalog = evidence_reader.build_machine_catalog()

    with section_shell(
        "Machine Evidence Lookup",
        (
            "Select one machine to compare all-time history with the readable recent-history window. "
            "Total-event and recent-window contracts are shown separately and labeled explicitly."
        ),
        eyebrow="Machine-Level Evidence",
    ):
        if machine_catalog.empty:
            st.info(
                "No machine-linked maintenance history is available yet. Upload records and complete "
                "matching to unlock machine evidence."
            )
            return

        option_labels = [
            (
                f"{row['machine_id']} ({int(row['total_events']):,} total events"
                f" | latest {row['latest_maintenance_datetime_label']})"
            )
            for _, row in machine_catalog.iterrows()
        ]
        selected_index = st.selectbox(
            "Select machine",
            options=range(len(option_labels)),
            format_func=lambda index: option_labels[index],
            index=0,
        )
        selected_machine_id = str(machine_catalog.iloc[int(selected_index)]["machine_id"])
        evidence = evidence_reader.build_machine_evidence(
            selected_machine_id,
            recent_window_limit=RECENT_HISTORY_LIMIT,
        )

        cards = [
            build_stat_card(
                "Total Events (All Time)",
                evidence["all_time_event_count"],
                compact=False,
                primary_decimals=0,
                full_decimals=0,
            ),
            build_stat_card(
                "Recent Events Shown",
                evidence["recent_window_event_count"],
                compact=False,
                primary_decimals=0,
                full_decimals=0,
                none_secondary="No recent history window is available.",
            ),
            build_surface_card(
                "PM Ratio (All Time)",
                _format_ratio_percent(evidence["pm_ratio_all_time"]),
                "PM rows divided by all stored matched events for this machine.",
            ),
            build_surface_card(
                "PM Ratio (Recent Window)",
                _format_ratio_percent(evidence["pm_ratio_recent_window"]),
                f"PM rows within the latest {int(evidence['recent_window_event_count']):,} visible events.",
            ),
            build_surface_card(
                "Latest Work Order Type",
                str(evidence["latest_work_order_type"] or "n/a"),
                f"Latest maintenance: {evidence['latest_maintenance_datetime_label']}",
            ),
            build_surface_card(
                "Days Since Last Maintenance",
                _format_nullable_int(evidence["days_since_last_maintenance"]),
                (
                    "Current recency from the latest stored maintenance event."
                    if evidence["days_since_last_maintenance"] is not None
                    else "No dated maintenance event is available for recency."
                ),
            ),
            build_surface_card(
                "Months Covered",
                f"{int(evidence['months_covered_count']):,}",
                _build_month_range_label(evidence["months_covered"]),
            ),
        ]
        _render_card_grid(cards, columns=4)

        st.caption(
            f"{evidence['history_window_note']} Showing {int(evidence['recent_window_event_count']):,} "
            f"of {int(evidence['all_time_event_count']):,} total events."
        )

        st.markdown("#### Most Recent Maintenance Window")
        history_df = evidence["recent_history_df"].copy()
        history_df["maintenance_datetime"] = history_df["maintenance_datetime"].apply(
            format_maintenance_timestamp
        )
        history_df["days_since_previous"] = pd.to_numeric(
            history_df["days_since_previous"],
            errors="coerce",
        ).round(2)
        st.dataframe(
            history_df.rename(
                columns={
                    "maintenance_datetime": "Date/Time",
                    "work_order": "Work Order",
                    "work_order_type": "Type",
                    "material_code": "Material",
                    "month_year": "Month",
                    "days_since_previous": "Days Since Previous",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )


def _render_supporting_visuals(evidence_reader: MaintenanceEvidenceReader) -> None:
    monthly_df = evidence_reader.build_monthly_record_counts()
    work_order_df = evidence_reader.build_work_order_distribution()

    with section_shell(
        "Supporting Visuals",
        (
            "These visuals summarize the same stored maintenance evidence at platform level. "
            "They support presentation context but do not replace the machine evidence contract above."
        ),
        eyebrow="Operational Context",
    ):
        if monthly_df.empty and work_order_df.empty:
            st.info("No maintenance visuals are available until records are stored.")
            return

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Records by Month")
            if monthly_df.empty:
                st.info("No month-level record counts are available yet.")
            else:
                fig = px.bar(
                    monthly_df,
                    x="month_year",
                    y="count",
                    title="Stored maintenance records by month",
                    labels={"month_year": "Month", "count": "Records"},
                )
                fig.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Records",
                    xaxis_tickangle=-45,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Work Order Type Mix")
            if work_order_df.empty:
                st.info("No work-order mix is available yet.")
            else:
                fig = px.pie(
                    work_order_df,
                    values="count",
                    names="work_order_type",
                    title="Distribution of stored maintenance types",
                    hole=0.45,
                )
                st.plotly_chart(fig, use_container_width=True)


def _render_energy_context(canonical_energy_reader: CanonicalEnergyReader) -> None:
    st.caption(
        "This is an observed weighted energy-intensity profile from canonical `fact_machine_hour` rows. "
        "It remains supporting context only and should not be read as a predictive-maintenance rule."
    )
    try:
        bucket_stats = canonical_energy_reader.build_maintenance_efficiency_curve()
    except Exception as exc:
        st.info(f"Maintenance-age energy context is unavailable: {exc}")
        return

    if bucket_stats.empty:
        st.info(
            "Canonical `fact_machine_hour` does not yet have enough eligible positive-good-qty rows "
            "with maintenance recency to build this curve."
        )
        return

    fig = px.line(
        bucket_stats,
        x="bucket",
        y="weighted_kwh_per_good_unit",
        markers=True,
        title="Observed weighted energy intensity by maintenance-age bucket",
        hover_data={
            "row_count": True,
            "total_good_qty": ":,.0f",
            "total_energy_kwh": ":,.1f",
        },
        labels={
            "bucket": "Hours Since Maintenance",
            "weighted_kwh_per_good_unit": "Weighted kWh / Good Unit",
            "row_count": "Rows",
            "total_good_qty": "Good Qty",
            "total_energy_kwh": "Energy (kWh)",
        },
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info(
        "Eligibility remains explicit: maintenance recency present, `good_qty > 0`, `energy_total_kwh IS NOT NULL`, "
        "`0 < kwh_per_good_unit < 20`, and at least 20 rows per bucket."
    )


def _render_legacy_risk_reference(db_path: str) -> None:
    st.caption(
        "This is a legacy/admin risk table kept for reference only. It does not drive the main "
        "maintenance evidence contract and is not reused to score ML or Optimization."
    )

    conn = sqlite3.connect(db_path)
    try:
        risk_df = pd.read_sql_query(
            """
            SELECT
                machine_id,
                date,
                days_since_last_maintenance,
                maintenance_count_30d,
                maintenance_count_90d,
                failure_risk_score,
                recommended_action
            FROM maintenance_ml_features
            ORDER BY failure_risk_score DESC, date DESC, machine_id ASC
            LIMIT 20
            """,
            conn,
        )
    except Exception as exc:
        conn.close()
        st.info(f"Legacy/admin maintenance risk view is unavailable: {exc}")
        return
    finally:
        if conn:
            conn.close()

    if risk_df.empty:
        st.info("No legacy/admin maintenance risk rows are stored.")
        return

    risk_df["date"] = risk_df["date"].apply(format_maintenance_timestamp)
    risk_df["failure_risk_score"] = pd.to_numeric(
        risk_df["failure_risk_score"],
        errors="coerce",
    ).round(2)
    st.dataframe(
        risk_df.rename(
            columns={
                "machine_id": "Machine",
                "date": "As Of",
                "days_since_last_maintenance": "Days Since Last Maintenance",
                "maintenance_count_30d": "Count 30d",
                "maintenance_count_90d": "Count 90d",
                "failure_risk_score": "Legacy Risk Score",
                "recommended_action": "Recommended Action",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def _render_upload_and_integration_controls(
    db_path: str,
    snapshot: dict[str, object],
) -> None:
    st.markdown("#### Upload Maintenance Records")
    st.caption(
        "This is the operational upload path. Reviewer-facing coverage and machine evidence remain above."
    )
    st.info(
        f"Current stored records: {int(snapshot['records_stored']):,} | "
        f"matched records: {int(snapshot['matched_records_stored']):,} | "
        f"months covered: {int(snapshot['months_covered_count']):,}"
    )
    st.markdown(
        """
        Upload monthly maintenance Excel files with these expected columns:
        - 工單 (Work Order)
        - 工單類型 (PM/AM/CM/EM)
        - 資產 (Asset ID - MES format)
        - 資產老編號 (Old Asset ID - Energy format)
        - 交易日期 (Transaction Date)
        - 物料編碼 (Material Code)
        """
    )

    uploaded_file = st.file_uploader(
        "Choose Maintenance Excel File",
        type=["xlsx", "xls"],
        help="Upload monthly maintenance records for analysis",
    )

    if uploaded_file is None:
        return

    month_col1, month_col2 = st.columns(2)
    with month_col1:
        month_options = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        selected_month = st.selectbox("Select Month", month_options, index=5)
    with month_col2:
        selected_year = st.number_input(
            "Select Year",
            min_value=2024,
            max_value=2026,
            value=2025,
        )

    month_year = f"{selected_month} {selected_year}"
    upload_mode = st.radio(
        "Upload Mode",
        ["Replace Month Data", "Append New Records"],
        help=(
            "Replace removes existing rows for any month found in the uploaded file before writing the new rows. "
            "Append adds only new unique rows."
        ),
        horizontal=True,
    )

    if upload_mode == "Replace Month Data":
        st.warning(
            "Replace mode will remove existing rows for every month found in the uploaded file, "
            "then write the new rows for those months only."
        )
    else:
        st.info("Append mode keeps existing rows and skips duplicates using a composite-key check.")

    if not st.button("Process Maintenance Data", type="primary"):
        return

    temp_path = Path("temp_uploads") / uploaded_file.name
    temp_path.parent.mkdir(exist_ok=True)

    try:
        with open(temp_path, "wb") as handle:
            handle.write(uploaded_file.getbuffer())

        with st.spinner(f"Processing maintenance data for {month_year}..."):
            result = integrate_maintenance_with_etl(str(temp_path), month_year)

        if not result:
            st.error("Failed to process maintenance data. Please check the file format.")
            return

        maintenance_df = result["maintenance_records"]
        unique_months = sorted(set(maintenance_df["month_year"].dropna().astype(str).tolist()))

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            st.info(f"File contains data for: {', '.join(unique_months)}")

            if upload_mode == "Replace Month Data":
                total_deleted = 0
                for month in unique_months:
                    cursor.execute(
                        "DELETE FROM maintenance_records WHERE month_year = ?",
                        (month,),
                    )
                    total_deleted += cursor.rowcount
                if total_deleted > 0:
                    st.info(
                        f"Replaced {total_deleted:,} existing records across {len(unique_months):,} months."
                    )
                maintenance_df.to_sql("maintenance_records", conn, if_exists="append", index=False)
            else:
                existing_df = pd.read_sql_query(
                    (
                        "SELECT work_order, transaction_date, asset_id, material_code "
                        "FROM maintenance_records "
                        f"WHERE month_year IN ({','.join(['?' for _ in unique_months])})"
                    ),
                    conn,
                    params=tuple(unique_months),
                )
                existing_df["composite_key"] = (
                    existing_df["work_order"].astype(str)
                    + "_"
                    + existing_df["transaction_date"].astype(str)
                    + "_"
                    + existing_df["asset_id"].fillna("").astype(str)
                    + "_"
                    + existing_df["material_code"].fillna("").astype(str)
                )
                maintenance_df = maintenance_df.copy()
                maintenance_df["composite_key"] = (
                    maintenance_df["work_order"].astype(str)
                    + "_"
                    + maintenance_df["transaction_date"].astype(str)
                    + "_"
                    + maintenance_df["asset_id"].fillna("").astype(str)
                    + "_"
                    + maintenance_df["material_code"].fillna("").astype(str)
                )
                existing_keys = set(existing_df["composite_key"].tolist())
                new_records = maintenance_df[~maintenance_df["composite_key"].isin(existing_keys)].copy()
                new_records = new_records.drop(columns=["composite_key"])
                if new_records.empty:
                    st.warning("All uploaded rows already exist. No new records were added.")
                else:
                    new_records.to_sql("maintenance_records", conn, if_exists="append", index=False)
                    st.info(
                        f"Added {len(new_records):,} new rows; "
                        f"{len(maintenance_df) - len(new_records):,} duplicates were skipped."
                    )

            if result["metrics"] is not None:
                result["metrics"].to_sql("maintenance_summary", conn, if_exists="replace", index=False)
            if result["predictions"] is not None:
                result["predictions"].to_sql(
                    "maintenance_ml_features",
                    conn,
                    if_exists="replace",
                    index=False,
                )
            conn.commit()
        finally:
            conn.close()

        total_records = len(maintenance_df)
        matched_records = int((maintenance_df["is_three_way_match"] == 1).sum())
        match_rate = (matched_records / total_records * 100.0) if total_records > 0 else 0.0
        st.success(
            f"Processed {total_records:,} rows. Matched rows: {matched_records:,} ({match_rate:.1f}%)."
        )
        st.rerun()
    except Exception as exc:
        st.error(f"Error processing file: {exc}")
        st.exception(exc)
    finally:
        temp_path.unlink(missing_ok=True)


def _render_browse_records_tab(
    evidence_reader: MaintenanceEvidenceReader,
    db_path: str,
) -> None:
    st.markdown("#### Browse Maintenance Records")
    st.caption(
        "Month options use the same chronological month-year parser as the main coverage visuals."
    )

    conn = sqlite3.connect(db_path)
    try:
        if not _table_exists(conn, "maintenance_records"):
            st.info("No maintenance records are stored yet.")
            return

        month_options = evidence_reader.get_available_months()
        machines_df = pd.read_sql_query(
            """
            SELECT DISTINCT machine_id
            FROM maintenance_records
            WHERE machine_id IS NOT NULL
              AND trim(machine_id) <> ''
            ORDER BY machine_id ASC
            """,
            conn,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            selected_months = st.multiselect(
                "Filter by Month",
                options=month_options,
                default=None,
            )
        with col2:
            selected_machine = st.selectbox(
                "Filter by Machine",
                options=["All"] + machines_df["machine_id"].tolist(),
                index=0,
            )
        with col3:
            selected_type = st.selectbox(
                "Filter by Type",
                options=["All", "AM", "CM", "PM", "EM", "EV", "OP", "SA"],
                index=0,
            )

        query = "SELECT * FROM maintenance_records WHERE 1=1"
        params: list[object] = []
        if selected_months:
            placeholders = ",".join(["?" for _ in selected_months])
            query += f" AND month_year IN ({placeholders})"
            params.extend(selected_months)
        if selected_machine != "All":
            query += " AND machine_id = ?"
            params.append(selected_machine)
        if selected_type != "All":
            query += " AND work_order_type = ?"
            params.append(selected_type)
        query += " ORDER BY transaction_date DESC LIMIT 100"

        records_df = pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()

    if records_df.empty:
        st.warning("No records matched the current filters.")
        return

    display_df = records_df.loc[
        :,
        [
            "machine_id",
            "transaction_date",
            "work_order",
            "work_order_type",
            "material_code",
            "month_year",
            "is_three_way_match",
        ],
    ].copy()
    display_df["transaction_date"] = display_df["transaction_date"].apply(format_maintenance_timestamp)
    display_df["is_three_way_match"] = display_df["is_three_way_match"].map({1: "Yes", 0: "No"})

    st.info(f"Showing {len(display_df):,} records (limited to the latest 100 rows).")
    st.dataframe(
        display_df.rename(
            columns={
                "machine_id": "Machine",
                "transaction_date": "Date/Time",
                "work_order": "Work Order",
                "work_order_type": "Type",
                "material_code": "Material",
                "month_year": "Month",
                "is_three_way_match": "Matched",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    csv_data = display_df.to_csv(index=False)
    st.download_button(
        label="Download filtered records as CSV",
        data=csv_data,
        file_name=f"maintenance_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def _render_card_grid(cards: list[dict[str, str]], *, columns: int) -> None:
    for start_index in range(0, len(cards), columns):
        row_cards = cards[start_index : start_index + columns]
        row_columns = st.columns(columns)
        for column, card in zip(row_columns, row_cards):
            with column:
                render_surface_card(card)


def _format_ratio_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _format_nullable_int(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def _build_month_range_label(months: list[str]) -> str:
    if not months:
        return "No stored month labels for this machine."
    if len(months) == 1:
        return months[0]
    return f"{months[0]} -> {months[-1]}"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


__all__ = ["render_maintenance_page"]
