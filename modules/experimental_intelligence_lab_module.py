from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from core.experimental_maintenance_prototype import (
    build_predictive_maintenance_export_artifacts,
    build_predictive_maintenance_prototype,
)
from core.experimental_scheduling import (
    build_scheduling_export_artifacts,
    build_real_seeded_queue,
    get_active_saved_artifact_binding,
    get_available_months,
    get_real_input_queue_contract,
    load_real_input_queue,
    run_constraint_aware_scheduling,
)
from core.runtime_capabilities import (
    experimental_exports_are_allowed,
    experimental_manual_stress_test_is_allowed,
    experimental_real_input_upload_is_allowed,
    experimental_route_is_exposed,
    get_runtime_capabilities,
)
from core.runtime_mode import normalize_runtime_mode
from core.runtime_paths import get_database_path
from core.ui_utils import (
    build_surface_card,
    load_custom_css,
    render_surface_card,
    section_shell,
)


def render_experimental_intelligence_lab(db_path=None, runtime_mode: str = "standard"):
    try:
        load_custom_css()
    except Exception:
        pass

    capabilities = get_runtime_capabilities(runtime_mode)
    normalized_mode = normalize_runtime_mode(runtime_mode)
    if not experimental_route_is_exposed(normalized_mode):
        st.warning(
            "The experimental route is hidden in the current runtime profile. "
            "Use `pilot_review` or `standard` mode for experimental access."
        )
        return

    active_artifact_binding = get_active_saved_artifact_binding()
    active_artifact_bundle_label = _format_active_artifact_bundle_label(active_artifact_binding)

    st.title("🧪 Experimental Intelligence Lab")
    st.markdown(
        "Internal-landing experimental flagship lane that reuses the current canonical backbone, "
        "maintenance evidence, and active saved live artifacts as read-only inputs. "
        "This page stays separate from the defended core platform routes and remains non-defended for production claims."
    )
    st.warning(
        "Internal-landing experimental flagship lane only. Read-only. Non-defended for production claims. "
        "No DB writes. No artifact promotion. No solver claim. No predictive-maintenance production claim."
    )
    st.caption(
        f"Active saved live artifacts currently resolve to `{active_artifact_bundle_label}` through repo-local live model paths."
    )
    st.caption(
        "Prototype provenance labels stay explicit: `real data`, `real-seeded synthetic queue`, "
        "`weak-label model`, and `fallback evidence score`."
    )
    if normalized_mode == "pilot_review":
        st.info(
            "Pilot review mode is active. Defended-core write controls stay hidden, while this experimental lane "
            "keeps real-input review, export, and provenance surfaces available for pilot evaluation."
        )

    available_months = get_available_months(db_path=db_path)
    if not available_months:
        st.warning("Canonical month slices are not available yet for the experimental lab.")
        return

    selected_month = st.selectbox(
        "Anchor month for current-state view",
        available_months,
        index=0,
        help=(
            "This month anchors the current machine pool, current cost proxy, and latest risk slice shown on this page. "
            "It is not the full historical support or weak-label training boundary."
        ),
    )
    scope_summary = _build_route_scope_summary(selected_month, db_path=db_path)
    st.caption(
        "The anchor month sets the current machine pool and latest month slice shown on each prototype. "
        "Historical support and weak-label training use broader real history."
    )

    top_cards = [
        build_surface_card(
            "Current-State Anchor",
            selected_month,
            f"Current machine pool and current-state slice use canonical rows from {scope_summary['anchor_exact_window_label']}.",
        ),
        build_surface_card(
            "Historical Support / Training Scope",
            scope_summary["history_month_window_label"],
            (
                f"Scheduling support reads canonical history through {scope_summary['history_end_label']}. "
                f"Maintenance snapshots use the same anchor-bounded history, with weak-label look-ahead supported by "
                f"stored maintenance events through {scope_summary['maintenance_event_end_label']}."
            ),
        ),
        build_surface_card(
            "Scheduling Queue Provenance",
            "Real-seeded synthetic queue",
            "Pending jobs are seeded from selected-month material/task/qty patterns while compatibility, energy cost proxy, and maintenance evidence stay real.",
        ),
        build_surface_card(
            "Runtime Profile",
            str(capabilities["experimental_profile_label"]),
            (
                "Experimental route exposure, real-input review, and export availability are now governed centrally "
                f"for runtime mode `{normalized_mode}`."
            ),
        ),
        build_surface_card(
            "Maintenance Prototype Mode",
            "Weak-label model or fallback evidence score",
            "Current risk rows stay anchored to the selected month; training uses actual machine-day history and real maintenance-event horizons rather than synthetic labels.",
        ),
    ]
    _render_card_grid(top_cards, columns=5)

    scheduling_tab, maintenance_tab = st.tabs(
        [
            "Constraint-Aware Scheduling Prototype",
            "Predictive Maintenance Prototype",
        ]
    )

    with scheduling_tab:
        _render_scheduling_tab(selected_month, scope_summary, runtime_mode=normalized_mode, db_path=db_path)

    with maintenance_tab:
        _render_maintenance_tab(selected_month, scope_summary, runtime_mode=normalized_mode, db_path=db_path)


