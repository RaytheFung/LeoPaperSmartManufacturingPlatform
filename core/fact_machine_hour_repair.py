"""Targeted repair helpers for rebuilding operational overlays on an existing Gold table."""

from __future__ import annotations

import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from core.csi_quantity_shadow import (
    CSI_QTY_SHADOW_MATERIAL_DIFF_THRESHOLD,
    evaluate_shadow_quantity,
)
from core.runtime_paths import get_database_path

CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES = 0.5
CSI_MINUTE_BUDGET_TOLERANCE_MINUTES = 0.5
TASK4S_LIVE_REPLACEMENT_FLOAT_TOLERANCE = 1e-6
TASK4S_LIVE_REPLACEMENT_BASELINE = {
    "eligible_rows": 31669,
    "anomaly_excluded_rows": 8,
    "eligible_groups": 29846,
    "ineligible_groups": 2,
    "dominant_identity_conflict_rows": 0,
}


def _normalize_suffix_sql(expr: str) -> str:
    text_expr = f"CAST({expr} AS TEXT)"
    return (
        f"CASE "
        f"WHEN {expr} IS NULL THEN NULL "
        f"WHEN {text_expr} LIKE '%.0' THEN substr({text_expr}, 1, length({text_expr}) - 2) "
        f"ELSE {text_expr} "
        f"END"
    )


def _count(conn: sqlite3.Connection, query: str) -> int:
    return int(conn.execute(query).fetchone()[0])


def _sql_text_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ensure_fact_machine_hour_columns(conn: sqlite3.Connection) -> None:
    required_columns = {
        "team_size": "REAL",
        "has_maintenance_history": "INTEGER",
        "maintenance_txn_in_hour": "INTEGER",
        "maintenance_distinct_work_order_count_7d": "INTEGER",
        "maintenance_distinct_work_order_count_30d": "INTEGER",
        "maintenance_distinct_work_order_in_hour_count": "INTEGER",
        "cumulative_maintenance_count": "INTEGER",
        "csi_qty_basis_method": "TEXT",
        "csi_qty_row_basis_minutes": "REAL",
        "csi_qty_event_basis_minutes": "REAL",
        "csi_qty_minutes_vs_production_diff": "REAL",
        "csi_qty_minutes_vs_production_abs_diff": "REAL",
        "csi_qty_alignment_status": "TEXT",
        "csi_qty_material_misalignment_flag": "INTEGER",
        "csi_qty_minute_budget_anomaly_flag": "INTEGER",
        "csi_qty_minute_budget_anomaly_reason": "TEXT",
    }
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(fact_machine_hour)")
    existing_columns = {column[1] for column in cursor.fetchall()}
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE fact_machine_hour ADD COLUMN {column_name} {column_type}")
    conn.commit()


