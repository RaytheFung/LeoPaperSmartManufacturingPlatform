"""
Canonical ML page backed by fact_machine_hour.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.maintenance_evidence import MaintenanceEvidenceReader
from core.canonical_ml_reader import CanonicalMLReader
from core.intervention_preview import (
    build_intervention_preview_table,
    build_machine_intervention_preview,
    candidate_support_label,
    run_intervention_prediction,
)
from core.ml_predictor import MLPredictor
from core.runtime_capabilities import suppress_write_controls
from core.runtime_mode import normalize_runtime_mode
from core.ml_review_queue import (
    build_blocked_reason_summary,
    build_inference_coverage_summary,
    build_model_review_queue,
    collect_blocked_rows,
    describe_blocked_reason,
)
from core.ml_trainer import get_canonical_retraining_status, run_canonical_retraining
from core.ui_utils import build_surface_card, render_surface_card, section_shell


_RETRAINING_RESULT_KEY = "canonical_ml_retraining_result"
_RETRAINING_NOTICE_KEY = "canonical_ml_retraining_notice"


def render_ml_module(db_path=None, runtime_mode: str = "standard"):
    """Render the canonical ML page."""
    try:
        try:
            from core.ui_utils import load_custom_css

            load_custom_css()
        except Exception:
            pass

        reader = CanonicalMLReader(db_path=db_path)
        maintenance_reader = MaintenanceEvidenceReader(db_path=db_path)
        predictor = MLPredictor()
        retraining_status = _get_canonical_retraining_status(db_path=db_path)

        st.title("🤖 Efficiency Prediction & Model Governance")
        st.markdown(
            "Canonical month-scoped efficiency review from machine-hour facts only. "
            "This page shows current-month inference coverage, a model-backed review queue, "
            "and Scenario Lab evidence from the active saved artifacts. Operational execution "
            "stays on `🎯 Operational Decision Support`."
        )
        st.caption("Canonical Gold source: fact_machine_hour")
        read_only_runtime = suppress_write_controls(runtime_mode)
        if read_only_runtime:
            info_message = (
                "Demo read-only mode is active. Reviewer-facing inference, review, and Scenario Lab surfaces stay available. "
                "Retraining controls are hidden."
                if normalize_runtime_mode(runtime_mode) == "demo_readonly"
                else "Pilot review mode is active. Reviewer-facing inference, review, and Scenario Lab surfaces stay available. "
                "Retraining controls are hidden while experimental pilot-review export surfaces remain available on the experimental route."
            )
            st.info(
                info_message
            )

        available_months = reader.get_available_months()
        predictor_status = reader.get_predictor_status(predictor)

        latest_canonical_month = available_months[0] if available_months else None
        _render_predictor_status(
            retraining_status,
            predictor_status,
            latest_canonical_month=latest_canonical_month,
        )

        selected_month = None
        input_df = pd.DataFrame()
        candidate_df = pd.DataFrame()
        prediction_df = pd.DataFrame()
        blocked_prediction_df = pd.DataFrame()
        metrics = None

        if available_months:
            selected_month = st.selectbox("Select month", available_months, index=0)
            input_df = reader.build_month_input_dataframe(selected_month, predictor=predictor)
            if not input_df.empty:
                candidate_df = reader.build_prediction_candidates(input_df)
                prediction_df, blocked_prediction_df = reader.build_prediction_dataframe(
                    candidate_df,
                    predictor=predictor,
                )
                metrics = reader.build_month_readiness_metrics(
                    input_df,
                    candidate_df,
                    blocked_prediction_df=blocked_prediction_df,
                )
                _render_readiness_metrics(
                    selected_month,
                    metrics,
                    input_df,
                    blocked_prediction_df,
                )

        tab_predictions, tab_training, tab_reference = st.tabs(
            ["🔮 Prediction Workflow", "🧪 Model Governance", "📘 Reference & Audit"]
        )

        with tab_predictions:
            if not available_months:
                st.warning(
                    "Canonical Gold is not available yet for the ML page. "
                    "Run ETL for a month that materializes `fact_machine_hour`, then reload this page."
                )
            elif input_df.empty:
                st.warning(
                    f"No canonical ML input rows are available for {selected_month}. "
                    "This page does not fall back to legacy or synthetic data."
                )
            else:
                _render_prediction_results(
                    prediction_df,
                    candidate_df,
                    input_df,
                    blocked_prediction_df,
                    predictor,
                    maintenance_reader,
                )

        with tab_training:
            _render_training_controls(db_path=db_path, runtime_mode=runtime_mode)

        with tab_reference:
            _render_reference_and_audit(
                prediction_df,
                candidate_df,
                input_df,
                blocked_prediction_df,
            )
    except Exception as exc:
        st.error(f"ML page failed: {exc}")
        st.info("The canonical ML route did not fall back to legacy or synthetic data.")


def _render_readiness_metrics(
    selected_month: str,
    metrics: dict[str, int],
    input_df: pd.DataFrame,
    blocked_prediction_df: pd.DataFrame,
) -> None:
    coverage_ratio = (
        metrics["rows_eligible_for_inference"] / metrics["canonical_rows_loaded_for_ml"]
        if metrics["canonical_rows_loaded_for_ml"] > 0
        else 0.0
    )
    coverage_df = build_inference_coverage_summary(input_df)
    blocked_df = collect_blocked_rows(input_df, blocked_prediction_df)
    blocked_summary_df = build_blocked_reason_summary(blocked_df)

    with section_shell(
        "Selected-Month Inference Readiness",
        (
            f"This section shows how much of {selected_month} can be scored now by the active saved model. "
            "It is about current-month inference eligibility and support coverage, not retraining status."
        ),
        eyebrow="Current-Month Scope",
    ):
        summary_cards = [
            build_surface_card(
                "Canonical Rows",
                f"{metrics['canonical_rows_loaded_for_ml']:,}",
                "All canonical machine-hour rows loaded for the selected month.",
            ),
            build_surface_card(
                "Distinct Machines",
                f"{metrics['distinct_machines']:,}",
                "Machines represented in the selected-month canonical ML slice.",
            ),
            build_surface_card(
                "Inferable Rows",
                f"{metrics['rows_eligible_for_inference']:,}",
                f"{_format_ratio(coverage_ratio)} of selected-month rows are currently inferable.",
                accent="#0f766e",
            ),
            build_surface_card(
                "Blocked Rows",
                f"{metrics['rows_blocked_for_missing_features']:,}",
                f"{_format_ratio(1.0 - coverage_ratio if metrics['canonical_rows_loaded_for_ml'] else 0.0)} still remain outside the supported inference contract.",
                accent="#b45309",
            ),
        ]
        _render_card_grid(summary_cards, columns=4)

        st.markdown("#### Current-Month Inference Coverage")
        st.caption(
            "Support-path composition is shown as coverage only. These counts and shares are not trend or improvement indicators."
        )
        if not coverage_df.empty:
            _render_inference_coverage_bar(coverage_df)
            coverage_cards = [
                build_surface_card(
                    row["coverage_bucket"],
                    f"{int(row['rows']):,}",
                    f"{_format_ratio(row['share'])} of canonical rows",
                    accent=_coverage_accent(str(row["support_path"])),
                )
                for _, row in coverage_df.iterrows()
            ]
            _render_card_grid(coverage_cards, columns=4)

        if not blocked_summary_df.empty and blocked_summary_df[
            "blocked_reason_family"
        ].eq("Missing / non-positive good_qty").any():
            st.caption(
                "The former single `missing_positive_good_qty` bucket is now split narrowly into "
                "nonproductive-state rows, a production-state zero-good-qty subtaxonomy, and insufficient-context rows. "
                "This improves readiness explanation only; inference eligibility is unchanged."
            )
        st.info(_blocked_reason_snapshot_text(blocked_summary_df))


def _render_predictor_status(
    retraining_status: dict[str, object],
    predictor_status: dict[str, object],
    *,
    latest_canonical_month: str | None,
) -> None:
    with section_shell(
        "Active Model Summary",
        (
            "Active saved-artifact provenance for the routed ML page. "
            "The selected-month readiness below measures current inference coverage only."
        ),
        eyebrow="Active Artifact",
    ):
        model_summary = _build_active_model_summary(retraining_status)
        summary_cards = [
            build_surface_card("Model Version", model_summary["model_version"], "Current active artifact version."),
            build_surface_card("Trained At", model_summary["trained_at"], "Last recorded training timestamp."),
            build_surface_card("R²", model_summary["r2_score"], "Holdout quality from the active saved model."),
            build_surface_card("MAE", model_summary["mae"], "Holdout error from the active saved model."),
        ]
        _render_card_grid(summary_cards, columns=4)

        chip_rows = [
            ("Latest canonical month", latest_canonical_month or "n/a"),
            ("Model loadable", "Yes" if predictor_status["model_artifact_present"] else "No"),
            ("Preprocessor loadable", "Yes" if predictor_status["predictor_bundle_present"] else "No"),
            (
                "Canonical inference",
                "Enabled" if predictor_status["canonical_inference_enabled"] else "Blocked",
            ),
            (
                "Training month footprint",
                ", ".join(retraining_status.get("month_coverage") or []) or "n/a",
            ),
        ]
        chip_html = "".join(
            [
                (
                    "<span style='display:inline-block;padding:0.25rem 0.65rem;margin:0 0.5rem 0.5rem 0;"
                    "border-radius:999px;background:#eef2ff;color:#1f2937;font-size:0.85rem;'>"
                    f"<strong>{label}:</strong> {value}</span>"
                )
                for label, value in chip_rows
            ]
        )
        st.markdown(chip_html, unsafe_allow_html=True)
        st.caption(
            "Active artifacts remain the accepted Task 14F bundle. Canonical month extension changes source coverage only; it does not retrain or refresh the live predictor bundle."
        )
        st.caption(
            "The active model can be trained on a broader canonical month footprint while the readiness view below "
            "still answers a different question: how much of the currently selected month is inferable now."
        )


def _render_prediction_results(
    prediction_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    input_df: pd.DataFrame,
    blocked_prediction_df: pd.DataFrame,
    predictor: MLPredictor,
    maintenance_reader: MaintenanceEvidenceReader,
) -> None:
    if prediction_df.empty:
        st.warning(
            "No canonical predictions were produced for the selected month. "
            "Rows are blocked instead of using fallback simulation."
        )
        return

    review_queue_df = build_model_review_queue(
        candidate_df,
        prediction_df,
        predictor=predictor,
    )

    with section_shell(
        "Model Review Queue",
        (
            "Primary review surface for the current month. Candidates are ranked by predicted excess kWh "
            "at the current seed volume, confidence, and support-path weight. This is a review queue, not an intervention engine."
        ),
        eyebrow="Decision-Oriented Output",
    ):
        if review_queue_df.empty:
            st.info("No model-backed review candidates are available for the selected month.")
        else:
            priority_candidates = int((review_queue_df["review_priority_score"] > 0).sum())
            preview_ready = int(review_queue_df["preview_available"].sum())
            top_row = review_queue_df.iloc[0]
            queue_cards = [
                build_surface_card(
                    "Top Review Candidate",
                    str(top_row["machine_id"]),
                    f"Priority score {float(top_row['review_priority_score']):,.2f} on the current selected-month evidence.",
                ),
                build_surface_card(
                    "Candidates Above Baseline",
                    f"{priority_candidates:,}",
                    "Machines whose predicted kWh / unit sits above the comparable peer baseline.",
                ),
                build_surface_card(
                    "Scenario Lab Ready",
                    f"{preview_ready:,}",
                    "Machines with at least one supported Scenario Lab template on the current seed row.",
                ),
                build_surface_card(
                    "Baseline Contract",
                    "Peer median",
                    "Preferred order: family + task difficulty, then task difficulty, then selected-month median fallback.",
                ),
            ]
            _render_card_grid(queue_cards, columns=4)

            _render_review_priority_chart(review_queue_df)
            st.dataframe(
                _build_review_queue_display(review_queue_df),
                hide_index=True,
                use_container_width=True,
            )

    _render_scenario_lab(
        candidate_df,
        prediction_df,
        predictor,
        review_queue_df,
        maintenance_reader,
    )


def _render_reference_and_audit(
    prediction_df: pd.DataFrame,
    candidate_df: pd.DataFrame,
    input_df: pd.DataFrame,
    blocked_prediction_df: pd.DataFrame,
) -> None:
    blocked_df = collect_blocked_rows(input_df, blocked_prediction_df)
    blocked_summary_df = build_blocked_reason_summary(blocked_df)

    with section_shell(
        "Blocked And Unsupported Evidence",
        "Blocked rows stay visible for honesty, but the raw detail is kept here as supporting evidence rather than the main review story.",
        eyebrow="Reference & Audit",
    ):
        if blocked_summary_df.empty:
            st.caption("No blocked rows for the selected month.")
        else:
            fig = px.bar(
                blocked_summary_df,
                x="row_count",
                y="blocked_reason_label",
                orientation="h",
                title="Blocked Reason Summary",
                labels={"row_count": "Rows", "blocked_reason_label": "Blocked Reason"},
                hover_data={
                    "blocked_reason": True,
                    "blocked_reason_family": True,
                    "blocked_reason_description": True,
                    "row_count": False,
                    "blocked_reason_label": False,
                },
                color_discrete_sequence=["#94a3b8"],
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Blocked row detail", expanded=False):
                st.dataframe(
                    _build_blocked_detail_display(blocked_df),
                    hide_index=True,
                    use_container_width=True,
                )

    with section_shell(
        "Machine-Level Prediction Evidence",
        "Full machine-level prediction evidence is retained here for audit review after the primary review queue.",
        eyebrow="Reference & Audit",
    ):
        if prediction_df.empty:
            st.caption("No machine-level predictions are available for the selected month.")
        else:
            st.dataframe(
                _build_prediction_audit_display(candidate_df, prediction_df),
                hide_index=True,
                use_container_width=True,
            )
        if not candidate_df.empty:
            st.caption(
                f"Latest machine-level candidates considered for inference: {candidate_df['machine_id'].nunique():,}"
            )

    _render_contract_notes()


def _render_contract_notes() -> None:
    with st.expander("Reference & Audit: Canonical ML Input Contract", expanded=False):
        st.markdown(
            """
            - Canonical inputs are loaded from `fact_machine_hour` only.
            - Direct canonical fields:
              `canonical_machine_id`, `hour_ts`, `material_code`, `task_name`, `good_qty`, `team_leader`, `team_size`, `manpower`, `hours_since_last_maintenance`, `last_maintenance_work_order_type`, `maintenance_distinct_work_order_count_30d`, `cumulative_maintenance_count`.
            - Derived fields:
              `machine_id`, `hour_of_day`, `day_of_week`, `month`, `is_weekend`, `production_qty = good_qty`.
            - Safe adapter rules:
              `task_difficulty` is derived from canonical printing vs finishing task families, including the Jan-Jun `UV` / `水油` / `啞油` variants; rows with still-unmapped task labels are blocked instead of defaulted.
              canonical Gold now prefers exact same-machine MES `manpower` and otherwise stores CSI roster-derived `team_size` when the overlapping CSI event still carries a leader/member list.
              the ML reader uses canonical `team_size` first, then rounded `manpower`, then the preprocessor median only for the remaining exceptional rows with no honest crew signal.
              canonical retraining status below exposes the current residual dependence on that last-resort preprocessor-default path.
              `maintenance_intensity_30d` comes from canonical `maintenance_distinct_work_order_count_30d`.
              `cumulative_maintenance_count` comes from canonical Gold directly and falls back to `0` only when the row is still missing the explicit value.
              `last_maintenance_type` uses canonical `last_maintenance_work_order_type`, then `unknown`.
            - Hard block rules:
              rows are blocked when machine ID is missing, timestamp is missing, `hours_since_last_maintenance` is missing, or `task_name` cannot be mapped into the supported task-difficulty families.
              rows with missing / non-positive `good_qty` still remain blocked, but are now reported more honestly as nonproductive-state rows, production-state zero-good-qty rows, or insufficient-context rows.
              within the production-state bucket, the routed ML path now distinguishes likely state-label contradictions, likely quantity-overlay gaps, likely order/material context conflicts, and likely source-quality/anomaly cases when the existing row fields support that split cleanly.
            - Prediction safety rule:
              if the saved predictor returns a non-`model` source, the page blocks that row instead of showing fallback simulation output.
            """
        )


def _render_training_pending() -> None:
    st.info("Canonical retraining status is shown below.")


def _get_canonical_retraining_status(db_path=None, model_path=None, preprocessor_path=None):
    return get_canonical_retraining_status(
        db_path=db_path,
        model_path=model_path,
        preprocessor_path=preprocessor_path,
    )


def _trigger_canonical_retraining(db_path=None, model_path=None, preprocessor_path=None):
    return run_canonical_retraining(
        db_path=db_path,
        model_path=model_path,
        preprocessor_path=preprocessor_path,
    )


def _render_training_controls(db_path=None, runtime_mode: str = "standard") -> None:
    _render_training_pending()

    status = _get_canonical_retraining_status(db_path=db_path)
    _render_retraining_status(status)

    notice = st.session_state.pop(_RETRAINING_NOTICE_KEY, None)
    if notice:
        st.success(notice)

    latest_result = st.session_state.get(_RETRAINING_RESULT_KEY)
    if latest_result:
        _render_retraining_result(latest_result)

    if suppress_write_controls(runtime_mode):
        warning_message = (
            "Demo read-only mode hides the retraining action because it can refresh candidate/active artifact state. "
            "Artifact status and provenance remain visible above."
            if normalize_runtime_mode(runtime_mode) == "demo_readonly"
            else "Pilot review mode hides the retraining action because defended-core artifact state must remain fixed during pilot evaluation. "
            "Artifact status and provenance remain visible above."
        )
        st.warning(
            warning_message
        )
        return

    retrain_disabled = not status["trainer_prerequisites_met"]
    if st.button(
        "Retrain from canonical Gold",
        disabled=retrain_disabled,
        use_container_width=True,
    ):
        try:
            result = _trigger_canonical_retraining(db_path=db_path)
        except Exception as exc:
            st.error(f"Canonical retraining failed: {exc}")
            st.info("No mock or fallback training results were shown.")
            return

        st.session_state[_RETRAINING_RESULT_KEY] = result
        if result.get("promotion_success"):
            st.session_state[_RETRAINING_NOTICE_KEY] = (
                "Canonical reevaluation completed and the active artifacts were refreshed."
            )
        else:
            st.session_state[_RETRAINING_NOTICE_KEY] = (
                "Canonical reevaluation completed and the prior active artifacts were retained."
            )
        st.rerun()


def _render_retraining_status(status: dict[str, object]) -> None:
    with section_shell(
        "Canonical Retraining Status",
        "Governance view for the active canonical training path. Detailed training-footprint evidence is available below on demand.",
        eyebrow="Model Governance",
    ):
        status_cards = [
            build_surface_card(
                "fact_machine_hour Reachable",
                "Yes" if status["fact_machine_hour_reachable"] else "No",
                "Whether the canonical training source is reachable from the active runtime.",
            ),
            build_surface_card(
                "Trainer Prerequisites",
                "Ready" if status["trainer_prerequisites_met"] else "Blocked",
                "Retraining remains a manual action and is blocked honestly when prerequisites fail.",
            ),
            build_surface_card(
                "Model Artifact",
                "Loadable" if status["artifact_status"]["model_loadable"] else "Missing / Broken",
                "Current saved model artifact state.",
            ),
            build_surface_card(
                "Preprocessor Artifact",
                "Loadable" if status["artifact_status"]["preprocessor_loadable"] else "Missing / Broken",
                "Current saved preprocessor state.",
            ),
        ]
        _render_card_grid(status_cards, columns=4)

        if status["missing_columns"]:
            st.warning(
                "Missing required canonical training columns: "
                + ", ".join(status["missing_columns"])
            )

        if status["blocker_reason"]:
            st.warning(f"Retraining blocker: {status['blocker_reason']}")
        else:
            st.caption("No current blocker was detected for canonical retraining.")

        with st.expander("Reference & Audit: Training footprint and provenance", expanded=False):
            if status["load_summary"]:
                summary = status["load_summary"]
                st.caption(
                    "Canonical training footprint: "
                    f"rows read {summary.get('fact_rows_read', 0):,}, "
                    f"rows after filtering {summary.get('rows_after_filtering', 0):,}, "
                    f"distinct machines {summary.get('distinct_machines_after_filtering', 0):,}, "
                    f"month coverage {', '.join(status.get('month_coverage') or []) or 'n/a'}"
                )

            fallback_summary = status.get("team_size_fallback_summary") or {}
            if fallback_summary:
                default_months = fallback_summary.get(
                    "monthly_rows_using_team_size_from_preprocessor_default",
                    {},
                )
                default_month_text = (
                    ", ".join(f"{month}={count}" for month, count in default_months.items())
                    if default_months
                    else "none"
                )
                st.caption(
                    "Residual crew fallback on the real canonical trainer path: "
                    f"default-team rows {fallback_summary.get('rows_using_team_size_from_preprocessor_default', 0):,} "
                    f"across {fallback_summary.get('distinct_machines_using_team_size_from_preprocessor_default', 0):,} machines; "
                    f"manpower-derived rows {fallback_summary.get('rows_using_team_size_from_manpower', 0):,}; "
                    f"monthly default breakdown {default_month_text}"
                )

            if status.get("evaluation_strategy"):
                st.caption(
                    "Current reevaluation split: "
                    f"train months {', '.join(status.get('train_months') or []) or 'n/a'} | "
                    f"eval months {', '.join(status.get('eval_months') or []) or 'n/a'} | "
                    f"train rows {status.get('train_rows', 0):,} | "
                    f"eval rows {status.get('eval_rows', 0):,}"
                )

            st.caption(
                "ML metadata table present: "
                + ("Yes" if status.get("ml_models_table_exists") else "No")
            )

            metadata = status.get("last_training_metadata")
            if metadata:
                st.caption("Last known training metadata")
                st.dataframe(
                    pd.DataFrame([metadata]).rename(
                        columns={
                            "model_name": "Model Name",
                            "model_type": "Model Type",
                            "training_date": "Training Date",
                            "r2_score": "R² Score",
                            "mae": "MAE",
                            "feature_count": "Feature Count",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

            artifact_df = pd.DataFrame(
                [
                    {
                        "Artifact": "Model",
                        "Active File": _short_file_label(status["model_path"]),
                        "Exists": status["artifact_status"]["model_exists"],
                        "Loadable": status["artifact_status"]["model_loadable"],
                        "Provenance": status["artifact_status"]["model_provenance_state"],
                        "Modified At": status["artifact_status"]["model_modified_at"],
                    },
                    {
                        "Artifact": "Preprocessor",
                        "Active File": _short_file_label(status["preprocessor_path"]),
                        "Exists": status["artifact_status"]["preprocessor_exists"],
                        "Loadable": status["artifact_status"]["preprocessor_loadable"],
                        "Provenance": status["artifact_status"]["preprocessor_provenance_state"],
                        "Modified At": status["artifact_status"]["preprocessor_modified_at"],
                    },
                ]
            )
            st.dataframe(artifact_df, hide_index=True, use_container_width=True)

            manifest_rows = []
            for artifact_name, prefix in (("Model", "model"), ("Preprocessor", "preprocessor")):
                summary = status["artifact_status"].get(f"{prefix}_manifest_summary") or {}
                if summary:
                    manifest_rows.append(
                        {
                            "Artifact": artifact_name,
                            "Artifact Version": summary.get("artifact_version_id"),
                            "Trained At": summary.get("trained_at"),
                            "Selected Model": summary.get("selected_model"),
                            "Promotion Success": summary.get("promotion_success"),
                        }
                    )
            if manifest_rows:
                st.caption("Active artifact provenance manifests")
                st.dataframe(pd.DataFrame(manifest_rows), hide_index=True, use_container_width=True)


def _render_retraining_result(result: dict[str, object]) -> None:
    st.subheader("Latest Canonical Retraining Result")
    summary_df = pd.DataFrame(
        [
            {
                "Active DB": _short_file_label(result["db_path"]),
                "Rows Loaded": result["rows_loaded"],
                "Rows After Hard Block": result["rows_after_hard_block"],
                "Rows After Filtering": result["rows_after_filtering"],
                "Distinct Machines": result["distinct_machines_after_filtering"],
                "Month Coverage": ", ".join(result.get("month_coverage") or []),
                "Evaluation Strategy": result.get("evaluation_strategy"),
                "Train Months": ", ".join(result.get("train_months") or []),
                "Eval Months": ", ".join(result.get("eval_months") or []),
                "Selected Model": result["selected_model"],
                "Training Source": result["training_source"],
                "Promotion Success": result.get("promotion_success"),
                "Artifact Decision": result.get("artifact_decision"),
                "Artifact Version": result.get("artifact_version_id"),
            }
        ]
    )
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

    metrics_df = pd.DataFrame(
        [
            {
                "Selected Model": result["selected_model"],
                "R² Score": result["evaluation_metrics"]["r2_score"],
                "MAE": result["evaluation_metrics"]["mae"],
                "RMSE": result["evaluation_metrics"]["rmse"],
            }
        ]
    )
    st.dataframe(metrics_df, hide_index=True, use_container_width=True)

    provenance_df = pd.DataFrame(
        [
            {
                "Model File": _short_file_label(result["model_path"]),
                "Preprocessor File": _short_file_label(result["preprocessor_path"]),
                "Source Table": result["training_provenance"]["source_table"],
                "Feature Contract": result.get("feature_contract_version"),
            }
        ]
    )
    st.dataframe(provenance_df, hide_index=True, use_container_width=True)

    artifact_rows = [
        {
            "Artifact Set": "Candidate",
            "Model File": _short_file_label(result["candidate_paths"]["model_path"]),
            "Preprocessor File": _short_file_label(result["candidate_paths"]["preprocessor_path"]),
            "Artifact Version": result.get("artifact_version_id"),
        },
        {
            "Artifact Set": "Backup",
            "Model File": _short_file_label(result["backup_paths"]["model_path"]),
            "Preprocessor File": _short_file_label(result["backup_paths"]["preprocessor_path"]),
            "Artifact Version": result.get("artifact_version_id"),
        },
    ]
    st.dataframe(pd.DataFrame(artifact_rows), hide_index=True, use_container_width=True)

    if result.get("promotion_gate"):
        gate = result["promotion_gate"]
        st.caption(
            "Promotion gate: "
            + ("passed" if gate.get("passed") else "blocked")
            + (
                ""
                if gate.get("passed")
                else f" ({', '.join(gate.get('failures') or [])})"
            )
        )
    if result.get("predictor_smoke"):
        smoke = result["predictor_smoke"]
        st.caption(
            "Predictor smoke: "
            + ("passed" if smoke.get("passed") else "blocked")
            + (
                f" | source={smoke.get('prediction_source')}"
                if smoke.get("prediction_source")
                else ""
            )
        )
    if result.get("artifact_decision_reason"):
        st.caption(f"Artifact decision reason: {result['artifact_decision_reason']}")
    if result.get("candidate_predictor_evaluation"):
        st.caption("Candidate holdout predictor evaluation")
        st.dataframe(pd.DataFrame([result["candidate_predictor_evaluation"]]), hide_index=True, use_container_width=True)
    if result.get("active_predictor_evaluation"):
        st.caption("Active holdout predictor evaluation")
        st.dataframe(pd.DataFrame([result["active_predictor_evaluation"]]), hide_index=True, use_container_width=True)


def _build_active_model_summary(status: dict[str, object]) -> dict[str, str]:
    metadata = status.get("last_training_metadata") or {}
    model_manifest = status.get("artifact_status", {}).get("model_manifest_summary") or {}
    version = (
        model_manifest.get("artifact_version_id")
        or metadata.get("model_name")
        or _short_file_label(status.get("model_path"))
    )
    trained_at = metadata.get("training_date") or model_manifest.get("trained_at")
    return {
        "model_version": str(version or "n/a"),
        "trained_at": _format_timestamp_label(trained_at),
        "r2_score": _format_metric_value(metadata.get("r2_score")),
        "mae": _format_metric_value(metadata.get("mae")),
    }


def _render_scenario_lab(
    candidate_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
    predictor: MLPredictor,
    review_queue_df: pd.DataFrame,
    maintenance_reader: MaintenanceEvidenceReader,
) -> None:
    if candidate_df.empty or prediction_df.empty:
        return
    if not (getattr(predictor, "loaded_model", False) and getattr(predictor, "loaded_preprocessor", False)):
        return

    machine_options = _scenario_machine_options(review_queue_df, prediction_df)
    if not machine_options:
        return

    with section_shell(
        "Scenario Lab",
        (
            "Model evidence for one current-month review candidate. Use this page to inspect supported template comparisons "
            "and why the active saved model suggests a direction. Move to `🎯 Operational Decision Support` for the operational worklist."
        ),
        eyebrow="Scenario Evidence",
    ):
        selected_machine = st.selectbox(
            "Select review candidate",
            options=machine_options,
            key="ml_scenario_machine",
        )
        preview = build_machine_intervention_preview(
            candidate_df,
            prediction_df,
            predictor,
            selected_machine,
        )
        if preview["blocked"]:
            st.info(str(preview["reason"]))
            return

        baseline = preview["baseline"]
        supported_templates = [
            scenario for scenario in preview["scenarios"] if scenario["status"] == "supported"
        ]
        best_scenario = preview["best_supported_scenario"]
        summary_cards = [
            build_surface_card(
                "Baseline kWh / Unit",
                f"{float(baseline['predicted_efficiency']):.4f}",
                "Prediction from the active saved model on the selected seed row.",
            ),
            build_surface_card(
                "Baseline Confidence",
                f"{float(baseline['confidence']):.2f}",
                f"Top driver: {baseline['top_driver']}",
            ),
            build_surface_card(
                "Supported Templates",
                f"{len(supported_templates)} / {len(preview['scenarios'])}",
                "Only safe template paths are shown. Unsupported rows stay visible and honest.",
            ),
            build_surface_card(
                "Best Supported Scenario",
                "n/a" if best_scenario is None else str(best_scenario["scenario_name"]),
                (
                    "No supported template is available on the selected seed row."
                    if best_scenario is None
                    else f"{float(best_scenario['delta_vs_baseline']):+.4f} kWh / unit vs baseline"
                ),
            ),
        ]
        _render_card_grid(summary_cards, columns=4)

        _render_maintenance_context_block(
            selected_machine,
            maintenance_reader,
            description=(
                "Direct maintenance-table context reused from `🔧 Maintenance`. "
                "It enriches the review story but does not change queue ranking."
            ),
        )

        st.caption(
            f"Seed row: {preview['seed_timestamp_label']} | support path: {preview['support_path']} | "
            f"task {preview['seed_task_difficulty']} | leader {preview['seed_team_leader']} | "
            f"material {preview['seed_material_code']} | comparable production volume {preview['seed_production_qty']:.1f}"
        )
        if preview["adapter_notes"]:
            st.caption(f"Adapter notes: {preview['adapter_notes']}")

        st.info(
            "Scenario Lab is a preview from the active saved model only. It is not an executed intervention, "
            "a realized-savings claim, or a solver."
        )

        scenario_table = build_intervention_preview_table(preview)
        if not scenario_table.empty:
            scenario_table["Predicted kWh/Unit"] = scenario_table["Predicted kWh/Unit"].round(4)
            scenario_table["Delta vs Baseline"] = scenario_table["Delta vs Baseline"].round(4)
            scenario_table["Confidence"] = scenario_table["Confidence"].round(4)
            scenario_table["Est. kWh Change @ Seed Volume"] = scenario_table[
                "Est. kWh Change @ Seed Volume"
            ].round(4)
            st.dataframe(
                scenario_table,
                hide_index=True,
                use_container_width=True,
            )

        st.caption(
            "Template scope remains intentionally narrow: `Maintenance Refresh`, `Crew Support +1`, and "
            "`Combined Support`. Unsupported scenarios remain visible instead of being fabricated."
        )


def _render_review_priority_chart(review_queue_df: pd.DataFrame) -> None:
    chart_df = review_queue_df.head(10).copy()
    if chart_df.empty:
        return

    chart_df = chart_df.sort_values("review_priority_score", ascending=True)
    fig = px.bar(
        chart_df,
        x="review_priority_score",
        y="machine_id",
        color="support_path",
        orientation="h",
        title="Top Review Priority Score",
        labels={
            "review_priority_score": "Review Priority Score",
            "machine_id": "Machine",
            "support_path": "Support Path",
        },
        color_discrete_map={
            "Direct canonical row": "#0f766e",
            "Adapted row": "#0369a1",
            "Defaulted row": "#b45309",
        },
    )
    fig.update_layout(legend_title_text="Support Path", height=420)
    st.plotly_chart(fig, use_container_width=True)


def _render_inference_coverage_bar(coverage_df: pd.DataFrame) -> None:
    if coverage_df.empty:
        return

    fig = go.Figure()
    for _, row in coverage_df.iterrows():
        label = str(row["coverage_bucket"])
        support_path = str(row["support_path"])
        fig.add_bar(
            name=label,
            x=[int(row["rows"])],
            y=["Selected month"],
            orientation="h",
            marker_color=_coverage_accent(support_path),
            text=[f"{int(row['rows']):,} ({_format_ratio(row['share'])})"],
            textposition="inside" if float(row["share"]) >= 0.12 else "outside",
            hovertemplate=(
                f"{label}<br>"
                f"Rows: {int(row['rows']):,}<br>"
                f"Share: {_format_ratio(row['share'])}<extra></extra>"
            ),
        )
    fig.update_layout(
        barmode="stack",
        height=220,
        xaxis_title="Rows",
        yaxis_title="",
        legend_title_text="Support Path",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _build_review_queue_display(review_queue_df: pd.DataFrame) -> pd.DataFrame:
    if review_queue_df.empty:
        return pd.DataFrame()

    display_df = review_queue_df.loc[
        :,
        [
            "machine_id",
            "support_path",
            "predicted_efficiency",
            "comparable_baseline",
            "estimated_excess_kwh",
            "confidence",
            "review_priority_score",
            "top_driver",
            "preview_available",
            "recommended_review_note",
        ],
    ].copy()
    display_df["predicted_efficiency"] = display_df["predicted_efficiency"].round(4)
    display_df["comparable_baseline"] = display_df["comparable_baseline"].round(4)
    display_df["estimated_excess_kwh"] = display_df["estimated_excess_kwh"].round(2)
    display_df["confidence"] = display_df["confidence"].round(4)
    display_df["review_priority_score"] = display_df["review_priority_score"].round(2)
    display_df["preview_available"] = display_df["preview_available"].map({True: "Yes", False: "No"})
    return display_df.rename(
        columns={
            "machine_id": "Machine",
            "support_path": "Support Path",
            "predicted_efficiency": "Predicted kWh / Unit",
            "comparable_baseline": "Comparable Baseline",
            "estimated_excess_kwh": "Excess @ Seed Volume",
            "confidence": "Confidence",
            "review_priority_score": "Review Priority Score",
            "top_driver": "Top Driver",
            "preview_available": "Preview Available",
            "recommended_review_note": "Recommended Review Note",
        }
    )


def _build_blocked_detail_display(blocked_df: pd.DataFrame) -> pd.DataFrame:
    if blocked_df.empty:
        return pd.DataFrame()

    display_df = blocked_df.loc[
        :,
        [
            "machine_id",
            "datetime",
            "blocked_reason",
            "adapter_notes",
            "material_code",
            "team_leader",
            "production_qty",
            "hours_since_last_maintenance",
        ],
    ].copy()
    display_df["blocked_reason_label"] = display_df["blocked_reason"].apply(
        lambda value: describe_blocked_reason(value)["label"]
    )
    display_df["production_qty"] = pd.to_numeric(display_df["production_qty"], errors="coerce").round(2)
    display_df["hours_since_last_maintenance"] = pd.to_numeric(
        display_df["hours_since_last_maintenance"], errors="coerce"
    ).round(2)
    return display_df.rename(
        columns={
            "machine_id": "Machine",
            "datetime": "Timestamp",
            "blocked_reason_label": "Blocked Reason",
            "blocked_reason": "Blocked Reason Code",
            "adapter_notes": "Adapter Notes",
            "material_code": "Material",
            "team_leader": "Team Leader",
            "production_qty": "Production Qty",
            "hours_since_last_maintenance": "Hours Since Maintenance",
        }
    )


def _build_prediction_audit_display(
    candidate_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
) -> pd.DataFrame:
    if prediction_df.empty:
        return pd.DataFrame()

    support_df = candidate_df.loc[:, ["machine_id", "datetime", "adapter_notes"]].copy()
    support_df["support_path"] = support_df.apply(_candidate_support_label, axis=1)
    display_df = prediction_df.merge(
        support_df.loc[:, ["machine_id", "datetime", "support_path"]],
        on=["machine_id", "datetime"],
        how="left",
    )
    display_df["predicted_efficiency"] = display_df["predicted_efficiency"].round(4)
    display_df["confidence"] = display_df["confidence"].round(4)
    display_df["production_qty"] = display_df["production_qty"].round(2)
    display_df["hours_since_last_maintenance"] = display_df["hours_since_last_maintenance"].round(2)
    return display_df.loc[
        :,
        [
            "machine_id",
            "datetime",
            "support_path",
            "predicted_efficiency",
            "confidence",
            "top_driver",
            "production_qty",
            "task_difficulty",
            "team_leader",
            "material_code",
        ],
    ].rename(
        columns={
            "machine_id": "Machine",
            "datetime": "Timestamp",
            "support_path": "Support Path",
            "predicted_efficiency": "Predicted kWh / Unit",
            "confidence": "Confidence",
            "top_driver": "Top Driver",
            "production_qty": "Production Qty",
            "task_difficulty": "Task Difficulty",
            "team_leader": "Team Leader",
            "material_code": "Material",
        }
    )


def _scenario_machine_options(
    review_queue_df: pd.DataFrame,
    prediction_df: pd.DataFrame,
) -> list[str]:
    if not review_queue_df.empty:
        preview_ready_df = review_queue_df[review_queue_df["preview_available"]].copy()
        ordered_df = preview_ready_df if not preview_ready_df.empty else review_queue_df
        options = ordered_df["machine_id"].dropna().astype(str).tolist()
        if options:
            return options
    return prediction_df.sort_values(["machine_id", "datetime"])["machine_id"].dropna().astype(str).tolist()


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


def _blocked_reason_snapshot_text(blocked_summary_df: pd.DataFrame) -> str:
    if blocked_summary_df.empty:
        return "Blocked rows remain visible as supporting evidence. No blocked rows are present for the selected month."

    top_rows = blocked_summary_df.head(2)
    top_text = ", ".join(
        f"{row.get('blocked_reason_label', row['blocked_reason'])} ({int(row['row_count']):,}, {_format_ratio(row['share'])})"
        for _, row in top_rows.iterrows()
    )
    return (
        "Blocked rows remain visible as supporting evidence. "
        f"Top current-month blockers: {top_text}."
    )


def _coverage_accent(support_path: str) -> str:
    if support_path == "Direct canonical row":
        return "#0f766e"
    if support_path == "Adapted row":
        return "#0369a1"
    if support_path == "Defaulted row":
        return "#b45309"
    return "#94a3b8"


def _format_optional_ratio(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _format_optional_int(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def _run_what_if_prediction(
    seed_row: pd.Series,
    overrides: dict[str, object],
    predictor: MLPredictor,
) -> dict[str, object]:
    return run_intervention_prediction(seed_row, overrides, predictor)


def _candidate_support_label(row: pd.Series) -> str:
    return candidate_support_label(row)


def _render_card_grid(cards: list[dict[str, str]], *, columns: int) -> None:
    for start_index in range(0, len(cards), columns):
        row_cards = cards[start_index : start_index + columns]
        row_columns = st.columns(columns)
        for column, card in zip(row_columns, row_cards):
            with column:
                render_surface_card(card)


def _format_metric_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.3f}"


def _format_ratio(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:.1f}%"


def _format_timestamp_label(value: object) -> str:
    if value is None:
        return "n/a"
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return str(value)
    return timestamp.strftime("%Y-%m-%d")


def _short_file_label(path_value: object) -> str:
    if not path_value:
        return "n/a"
    return Path(str(path_value)).name or str(path_value)