def _render_scheduling_tab(
    selected_month: str,
    scope_summary: dict[str, object],
    *,
    runtime_mode: str,
    db_path=None,
) -> None:
    with section_shell(
        "Constraint-Aware Scheduling Prototype",
        (
            "This prototype anchors the current machine pool to the selected month, seeds a small pending queue from "
            "real selected-month distributions, and scores assignments with historical support plus maintenance evidence "
            "through the anchor month. It is not a live MES/ERP queue or a production scheduling engine."
        ),
        eyebrow="Experimental Prototype",
    ):
        real_input_allowed = experimental_real_input_upload_is_allowed(runtime_mode)
        export_allowed = experimental_exports_are_allowed(runtime_mode)
        manual_stress_test_allowed = experimental_manual_stress_test_is_allowed(runtime_mode)
        controls_col1, controls_col2 = st.columns(2)
        with controls_col1:
            queue_size = st.slider("Queue size", min_value=5, max_value=8, value=6, step=1)
        with controls_col2:
            max_jobs_per_machine = st.slider("Max jobs / machine", min_value=1, max_value=3, value=2, step=1)

        queue_mode = "real_seeded"
        queue_input_payload = None
        queue_provenance = "Real-seeded synthetic queue"
        queue_provenance_note = (
            "Default pending jobs are seeded from real selected-month material/task/qty distributions because no live "
            "ERP/MES future order book is stored in the current platform."
        )

        if real_input_allowed:
            contract = get_real_input_queue_contract()
            with st.expander("Preferred pilot input: Pending queue upload", expanded=(runtime_mode == "pilot_review")):
                st.caption(
                    "For pilot review, prefer a narrow real pending-queue file over manual editing. The file is validated "
                    "read-only and never written into the platform database."
                )
                st.markdown(
                    "Required columns: "
                    + ", ".join(f"`{column}`" for column in contract["required_columns"])
                )
                st.markdown(
                    "Optional columns: "
                    + ", ".join(f"`{column}`" for column in contract["optional_columns"])
                )
                uploaded_file = st.file_uploader(
                    "Upload pending queue CSV/XLSX",
                    type=["csv", "xlsx", "xls"],
                    help="Preferred pilot-review path for bringing in a small real pending queue without writing the DB.",
                )
                if uploaded_file is not None:
                    queue_input_payload = load_real_input_queue(
                        uploaded_file.getvalue(),
                        file_name=uploaded_file.name,
                        month_year=selected_month,
                    )
                    if queue_input_payload["blocked"]:
                        st.warning(queue_input_payload["message"])
                        return
                    queue_mode = "real_input"
                    queue_provenance = "Real-input pilot queue"
                    queue_provenance_note = (
                        f"Validated from `{queue_input_payload['input_summary']['file_name']}` with "
                        f"{queue_input_payload['input_summary']['accepted_rows']} accepted rows. "
                        "No queue rows were written back into the platform."
                    )
                    st.success(
                        f"Accepted {queue_input_payload['input_summary']['accepted_rows']} of "
                        f"{queue_input_payload['input_summary']['uploaded_rows']} uploaded rows for pilot review."
                    )
                    st.dataframe(queue_input_payload["queue_df"], hide_index=True, use_container_width=True)

        manual_queue_enabled = False
        manual_queue_df = None
        if manual_stress_test_allowed:
            with st.expander("Stress-test mode: Manual demo queue", expanded=False):
                st.caption(
                    "Use manual input only when you want to override the default path for a narrow stress test. "
                    "The route still stays read-only."
                )
                manual_queue_enabled = st.checkbox(
                    "Use manual demo queue instead of the preferred queue path",
                    value=False,
                )
                if manual_queue_enabled:
                    seed_payload = build_real_seeded_queue(selected_month, queue_size=queue_size, db_path=db_path)
                    if seed_payload["blocked"]:
                        st.warning(seed_payload["message"])
                        return
                    editable_df = seed_payload["queue_df"][
                        [
                            "job_id",
                            "preferred_machine_family",
                            "material_code",
                            "task_name",
                            "task_difficulty",
                            "quantity",
                            "urgency_label",
                            "team_leader",
                            "team_size",
                            "hour_of_day",
                        ]
                    ].copy()
                    manual_queue_df = st.data_editor(
                        editable_df,
                        hide_index=True,
                        use_container_width=True,
                        num_rows="fixed",
                    )
                    queue_mode = "manual"
                    queue_provenance = "Manual demo queue (stress-test)"
                    queue_provenance_note = (
                        "Manual queue is a stress-test override only. Compatibility, maintenance evidence, and scoring remain read-only."
                    )
        st.caption(
            "No live ERP/MES future order book is stored in the current platform, so the prototype defaults to a "
            "real-seeded synthetic pending queue while keeping machine, energy, support, and maintenance evidence real."
        )

        scope_cards = [
            build_surface_card(
                "Current-State Anchor",
                selected_month,
                f"Current machine pool and selected-month cost proxy use {scope_summary['anchor_exact_window_label']}.",
            ),
            build_surface_card(
                "Historical Support Window",
                scope_summary["history_month_window_label"],
                f"Compatibility tiers count canonical history from {scope_summary['history_exact_window_label']} through the anchor month.",
            ),
            build_surface_card(
                "Queue Provenance",
                queue_provenance,
                queue_provenance_note,
            ),
            build_surface_card(
                "Machine Pool Scope",
                f"{scope_summary['anchor_machine_count']} machines",
                "Candidate machines come from the anchor month only; support scores then expand to broader history.",
            ),
        ]
        _render_card_grid(scope_cards, columns=4)

        payload = run_constraint_aware_scheduling(
            selected_month,
            queue_size=queue_size,
            max_jobs_per_machine=max_jobs_per_machine,
            queue_mode=queue_mode,
            manual_queue_df=(
                queue_input_payload["queue_df"]
                if queue_mode == "real_input" and queue_input_payload is not None
                else manual_queue_df
            ),
            db_path=db_path,
        )
        if payload["blocked"]:
            st.warning(payload["message"])
            return

        if payload.get("message"):
            st.info(payload["message"])

        optimized_score = (
            float(payload["optimized_schedule_df"]["total_score"].fillna(0.0).sum())
            if not payload["optimized_schedule_df"].empty
            else 0.0
        )
        naive_score = (
            float(payload["naive_schedule_df"]["total_score"].fillna(0.0).sum())
            if not payload["naive_schedule_df"].empty
            else 0.0
        )
        result_cards = [
            build_surface_card(
                "Queue Rows",
                str(len(payload["queue_df"])),
                "Prototype horizon stays intentionally small for deterministic review.",
            ),
            build_surface_card(
                "Assigned Jobs",
                str(len(payload["optimized_schedule_df"])),
                "Optimized schedule rows placed inside the current prototype horizon.",
            ),
            build_surface_card(
                "Optimized Composite Score",
                f"{optimized_score:.4f}",
                "Lower is better on the prototype objective.",
            ),
            build_surface_card(
                "Naive Composite Score",
                f"{naive_score:.4f}",
                "Shown as a transparent baseline rather than a production benchmark.",
            ),
        ]
        _render_card_grid(result_cards, columns=4)

        st.caption(
            "Predictor-backed scheduling scores use "
            f"`{_format_active_artifact_bundle_label(payload.get('active_artifact_binding') or {})}` "
            "through the current repo-local live artifact paths."
        )
        st.info(
            "Compatibility/support tiers come from historical canonical evidence through the anchor month, and "
            "maintenance penalties use stored maintenance evidence rather than synthetic data."
        )

        st.markdown(
            "#### Default Real-Seeded Queue"
            if not manual_queue_enabled
            else "#### Manual Stress-Test Queue"
        )
        st.dataframe(payload["queue_df"], hide_index=True, use_container_width=True)

        comparison_col1, comparison_col2 = st.columns(2)
        with comparison_col1:
            st.markdown("#### Naive Baseline Comparison")
            st.dataframe(payload["baseline_comparison_df"], hide_index=True, use_container_width=True)
        with comparison_col2:
            st.markdown("#### Score Breakdown")
            st.dataframe(payload["score_breakdown_df"], hide_index=True, use_container_width=True)

        st.markdown("#### Constraint Summary")
        st.dataframe(payload["constraint_summary_df"], hide_index=True, use_container_width=True)

        st.markdown("#### Feasible Assignment Candidates")
        st.dataframe(payload["feasible_assignment_df"], hide_index=True, use_container_width=True)

        schedule_view_df = payload["optimized_schedule_df"].merge(
            payload["queue_df"][
                ["job_id", "material_code", "task_name", "quantity", "urgency_label"]
            ],
            on="job_id",
            how="left",
        )
        st.markdown("#### Optimized Schedule")
        st.dataframe(schedule_view_df, hide_index=True, use_container_width=True)

        with st.expander("Reference & Audit: Naive schedule details", expanded=False):
            naive_view_df = payload["naive_schedule_df"].merge(
                payload["queue_df"][
                    ["job_id", "material_code", "task_name", "quantity", "urgency_label"]
                ],
                on="job_id",
                how="left",
            )
            st.dataframe(naive_view_df, hide_index=True, use_container_width=True)

        if payload["blocked_reasons_df"] is not None and not payload["blocked_reasons_df"].empty:
            with st.expander("Blocked / Excluded Reasons", expanded=False):
                st.dataframe(payload["blocked_reasons_df"], hide_index=True, use_container_width=True)

        st.caption(payload["swap_summary"])
        st.info(payload["optimization_note"])
        _render_scheduling_provenance_and_exports(
            payload,
            selected_month=selected_month,
            runtime_mode=runtime_mode,
            queue_provenance=queue_provenance,
            export_allowed=export_allowed,
        )