def _ensure_operational_overlay_indexes(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_fact_machine_hour_machine_hour
            ON fact_machine_hour (canonical_machine_id, hour_ts);
        CREATE INDEX IF NOT EXISTS idx_csi_job_event_machine
            ON csi_job_event (canonical_machine_id);
        CREATE INDEX IF NOT EXISTS idx_mes_report_event_machine
            ON mes_report_event (canonical_machine_id);
        CREATE INDEX IF NOT EXISTS idx_maintenance_txn_event_machine_ts
            ON maintenance_txn_event (canonical_machine_id, txn_ts);
        """
    )
    conn.commit()


def _coverage_snapshot(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "fact_rows": _count(conn, "SELECT COUNT(*) FROM fact_machine_hour"),
        "rows_with_csi_overlay": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE csi_source_row_hash IS NOT NULL",
        ),
        "rows_with_mes_overlay": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE mes_source_row_hash IS NOT NULL",
        ),
        "rows_with_good_qty": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE good_qty IS NOT NULL",
        ),
        "rows_with_positive_good_qty": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE good_qty > 0",
        ),
        "rows_with_team_leader": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE team_leader IS NOT NULL AND trim(team_leader) <> ''",
        ),
        "rows_with_material_code": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE material_code IS NOT NULL AND trim(material_code) <> ''",
        ),
        "rows_with_task_name": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE task_name IS NOT NULL AND trim(task_name) <> ''",
        ),
        "rows_with_manpower": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE manpower IS NOT NULL",
        ),
        "rows_with_team_size": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE team_size IS NOT NULL AND team_size > 0",
        ),
        "rows_with_maintenance_history": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE has_maintenance_history = 1",
        ),
        "rows_with_maintenance_txn_in_hour": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE maintenance_txn_in_hour = 1",
        ),
        "rows_with_maintenance_count_30d": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE maintenance_distinct_work_order_count_30d > 0",
        ),
        "rows_with_cumulative_maintenance_count": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE cumulative_maintenance_count > 0",
        ),
        "rows_with_hours_since_last_maintenance": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE hours_since_last_maintenance IS NOT NULL",
        ),
        "rows_with_last_maintenance_work_order_type": _count(
            conn,
            "SELECT COUNT(*) FROM fact_machine_hour WHERE last_maintenance_work_order_type IS NOT NULL AND trim(last_maintenance_work_order_type) <> ''",
        ),
    }


def repair_fact_machine_hour_operational_overlays(
    db_path: str | Path | None = None,
) -> dict[str, object]:
    """Rebuild ML-critical operational overlays on top of an existing Gold backbone.

    This repair path is intentionally narrow:
    - it preserves existing energy totals/backbone rows
    - it reconstructs CSI, MES, and maintenance overlays from the populated Silver tables
    - it resets only overlay-derived Gold columns before reapplying them
    """

    resolved_db_path = str(db_path or get_database_path())
    conn = sqlite3.connect(resolved_db_path)
    try:
        _ensure_fact_machine_hour_columns(conn)
        _ensure_operational_overlay_indexes(conn)
        before = _coverage_snapshot(conn)
        cursor = conn.cursor()
        cursor.execute("PRAGMA temp_store = MEMORY")

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                machine_state = 'energy_only',
                state_confidence = 'low',
                order_id = NULL,
                order_suffix = NULL,
                material_code = NULL,
                task_name = NULL,
                setup_minutes = NULL,
                production_minutes = NULL,
                planned_stop_minutes = NULL,
                unplanned_stop_minutes = NULL,
                maintenance_minutes = NULL,
                idle_minutes = NULL,
                good_qty = NULL,
                scrap_qty = NULL,
                csi_qty_basis_method = NULL,
                csi_qty_row_basis_minutes = NULL,
                csi_qty_event_basis_minutes = NULL,
                csi_qty_minutes_vs_production_diff = NULL,
                csi_qty_minutes_vs_production_abs_diff = NULL,
                csi_qty_alignment_status = NULL,
                csi_qty_material_misalignment_flag = NULL,
                csi_qty_minute_budget_anomaly_flag = NULL,
                csi_qty_minute_budget_anomaly_reason = NULL,
                actual_speed_per_hour = NULL,
                team_leader = NULL,
                csi_source_row_hash = NULL,
                csi_overlap_minutes = NULL,
                multiple_csi_overlap_flag = 0,
                setup_inference_method = NULL,
                setup_confidence = NULL,
                mes_source_row_hash = NULL,
                mes_report_ts = NULL,
                mes_match_method = NULL,
                mes_match_confidence = NULL,
                last_maintenance_txn_ts = NULL,
                last_maintenance_source_row_hash = NULL,
                last_maintenance_work_order_type = NULL,
                team_size = NULL,
                manpower = NULL,
                has_maintenance_history = 0,
                maintenance_txn_in_hour = 0,
                maintenance_distinct_work_order_count_7d = 0,
                maintenance_distinct_work_order_count_30d = 0,
                maintenance_distinct_work_order_in_hour_count = 0,
                cumulative_maintenance_count = 0,
                hours_since_last_maintenance = NULL,
                days_since_last_maintenance = NULL,
                attribution_method = 'energy_only_projection'
            """
        )

        csi_suffix_sql = _normalize_suffix_sql("c.suffix")
        mes_suffix_sql = _normalize_suffix_sql("m.suffix")
        cursor.executescript(
            f"""
            DROP TABLE IF EXISTS temp_task4g_csi_candidate;
            DROP TABLE IF EXISTS temp_task4g_csi_dominant;
            DROP TABLE IF EXISTS temp_task4g_csi_coverage_intervals;
            DROP TABLE IF EXISTS temp_task4g_csi_coverage_points;
            DROP TABLE IF EXISTS temp_task4g_csi_coverage_segments;
            DROP TABLE IF EXISTS temp_task4g_csi_coverage;
            DROP TABLE IF EXISTS temp_task4g_csi_row_blend;
            DROP TABLE IF EXISTS temp_task4g_csi_basis;
            DROP TABLE IF EXISTS temp_task4g_csi_qty_audit;
            DROP TABLE IF EXISTS temp_task4g_mes_match;
            DROP TABLE IF EXISTS temp_task4g_maintenance_latest;
            DROP TABLE IF EXISTS temp_task4g_maintenance_metrics;

            CREATE TEMP TABLE temp_task4g_csi_candidate AS
            WITH base AS (
                SELECT
                    f.canonical_machine_id,
                    f.hour_ts,
                    julianday(f.hour_ts) AS hour_start_jd,
                    julianday(datetime(f.hour_ts, '+1 hour')) AS hour_end_jd,
                    c.source_row_hash,
                    NULLIF(TRIM(c.order_id), '') AS order_id,
                    {csi_suffix_sql} AS order_suffix,
                    NULLIF(TRIM(c.material_code), '') AS material_code,
                    NULLIF(TRIM(c.task_name), '') AS task_name,
                    NULLIF(TRIM(c.team_leader), '') AS team_leader,
                    (
                        CASE
                            WHEN NULLIF(TRIM(c.team_leader), '') IS NOT NULL THEN 1
                            ELSE 0
                        END
                        + CASE
                            WHEN json_valid(c.team_members_raw)
                            THEN COALESCE(json_array_length(c.team_members_raw), 0)
                            ELSE 0
                        END
                    ) AS csi_team_size,
                    c.actual_speed_per_hour,
                    c.good_qty AS event_good_qty,
                    c.scrap_qty AS event_scrap_qty,
                    c.actual_prod_minutes,
                    c.planned_stop_minutes,
                    c.unplanned_stop_minutes,
                    c.actual_changeover_minutes,
                    julianday(c.prod_start_ts) AS prod_start_jd,
                    julianday(c.prep_end_ts) AS prep_end_jd,
                    julianday(c.prod_end_ts) AS prod_end_jd
                FROM fact_machine_hour f
                JOIN csi_job_event c
                  ON c.canonical_machine_id = f.canonical_machine_id
            ),
            computed AS (
                SELECT
                    base.*,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND actual_changeover_minutes IS NOT NULL
                         AND actual_changeover_minutes >= 0
                        THEN prep_end_jd - (actual_changeover_minutes / 1440.0)
                    END AS setup_start_jd,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND actual_changeover_minutes IS NOT NULL
                         AND actual_changeover_minutes >= 0
                         AND prep_end_jd > prep_end_jd - (actual_changeover_minutes / 1440.0)
                        THEN MAX(
                            0.0,
                            (
                                MIN(prep_end_jd, hour_end_jd)
                                - MAX(prep_end_jd - (actual_changeover_minutes / 1440.0), hour_start_jd)
                            ) * 1440.0
                        )
                        ELSE 0.0
                    END AS setup_overlap_minutes,
                    CASE
                        WHEN COALESCE(prep_end_jd, prod_start_jd) IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > COALESCE(prep_end_jd, prod_start_jd)
                        THEN MAX(
                            0.0,
                            (
                                MIN(prod_end_jd, hour_end_jd)
                                - MAX(COALESCE(prep_end_jd, prod_start_jd), hour_start_jd)
                            ) * 1440.0
                        )
                        ELSE 0.0
                    END AS production_overlap_minutes,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                        THEN (prod_end_jd - prep_end_jd) * 1440.0
                    END AS event_window_minutes,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                        THEN MAX(
                            0.0,
                            (
                                MIN(prod_end_jd, hour_end_jd)
                                - MAX(prep_end_jd, hour_start_jd)
                            ) * 1440.0
                        )
                        ELSE 0.0
                    END AS hour_post_setup_overlap_minutes
                FROM base
            ),
            scored AS (
                SELECT
                    computed.*,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND planned_stop_minutes IS NOT NULL
                         AND unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                         AND (
                            actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                        THEN actual_prod_minutes * (hour_post_setup_overlap_minutes / event_window_minutes)
                        ELSE production_overlap_minutes
                    END AS dominant_production_minutes,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND planned_stop_minutes IS NOT NULL
                         AND unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                         AND (
                            actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                        THEN 'csi_fractional_minute_reconciliation'
                        ELSE 'csi_wall_clock_overlap_fallback'
                    END AS minute_attribution_method,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND planned_stop_minutes IS NOT NULL
                         AND unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                         AND (
                            actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes - event_window_minutes
                         ) > MAX(5.0, event_window_minutes * 0.05)
                        THEN 1
                        ELSE 0
                    END AS totals_exceed_window,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND planned_stop_minutes IS NOT NULL
                         AND unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                         AND (
                            actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                        THEN 0
                        ELSE 1
                    END AS used_wall_clock_fallback,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND planned_stop_minutes IS NOT NULL
                         AND unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                         AND (
                            actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                        THEN planned_stop_minutes * (hour_post_setup_overlap_minutes / event_window_minutes)
                    END AS planned_stop_alloc_minutes,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND planned_stop_minutes IS NOT NULL
                         AND unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                         AND (
                            actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                        THEN unplanned_stop_minutes * (hour_post_setup_overlap_minutes / event_window_minutes)
                    END AS unplanned_stop_alloc_minutes
                FROM computed
            ),
            ranked AS (
                SELECT
                    scored.*,
                    setup_overlap_minutes + production_overlap_minutes AS total_overlap_minutes,
                    ROW_NUMBER() OVER (
                        PARTITION BY canonical_machine_id, hour_ts
                        ORDER BY
                            setup_overlap_minutes + production_overlap_minutes DESC,
                            production_overlap_minutes DESC,
                            source_row_hash
                    ) AS rn,
                    COUNT(*) OVER (
                        PARTITION BY canonical_machine_id, hour_ts
                    ) AS overlap_candidate_count
                FROM scored
                WHERE (setup_overlap_minutes + production_overlap_minutes) > 0
            )
            SELECT
                canonical_machine_id,
                hour_ts,
                source_row_hash,
                order_id,
                order_suffix,
                material_code,
                task_name,
                team_leader,
                csi_team_size,
                actual_speed_per_hour,
                setup_overlap_minutes,
                dominant_production_minutes,
                planned_stop_alloc_minutes,
                unplanned_stop_alloc_minutes,
                total_overlap_minutes,
                event_good_qty,
                event_scrap_qty,
                overlap_candidate_count,
                minute_attribution_method,
                totals_exceed_window,
                used_wall_clock_fallback,
                CASE
                    WHEN setup_start_jd IS NOT NULL
                     AND prep_end_jd IS NOT NULL
                    THEN MAX(setup_start_jd, hour_start_jd)
                END AS setup_interval_start_jd,
                CASE
                    WHEN setup_start_jd IS NOT NULL
                     AND prep_end_jd IS NOT NULL
                    THEN MIN(prep_end_jd, hour_end_jd)
                END AS setup_interval_end_jd,
                CASE
                    WHEN COALESCE(prep_end_jd, prod_start_jd) IS NOT NULL
                     AND prod_end_jd IS NOT NULL
                    THEN MAX(COALESCE(prep_end_jd, prod_start_jd), hour_start_jd)
                END AS production_interval_start_jd,
                CASE
                    WHEN COALESCE(prep_end_jd, prod_start_jd) IS NOT NULL
                     AND prod_end_jd IS NOT NULL
                    THEN MIN(prod_end_jd, hour_end_jd)
                END AS production_interval_end_jd,
                rn,
                setup_inference_method,
                setup_confidence
            FROM (
                SELECT
                    ranked.*,
                    CASE
                        WHEN setup_overlap_minutes > 0 THEN 'csi_prep_end_minus_actual_changeover_minutes'
                    END AS setup_inference_method,
                    CASE
                        WHEN setup_overlap_minutes > 0 THEN 'high'
                    END AS setup_confidence
                FROM ranked
            );

            CREATE INDEX temp_idx_task4g_csi_candidate_key
                ON temp_task4g_csi_candidate (canonical_machine_id, hour_ts);

            CREATE TEMP TABLE temp_task4g_csi_coverage_intervals AS
            SELECT
                canonical_machine_id,
                hour_ts,
                setup_interval_start_jd AS interval_start_jd,
                setup_interval_end_jd AS interval_end_jd
            FROM temp_task4g_csi_candidate
            WHERE setup_interval_start_jd IS NOT NULL
              AND setup_interval_end_jd IS NOT NULL
              AND setup_interval_end_jd > setup_interval_start_jd
            UNION ALL
            SELECT
                canonical_machine_id,
                hour_ts,
                production_interval_start_jd AS interval_start_jd,
                production_interval_end_jd AS interval_end_jd
            FROM temp_task4g_csi_candidate
            WHERE production_interval_start_jd IS NOT NULL
              AND production_interval_end_jd IS NOT NULL
              AND production_interval_end_jd > production_interval_start_jd;

            CREATE TEMP TABLE temp_task4g_csi_coverage_points AS
            SELECT canonical_machine_id, hour_ts, interval_start_jd AS point_jd
            FROM temp_task4g_csi_coverage_intervals
            UNION
            SELECT canonical_machine_id, hour_ts, interval_end_jd AS point_jd
            FROM temp_task4g_csi_coverage_intervals;

            CREATE TEMP TABLE temp_task4g_csi_coverage_segments AS
            SELECT
                canonical_machine_id,
                hour_ts,
                point_jd,
                LEAD(point_jd) OVER (
                    PARTITION BY canonical_machine_id, hour_ts
                    ORDER BY point_jd
                ) AS next_point_jd
            FROM temp_task4g_csi_coverage_points;

            CREATE TEMP TABLE temp_task4g_csi_coverage AS
            SELECT
                s.canonical_machine_id,
                s.hour_ts,
                MIN(
                    60.0,
                    SUM(
                        CASE
                            WHEN s.next_point_jd IS NOT NULL
                             AND EXISTS (
                                SELECT 1
                                FROM temp_task4g_csi_coverage_intervals i
                                WHERE i.canonical_machine_id = s.canonical_machine_id
                                  AND i.hour_ts = s.hour_ts
                                  AND i.interval_start_jd < s.next_point_jd
                                  AND i.interval_end_jd > s.point_jd
                             )
                            THEN (s.next_point_jd - s.point_jd) * 1440.0
                            ELSE 0.0
                        END
                    )
                ) AS coverage_minutes
            FROM temp_task4g_csi_coverage_segments s
            GROUP BY s.canonical_machine_id, s.hour_ts;

            CREATE INDEX temp_idx_task4g_csi_coverage_key
                ON temp_task4g_csi_coverage (canonical_machine_id, hour_ts);

            CREATE TEMP TABLE temp_task4g_csi_row_blend AS
            WITH row_sums AS (
                SELECT
                    c.canonical_machine_id,
                    c.hour_ts,
                    c.overlap_candidate_count,
                    SUM(c.setup_overlap_minutes) AS raw_setup_minutes,
                    SUM(COALESCE(c.dominant_production_minutes, 0.0)) AS raw_production_minutes,
                    SUM(COALESCE(c.planned_stop_alloc_minutes, 0.0)) AS raw_planned_stop_minutes,
                    SUM(COALESCE(c.unplanned_stop_alloc_minutes, 0.0)) AS raw_unplanned_stop_minutes,
                    SUM(
                        c.setup_overlap_minutes
                        + COALESCE(c.dominant_production_minutes, 0.0)
                        + COALESCE(c.planned_stop_alloc_minutes, 0.0)
                        + COALESCE(c.unplanned_stop_alloc_minutes, 0.0)
                    ) AS raw_assigned_minutes,
                    COALESCE(cv.coverage_minutes, 0.0) AS coverage_minutes,
                    MIN(
                        CASE
                            WHEN c.minute_attribution_method = 'csi_fractional_minute_reconciliation'
                             AND COALESCE(c.used_wall_clock_fallback, 0) = 0
                             AND COALESCE(c.totals_exceed_window, 0) = 0
                            THEN 1
                            ELSE 0
                        END
                    ) AS all_minutes_fractional,
                    MAX(CASE WHEN COALESCE(c.totals_exceed_window, 0) = 1 THEN 1 ELSE 0 END) AS any_totals_exceed_window
                FROM temp_task4g_csi_candidate c
                LEFT JOIN temp_task4g_csi_coverage cv
                  ON cv.canonical_machine_id = c.canonical_machine_id
                 AND cv.hour_ts = c.hour_ts
                GROUP BY
                    c.canonical_machine_id,
                    c.hour_ts,
                    c.overlap_candidate_count,
                    cv.coverage_minutes
            )
            SELECT
                canonical_machine_id,
                hour_ts,
                overlap_candidate_count,
                raw_setup_minutes,
                raw_production_minutes,
                raw_planned_stop_minutes,
                raw_unplanned_stop_minutes,
                raw_assigned_minutes,
                coverage_minutes,
                CASE
                    WHEN raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN coverage_minutes / raw_assigned_minutes
                    ELSE 1.0
                END AS scale_factor,
                CASE
                    WHEN raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN 1
                    ELSE 0
                END AS competing_overlap,
                CASE
                    WHEN overlap_candidate_count > 1
                     AND raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN 'multi_event_sum_capped_to_coverage_budget'
                    WHEN overlap_candidate_count > 1
                    THEN 'multi_event_sum_within_coverage_budget'
                    ELSE 'dominant_event_passthrough'
                END AS minute_contract,
                raw_setup_minutes * CASE
                    WHEN raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN coverage_minutes / raw_assigned_minutes
                    ELSE 1.0
                END AS setup_minutes,
                raw_production_minutes * CASE
                    WHEN raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN coverage_minutes / raw_assigned_minutes
                    ELSE 1.0
                END AS production_minutes,
                raw_planned_stop_minutes * CASE
                    WHEN raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN coverage_minutes / raw_assigned_minutes
                    ELSE 1.0
                END AS planned_stop_minutes,
                raw_unplanned_stop_minutes * CASE
                    WHEN raw_assigned_minutes > coverage_minutes
                     AND raw_assigned_minutes > 0
                    THEN coverage_minutes / raw_assigned_minutes
                    ELSE 1.0
                END AS unplanned_stop_minutes,
                all_minutes_fractional,
                any_totals_exceed_window
            FROM row_sums;

            CREATE INDEX temp_idx_task4g_csi_row_blend_key
                ON temp_task4g_csi_row_blend (canonical_machine_id, hour_ts);

            CREATE TEMP TABLE temp_task4g_csi_dominant AS
            SELECT
                c.canonical_machine_id,
                c.hour_ts,
                c.source_row_hash,
                c.order_id,
                c.order_suffix,
                c.material_code,
                c.task_name,
                c.team_leader,
                c.csi_team_size,
                c.actual_speed_per_hour,
                c.dominant_production_minutes,
                c.event_good_qty,
                c.event_scrap_qty,
                c.overlap_candidate_count,
                CASE
                    WHEN b.setup_minutes > 0 THEN 'setup_changeover'
                    WHEN b.production_minutes > 0 THEN 'production'
                    WHEN b.planned_stop_minutes > 0 THEN 'planned_stop'
                    WHEN b.unplanned_stop_minutes > 0 THEN 'unplanned_stop'
                END AS machine_state,
                CASE
                    WHEN b.setup_minutes > 0
                      OR b.production_minutes > 0
                      OR b.planned_stop_minutes > 0
                      OR b.unplanned_stop_minutes > 0
                    THEN CASE
                        WHEN c.overlap_candidate_count > 1 THEN 'medium'
                        ELSE 'high'
                    END
                END AS state_confidence,
                c.setup_inference_method,
                c.setup_confidence
            FROM temp_task4g_csi_candidate c
            JOIN temp_task4g_csi_row_blend b
              ON b.canonical_machine_id = c.canonical_machine_id
             AND b.hour_ts = c.hour_ts
            WHERE c.rn = 1;

            CREATE INDEX temp_idx_task4g_csi_dominant_key
                ON temp_task4g_csi_dominant (canonical_machine_id, hour_ts);

            CREATE TEMP TABLE temp_task4g_csi_basis AS
            SELECT
                source_row_hash,
                SUM(
                    CASE
                        WHEN dominant_production_minutes IS NOT NULL AND dominant_production_minutes > 0
                        THEN dominant_production_minutes
                        ELSE 0.0
                    END
                ) AS basis_minutes
            FROM temp_task4g_csi_dominant
            GROUP BY source_row_hash;

            CREATE INDEX temp_idx_task4g_csi_basis_hash
                ON temp_task4g_csi_basis (source_row_hash);

            CREATE TEMP TABLE temp_task4g_csi_qty_audit AS
            SELECT
                d.canonical_machine_id,
                d.hour_ts,
                'csi_dominant_event_production_minutes_share' AS csi_qty_basis_method,
                d.dominant_production_minutes AS csi_qty_row_basis_minutes,
                b.basis_minutes AS csi_qty_event_basis_minutes,
                CASE
                    WHEN NULLIF(rb.production_minutes, 0.0) IS NOT NULL
                     AND d.dominant_production_minutes IS NOT NULL
                    THEN NULLIF(rb.production_minutes, 0.0) - d.dominant_production_minutes
                END AS csi_qty_minutes_vs_production_diff,
                CASE
                    WHEN NULLIF(rb.production_minutes, 0.0) IS NOT NULL
                     AND d.dominant_production_minutes IS NOT NULL
                    THEN ABS(NULLIF(rb.production_minutes, 0.0) - d.dominant_production_minutes)
                END AS csi_qty_minutes_vs_production_abs_diff,
                CASE
                    WHEN d.dominant_production_minutes IS NULL
                      OR d.dominant_production_minutes <= 0
                    THEN 'missing_positive_row_basis_minutes'
                    WHEN NULLIF(rb.production_minutes, 0.0) IS NULL
                    THEN 'missing_row_production_minutes'
                    WHEN d.event_good_qty IS NULL
                      AND d.event_scrap_qty IS NULL
                    THEN 'no_quantity_allocated'
                    WHEN ABS(NULLIF(rb.production_minutes, 0.0) - d.dominant_production_minutes)
                         > {CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES}
                    THEN 'material_misaligned'
                    ELSE 'aligned'
                END AS csi_qty_alignment_status,
                CASE
                    WHEN d.dominant_production_minutes IS NOT NULL
                     AND d.dominant_production_minutes > 0
                     AND NULLIF(rb.production_minutes, 0.0) IS NOT NULL
                     AND (d.event_good_qty IS NOT NULL OR d.event_scrap_qty IS NOT NULL)
                     AND ABS(NULLIF(rb.production_minutes, 0.0) - d.dominant_production_minutes)
                         > {CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES}
                    THEN 1
                    ELSE 0
                END AS csi_qty_material_misalignment_flag,
                CASE
                    WHEN rb.production_minutes > 60.0 THEN 1
                    WHEN COALESCE(rb.setup_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                      OR COALESCE(rb.production_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                      OR COALESCE(rb.planned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                      OR COALESCE(rb.unplanned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                    THEN 1
                    WHEN (
                        COALESCE(rb.setup_minutes, 0.0)
                        + COALESCE(rb.production_minutes, 0.0)
                        + COALESCE(rb.planned_stop_minutes, 0.0)
                        + COALESCE(rb.unplanned_stop_minutes, 0.0)
                    ) > 60.0 + {CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                    THEN 1
                    ELSE 0
                END AS csi_qty_minute_budget_anomaly_flag,
                CASE
                    WHEN rb.production_minutes > 60.0 THEN 'production_minutes_gt_60'
                    WHEN COALESCE(rb.setup_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                      OR COALESCE(rb.production_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                      OR COALESCE(rb.planned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                      OR COALESCE(rb.unplanned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                    THEN 'negative_operational_minutes'
                    WHEN (
                        COALESCE(rb.setup_minutes, 0.0)
                        + COALESCE(rb.production_minutes, 0.0)
                        + COALESCE(rb.planned_stop_minutes, 0.0)
                        + COALESCE(rb.unplanned_stop_minutes, 0.0)
                    ) > 60.0 + {CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                    THEN 'operational_minutes_exceed_hour_budget'
                END AS csi_qty_minute_budget_anomaly_reason
            FROM temp_task4g_csi_dominant d
            JOIN temp_task4g_csi_row_blend rb
              ON rb.canonical_machine_id = d.canonical_machine_id
             AND rb.hour_ts = d.hour_ts
            LEFT JOIN temp_task4g_csi_basis b
              ON b.source_row_hash = d.source_row_hash;

            CREATE INDEX temp_idx_task4g_csi_qty_audit_key
                ON temp_task4g_csi_qty_audit (canonical_machine_id, hour_ts);
            """
        )

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                machine_state = (
                    SELECT d.machine_state
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                state_confidence = (
                    SELECT d.state_confidence
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                order_id = (
                    SELECT d.order_id
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                order_suffix = (
                    SELECT d.order_suffix
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                material_code = (
                    SELECT d.material_code
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                task_name = (
                    SELECT d.task_name
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                setup_minutes = (
                    SELECT NULLIF(b.setup_minutes, 0.0)
                    FROM temp_task4g_csi_row_blend b
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                production_minutes = (
                    SELECT NULLIF(b.production_minutes, 0.0)
                    FROM temp_task4g_csi_row_blend b
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                planned_stop_minutes = (
                    SELECT NULLIF(b.planned_stop_minutes, 0.0)
                    FROM temp_task4g_csi_row_blend b
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                unplanned_stop_minutes = (
                    SELECT NULLIF(b.unplanned_stop_minutes, 0.0)
                    FROM temp_task4g_csi_row_blend b
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                actual_speed_per_hour = (
                    SELECT d.actual_speed_per_hour
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                team_leader = (
                    SELECT d.team_leader
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                team_size = (
                    SELECT CASE
                        WHEN d.csi_team_size > 0 THEN d.csi_team_size
                    END
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_source_row_hash = (
                    SELECT d.source_row_hash
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_overlap_minutes = (
                    SELECT b.coverage_minutes
                    FROM temp_task4g_csi_row_blend b
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                multiple_csi_overlap_flag = (
                    SELECT CASE WHEN d.overlap_candidate_count > 1 THEN 1 ELSE 0 END
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                setup_inference_method = (
                    SELECT d.setup_inference_method
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                setup_confidence = (
                    SELECT d.setup_confidence
                    FROM temp_task4g_csi_dominant d
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                attribution_method = 'energy_csi_overlay'
            WHERE EXISTS (
                SELECT 1
                FROM temp_task4g_csi_dominant d
                WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                  AND d.hour_ts = fact_machine_hour.hour_ts
            )
            """
        )

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                good_qty = (
                    SELECT CASE
                        WHEN d.dominant_production_minutes IS NOT NULL
                         AND d.dominant_production_minutes > 0
                         AND b.basis_minutes > 0
                         AND d.event_good_qty IS NOT NULL
                        THEN d.event_good_qty * d.dominant_production_minutes / b.basis_minutes
                    END
                    FROM temp_task4g_csi_dominant d
                    JOIN temp_task4g_csi_basis b
                      ON b.source_row_hash = d.source_row_hash
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                scrap_qty = (
                    SELECT CASE
                        WHEN d.dominant_production_minutes IS NOT NULL
                         AND d.dominant_production_minutes > 0
                         AND b.basis_minutes > 0
                         AND d.event_scrap_qty IS NOT NULL
                        THEN d.event_scrap_qty * d.dominant_production_minutes / b.basis_minutes
                    END
                    FROM temp_task4g_csi_dominant d
                    JOIN temp_task4g_csi_basis b
                      ON b.source_row_hash = d.source_row_hash
                    WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND d.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_basis_method = (
                    SELECT a.csi_qty_basis_method
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_row_basis_minutes = (
                    SELECT a.csi_qty_row_basis_minutes
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_event_basis_minutes = (
                    SELECT a.csi_qty_event_basis_minutes
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minutes_vs_production_diff = (
                    SELECT a.csi_qty_minutes_vs_production_diff
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minutes_vs_production_abs_diff = (
                    SELECT a.csi_qty_minutes_vs_production_abs_diff
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_alignment_status = (
                    SELECT a.csi_qty_alignment_status
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_material_misalignment_flag = (
                    SELECT a.csi_qty_material_misalignment_flag
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minute_budget_anomaly_flag = (
                    SELECT a.csi_qty_minute_budget_anomaly_flag
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minute_budget_anomaly_reason = (
                    SELECT a.csi_qty_minute_budget_anomaly_reason
                    FROM temp_task4g_csi_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                )
            WHERE EXISTS (
                SELECT 1
                FROM temp_task4g_csi_dominant d
                JOIN temp_task4g_csi_basis b
                  ON b.source_row_hash = d.source_row_hash
                WHERE d.canonical_machine_id = fact_machine_hour.canonical_machine_id
                  AND d.hour_ts = fact_machine_hour.hour_ts
            )
            """
        )

        cursor.executescript(
            f"""
            CREATE TEMP TABLE temp_task4g_mes_match AS
            WITH mes_ranked AS (
                SELECT
                    f.canonical_machine_id,
                    f.hour_ts,
                    m.source_row_hash,
                    m.report_ts,
                    m.manpower,
                    CASE
                        WHEN m.manpower IS NOT NULL AND m.manpower > 0
                        THEN ROUND(m.manpower)
                    END AS team_size,
                    CASE
                        WHEN SUM(
                            CASE
                                WHEN m.manpower IS NOT NULL AND m.manpower > 0 THEN 1
                                ELSE 0
                            END
                        ) OVER (PARTITION BY f.canonical_machine_id, f.hour_ts) > 0
                        THEN 'canonical_order_suffix_same_date_prefer_positive_manpower_then_closest_hour_end'
                        ELSE 'canonical_order_suffix_same_date_closest_hour_end'
                    END AS match_method,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.canonical_machine_id, f.hour_ts
                        ORDER BY
                            CASE
                                WHEN m.manpower IS NOT NULL AND m.manpower > 0 THEN 0
                                ELSE 1
                            END,
                            ABS((julianday(m.report_ts) - julianday(datetime(f.hour_ts, '+1 hour'))) * 86400.0),
                            m.source_row_hash
                    ) AS rn
                FROM fact_machine_hour f
                JOIN mes_report_event m
                  ON m.canonical_machine_id = f.canonical_machine_id
                 AND NULLIF(TRIM(m.order_id), '') = f.order_id
                 AND {mes_suffix_sql} = f.order_suffix
                 AND date(m.report_ts) = date(f.hour_ts)
                WHERE f.order_id IS NOT NULL
                  AND f.order_suffix IS NOT NULL
            )
            SELECT
                canonical_machine_id,
                hour_ts,
                source_row_hash,
                report_ts,
                manpower,
                team_size,
                match_method
            FROM mes_ranked
            WHERE rn = 1;

            CREATE INDEX temp_idx_task4g_mes_match_key
                ON temp_task4g_mes_match (canonical_machine_id, hour_ts);
            """
        )

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                manpower = (
                    SELECT m.manpower
                    FROM temp_task4g_mes_match m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                team_size = (
                    SELECT COALESCE(m.team_size, fact_machine_hour.team_size)
                    FROM temp_task4g_mes_match m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                mes_source_row_hash = (
                    SELECT m.source_row_hash
                    FROM temp_task4g_mes_match m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                mes_report_ts = (
                    SELECT m.report_ts
                    FROM temp_task4g_mes_match m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                mes_match_method = (
                    SELECT m.match_method
                    FROM temp_task4g_mes_match m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                mes_match_confidence = 'high',
                attribution_method = 'energy_csi_mes_overlay'
            WHERE EXISTS (
                SELECT 1
                FROM temp_task4g_mes_match m
                WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                  AND m.hour_ts = fact_machine_hour.hour_ts
            )
            """
        )

        cursor.executescript(
            """
            CREATE TEMP TABLE temp_task4g_maintenance_latest AS
            WITH maintenance_ranked AS (
                SELECT
                    f.canonical_machine_id,
                    f.hour_ts,
                    m.txn_ts,
                    m.source_row_hash,
                    m.work_order_type,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.canonical_machine_id, f.hour_ts
                        ORDER BY m.txn_ts DESC, m.source_row_hash DESC
                    ) AS rn
                FROM fact_machine_hour f
                JOIN maintenance_txn_event m
                  ON m.canonical_machine_id = f.canonical_machine_id
                 AND julianday(m.txn_ts) < julianday(f.hour_ts)
            )
            SELECT
                canonical_machine_id,
                hour_ts,
                txn_ts,
                source_row_hash,
                work_order_type
            FROM maintenance_ranked
            WHERE rn = 1;

            CREATE INDEX temp_idx_task4g_maintenance_key
                ON temp_task4g_maintenance_latest (canonical_machine_id, hour_ts);
            """
        )

        cursor.executescript(
            """
            CREATE TEMP TABLE temp_task4g_maintenance_metrics AS
            SELECT
                f.canonical_machine_id,
                f.hour_ts,
                MAX(
                    CASE
                        WHEN julianday(m.txn_ts) < julianday(f.hour_ts)
                        THEN 1 ELSE 0
                    END
                ) AS has_maintenance_history,
                MAX(
                    CASE
                        WHEN julianday(m.txn_ts) >= julianday(f.hour_ts)
                         AND julianday(m.txn_ts) < julianday(datetime(f.hour_ts, '+1 hour'))
                        THEN 1 ELSE 0
                    END
                ) AS maintenance_txn_in_hour,
                COUNT(
                    DISTINCT CASE
                        WHEN julianday(m.txn_ts) >= julianday(datetime(f.hour_ts, '-7 day'))
                         AND julianday(m.txn_ts) < julianday(f.hour_ts)
                        THEN COALESCE(NULLIF(TRIM(m.work_order_id), ''), m.source_row_hash)
                    END
                ) AS maintenance_distinct_work_order_count_7d,
                COUNT(
                    DISTINCT CASE
                        WHEN julianday(m.txn_ts) >= julianday(datetime(f.hour_ts, '-30 day'))
                         AND julianday(m.txn_ts) < julianday(f.hour_ts)
                        THEN COALESCE(NULLIF(TRIM(m.work_order_id), ''), m.source_row_hash)
                    END
                ) AS maintenance_distinct_work_order_count_30d,
                COUNT(
                    DISTINCT CASE
                        WHEN julianday(m.txn_ts) >= julianday(f.hour_ts)
                         AND julianday(m.txn_ts) < julianday(datetime(f.hour_ts, '+1 hour'))
                        THEN COALESCE(NULLIF(TRIM(m.work_order_id), ''), m.source_row_hash)
                    END
                ) AS maintenance_distinct_work_order_in_hour_count,
                COUNT(
                    DISTINCT CASE
                        WHEN julianday(m.txn_ts) < julianday(f.hour_ts)
                        THEN COALESCE(NULLIF(TRIM(m.work_order_id), ''), m.source_row_hash)
                    END
                ) AS cumulative_maintenance_count
            FROM fact_machine_hour f
            LEFT JOIN maintenance_txn_event m
              ON m.canonical_machine_id = f.canonical_machine_id
             AND julianday(m.txn_ts) < julianday(datetime(f.hour_ts, '+1 hour'))
            GROUP BY f.canonical_machine_id, f.hour_ts;

            CREATE INDEX temp_idx_task4g_maintenance_metrics_key
                ON temp_task4g_maintenance_metrics (canonical_machine_id, hour_ts);
            """
        )

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                last_maintenance_txn_ts = (
                    SELECT m.txn_ts
                    FROM temp_task4g_maintenance_latest m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                last_maintenance_source_row_hash = (
                    SELECT m.source_row_hash
                    FROM temp_task4g_maintenance_latest m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                last_maintenance_work_order_type = (
                    SELECT m.work_order_type
                    FROM temp_task4g_maintenance_latest m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                hours_since_last_maintenance = (
                    SELECT (julianday(fact_machine_hour.hour_ts) - julianday(m.txn_ts)) * 24.0
                    FROM temp_task4g_maintenance_latest m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                days_since_last_maintenance = (
                    SELECT (julianday(fact_machine_hour.hour_ts) - julianday(m.txn_ts))
                    FROM temp_task4g_maintenance_latest m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                has_maintenance_history = (
                    SELECT m.has_maintenance_history
                    FROM temp_task4g_maintenance_metrics m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                maintenance_txn_in_hour = (
                    SELECT m.maintenance_txn_in_hour
                    FROM temp_task4g_maintenance_metrics m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                maintenance_distinct_work_order_count_7d = (
                    SELECT m.maintenance_distinct_work_order_count_7d
                    FROM temp_task4g_maintenance_metrics m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                maintenance_distinct_work_order_count_30d = (
                    SELECT m.maintenance_distinct_work_order_count_30d
                    FROM temp_task4g_maintenance_metrics m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                maintenance_distinct_work_order_in_hour_count = (
                    SELECT m.maintenance_distinct_work_order_in_hour_count
                    FROM temp_task4g_maintenance_metrics m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                ),
                cumulative_maintenance_count = (
                    SELECT m.cumulative_maintenance_count
                    FROM temp_task4g_maintenance_metrics m
                    WHERE m.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND m.hour_ts = fact_machine_hour.hour_ts
                )
            """
        )

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                idle_minutes = (
                    SELECT CASE
                        WHEN COALESCE(metrics.maintenance_txn_in_hour, 0) != 0 THEN NULL
                        WHEN COALESCE(b.all_minutes_fractional, 0) = 0 THEN NULL
                        WHEN COALESCE(b.coverage_minutes, 0.0) < 59.5 THEN NULL
                        WHEN ABS(
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        ) < 0.5
                        THEN 0.0
                        WHEN (
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        ) > 0
                        THEN (
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        )
                        ELSE NULL
                    END
                    FROM temp_task4g_csi_row_blend b
                    LEFT JOIN temp_task4g_maintenance_metrics metrics
                      ON metrics.canonical_machine_id = b.canonical_machine_id
                     AND metrics.hour_ts = b.hour_ts
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                machine_state = (
                    SELECT CASE
                        WHEN fact_machine_hour.machine_state IS NOT NULL THEN fact_machine_hour.machine_state
                        WHEN COALESCE(metrics.maintenance_txn_in_hour, 0) != 0 THEN fact_machine_hour.machine_state
                        WHEN COALESCE(b.all_minutes_fractional, 0) = 0 THEN fact_machine_hour.machine_state
                        WHEN COALESCE(b.coverage_minutes, 0.0) < 59.5 THEN fact_machine_hour.machine_state
                        WHEN (
                            COALESCE(fact_machine_hour.setup_minutes, 0.0)
                            + COALESCE(fact_machine_hour.production_minutes, 0.0)
                            + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                            + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                        ) > 0 THEN fact_machine_hour.machine_state
                        WHEN ABS(
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        ) < 0.5 THEN fact_machine_hour.machine_state
                        WHEN (
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        ) > 0 THEN 'idle'
                        ELSE fact_machine_hour.machine_state
                    END
                    FROM temp_task4g_csi_row_blend b
                    LEFT JOIN temp_task4g_maintenance_metrics metrics
                      ON metrics.canonical_machine_id = b.canonical_machine_id
                     AND metrics.hour_ts = b.hour_ts
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                ),
                state_confidence = (
                    SELECT CASE
                        WHEN fact_machine_hour.machine_state IS NOT NULL THEN fact_machine_hour.state_confidence
                        WHEN COALESCE(metrics.maintenance_txn_in_hour, 0) != 0 THEN fact_machine_hour.state_confidence
                        WHEN COALESCE(b.all_minutes_fractional, 0) = 0 THEN fact_machine_hour.state_confidence
                        WHEN COALESCE(b.coverage_minutes, 0.0) < 59.5 THEN fact_machine_hour.state_confidence
                        WHEN (
                            COALESCE(fact_machine_hour.setup_minutes, 0.0)
                            + COALESCE(fact_machine_hour.production_minutes, 0.0)
                            + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                            + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                        ) > 0 THEN fact_machine_hour.state_confidence
                        WHEN ABS(
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        ) < 0.5 THEN fact_machine_hour.state_confidence
                        WHEN (
                            60.0 - (
                                COALESCE(fact_machine_hour.setup_minutes, 0.0)
                                + COALESCE(fact_machine_hour.production_minutes, 0.0)
                                + COALESCE(fact_machine_hour.planned_stop_minutes, 0.0)
                                + COALESCE(fact_machine_hour.unplanned_stop_minutes, 0.0)
                            )
                        ) > 0 THEN 'high'
                        ELSE fact_machine_hour.state_confidence
                    END
                    FROM temp_task4g_csi_row_blend b
                    LEFT JOIN temp_task4g_maintenance_metrics metrics
                      ON metrics.canonical_machine_id = b.canonical_machine_id
                     AND metrics.hour_ts = b.hour_ts
                    WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND b.hour_ts = fact_machine_hour.hour_ts
                )
            WHERE EXISTS (
                SELECT 1
                FROM temp_task4g_csi_row_blend b
                WHERE b.canonical_machine_id = fact_machine_hour.canonical_machine_id
                  AND b.hour_ts = fact_machine_hour.hour_ts
            )
            """
        )

        conn.commit()
        after = _coverage_snapshot(conn)
        return {
            "db_path": resolved_db_path,
            "before": before,
            "after": after,
            "delta": {key: after[key] - before.get(key, 0) for key in after},
            "csi_dominant_rows": _count(conn, "SELECT COUNT(*) FROM temp_task4g_csi_dominant"),
            "mes_match_rows": _count(conn, "SELECT COUNT(*) FROM temp_task4g_mes_match"),
            "maintenance_latest_rows": _count(conn, "SELECT COUNT(*) FROM temp_task4g_maintenance_latest"),
            "maintenance_metrics_rows": _count(conn, "SELECT COUNT(*) FROM temp_task4g_maintenance_metrics"),
        }
    finally:
        conn.close()


def repair_fact_machine_hour_quantity_audit_metadata(
    db_path: str | Path | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
    overlap_only: bool = True,
    quantity_rows_only: bool = True,
) -> dict[str, object]:
    """Backfill quantity-audit metadata onto existing Gold rows without changing quantities or minutes."""

    resolved_db_path = str(db_path or get_database_path())
    conn = sqlite3.connect(resolved_db_path)
    try:
        _ensure_fact_machine_hour_columns(conn)
        cursor = conn.cursor()
        scope_clauses = ["csi_source_row_hash IS NOT NULL"]
        aliased_scope_clauses = ["f.csi_source_row_hash IS NOT NULL"]
        if start_ts is not None:
            literal = _sql_text_literal(start_ts)
            scope_clauses.append(f"hour_ts >= {literal}")
            aliased_scope_clauses.append(f"f.hour_ts >= {literal}")
        if end_ts is not None:
            literal = _sql_text_literal(end_ts)
            scope_clauses.append(f"hour_ts < {literal}")
            aliased_scope_clauses.append(f"f.hour_ts < {literal}")
        if overlap_only:
            scope_clauses.append("multiple_csi_overlap_flag = 1")
            aliased_scope_clauses.append("f.multiple_csi_overlap_flag = 1")
        if quantity_rows_only:
            quantity_scope = "(good_qty IS NOT NULL OR scrap_qty IS NOT NULL)"
            scope_clauses.append(quantity_scope)
            aliased_scope_clauses.append(f"(f.good_qty IS NOT NULL OR f.scrap_qty IS NOT NULL)")
        scope_sql = " AND ".join(scope_clauses)
        aliased_scope_sql = " AND ".join(aliased_scope_clauses)

        cursor.executescript(
            f"""
            DROP TABLE IF EXISTS temp_task4r_qty_basis_row;
            DROP TABLE IF EXISTS temp_task4r_qty_event_basis;
            DROP TABLE IF EXISTS temp_task4r_qty_audit;

            CREATE TEMP TABLE temp_task4r_qty_basis_row AS
            WITH base AS (
                SELECT
                    f.canonical_machine_id,
                    f.hour_ts,
                    f.csi_source_row_hash AS source_row_hash,
                    f.csi_qty_row_basis_minutes AS existing_landed_basis_minutes,
                    f.setup_minutes AS row_setup_minutes,
                    f.production_minutes AS row_production_minutes,
                    f.planned_stop_minutes AS row_planned_stop_minutes,
                    f.unplanned_stop_minutes AS row_unplanned_stop_minutes,
                    CASE
                        WHEN json_valid(f.source_flags)
                        THEN CAST(json_extract(f.source_flags, '$.csi_dominant_production_minutes') AS REAL)
                    END AS source_flag_dominant_production_minutes,
                    CASE
                        WHEN json_valid(f.source_flags)
                        THEN CAST(json_extract(f.source_flags, '$.dominant_csi_source_row_hash') AS TEXT)
                    END AS source_flag_dominant_source_row_hash,
                    julianday(f.hour_ts) AS hour_start_jd,
                    julianday(datetime(f.hour_ts, '+1 hour')) AS hour_end_jd,
                    c.actual_prod_minutes,
                    c.planned_stop_minutes AS csi_planned_stop_minutes,
                    c.unplanned_stop_minutes AS csi_unplanned_stop_minutes,
                    c.actual_changeover_minutes,
                    julianday(c.prod_start_ts) AS prod_start_jd,
                    julianday(c.prep_end_ts) AS prep_end_jd,
                    julianday(c.prod_end_ts) AS prod_end_jd
                FROM fact_machine_hour f
                LEFT JOIN csi_job_event c
                  ON c.source_row_hash = f.csi_source_row_hash
                WHERE {aliased_scope_sql}
            ),
            computed AS (
                SELECT
                    base.*,
                    CASE
                        WHEN row_production_minutes > 60.0 THEN 1
                        WHEN COALESCE(row_setup_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                          OR COALESCE(row_production_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                          OR COALESCE(row_planned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                          OR COALESCE(row_unplanned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                        THEN 1
                        WHEN (
                            COALESCE(row_setup_minutes, 0.0)
                            + COALESCE(row_production_minutes, 0.0)
                            + COALESCE(row_planned_stop_minutes, 0.0)
                            + COALESCE(row_unplanned_stop_minutes, 0.0)
                        ) > 60.0 + {CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                        THEN 1
                        ELSE 0
                    END AS minute_budget_anomaly_flag,
                    CASE
                        WHEN row_production_minutes > 60.0 THEN 'production_minutes_gt_60'
                        WHEN COALESCE(row_setup_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                          OR COALESCE(row_production_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                          OR COALESCE(row_planned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                          OR COALESCE(row_unplanned_stop_minutes, 0.0) < -{CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                        THEN 'negative_operational_minutes'
                        WHEN (
                            COALESCE(row_setup_minutes, 0.0)
                            + COALESCE(row_production_minutes, 0.0)
                            + COALESCE(row_planned_stop_minutes, 0.0)
                            + COALESCE(row_unplanned_stop_minutes, 0.0)
                        ) > 60.0 + {CSI_MINUTE_BUDGET_TOLERANCE_MINUTES}
                        THEN 'operational_minutes_exceed_hour_budget'
                    END AS minute_budget_anomaly_reason,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND actual_changeover_minutes IS NOT NULL
                         AND actual_changeover_minutes >= 0
                        THEN prep_end_jd - (actual_changeover_minutes / 1440.0)
                    END AS setup_start_jd,
                    CASE
                        WHEN COALESCE(prep_end_jd, prod_start_jd) IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > COALESCE(prep_end_jd, prod_start_jd)
                        THEN MAX(
                            0.0,
                            (
                                MIN(prod_end_jd, hour_end_jd)
                                - MAX(COALESCE(prep_end_jd, prod_start_jd), hour_start_jd)
                            ) * 1440.0
                        )
                        ELSE 0.0
                    END AS production_overlap_minutes,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                        THEN (prod_end_jd - prep_end_jd) * 1440.0
                    END AS event_window_minutes,
                    CASE
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                        THEN MAX(
                            0.0,
                            (
                                MIN(prod_end_jd, hour_end_jd)
                                - MAX(prep_end_jd, hour_start_jd)
                            ) * 1440.0
                        )
                        ELSE 0.0
                    END AS hour_post_setup_overlap_minutes
                FROM base
            ),
            resolved AS (
                SELECT
                    canonical_machine_id,
                    hour_ts,
                    source_row_hash,
                    minute_budget_anomaly_flag,
                    minute_budget_anomaly_reason,
                    CASE
                        WHEN existing_landed_basis_minutes IS NOT NULL
                         AND existing_landed_basis_minutes > 0
                        THEN existing_landed_basis_minutes
                        WHEN minute_budget_anomaly_flag = 1
                        THEN NULL
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND csi_planned_stop_minutes IS NOT NULL
                         AND csi_unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                        AND (
                            actual_prod_minutes + csi_planned_stop_minutes + csi_unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                        THEN actual_prod_minutes * (hour_post_setup_overlap_minutes / event_window_minutes)
                        WHEN production_overlap_minutes > 0
                        THEN production_overlap_minutes
                        WHEN source_flag_dominant_production_minutes IS NOT NULL
                         AND source_flag_dominant_production_minutes > 0
                         AND source_flag_dominant_source_row_hash IS NOT NULL
                         AND source_flag_dominant_source_row_hash <> source_row_hash
                        THEN NULL
                        WHEN source_flag_dominant_production_minutes IS NOT NULL
                         AND source_flag_dominant_production_minutes > 0
                        THEN source_flag_dominant_production_minutes
                    END AS dominant_production_minutes,
                    CASE
                        WHEN existing_landed_basis_minutes IS NOT NULL
                         AND existing_landed_basis_minutes > 0
                        THEN 'preserved_existing_landed_positive_basis'
                        WHEN minute_budget_anomaly_flag = 1
                        THEN 'excluded_minute_budget_anomaly'
                        WHEN prep_end_jd IS NOT NULL
                         AND prod_end_jd IS NOT NULL
                         AND prod_end_jd > prep_end_jd
                         AND actual_prod_minutes IS NOT NULL
                         AND csi_planned_stop_minutes IS NOT NULL
                         AND csi_unplanned_stop_minutes IS NOT NULL
                         AND event_window_minutes IS NOT NULL
                         AND event_window_minutes > 0
                        AND (
                            actual_prod_minutes + csi_planned_stop_minutes + csi_unplanned_stop_minutes - event_window_minutes
                         ) <= MAX(5.0, event_window_minutes * 0.05)
                         AND (
                            actual_prod_minutes * (hour_post_setup_overlap_minutes / event_window_minutes)
                         ) > 0
                        THEN 'reconstructed_from_csi_event'
                        WHEN production_overlap_minutes > 0
                        THEN 'reconstructed_from_csi_event'
                        WHEN source_flag_dominant_production_minutes IS NOT NULL
                         AND source_flag_dominant_production_minutes > 0
                         AND source_flag_dominant_source_row_hash IS NOT NULL
                         AND source_flag_dominant_source_row_hash <> source_row_hash
                        THEN 'blocked_dominant_identity_conflict'
                        WHEN source_flag_dominant_production_minutes IS NOT NULL
                         AND source_flag_dominant_production_minutes > 0
                         AND source_flag_dominant_source_row_hash IS NULL
                        THEN 'reconstructed_from_source_flags_missing_dominant_hash_flag'
                        WHEN source_flag_dominant_production_minutes IS NOT NULL
                         AND source_flag_dominant_production_minutes > 0
                        THEN 'reconstructed_from_source_flags_matching_dominant_hash'
                        ELSE 'missing_positive_dominant_basis_evidence'
                    END AS reconstruction_status
                FROM computed
            )
            SELECT
                canonical_machine_id,
                hour_ts,
                source_row_hash,
                dominant_production_minutes,
                reconstruction_status,
                minute_budget_anomaly_flag,
                minute_budget_anomaly_reason
            FROM resolved;

            CREATE INDEX temp_idx_task4r_qty_basis_row_key
                ON temp_task4r_qty_basis_row (canonical_machine_id, hour_ts);

            CREATE TEMP TABLE temp_task4r_qty_event_basis AS
            SELECT
                source_row_hash,
                NULLIF(
                    SUM(
                        CASE
                            WHEN dominant_production_minutes IS NOT NULL
                             AND dominant_production_minutes > 0
                            THEN dominant_production_minutes
                            ELSE 0.0
                        END
                    ),
                    0.0
                ) AS basis_minutes
            FROM temp_task4r_qty_basis_row
            GROUP BY source_row_hash;

            CREATE INDEX temp_idx_task4r_qty_event_basis_hash
                ON temp_task4r_qty_event_basis (source_row_hash);

            CREATE TEMP TABLE temp_task4r_qty_audit AS
            SELECT
                f.canonical_machine_id,
                f.hour_ts,
                'csi_dominant_event_production_minutes_share' AS csi_qty_basis_method,
                b.dominant_production_minutes AS csi_qty_row_basis_minutes,
                e.basis_minutes AS csi_qty_event_basis_minutes,
                CASE
                    WHEN f.production_minutes IS NOT NULL
                     AND b.dominant_production_minutes IS NOT NULL
                    THEN f.production_minutes - b.dominant_production_minutes
                END AS csi_qty_minutes_vs_production_diff,
                CASE
                    WHEN f.production_minutes IS NOT NULL
                     AND b.dominant_production_minutes IS NOT NULL
                    THEN ABS(f.production_minutes - b.dominant_production_minutes)
                END AS csi_qty_minutes_vs_production_abs_diff,
                CASE
                    WHEN b.dominant_production_minutes IS NULL
                      OR b.dominant_production_minutes <= 0
                    THEN 'missing_positive_row_basis_minutes'
                    WHEN f.production_minutes IS NULL
                    THEN 'missing_row_production_minutes'
                    WHEN f.good_qty IS NULL
                      AND f.scrap_qty IS NULL
                    THEN 'no_quantity_allocated'
                    WHEN ABS(f.production_minutes - b.dominant_production_minutes)
                         > {CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES}
                    THEN 'material_misaligned'
                    ELSE 'aligned'
                END AS csi_qty_alignment_status,
                CASE
                    WHEN b.dominant_production_minutes IS NOT NULL
                     AND b.dominant_production_minutes > 0
                     AND f.production_minutes IS NOT NULL
                     AND (f.good_qty IS NOT NULL OR f.scrap_qty IS NOT NULL)
                     AND ABS(f.production_minutes - b.dominant_production_minutes)
                         > {CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES}
                    THEN 1
                    ELSE 0
                END AS csi_qty_material_misalignment_flag,
                b.minute_budget_anomaly_flag AS csi_qty_minute_budget_anomaly_flag,
                b.minute_budget_anomaly_reason AS csi_qty_minute_budget_anomaly_reason
            FROM fact_machine_hour f
            JOIN temp_task4r_qty_basis_row b
              ON b.canonical_machine_id = f.canonical_machine_id
             AND b.hour_ts = f.hour_ts
            LEFT JOIN temp_task4r_qty_event_basis e
              ON e.source_row_hash = b.source_row_hash
            WHERE {aliased_scope_sql};

            CREATE INDEX temp_idx_task4r_qty_audit_key
                ON temp_task4r_qty_audit (canonical_machine_id, hour_ts);
            """
        )

        cursor.execute(
            """
            UPDATE fact_machine_hour
            SET
                csi_qty_basis_method = (
                    SELECT a.csi_qty_basis_method
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_row_basis_minutes = (
                    SELECT a.csi_qty_row_basis_minutes
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_event_basis_minutes = (
                    SELECT a.csi_qty_event_basis_minutes
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minutes_vs_production_diff = (
                    SELECT a.csi_qty_minutes_vs_production_diff
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minutes_vs_production_abs_diff = (
                    SELECT a.csi_qty_minutes_vs_production_abs_diff
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_alignment_status = (
                    SELECT a.csi_qty_alignment_status
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_material_misalignment_flag = (
                    SELECT a.csi_qty_material_misalignment_flag
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minute_budget_anomaly_flag = (
                    SELECT a.csi_qty_minute_budget_anomaly_flag
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                ),
                csi_qty_minute_budget_anomaly_reason = (
                    SELECT a.csi_qty_minute_budget_anomaly_reason
                    FROM temp_task4r_qty_audit a
                    WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                      AND a.hour_ts = fact_machine_hour.hour_ts
                )
            WHERE EXISTS (
                SELECT 1
                FROM temp_task4r_qty_audit a
                WHERE a.canonical_machine_id = fact_machine_hour.canonical_machine_id
                  AND a.hour_ts = fact_machine_hour.hour_ts
            )
            """
        )

        conn.commit()
        return {
            "db_path": resolved_db_path,
            "scope_sql": scope_sql,
            "quantity_rows_only": quantity_rows_only,
            "target_rows": _count(conn, f"SELECT COUNT(*) FROM fact_machine_hour WHERE {scope_sql}"),
            "audit_rows": _count(conn, "SELECT COUNT(*) FROM temp_task4r_qty_audit"),
            "preserved_existing_basis_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_basis_row "
                "WHERE reconstruction_status = 'preserved_existing_landed_positive_basis'",
            ),
            "newly_reconstructible_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_basis_row "
                "WHERE reconstruction_status IN ("
                "'reconstructed_from_csi_event', "
                "'reconstructed_from_source_flags_matching_dominant_hash', "
                "'reconstructed_from_source_flags_missing_dominant_hash_flag'"
                ")",
            ),
            "still_unreconstructible_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_basis_row "
                "WHERE reconstruction_status IN ("
                "'missing_positive_dominant_basis_evidence', "
                "'blocked_dominant_identity_conflict'"
                ")",
            ),
            "excluded_anomaly_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_basis_row "
                "WHERE reconstruction_status = 'excluded_minute_budget_anomaly'",
            ),
            "dominant_identity_conflict_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_basis_row "
                "WHERE reconstruction_status = 'blocked_dominant_identity_conflict'",
            ),
            "material_misaligned_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_audit WHERE csi_qty_material_misalignment_flag = 1",
            ),
            "minute_budget_anomaly_rows": _count(
                conn,
                "SELECT COUNT(*) FROM temp_task4r_qty_audit WHERE csi_qty_minute_budget_anomaly_flag = 1",
            ),
        }
    finally:
        conn.close()


def _task4s_scope_sql(
    start_ts: str,
    end_ts: str,
    *,
    table_alias: str | None = None,
) -> str:
    prefix = f"{table_alias}." if table_alias else ""
    return " AND ".join(
        [
            f"{prefix}csi_source_row_hash IS NOT NULL",
            f"{prefix}hour_ts >= {_sql_text_literal(start_ts)}",
            f"{prefix}hour_ts < {_sql_text_literal(end_ts)}",
            f"{prefix}multiple_csi_overlap_flag = 1",
            f"({prefix}good_qty IS NOT NULL OR {prefix}scrap_qty IS NOT NULL)",
        ]
    )


def _task4s_load_exact_scope_rows(
    conn: sqlite3.Connection,
    start_ts: str,
    end_ts: str,
) -> list[dict[str, object]]:
    scope_sql = _task4s_scope_sql(start_ts, end_ts)
    rows = conn.execute(
        f"""
        SELECT
            rowid AS target_rowid,
            canonical_machine_id,
            hour_ts,
            machine_state,
            order_id,
            material_code,
            task_name,
            csi_source_row_hash,
            setup_minutes,
            production_minutes,
            planned_stop_minutes,
            unplanned_stop_minutes,
            idle_minutes,
            good_qty,
            scrap_qty,
            csi_qty_basis_method,
            csi_qty_row_basis_minutes,
            csi_qty_event_basis_minutes,
            csi_qty_minutes_vs_production_diff,
            csi_qty_minutes_vs_production_abs_diff,
            csi_qty_alignment_status,
            csi_qty_material_misalignment_flag,
            csi_qty_minute_budget_anomaly_flag,
            csi_qty_minute_budget_anomaly_reason
        FROM fact_machine_hour
        WHERE {scope_sql}
        ORDER BY rowid
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _task4s_group_quantity_totals(
    rows: list[dict[str, object]],
    *,
    good_key: str,
    scrap_key: str,
) -> dict[str, tuple[float, float]]:
    totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for row in rows:
        source_row_hash = str(row["csi_source_row_hash"])
        totals[source_row_hash][0] += float(row.get(good_key) or 0.0)
        totals[source_row_hash][1] += float(row.get(scrap_key) or 0.0)
    return {
        source_row_hash: (group_totals[0], group_totals[1])
        for source_row_hash, group_totals in totals.items()
    }


def _task4s_dominant_identity_conflict_count(
    conn: sqlite3.Connection,
    start_ts: str,
    end_ts: str,
) -> int:
    aliased_scope_sql = _task4s_scope_sql(start_ts, end_ts, table_alias="f")
    return _count(
        conn,
        f"""
        SELECT COUNT(*)
        FROM fact_machine_hour f
        WHERE {aliased_scope_sql}
          AND json_valid(f.source_flags)
          AND CAST(json_extract(f.source_flags, '$.csi_dominant_production_minutes') AS REAL) > 0
          AND NULLIF(TRIM(CAST(json_extract(f.source_flags, '$.dominant_csi_source_row_hash') AS TEXT)), '') IS NOT NULL
          AND CAST(json_extract(f.source_flags, '$.dominant_csi_source_row_hash') AS TEXT) <> f.csi_source_row_hash
        """,
    )


def _task4s_shadow_diagnostics(rows: list[dict[str, object]]) -> dict[str, object]:
    evaluated_rows = evaluate_shadow_quantity(rows)
    eligible_rows = [row for row in evaluated_rows if row["shadow_group_eligible"] == 1]
    ineligible_rows = [row for row in evaluated_rows if row["shadow_group_eligible"] == 0]
    anomaly_rows = [
        row for row in evaluated_rows if row["shadow_group_ineligible_reason"] == "minute_budget_anomaly"
    ]
    materially_changed_rows = [
        row for row in eligible_rows if row["shadow_material_change_flag"] == 1
    ]

    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in evaluated_rows:
        groups[str(row["csi_source_row_hash"])].append(row)

    eligible_group_hashes = {
        source_row_hash
        for source_row_hash, group_rows in groups.items()
        if group_rows[0]["shadow_group_eligible"] == 1
    }
    ineligible_group_hashes = {
        source_row_hash
        for source_row_hash, group_rows in groups.items()
        if group_rows[0]["shadow_group_eligible"] == 0
    }

    return {
        "evaluated_rows": evaluated_rows,
        "eligible_rows": eligible_rows,
        "ineligible_rows": ineligible_rows,
        "anomaly_rows": anomaly_rows,
        "materially_changed_rows": materially_changed_rows,
        "eligible_rows_count": len(eligible_rows),
        "anomaly_excluded_rows_count": len(anomaly_rows),
        "eligible_groups_count": len(eligible_group_hashes),
        "ineligible_groups_count": len(ineligible_group_hashes),
        "eligible_group_hashes": eligible_group_hashes,
        "ineligible_group_hashes": ineligible_group_hashes,
        "aggregate_abs_good_qty_drift": sum(
            abs(float(row.get("shadow_good_qty") or 0.0) - float(row.get("good_qty") or 0.0))
            for row in eligible_rows
        ),
        "aggregate_abs_scrap_qty_drift": sum(
            abs(float(row.get("shadow_scrap_qty") or 0.0) - float(row.get("scrap_qty") or 0.0))
            for row in eligible_rows
        ),
        "current_good_qty_total": sum(float(row.get("good_qty") or 0.0) for row in evaluated_rows),
        "shadow_good_qty_total": sum(float(row.get("shadow_good_qty") or 0.0) for row in evaluated_rows),
        "current_scrap_qty_total": sum(float(row.get("scrap_qty") or 0.0) for row in evaluated_rows),
        "shadow_scrap_qty_total": sum(float(row.get("shadow_scrap_qty") or 0.0) for row in evaluated_rows),
        "group_totals_current": _task4s_group_quantity_totals(
            evaluated_rows,
            good_key="good_qty",
            scrap_key="scrap_qty",
        ),
        "group_totals_shadow": _task4s_group_quantity_totals(
            evaluated_rows,
            good_key="shadow_good_qty",
            scrap_key="shadow_scrap_qty",
        ),
        "top_affected_machines": Counter(
            row.get("canonical_machine_id") or "<null>"
            for row in materially_changed_rows
        ).most_common(10),
        "top_affected_task_names": Counter(
            row.get("task_name") or "<null>"
            for row in materially_changed_rows
        ).most_common(10),
        "top_affected_material_codes": Counter(
            row.get("material_code") or "<null>"
            for row in materially_changed_rows
        ).most_common(10),
    }


def _task4s_assert_close(value: float, expected: float, *, label: str) -> None:
    if abs(value - expected) > TASK4S_LIVE_REPLACEMENT_FLOAT_TOLERANCE:
        raise ValueError(
            f"{label} drifted beyond tolerance: {value} vs {expected}"
        )


def _task4s_create_rollback_snapshot(
    snapshot_path: Path,
    *,
    scope_sql: str,
    eligible_rows: list[dict[str, object]],
    created_at_utc: str,
) -> None:
    snapshot_conn = sqlite3.connect(snapshot_path)
    try:
        snapshot_conn.execute(
            """
            CREATE TABLE rollback_metadata (
                created_at_utc TEXT NOT NULL,
                scope_sql TEXT NOT NULL,
                row_key_name TEXT NOT NULL,
                eligible_row_count INTEGER NOT NULL
            )
            """
        )
        snapshot_conn.execute(
            """
            CREATE TABLE rollback_snapshot (
                target_rowid INTEGER PRIMARY KEY,
                canonical_machine_id TEXT NOT NULL,
                hour_ts TEXT NOT NULL,
                csi_source_row_hash TEXT NOT NULL,
                pre_good_qty REAL,
                pre_scrap_qty REAL
            )
            """
        )
        snapshot_conn.execute(
            """
            INSERT INTO rollback_metadata (
                created_at_utc,
                scope_sql,
                row_key_name,
                eligible_row_count
            ) VALUES (?, ?, ?, ?)
            """,
            (
                created_at_utc,
                scope_sql,
                "rowid",
                len(eligible_rows),
            ),
        )
        snapshot_conn.executemany(
            """
            INSERT INTO rollback_snapshot (
                target_rowid,
                canonical_machine_id,
                hour_ts,
                csi_source_row_hash,
                pre_good_qty,
                pre_scrap_qty
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(row["target_rowid"]),
                    str(row["canonical_machine_id"]),
                    str(row["hour_ts"]),
                    str(row["csi_source_row_hash"]),
                    row.get("good_qty"),
                    row.get("scrap_qty"),
                )
                for row in eligible_rows
            ],
        )
        snapshot_conn.commit()
    finally:
        snapshot_conn.close()


def execute_task4s_live_quantity_replacement(
    db_path: str | Path | None = None,
    *,
    start_ts: str = "2025-01-01T00:00:00",
    end_ts: str = "2025-07-01T00:00:00",
    backup_dir: str | Path | None = None,
    expected_baseline: dict[str, int] | None = None,
    timestamp_override: str | None = None,
) -> dict[str, object]:
    """Apply the approved Task 4S live quantity replacement on fully eligible dominant groups only."""

    resolved_db_path = Path(db_path or get_database_path()).resolve()
    resolved_backup_dir = Path(backup_dir or (resolved_db_path.parent / "backups")).resolve()
    resolved_backup_dir.mkdir(parents=True, exist_ok=True)

    baseline = dict(TASK4S_LIVE_REPLACEMENT_BASELINE)
    if expected_baseline is not None:
        baseline.update(expected_baseline)

    scope_sql = _task4s_scope_sql(start_ts, end_ts)
    created_at_utc = timestamp_override or datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    pre_conn = sqlite3.connect(resolved_db_path)
    pre_conn.row_factory = sqlite3.Row
    try:
        total_rows, distinct_rowids = pre_conn.execute(
            f"""
            SELECT COUNT(*), COUNT(DISTINCT rowid)
            FROM fact_machine_hour
            WHERE {scope_sql}
            """
        ).fetchone()
        if total_rows != distinct_rowids:
            raise ValueError(
                f"Task 4S live replacement aborted: rowid is not unique on the exact scope ({total_rows} vs {distinct_rowids})"
            )

        pre_rows = _task4s_load_exact_scope_rows(pre_conn, start_ts, end_ts)
        pre_diagnostics = _task4s_shadow_diagnostics(pre_rows)
        dominant_identity_conflict_rows = _task4s_dominant_identity_conflict_count(
            pre_conn,
            start_ts,
            end_ts,
        )
    finally:
        pre_conn.close()

    if pre_diagnostics["eligible_rows_count"] != baseline["eligible_rows"]:
        raise ValueError(
            f"Task 4S live replacement aborted: eligible row baseline drifted to {pre_diagnostics['eligible_rows_count']}"
        )
    if pre_diagnostics["anomaly_excluded_rows_count"] != baseline["anomaly_excluded_rows"]:
        raise ValueError(
            "Task 4S live replacement aborted: anomaly-excluded row baseline drifted "
            f"to {pre_diagnostics['anomaly_excluded_rows_count']}"
        )
    if pre_diagnostics["eligible_groups_count"] != baseline["eligible_groups"]:
        raise ValueError(
            f"Task 4S live replacement aborted: eligible dominant-group baseline drifted to {pre_diagnostics['eligible_groups_count']}"
        )
    if pre_diagnostics["ineligible_groups_count"] != baseline["ineligible_groups"]:
        raise ValueError(
            f"Task 4S live replacement aborted: ineligible dominant-group baseline drifted to {pre_diagnostics['ineligible_groups_count']}"
        )
    if dominant_identity_conflict_rows != baseline["dominant_identity_conflict_rows"]:
        raise ValueError(
            "Task 4S live replacement aborted: dominant-identity conflict baseline drifted "
            f"to {dominant_identity_conflict_rows}"
        )

    backup_path = resolved_backup_dir / f"manufacturing_data_task4s_live_qty_replace_{created_at_utc}.db"
    rollback_snapshot_path = (
        resolved_backup_dir / f"task4s_live_qty_replace_rollback_{created_at_utc}.db"
    )
    if backup_path.exists() or rollback_snapshot_path.exists():
        raise FileExistsError(
            f"Task 4S live replacement aborted: backup artifact path already exists for timestamp {created_at_utc}"
        )

    eligible_rows = [dict(row) for row in pre_diagnostics["eligible_rows"]]
    pre_non_quantity_by_rowid = {
        int(row["target_rowid"]): (
            row.get("machine_state"),
            row.get("order_id"),
            row.get("material_code"),
            row.get("task_name"),
            row.get("csi_source_row_hash"),
            row.get("setup_minutes"),
            row.get("production_minutes"),
            row.get("planned_stop_minutes"),
            row.get("unplanned_stop_minutes"),
            row.get("idle_minutes"),
            row.get("csi_qty_basis_method"),
            row.get("csi_qty_row_basis_minutes"),
            row.get("csi_qty_event_basis_minutes"),
            row.get("csi_qty_minutes_vs_production_diff"),
            row.get("csi_qty_minutes_vs_production_abs_diff"),
            row.get("csi_qty_alignment_status"),
            row.get("csi_qty_material_misalignment_flag"),
            row.get("csi_qty_minute_budget_anomaly_flag"),
            row.get("csi_qty_minute_budget_anomaly_reason"),
        )
        for row in eligible_rows
    }
    materially_changed_rows = [
        row
        for row in eligible_rows
        if float(row["shadow_total_abs_qty_diff"]) > CSI_QTY_SHADOW_MATERIAL_DIFF_THRESHOLD
    ]

    shutil.copy2(resolved_db_path, backup_path)
    _task4s_create_rollback_snapshot(
        rollback_snapshot_path,
        scope_sql=scope_sql,
        eligible_rows=eligible_rows,
        created_at_utc=created_at_utc,
    )

    tx_conn = sqlite3.connect(resolved_db_path)
    tx_conn.row_factory = sqlite3.Row
    rollback_needed = False
    try:
        tx_conn.execute("BEGIN IMMEDIATE")
        tx_conn.execute("DROP TABLE IF EXISTS temp_task4s_live_stage")
        tx_conn.execute(
            """
            CREATE TEMP TABLE temp_task4s_live_stage (
                target_rowid INTEGER PRIMARY KEY,
                csi_source_row_hash TEXT NOT NULL,
                current_good_qty REAL,
                current_scrap_qty REAL,
                shadow_good_qty REAL,
                shadow_scrap_qty REAL
            )
            """
        )
        tx_conn.executemany(
            """
            INSERT INTO temp_task4s_live_stage (
                target_rowid,
                csi_source_row_hash,
                current_good_qty,
                current_scrap_qty,
                shadow_good_qty,
                shadow_scrap_qty
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(row["target_rowid"]),
                    str(row["csi_source_row_hash"]),
                    row.get("good_qty"),
                    row.get("scrap_qty"),
                    row.get("shadow_good_qty"),
                    row.get("shadow_scrap_qty"),
                )
                for row in eligible_rows
            ],
        )

        stage_rows, distinct_stage_rowids = tx_conn.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT target_rowid)
            FROM temp_task4s_live_stage
            """
        ).fetchone()
        if stage_rows != len(eligible_rows) or distinct_stage_rowids != len(eligible_rows):
            raise ValueError("Task 4S live replacement aborted: staging row count mismatch")

        out_of_scope_targets = _count(
            tx_conn,
            f"""
            SELECT COUNT(*)
            FROM temp_task4s_live_stage s
            JOIN fact_machine_hour f
              ON f.rowid = s.target_rowid
            WHERE NOT ({_task4s_scope_sql(start_ts, end_ts, table_alias='f')})
            """,
        )
        if out_of_scope_targets != 0:
            raise ValueError("Task 4S live replacement aborted: out-of-scope rows appeared in staging")

        anomaly_group_targets = _count(
            tx_conn,
            """
            SELECT COUNT(*)
            FROM temp_task4s_live_stage s
            JOIN fact_machine_hour f
              ON f.rowid = s.target_rowid
            WHERE f.csi_qty_minute_budget_anomaly_flag = 1
            """,
        )
        if anomaly_group_targets != 0:
            raise ValueError("Task 4S live replacement aborted: anomaly-flagged rows appeared in staging")

        negative_targets = _count(
            tx_conn,
            """
            SELECT COUNT(*)
            FROM temp_task4s_live_stage
            WHERE COALESCE(shadow_good_qty, 0.0) < 0.0
               OR COALESCE(shadow_scrap_qty, 0.0) < 0.0
            """,
        )
        if negative_targets != 0:
            raise ValueError("Task 4S live replacement aborted: negative target quantity detected")

        tx_conn.execute(
            """
            UPDATE fact_machine_hour
            SET
                good_qty = (
                    SELECT s.shadow_good_qty
                    FROM temp_task4s_live_stage s
                    WHERE s.target_rowid = fact_machine_hour.rowid
                ),
                scrap_qty = (
                    SELECT s.shadow_scrap_qty
                    FROM temp_task4s_live_stage s
                    WHERE s.target_rowid = fact_machine_hour.rowid
                )
            WHERE rowid IN (
                SELECT target_rowid
                FROM temp_task4s_live_stage
            )
            """
        )
        updated_rows = int(tx_conn.execute("SELECT changes()").fetchone()[0])
        if updated_rows != len(eligible_rows):
            raise ValueError(
                f"Task 4S live replacement aborted: updated row count {updated_rows} did not match staging row count {len(eligible_rows)}"
            )

        post_rows_in_tx = _task4s_load_exact_scope_rows(tx_conn, start_ts, end_ts)
        post_diagnostics_in_tx = _task4s_shadow_diagnostics(post_rows_in_tx)

        _task4s_assert_close(
            post_diagnostics_in_tx["current_good_qty_total"],
            pre_diagnostics["current_good_qty_total"],
            label="exact-scope good_qty total",
        )
        _task4s_assert_close(
            post_diagnostics_in_tx["current_scrap_qty_total"],
            pre_diagnostics["current_scrap_qty_total"],
            label="exact-scope scrap_qty total",
        )

        for source_row_hash, pre_group_totals in pre_diagnostics["group_totals_current"].items():
            post_group_totals = post_diagnostics_in_tx["group_totals_current"].get(source_row_hash)
            if post_group_totals is None:
                raise ValueError(
                    f"Task 4S live replacement aborted: group {source_row_hash} disappeared during transaction"
                )
            _task4s_assert_close(
                post_group_totals[0],
                pre_group_totals[0],
                label=f"group good_qty total for {source_row_hash}",
            )
            _task4s_assert_close(
                post_group_totals[1],
                pre_group_totals[1],
                label=f"group scrap_qty total for {source_row_hash}",
            )

        post_rows_by_rowid = {
            int(row["target_rowid"]): row
            for row in post_rows_in_tx
            if int(row["target_rowid"]) in pre_non_quantity_by_rowid
        }
        for target_rowid, pre_non_quantity_tuple in pre_non_quantity_by_rowid.items():
            post_row = post_rows_by_rowid[target_rowid]
            post_non_quantity_tuple = (
                post_row.get("machine_state"),
                post_row.get("order_id"),
                post_row.get("material_code"),
                post_row.get("task_name"),
                post_row.get("csi_source_row_hash"),
                post_row.get("setup_minutes"),
                post_row.get("production_minutes"),
                post_row.get("planned_stop_minutes"),
                post_row.get("unplanned_stop_minutes"),
                post_row.get("idle_minutes"),
                post_row.get("csi_qty_basis_method"),
                post_row.get("csi_qty_row_basis_minutes"),
                post_row.get("csi_qty_event_basis_minutes"),
                post_row.get("csi_qty_minutes_vs_production_diff"),
                post_row.get("csi_qty_minutes_vs_production_abs_diff"),
                post_row.get("csi_qty_alignment_status"),
                post_row.get("csi_qty_material_misalignment_flag"),
                post_row.get("csi_qty_minute_budget_anomaly_flag"),
                post_row.get("csi_qty_minute_budget_anomaly_reason"),
            )
            if post_non_quantity_tuple != pre_non_quantity_tuple:
                raise ValueError(
                    f"Task 4S live replacement aborted: non-quantity fields changed for target rowid {target_rowid}"
                )

        if post_diagnostics_in_tx["materially_changed_rows"]:
            raise ValueError(
                "Task 4S live replacement aborted: eligible groups still show residual shadow drift before commit"
            )

        tx_conn.commit()
    except Exception:
        rollback_needed = True
        tx_conn.rollback()
        raise
    finally:
        tx_conn.close()

    post_conn = sqlite3.connect(resolved_db_path)
    post_conn.row_factory = sqlite3.Row
    try:
        post_rows = _task4s_load_exact_scope_rows(post_conn, start_ts, end_ts)
        post_diagnostics = _task4s_shadow_diagnostics(post_rows)
    finally:
        post_conn.close()

    return {
        "db_path": str(resolved_db_path),
        "scope_sql": scope_sql,
        "row_unique_key": "rowid",
        "row_unique_key_count": int(total_rows),
        "row_unique_key_distinct_count": int(distinct_rowids),
        "backup_path": str(backup_path),
        "rollback_snapshot_path": str(rollback_snapshot_path),
        "rollback_snapshot_schema": "rollback_snapshot(target_rowid PRIMARY KEY, canonical_machine_id, hour_ts, csi_source_row_hash, pre_good_qty, pre_scrap_qty)",
        "rollback_snapshot_key": "target_rowid",
        "rollback_needed": rollback_needed,
        "write_scope_exact_rows": len(pre_rows),
        "write_scope_target_rows": len(eligible_rows),
        "write_scope_anomaly_excluded_rows": pre_diagnostics["anomaly_excluded_rows_count"],
        "write_scope_eligible_groups": pre_diagnostics["eligible_groups_count"],
        "write_scope_ineligible_groups": pre_diagnostics["ineligible_groups_count"],
        "dominant_identity_conflict_rows": dominant_identity_conflict_rows,
        "before_good_qty_total": pre_diagnostics["current_good_qty_total"],
        "after_good_qty_total": post_diagnostics["current_good_qty_total"],
        "before_scrap_qty_total": pre_diagnostics["current_scrap_qty_total"],
        "after_scrap_qty_total": post_diagnostics["current_scrap_qty_total"],
        "before_shadow_good_qty_total": pre_diagnostics["shadow_good_qty_total"],
        "after_shadow_good_qty_total": post_diagnostics["shadow_good_qty_total"],
        "materially_changed_row_count": len(materially_changed_rows),
        "post_write_residual_materially_changed_row_count": len(post_diagnostics["materially_changed_rows"]),
        "per_group_conservation_passed": True,
        "pre_write_diagnostics": pre_diagnostics,
        "post_write_diagnostics": post_diagnostics,
        "top_affected_machines": pre_diagnostics["top_affected_machines"],
        "top_affected_task_names": pre_diagnostics["top_affected_task_names"],
        "top_affected_material_codes": pre_diagnostics["top_affected_material_codes"],
    }


__all__ = [
    "repair_fact_machine_hour_operational_overlays",
    "repair_fact_machine_hour_quantity_audit_metadata",
    "execute_task4s_live_quantity_replacement",
]