def _render_maintenance_tab(
    selected_month: str,
    scope_summary: dict[str, object],
    *,
    runtime_mode: str,
    db_path=None,
) -> None:
    with section_shell(
        "Predictive Maintenance Prototype",
        (
            "This prototype anchors the current risk table to the selected month, builds machine-day snapshots from "
            "broader canonical history through that anchor, trains a lightweight time-aware classifier only when weak "
            "labels are genuinely sufficient, and otherwise falls back to a transparent evidence score. "
            "It does not change the defended Maintenance route."
        ),
        eyebrow="Experimental Prototype",
    ):
        export_allowed = experimental_exports_are_allowed(runtime_mode)
        horizon_days = st.selectbox("Future maintenance horizon", options=[14, 7], index=0)
        payload = build_predictive_maintenance_prototype(
            selected_month,
            horizon_days=horizon_days,
            db_path=db_path,
        )
        if payload["blocked"]:
            st.warning(payload["message"])
            return

        st.info(
            "The selected month anchors the current-state risk view. Historical machine-day training uses broader real "
            "history through the anchor month, and weak labels are attached only when a real future maintenance window "
            "is observable from stored maintenance events."
        )
        maintenance_horizon_note = _build_maintenance_horizon_note(
            selected_month,
            scope_summary["maintenance_event_end_label"],
        )
        if maintenance_horizon_note:
            st.caption(maintenance_horizon_note)

        label_counts = payload["label_counts"]
        eval_summary = payload["eval_summary"]
        snapshot_df = payload["snapshot_df"].copy()
        labeled_df = snapshot_df[snapshot_df["label_available"] == 1].copy()
        latest_snapshot_date = _safe_timestamp(payload["scored_latest_df"]["snapshot_date"].max())
        mode_secondary = (
            f"Eval ROC AUC {eval_summary['eval_roc_auc']:.4f}, average precision {eval_summary['eval_average_precision']:.4f}."
            if payload["prototype_mode"] == "Weak-label model"
            and eval_summary["eval_roc_auc"] is not None
            and eval_summary["eval_average_precision"] is not None
            else payload["model_payload"].get("reason", "Used transparent fallback evidence scoring.")
        )

        st.markdown("#### Historical Training / Label Scope")
        training_cards = [
            build_surface_card(
                "Historical Snapshot Window",
                scope_summary["history_month_window_label"],
                f"Machine-day features span {scope_summary['history_exact_window_label']} through the anchor month.",
            ),
            build_surface_card(
                "Weak-Label Observation Scope",
                f"{label_counts['labeled_snapshots']:,} eligible snapshots",
                (
                    f"Real {horizon_days}-day look-ahead is available on "
                    f"{_format_exact_span(labeled_df['snapshot_date'].min(), labeled_df['snapshot_date'].max(), fallback='n/a')} "
                    f"using stored maintenance events through {scope_summary['maintenance_event_end_label']}."
                ),
            ),
            build_surface_card(
                "Prototype Mode",
                payload["prototype_mode"],
                mode_secondary,
            ),
            build_surface_card(
                "Class Counts",
                f"{label_counts['positive_labels']:,} / {label_counts['negative_labels']:,}",
                "Positive / negative weak labels from actual maintenance-event history.",
            ),
        ]
        _render_card_grid(training_cards, columns=4)

        st.markdown("#### Current-State Risk View")
        current_view_cards = [
            build_surface_card(
                "Current-State Anchor",
                selected_month,
                f"Latest machine snapshots inside {scope_summary['anchor_exact_window_label']} drive the risk table.",
            ),
            build_surface_card(
                "Latest Snapshot Date",
                latest_snapshot_date or "n/a",
                "One latest machine snapshot per machine inside the anchor month.",
            ),
            build_surface_card(
                "Machines Scored",
                str(len(payload["risk_table_df"])),
                "Current at-risk table rows shown for the anchor month.",
            ),
            build_surface_card(
                "Future Horizon",
                f"{payload['horizon_days']} days",
                "Audit columns mark whether an actual maintenance event was observed within this horizon.",
            ),
        ]
        _render_card_grid(current_view_cards, columns=4)

        st.markdown("#### Current-State At-Risk Machine Table")
        st.dataframe(payload["risk_table_df"], hide_index=True, use_container_width=True)

        selected_summary = payload["selected_machine_summary"]
        st.markdown("#### Selected Machine Evidence")
        detail_cards = [
            build_surface_card(
                "Machine",
                selected_summary["machine_id"],
                f"Latest snapshot in {selected_month}: {selected_summary['snapshot_date']}",
            ),
            build_surface_card(
                "Risk Score",
                f"{selected_summary['risk_score']:.4f}",
                f"Prototype band: {selected_summary['risk_band']}.",
            ),
            build_surface_card(
                "Days Since Maintenance",
                str(selected_summary["days_since_last_maintenance"] or 0),
                "Derived from canonical maintenance-age fields and/or actual event history.",
            ),
            build_surface_card(
                "Events In 30d",
                str(selected_summary["recent_events_count_30d"]),
                "Recent maintenance-event density from the stored maintenance tables.",
            ),
        ]
        _render_card_grid(detail_cards, columns=4)

        factors_col, history_col = st.columns(2)
        with factors_col:
            st.markdown("##### Top Evidence Factors")
            st.dataframe(payload["evidence_factors_df"], hide_index=True, use_container_width=True)
        with history_col:
            st.markdown("##### Recent Work-Order Context")
            recent_work_order_df = payload["recent_work_order_df"]
            if recent_work_order_df is None or recent_work_order_df.empty:
                st.info("No recent work-order context is available for the selected machine.")
            else:
                st.dataframe(recent_work_order_df, hide_index=True, use_container_width=True)

        with st.expander("Reference & Audit: Latest scored snapshot detail", expanded=False):
            scored_latest_df = payload["scored_latest_df"]
            selected_row_df = scored_latest_df[
                scored_latest_df["machine_id"] == selected_summary["machine_id"]
            ].copy()
            st.dataframe(selected_row_df, hide_index=True, use_container_width=True)

        st.info(payload["prototype_note"])
        _render_maintenance_provenance_and_exports(
            payload,
            selected_month=selected_month,
            runtime_mode=runtime_mode,
            export_allowed=export_allowed,
        )


def _render_scheduling_provenance_and_exports(
    payload: dict[str, object],
    *,
    selected_month: str,
    runtime_mode: str,
    queue_provenance: str,
    export_allowed: bool,
) -> None:
    st.markdown("#### Pilot Provenance & Export")
    provenance_cards = [
        build_surface_card(
            "Runtime Mode",
            runtime_mode,
            "Central runtime capability registry governs experimental exposure, real-input upload, export availability, and defended-core write suppression.",
        ),
        build_surface_card(
            "Input Provenance",
            queue_provenance,
            "The prototype keeps queue-source provenance explicit for every review/export handoff.",
        ),
        build_surface_card(
            "Export Availability",
            "Enabled" if export_allowed else "Hidden",
            "Pilot-review exports stay read-only and do not write the platform database.",
        ),
    ]
    _render_card_grid(provenance_cards, columns=3)
    if not export_allowed:
        st.caption("Scheduling exports are hidden in the current runtime mode.")
        return

    export_artifacts = build_scheduling_export_artifacts(
        payload,
        runtime_mode=runtime_mode,
        anchor_month=selected_month,
    )
    _render_export_download_block(
        "Scheduling exports",
        export_artifacts,
        file_prefix=f"scheduling_{selected_month.replace(' ', '_').lower()}",
    )


def _render_maintenance_provenance_and_exports(
    payload: dict[str, object],
    *,
    selected_month: str,
    runtime_mode: str,
    export_allowed: bool,
) -> None:
    st.markdown("#### Pilot Provenance & Export")
    provenance_cards = [
        build_surface_card(
            "Runtime Mode",
            runtime_mode,
            "Central runtime capability registry governs experimental exposure, real-input upload, export availability, and defended-core write suppression.",
        ),
        build_surface_card(
            "Current-State Risk View",
            selected_month,
            "The current machine risk table stays anchored to the selected month even when historical training support reaches further back.",
        ),
        build_surface_card(
            "Export Availability",
            "Enabled" if export_allowed else "Hidden",
            "Pilot-review exports stay read-only and do not write the platform database.",
        ),
    ]
    _render_card_grid(provenance_cards, columns=3)
    if not export_allowed:
        st.caption("Predictive-maintenance exports are hidden in the current runtime mode.")
        return

    export_artifacts = build_predictive_maintenance_export_artifacts(
        payload,
        runtime_mode=runtime_mode,
        anchor_month=selected_month,
    )
    _render_export_download_block(
        "Predictive-maintenance exports",
        export_artifacts,
        file_prefix=f"maintenance_{selected_month.replace(' ', '_').lower()}",
    )


def _render_export_download_block(
    heading: str,
    export_artifacts: dict[str, object],
    *,
    file_prefix: str,
) -> None:
    st.caption(
        f"{heading} package the current review state for handoff without claiming defended production capability."
    )
    for export_name, frame in export_artifacts["export_frames"].items():
        if frame.empty:
            continue
        st.download_button(
            label=f"Download {export_name}",
            data=frame.to_csv(index=False),
            file_name=f"{file_prefix}_{export_name}",
            mime="text/csv",
        )
    st.download_button(
        label="Download provenance manifest (JSON)",
        data=export_artifacts["manifest_json"],
        file_name=f"{file_prefix}_provenance_manifest.json",
        mime="application/json",
    )


def build_experimental_lab_route_snapshot(
    selected_month: str,
    *,
    runtime_mode: str = "standard",
    db_path=None,
    queue_size: int = 3,
    max_jobs_per_machine: int = 1,
    horizon_days: int = 14,
) -> dict[str, object]:
    normalized_mode = normalize_runtime_mode(runtime_mode)
    route_exposed = experimental_route_is_exposed(normalized_mode)
    resolved_db_path = str(Path(db_path or get_database_path()).resolve())
    available_months = get_available_months(db_path=resolved_db_path)
    scope_summary = _build_route_scope_summary(selected_month, db_path=resolved_db_path)
    active_artifact_binding = get_active_saved_artifact_binding()

    if not route_exposed:
        return {
            "runtime_mode": normalized_mode,
            "route_exposed": False,
            "resolved_db_path": resolved_db_path,
            "available_months": available_months,
            "selected_month": selected_month,
            "scope_summary": scope_summary,
            "active_artifact_binding": active_artifact_binding,
            "scheduling": None,
            "maintenance": None,
        }

    scheduling_payload = run_constraint_aware_scheduling(
        selected_month,
        queue_size=queue_size,
        max_jobs_per_machine=max_jobs_per_machine,
        db_path=resolved_db_path,
    )
    maintenance_payload = build_predictive_maintenance_prototype(
        selected_month,
        horizon_days=horizon_days,
        db_path=resolved_db_path,
    )
    scheduling_binding = scheduling_payload.get("active_artifact_binding") or active_artifact_binding

    return {
        "runtime_mode": normalized_mode,
        "route_exposed": True,
        "resolved_db_path": resolved_db_path,
        "available_months": available_months,
        "selected_month": selected_month,
        "scope_summary": scope_summary,
        "active_artifact_binding": scheduling_binding,
        "scheduling": {
            "blocked": bool(scheduling_payload.get("blocked")),
            "message": scheduling_payload.get("message"),
            "queue_rows": int(len(scheduling_payload.get("queue_df", pd.DataFrame()))),
            "assigned_rows": int(len(scheduling_payload.get("optimized_schedule_df", pd.DataFrame()))),
            "naive_rows": int(len(scheduling_payload.get("naive_schedule_df", pd.DataFrame()))),
            "queue_provenance": scheduling_payload.get("provenance_label"),
            "queue_generation_rule": scheduling_payload.get("queue_generation_rule"),
        },
        "maintenance": {
            "blocked": bool(maintenance_payload.get("blocked")),
            "message": maintenance_payload.get("message"),
            "prototype_mode": maintenance_payload.get("prototype_mode"),
            "risk_rows": int(len(maintenance_payload.get("risk_table_df", pd.DataFrame()))),
            "selected_machine_id": (
                maintenance_payload.get("selected_machine_summary", {}) or {}
            ).get("machine_id"),
            "maintenance_event_horizon_end": maintenance_payload.get("maintenance_event_horizon_end"),
            "prototype_note": maintenance_payload.get("prototype_note"),
        },
    }


def _build_route_scope_summary(
    selected_month: str,
    *,
    db_path=None,
) -> dict[str, object]:
    db_path = str(db_path or get_database_path())
    start_ts, next_month_start = _month_label_to_bounds(selected_month)
    conn = sqlite3.connect(db_path)
    try:
        history_df = pd.read_sql_query(
            """
            SELECT
                MIN(date(hour_ts)) AS history_start_date,
                MAX(date(hour_ts)) AS history_end_date
            FROM fact_machine_hour
            WHERE hour_ts < ?
            """,
            conn,
            params=(next_month_start,),
        )
        anchor_df = pd.read_sql_query(
            """
            SELECT
                MIN(date(hour_ts)) AS anchor_start_date,
                MAX(date(hour_ts)) AS anchor_end_date,
                COUNT(DISTINCT canonical_machine_id) AS anchor_machine_count
            FROM fact_machine_hour
            WHERE hour_ts >= ?
              AND hour_ts < ?
            """,
            conn,
            params=(start_ts, next_month_start),
        )
        maintenance_df = pd.read_sql_query(
            """
            SELECT
                MIN(date(transaction_date)) AS maintenance_event_start_date,
                MAX(date(transaction_date)) AS maintenance_event_end_date
            FROM maintenance_records
            WHERE ((canonical_machine_id IS NOT NULL AND trim(canonical_machine_id) <> '')
                OR (machine_id IS NOT NULL AND trim(machine_id) <> ''))
            """,
            conn,
        )
    finally:
        conn.close()

    history_row = history_df.iloc[0] if not history_df.empty else {}
    anchor_row = anchor_df.iloc[0] if not anchor_df.empty else {}
    maintenance_row = maintenance_df.iloc[0] if not maintenance_df.empty else {}

    history_start = _safe_timestamp(history_row.get("history_start_date"))
    history_end = _safe_timestamp(history_row.get("history_end_date"))
    anchor_start = _safe_timestamp(anchor_row.get("anchor_start_date"))
    anchor_end = _safe_timestamp(anchor_row.get("anchor_end_date"))
    maintenance_start = _safe_timestamp(maintenance_row.get("maintenance_event_start_date"))
    maintenance_end = _safe_timestamp(maintenance_row.get("maintenance_event_end_date"))

    return {
        "history_exact_window_label": _format_exact_span(history_start, history_end, fallback=f"through {selected_month}"),
        "history_month_window_label": _format_month_span(history_start, history_end, fallback=f"through {selected_month}"),
        "history_end_label": history_end or "n/a",
        "anchor_exact_window_label": _format_exact_span(anchor_start, anchor_end, fallback=selected_month),
        "anchor_machine_count": int(anchor_row.get("anchor_machine_count") or 0),
        "maintenance_event_end_label": maintenance_end or "n/a",
        "maintenance_event_month_window_label": _format_month_span(
            maintenance_start,
            maintenance_end,
            fallback="stored maintenance history unavailable",
        ),
    }


def _format_active_artifact_bundle_label(binding: dict[str, object]) -> str:
    task_tag = binding.get("task_tag")
    artifact_version_id = binding.get("artifact_version_id")
    selected_model = binding.get("selected_model")
    if task_tag and artifact_version_id and selected_model:
        return f"{task_tag} / {artifact_version_id} / {selected_model}"
    return "active saved live artifacts"


def _build_maintenance_horizon_note(selected_month: str, maintenance_event_end_label: str) -> str | None:
    if not _anchor_extends_beyond_maintenance_event_horizon(selected_month, maintenance_event_end_label):
        return None
    return (
        "Stored maintenance-event horizon currently ends at "
        f"`{maintenance_event_end_label}`. Later-anchor views therefore keep current-state operational evidence real, "
        "but any future-event weak-label observation beyond that stored horizon cannot be claimed."
    )


def _anchor_extends_beyond_maintenance_event_horizon(
    selected_month: str,
    maintenance_event_end_label: str,
) -> bool:
    anchor_month = pd.to_datetime(selected_month, format="%B %Y", errors="coerce")
    maintenance_end = pd.to_datetime(maintenance_event_end_label, errors="coerce")
    if pd.isna(anchor_month) or pd.isna(maintenance_end):
        return False
    anchor_month_end = anchor_month + pd.offsets.MonthEnd(0)
    return anchor_month_end > maintenance_end


def _month_label_to_bounds(month_year: str) -> tuple[str, str]:
    month_dt = pd.to_datetime(month_year, format="%B %Y", errors="coerce")
    if pd.isna(month_dt):
        raise ValueError(f"Invalid month label: {month_year}")
    start_ts = month_dt.strftime("%Y-%m-%dT00:00:00")
    next_month_start = (month_dt + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%dT00:00:00")
    return start_ts, next_month_start


def _safe_timestamp(value: object) -> str | None:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.strftime("%Y-%m-%d")


def _format_exact_span(start_value: object, end_value: object, *, fallback: str) -> str:
    start_label = _safe_timestamp(start_value)
    end_label = _safe_timestamp(end_value)
    if start_label and end_label:
        return f"{start_label} -> {end_label}"
    if end_label:
        return f"through {end_label}"
    return fallback


def _format_month_span(start_value: object, end_value: object, *, fallback: str) -> str:
    start_ts = pd.to_datetime(start_value, errors="coerce")
    end_ts = pd.to_datetime(end_value, errors="coerce")
    if pd.isna(start_ts) and pd.isna(end_ts):
        return fallback
    if pd.isna(start_ts):
        return end_ts.strftime("%B %Y")
    if pd.isna(end_ts):
        return start_ts.strftime("%B %Y")
    start_label = start_ts.strftime("%B %Y")
    end_label = end_ts.strftime("%B %Y")
    if start_label == end_label:
        return start_label
    return f"{start_label} -> {end_label}"


def _render_card_grid(cards: list[dict[str, str]], *, columns: int) -> None:
    if not cards:
        return
    rendered_columns = st.columns(columns)
    for index, card in enumerate(cards):
        with rendered_columns[index % columns]:
            render_surface_card(card)
