"""Month-scoped canonical Silver/Gold materialization for the shared runtime DB."""

from __future__ import annotations

import json
import signal
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from pathlib import Path

import pandas as pd

from core.gold_fact_builder import GoldFactBuilder
from core.runtime_paths import get_database_path
from core.silver_normalizer import SilverNormalizer


@dataclass(frozen=True)
class MonthBounds:
    label: str
    start: pd.Timestamp
    end: pd.Timestamp
    month_key: str


class CanonicalMaterializer:
    GOLD_DEBUG_STAGE_NAMES = (
        "energy_backbone_only",
        "energy_backbone_plus_csi_state_overlay",
        "energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay",
        "energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay_plus_mes_overlay",
        "energy_backbone_plus_csi_state_overlay_plus_csi_quantity_overlay_plus_mes_overlay_plus_maintenance_overlay",
        "final_replace_commit_index_phase",
    )
    REQUIRED_BRONZE_TABLES = (
        "raw_energy_hourly",
        "raw_csi_event",
        "raw_mes_report",
    )
    BRONZE_MONTH_SQL = {
        "raw_energy_hourly": "substr(raw_timestamp, 1, 7)",
        "raw_csi_event": (
            "COALESCE("
            "substr(raw_start_time, 1, 7), "
            "substr(raw_end_time, 1, 7), "
            "substr(raw_prep_end_time, 1, 7), "
            "substr(json_extract(raw_payload_json, '$.班次內日期'), 1, 7)"
            ")"
        ),
        "raw_mes_report": (
            "substr(json_extract(raw_payload_json, '$.報工時間'), 1, 7)"
        ),
        "raw_maintenance_txn": "substr(raw_transaction_date, 1, 7)",
    }
    SILVER_MONTH_SQL = {
        "energy_meter_hour": "substr(hour_ts, 1, 7)",
        "csi_job_event": (
            "COALESCE("
            "substr(prod_start_ts, 1, 7), "
            "substr(prod_end_ts, 1, 7), "
            "substr(prep_end_ts, 1, 7), "
            "substr(shift_date, 1, 7)"
            ")"
        ),
        "mes_report_event": (
            "substr(report_ts, 1, 7)"
        ),
        "maintenance_txn_event": "substr(txn_ts, 1, 7)",
    }
    GOLD_MONTH_SQL = {
        "fact_machine_hour": "substr(hour_ts, 1, 7)",
    }
    BRONZE_MONTH_SELECT_SQL = {
        "raw_energy_hourly": """
            SELECT
                source_row_hash,
                canonical_machine_id,
                source_file,
                raw_machine_id_or_label,
                raw_timestamp,
                raw_kwh,
                raw_cost
            FROM raw_energy_hourly
            WHERE {month_expression} = ?
        """,
        "raw_csi_event": """
            SELECT
                source_row_hash,
                canonical_machine_id,
                source_file,
                raw_machine_id_or_label,
                raw_start_time,
                raw_end_time,
                raw_prep_end_time,
                raw_order_id,
                raw_material,
                raw_good_qty,
                raw_scrap_qty,
                json_extract(raw_payload_json, '$."班次內日期"') AS "班次內日期",
                json_extract(raw_payload_json, '$."班次"') AS "班次",
                json_extract(raw_payload_json, '$."區域"') AS "區域",
                json_extract(raw_payload_json, '$."機台編號"') AS "機台編號",
                json_extract(raw_payload_json, '$."作业"') AS "作业",
                json_extract(raw_payload_json, '$."作业后缀"') AS "作业后缀",
                json_extract(raw_payload_json, '$."操作"') AS "操作",
                json_extract(raw_payload_json, '$."物料"') AS "物料",
                json_extract(raw_payload_json, '$."任務"') AS "任務",
                json_extract(raw_payload_json, '$."工程開始時間"') AS "工程開始時間",
                json_extract(raw_payload_json, '$."準備結束時間"') AS "準備結束時間",
                json_extract(raw_payload_json, '$."工程結束時間"') AS "工程結束時間",
                json_extract(raw_payload_json, '$."正品數量"') AS "正品數量",
                json_extract(raw_payload_json, '$."廢品數量"') AS "廢品數量",
                json_extract(raw_payload_json, '$."纍計數量"') AS "纍計數量",
                json_extract(raw_payload_json, '$."心電圖整體運作時間"') AS "心電圖整體運作時間",
                json_extract(raw_payload_json, '$."實際生產時間"') AS "實際生產時間",
                json_extract(raw_payload_json, '$."實際速度_本_時"') AS "實際速度_本_時",
                json_extract(raw_payload_json, '$."心電圖實際轉版時間"') AS "心電圖實際轉版時間",
                json_extract(raw_payload_json, '$."實際計劃停機時間"') AS "實際計劃停機時間",
                json_extract(raw_payload_json, '$."實際無計劃停機時間"') AS "實際無計劃停機時間",
                json_extract(raw_payload_json, '$."停機原因"') AS "停機原因",
                json_extract(raw_payload_json, '$."運作中途總停機次數"') AS "運作中途總停機次數",
                json_extract(raw_payload_json, '$."機長姓名1"') AS "機長姓名1",
                json_extract(raw_payload_json, '$."機長姓名2"') AS "機長姓名2",
                json_extract(raw_payload_json, '$."機組人員姓名1"') AS "機組人員姓名1",
                json_extract(raw_payload_json, '$."機組人員姓名2"') AS "機組人員姓名2",
                json_extract(raw_payload_json, '$."機組人員姓名3"') AS "機組人員姓名3",
                json_extract(raw_payload_json, '$."機組人員姓名4"') AS "機組人員姓名4"
            FROM raw_csi_event
            WHERE {month_expression} = ?
        """,
        "raw_mes_report": """
            SELECT
                source_row_hash,
                canonical_machine_id,
                source_file,
                raw_machine_id_or_label,
                raw_task,
                raw_material_code,
                json_extract(raw_payload_json, '$."資源"') AS "資源",
                json_extract(raw_payload_json, '$."報工時間"') AS "報工時間",
                json_extract(raw_payload_json, '$."作業"') AS "作業",
                json_extract(raw_payload_json, '$."後綴"') AS "後綴",
                json_extract(raw_payload_json, '$."操作"') AS "操作",
                json_extract(raw_payload_json, '$."任務"') AS "任務",
                json_extract(raw_payload_json, '$."物料"') AS "物料",
                json_extract(raw_payload_json, '$."要求生產數量"') AS "要求生產數量",
                json_extract(raw_payload_json, '$."生產數量"') AS "生產數量",
                json_extract(raw_payload_json, '$."累計生產數量"') AS "累計生產數量",
                json_extract(raw_payload_json, '$."報工類型"') AS "報工類型",
                json_extract(raw_payload_json, '$."設備總用時"') AS "設備總用時",
                json_extract(raw_payload_json, '$."準備時間"') AS "準備時間",
                json_extract(raw_payload_json, '$."設備生產時間"') AS "設備生產時間",
                json_extract(raw_payload_json, '$."人數"') AS "人數",
                json_extract(raw_payload_json, '$."班次"') AS "班次",
                json_extract(raw_payload_json, '$."上傳CSI狀態"') AS "上傳CSI狀態",
                json_extract(raw_payload_json, '$."狀態變更時間"') AS "狀態變更時間",
                json_extract(raw_payload_json, '$."記錄新增時間"') AS "記錄新增時間"
            FROM raw_mes_report
            WHERE {month_expression} = ?
        """,
    }

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_database_path())
        self.silver = SilverNormalizer(self.db_path)
        self.gold = GoldFactBuilder(self.db_path)

    def materialize_month(self, month_year: str) -> dict[str, object]:
        bounds = self._parse_month_bounds(month_year)
        bronze_counts, silver_rows_by_table = self._materialize_month_silver(bounds, month_year)
        gold_df = self._materialize_gold_month(bounds)

        return {
            "status": "success",
            "target_month": bounds.label,
            "target_month_key": bounds.month_key,
            "silver_materialized": True,
            "gold_materialized": True,
            "gold_materialization_mode": "full_overlay",
            "silver_rows_materialized_by_table": {
                table_name: len(rows) for table_name, rows in silver_rows_by_table.items()
            },
            "bronze_rows_used_by_table": bronze_counts,
            "gold_fact_machine_hour_rows_created": len(gold_df),
            "fact_machine_hour_rows_created": len(gold_df),
            "legacy_unified_view_bypassed": True,
        }

    def materialize_backfill_month(self, month_year: str) -> dict[str, object]:
        bounds = self._parse_month_bounds(month_year)
        bronze_counts, silver_rows_by_table = self._materialize_month_silver(bounds, month_year)
        gold_df = self._materialize_gold_month(bounds)

        return {
            "status": "success",
            "target_month": bounds.label,
            "target_month_key": bounds.month_key,
            "silver_materialized": True,
            "gold_materialized": True,
            "gold_materialization_mode": "full_overlay",
            "gold_overlay_execution_path": "full_overlay_month_replace",
            "silver_rows_materialized_by_table": {
                table_name: len(rows) for table_name, rows in silver_rows_by_table.items()
            },
            "bronze_rows_used_by_table": bronze_counts,
            "gold_fact_machine_hour_rows_created": len(gold_df),
            "fact_machine_hour_rows_created": len(gold_df),
            "legacy_unified_view_bypassed": True,
        }

    def _materialize_month_silver(
        self,
        bounds: MonthBounds,
        month_year: str,
    ) -> tuple[dict[str, int], dict[str, list[dict[str, object]]]]:
        bronze_energy = self._filter_bronze_rows("raw_energy_hourly", bounds)
        bronze_csi = self._filter_bronze_rows("raw_csi_event", bounds)
        bronze_mes = self._filter_bronze_rows("raw_mes_report", bounds)
        bronze_maintenance = self._filter_bronze_rows("raw_maintenance_txn", bounds)

        bronze_counts = {
            "raw_energy_hourly": len(bronze_energy),
            "raw_csi_event": len(bronze_csi),
            "raw_mes_report": len(bronze_mes),
            "raw_maintenance_txn": len(bronze_maintenance),
        }
        missing_required = [
            table_name
            for table_name in ("raw_energy_hourly", "raw_csi_event", "raw_mes_report")
            if bronze_counts[table_name] == 0
        ]
        if missing_required:
            raise ValueError(
                "Canonical materialization cannot run because target-month Bronze rows are missing for: "
                + ", ".join(missing_required)
            )

        silver_rows_by_table = {
            "energy_meter_hour": self.silver._normalize_energy_rows(bronze_energy),
            "csi_job_event": self.silver._normalize_csi_rows(bronze_csi),
            "mes_report_event": self.silver._normalize_mes_rows(bronze_mes),
            "maintenance_txn_event": self.silver._normalize_maintenance_rows(bronze_maintenance),
        }

        if not silver_rows_by_table["energy_meter_hour"]:
            raise ValueError(
                f"Canonical materialization found Bronze energy rows for {month_year} but none normalized into energy_meter_hour."
            )

        for table_name, fresh_rows in silver_rows_by_table.items():
            self._replace_silver_month_partition(table_name, fresh_rows, bounds)
        return bronze_counts, silver_rows_by_table

    def materialize_backfill_months(self, month_years: list[str] | None = None) -> dict[str, object]:
        requested_months = month_years or self.list_materializable_months()
        if not requested_months:
            return {
                "status": "error",
                "requested_months": [],
                "successful_months": [],
                "failed_months": [],
                "monthly_results": [],
                "legacy_unified_view_bypassed": True,
                "message": "No materializable months were found in Bronze coverage.",
            }

        monthly_results: list[dict[str, object]] = []
        failed_months: list[dict[str, object]] = []

        for month_year in requested_months:
            try:
                monthly_results.append(self.materialize_backfill_month(month_year))
            except Exception as exc:
                failed_months.append(
                    {
                        "target_month": month_year,
                        "message": str(exc),
                    }
                )

        if failed_months and monthly_results:
            status = "partial_error"
        elif failed_months:
            status = "error"
        else:
            status = "success"

        return {
            "status": status,
            "requested_months": requested_months,
            "successful_months": [result["target_month"] for result in monthly_results],
            "failed_months": failed_months,
            "monthly_results": monthly_results,
            "legacy_unified_view_bypassed": True,
        }

    def summarize_month_coverage(self) -> dict[str, object]:
        bronze = self._summarize_month_counts(self.BRONZE_MONTH_SQL)
        silver = self._summarize_month_counts(self.SILVER_MONTH_SQL)
        gold = self._summarize_month_counts(self.GOLD_MONTH_SQL)
        return {
            "bronze": bronze,
            "silver": silver,
            "gold": gold,
            "materializable_months": self.list_materializable_months(bronze),
        }

    def list_materializable_months(self, bronze_summary: list[dict[str, object]] | None = None) -> list[str]:
        summary_rows = bronze_summary or self._summarize_month_counts(self.BRONZE_MONTH_SQL)
        months_by_table = {
            table_name: {
                str(row["month"])
                for row in summary_rows
                if row["table_name"] == table_name and int(row["row_count"]) > 0
            }
            for table_name in self.REQUIRED_BRONZE_TABLES
        }
        if not months_by_table:
            return []

        available_sets = [months_by_table[table_name] for table_name in self.REQUIRED_BRONZE_TABLES]
        if not all(available_sets):
            return []
        return [
            self._month_key_to_label(month_key)
            for month_key in sorted(set.intersection(*available_sets))
        ]

    def _materialize_gold_month(self, bounds: MonthBounds) -> pd.DataFrame:
        energy_month_df = self._filter_silver_rows("energy_meter_hour", bounds)
        target_rows = self._build_base_gold_rows(energy_month_df)
        csi_df = self._filter_silver_rows("csi_job_event", bounds)
        csi_by_machine = self.gold._build_csi_event_groups(csi_df)
        target_rows = self._overlay_gold_rows_with_csi(
            target_rows,
            csi_by_machine,
        )
        target_csi_hashes = self._collect_target_csi_hashes(target_rows)
        supporting_gold_df = self._read_other_gold_rows_by_csi_source_hashes(bounds, target_csi_hashes)
        target_rows = self._apply_csi_quantity(
            target_rows,
            supporting_gold_df,
            csi_df,
        )
        mes_df = self._filter_silver_rows("mes_report_event", bounds)
        mes_by_machine = self.gold._build_mes_event_groups(mes_df)
        csi_team_size_by_hash = self.gold._build_csi_team_size_lookup(csi_df)
        target_rows = self._overlay_gold_rows_with_mes(
            target_rows,
            mes_by_machine,
            csi_team_size_by_hash,
        )
        maintenance_df = self._read_table("maintenance_txn_event")
        maintenance_by_machine = self.gold._build_maintenance_event_groups(maintenance_df)
        target_rows = self._overlay_gold_rows_with_maintenance(
            target_rows,
            maintenance_by_machine,
        )
        target_rows = self._overlay_gold_rows_with_idle_and_maintenance_state_review(target_rows)
        target_rows = self._serialize_gold_rows(target_rows)

        self._replace_gold_month_partition(target_rows, bounds)
        return pd.DataFrame(target_rows)

    def materialize_gold_month_debug(
        self,
        month_year: str | MonthBounds,
        *,
        stage_duration_warning_seconds: float | None = None,
        stage_timeout_seconds: float | None = None,
        stage_callback=None,
    ) -> dict[str, object]:
        bounds = (
            month_year
            if isinstance(month_year, MonthBounds)
            else self._parse_month_bounds(str(month_year))
        )
        existing_gold_rows = self._count_gold_month_rows(bounds)
        stage_results: list[dict[str, object]] = []
        csi_df = pd.DataFrame()
        csi_team_size_by_hash: dict[str, float | None] = {}
        target_rows: list[dict[str, object]] = []

        def emit_stage_event(event_type: str, payload: dict[str, object]) -> None:
            if stage_callback is None:
                return
            stage_callback(
                {
                    "event": event_type,
                    "target_month": bounds.label,
                    "target_month_key": bounds.month_key,
                    **payload,
                }
            )

        def run_stage(stage_name: str, fn):
            emit_stage_event("stage_start", {"stage_name": stage_name})
            if stage_timeout_seconds is None or stage_timeout_seconds <= 0:
                return fn()
            if not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"):
                return fn()

            previous_handler = signal.getsignal(signal.SIGALRM)

            def _timeout_handler(signum, frame):
                del signum, frame
                raise TimeoutError(
                    f"Gold debug stage exceeded {stage_timeout_seconds} seconds: {stage_name}"
                )

            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.setitimer(signal.ITIMER_REAL, stage_timeout_seconds)
            try:
                return fn()
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)

        def append_stage_result(
            stage_name: str,
            duration_seconds: float,
            rows_loaded: dict[str, int],
            *,
            rows: list[dict[str, object]] | None = None,
            extra_metrics: dict[str, object] | None = None,
            error: Exception | None = None,
        ) -> bool:
            stage_payload = {
                "stage_name": stage_name,
                "status": "success",
                "duration_seconds": round(duration_seconds, 3),
                "rows_loaded_read": rows_loaded,
                "rows_written": 0,
                "rows_replaced": 0,
            }
            if rows is not None:
                stage_payload.update(self._summarize_debug_gold_rows(rows))
            if extra_metrics:
                stage_payload.update(extra_metrics)
            if error is not None:
                stage_payload["status"] = "timeout" if isinstance(error, TimeoutError) else "error"
                stage_payload["error"] = str(error)
            elif (
                stage_duration_warning_seconds is not None
                and stage_payload["duration_seconds"] > stage_duration_warning_seconds
            ):
                stage_payload["status"] = "threshold_exceeded"
                stage_payload["stage_duration_warning_seconds"] = stage_duration_warning_seconds
            stage_results.append(stage_payload)
            emit_stage_event("stage_result", stage_payload)
            return stage_payload["status"] != "success"

        stage_start = time.perf_counter()
        try:
            def _stage_one():
                energy_df = self._filter_silver_rows("energy_meter_hour", bounds)
                return energy_df, self._build_base_gold_rows(energy_df)

            energy_month_df, target_rows = run_stage(
                self.GOLD_DEBUG_STAGE_NAMES[0],
                _stage_one,
            )
        except Exception as exc:
            append_stage_result(
                self.GOLD_DEBUG_STAGE_NAMES[0],
                time.perf_counter() - stage_start,
                {"energy_meter_hour": 0},
                error=exc,
            )
            return self._build_gold_debug_result(bounds, stage_results)
        if append_stage_result(
            self.GOLD_DEBUG_STAGE_NAMES[0],
            time.perf_counter() - stage_start,
            {"energy_meter_hour": len(energy_month_df)},
            rows=target_rows,
        ):
            return self._build_gold_debug_result(bounds, stage_results)

        stage_start = time.perf_counter()
        try:
            def _stage_two():
                stage_csi_df = self._filter_silver_rows("csi_job_event", bounds)
                stage_csi_by_machine = self.gold._build_csi_event_groups(stage_csi_df)
                return (
                    stage_csi_df,
                    stage_csi_by_machine,
                    self._overlay_gold_rows_with_csi(target_rows, stage_csi_by_machine),
                )

            csi_df, csi_by_machine, target_rows = run_stage(
                self.GOLD_DEBUG_STAGE_NAMES[1],
                _stage_two,
            )
        except Exception as exc:
            append_stage_result(
                self.GOLD_DEBUG_STAGE_NAMES[1],
                time.perf_counter() - stage_start,
                {"csi_job_event": len(csi_df)},
                error=exc,
            )
            return self._build_gold_debug_result(bounds, stage_results)
        if append_stage_result(
            self.GOLD_DEBUG_STAGE_NAMES[1],
            time.perf_counter() - stage_start,
            {"csi_job_event": len(csi_df)},
            rows=target_rows,
            extra_metrics={"csi_machine_group_count": len(csi_by_machine)},
        ):
            return self._build_gold_debug_result(bounds, stage_results)

        target_csi_hashes = self._collect_target_csi_hashes(target_rows)
        stage_start = time.perf_counter()
        try:
            def _stage_three():
                stage_supporting_gold_df = self._read_other_gold_rows_by_csi_source_hashes(
                    bounds,
                    target_csi_hashes,
                )
                return stage_supporting_gold_df, self._apply_csi_quantity(
                    target_rows,
                    stage_supporting_gold_df,
                    csi_df,
                )

            supporting_gold_df, target_rows = run_stage(
                self.GOLD_DEBUG_STAGE_NAMES[2],
                _stage_three,
            )
        except Exception as exc:
            append_stage_result(
                self.GOLD_DEBUG_STAGE_NAMES[2],
                time.perf_counter() - stage_start,
                {"csi_job_event": len(csi_df)},
                error=exc,
                extra_metrics={"target_csi_source_hash_count": len(target_csi_hashes)},
            )
            return self._build_gold_debug_result(bounds, stage_results)
        if append_stage_result(
            self.GOLD_DEBUG_STAGE_NAMES[2],
            time.perf_counter() - stage_start,
            {"csi_job_event": len(csi_df)},
            rows=target_rows,
            extra_metrics={
                "target_csi_source_hash_count": len(target_csi_hashes),
                "supporting_gold_rows_read": len(supporting_gold_df),
            },
        ):
            return self._build_gold_debug_result(bounds, stage_results)

        stage_start = time.perf_counter()
        try:
            def _stage_four():
                stage_mes_df = self._filter_silver_rows("mes_report_event", bounds)
                stage_mes_by_machine = self.gold._build_mes_event_groups(stage_mes_df)
                stage_csi_team_size_by_hash = self.gold._build_csi_team_size_lookup(csi_df)
                return stage_mes_df, stage_mes_by_machine, stage_csi_team_size_by_hash, self._overlay_gold_rows_with_mes(
                    target_rows,
                    stage_mes_by_machine,
                    stage_csi_team_size_by_hash,
                )

            mes_df, mes_by_machine, csi_team_size_by_hash, target_rows = run_stage(
                self.GOLD_DEBUG_STAGE_NAMES[3],
                _stage_four,
            )
        except Exception as exc:
            append_stage_result(
                self.GOLD_DEBUG_STAGE_NAMES[3],
                time.perf_counter() - stage_start,
                {"mes_report_event": 0},
                error=exc,
            )
            return self._build_gold_debug_result(bounds, stage_results)
        if append_stage_result(
            self.GOLD_DEBUG_STAGE_NAMES[3],
            time.perf_counter() - stage_start,
            {"mes_report_event": len(mes_df)},
            rows=target_rows,
            extra_metrics={"mes_machine_group_count": len(mes_by_machine)},
        ):
            return self._build_gold_debug_result(bounds, stage_results)

        stage_start = time.perf_counter()
        try:
            def _stage_five():
                stage_maintenance_df = self._read_table("maintenance_txn_event")
                stage_maintenance_by_machine = self.gold._build_maintenance_event_groups(
                    stage_maintenance_df
                )
                return (
                    stage_maintenance_df,
                    stage_maintenance_by_machine,
                    self._overlay_gold_rows_with_idle_and_maintenance_state_review(
                        self._overlay_gold_rows_with_maintenance(
                            target_rows,
                            stage_maintenance_by_machine,
                        )
                    ),
                )

            maintenance_df, maintenance_by_machine, target_rows = run_stage(
                self.GOLD_DEBUG_STAGE_NAMES[4],
                _stage_five,
            )
        except Exception as exc:
            append_stage_result(
                self.GOLD_DEBUG_STAGE_NAMES[4],
                time.perf_counter() - stage_start,
                {"maintenance_txn_event": 0},
                error=exc,
            )
            return self._build_gold_debug_result(bounds, stage_results)
        if append_stage_result(
            self.GOLD_DEBUG_STAGE_NAMES[4],
            time.perf_counter() - stage_start,
            {"maintenance_txn_event": len(maintenance_df)},
            rows=target_rows,
            extra_metrics={"maintenance_machine_group_count": len(maintenance_by_machine)},
        ):
            return self._build_gold_debug_result(bounds, stage_results)

        stage_start = time.perf_counter()
        try:
            def _stage_six():
                stage_final_rows = self._serialize_gold_rows(target_rows)
                self._replace_gold_month_partition(stage_final_rows, bounds)
                return stage_final_rows

            final_rows = run_stage(
                self.GOLD_DEBUG_STAGE_NAMES[5],
                _stage_six,
            )
        except Exception as exc:
            append_stage_result(
                self.GOLD_DEBUG_STAGE_NAMES[5],
                time.perf_counter() - stage_start,
                {
                    "existing_fact_machine_hour_rows_in_month": existing_gold_rows,
                    "final_stage_input_rows": len(target_rows),
                },
                error=exc,
            )
            return self._build_gold_debug_result(bounds, stage_results)
        append_stage_result(
            self.GOLD_DEBUG_STAGE_NAMES[5],
            time.perf_counter() - stage_start,
            {
                "existing_fact_machine_hour_rows_in_month": existing_gold_rows,
                "final_stage_input_rows": len(final_rows),
            },
            extra_metrics={
                "rows_replaced": existing_gold_rows,
                "rows_written": len(final_rows),
                "post_replace_fact_machine_hour_rows_in_month": self._count_gold_month_rows(bounds),
            },
        )
        return self._build_gold_debug_result(bounds, stage_results)

    def _read_other_gold_rows(self, bounds: MonthBounds) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query(
                """
                SELECT *
                FROM fact_machine_hour
                WHERE hour_ts < ?
                   OR hour_ts >= ?
                """,
                conn,
                params=(bounds.start.isoformat(), bounds.end.isoformat()),
            )
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _read_other_gold_rows_by_csi_source_hashes(
        self,
        bounds: MonthBounds,
        source_hashes: set[str],
    ) -> pd.DataFrame:
        if not source_hashes:
            return pd.DataFrame()

        placeholders = ", ".join("?" for _ in source_hashes)
        params = [*sorted(source_hashes), bounds.start.isoformat(), bounds.end.isoformat()]
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query(
                f"""
                SELECT *
                FROM fact_machine_hour
                WHERE csi_source_row_hash IN ({placeholders})
                  AND (hour_ts < ? OR hour_ts >= ?)
                """,
                conn,
                params=params,
            )
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _materialize_gold_backbone_only(self, bounds: MonthBounds) -> pd.DataFrame:
        energy_month_df = self._filter_silver_rows("energy_meter_hour", bounds)
        target_rows = self._build_base_gold_rows(energy_month_df)
        self._replace_gold_month_partition(target_rows, bounds)
        return pd.DataFrame(target_rows)

    def _build_base_gold_rows(self, energy_month_df: pd.DataFrame) -> list[dict[str, object]]:
        gold_rows = self.gold.build_gold_rows_from_energy_dataframe(energy_month_df)
        unique_hour_values = sorted(
            {
                str(row["hour_ts"]).strip()
                for row in gold_rows
                if str(row.get("hour_ts") or "").strip()
            }
        )
        parsed_hour_values = pd.to_datetime(unique_hour_values, errors="coerce")
        hour_ts_lookup = {
            hour_ts: parsed_hour_ts
            for hour_ts, parsed_hour_ts in zip(unique_hour_values, parsed_hour_values)
        }
        return [
            {
                **row,
                "_hour_ts_dt": hour_ts_lookup.get(str(row.get("hour_ts") or "").strip()),
                "source_flags": self.gold._load_source_flags(row.get("source_flags")),
            }
            for row in gold_rows
        ]

    def _build_gold_stage_context(self, bounds: MonthBounds) -> dict[str, object]:
        csi_df = self._filter_silver_rows("csi_job_event", bounds)
        mes_df = self._filter_silver_rows("mes_report_event", bounds)
        maintenance_df = self._read_table("maintenance_txn_event")
        return {
            "energy_month_df": self._filter_silver_rows("energy_meter_hour", bounds),
            "csi_df": csi_df,
            "mes_df": mes_df,
            "maintenance_df": maintenance_df,
            "csi_by_machine": self.gold._build_csi_event_groups(csi_df),
            "mes_by_machine": self.gold._build_mes_event_groups(mes_df),
            "maintenance_by_machine": self.gold._build_maintenance_event_groups(maintenance_df),
            "csi_team_size_by_hash": self.gold._build_csi_team_size_lookup(csi_df),
        }

    def _overlay_gold_rows_with_csi(
        self,
        gold_rows: list[dict[str, object]],
        csi_by_machine: dict[str, list[dict[str, object]]],
        profiler: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        target_rows = []
        for canonical_machine_id, machine_rows_iter in groupby(
            gold_rows,
            key=lambda row: row["canonical_machine_id"],
        ):
            machine_rows = list(machine_rows_iter)
            target_rows.extend(
                self.gold._overlay_machine_rows_with_csi(
                    machine_rows,
                    csi_by_machine.get(canonical_machine_id, []),
                    profiler=profiler,
                )
            )
        return target_rows

    def profile_gold_csi_overlay_hot_path(
        self,
        month_year: str | MonthBounds,
        *,
        top_n: int = 10,
    ) -> dict[str, object]:
        bounds = (
            month_year
            if isinstance(month_year, MonthBounds)
            else self._parse_month_bounds(str(month_year))
        )
        energy_month_df = self._filter_silver_rows("energy_meter_hour", bounds)
        base_gold_rows = self._build_base_gold_rows(energy_month_df)
        csi_df = self._filter_silver_rows("csi_job_event", bounds)
        csi_by_machine = self.gold._build_csi_event_groups(csi_df)
        profiler = self.gold.build_csi_overlay_profile()

        overlay_started_at = time.perf_counter()
        overlaid_rows = self._overlay_gold_rows_with_csi(
            base_gold_rows,
            csi_by_machine,
            profiler=profiler,
        )
        overlay_seconds = time.perf_counter() - overlay_started_at
        summary = self.gold.summarize_csi_overlay_profile(
            profiler,
            total_overlay_seconds=overlay_seconds,
            top_n=top_n,
        )
        return {
            "status": "success",
            "target_month": bounds.label,
            "target_month_key": bounds.month_key,
            "base_gold_row_count": len(base_gold_rows),
            "csi_job_event_row_count": len(csi_df),
            "machine_groups_with_csi_events": len(csi_by_machine),
            "rows_with_csi_source_after_overlay": sum(
                1
                for row in overlaid_rows
                if self.gold._clean_text(row.get("csi_source_row_hash"))
            ),
            **summary,
        }

    def _overlay_gold_rows_with_mes(
        self,
        target_rows: list[dict[str, object]],
        mes_by_machine: dict[str, dict[str, object]],
        csi_team_size_by_hash: dict[str, float | None],
    ) -> list[dict[str, object]]:
        updated_rows = []
        for row in target_rows:
            updated_rows.append(
                self.gold._overlay_fact_row_with_mes(
                    row,
                    mes_by_machine.get(row["canonical_machine_id"], {"candidates_by_key": {}}),
                    csi_team_size_by_hash,
                )
            )
        return updated_rows

    def _overlay_gold_rows_with_maintenance(
        self,
        target_rows: list[dict[str, object]],
        maintenance_by_machine: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        updated_rows = []
        for row in target_rows:
            updated_rows.append(
                self.gold._overlay_fact_row_with_maintenance(
                    row,
                    maintenance_by_machine.get(
                        row["canonical_machine_id"],
                        {"events": [], "txn_ts_values": []},
                    ),
                )
            )
        return updated_rows

    def _overlay_gold_rows_with_idle_and_maintenance_state_review(
        self,
        target_rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        return [
            self.gold._overlay_fact_row_with_maintenance_state_review(
                self.gold._overlay_fact_row_with_idle(row)
            )
            for row in target_rows
        ]

    def _serialize_gold_rows(self, target_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                **{key: value for key, value in row.items() if key != "_hour_ts_dt"},
                "source_flags": json.dumps(
                    self.gold._load_source_flags(row.get("source_flags")),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
            for row in target_rows
        ]

    def _collect_target_csi_hashes(self, target_rows: list[dict[str, object]]) -> set[str]:
        return {
            self.gold._clean_text(row.get("csi_source_row_hash"))
            for row in target_rows
            if self.gold._clean_text(row.get("csi_source_row_hash"))
        }

    def _count_supporting_gold_rows(self, bounds: MonthBounds, source_hashes: set[str]) -> int:
        if not source_hashes:
            return 0
        return len(self._read_other_gold_rows_by_csi_source_hashes(bounds, source_hashes))

    def _build_gold_debug_result(
        self,
        bounds: MonthBounds,
        stage_results: list[dict[str, object]],
    ) -> dict[str, object]:
        final_status = "success"
        first_non_success_stage = None
        for stage in stage_results:
            if stage["status"] != "success":
                final_status = stage["status"]
                first_non_success_stage = stage["stage_name"]
                break
        return {
            "status": final_status,
            "target_month": bounds.label,
            "target_month_key": bounds.month_key,
            "stage_results": stage_results,
            "first_non_success_stage": first_non_success_stage,
            "available_months_after_run": (
                self._query_available_gold_months()
                if final_status == "success"
                else []
            ),
        }

    def _summarize_debug_gold_rows(self, rows: list[dict[str, object]]) -> dict[str, object]:
        machine_ids = {
            self.gold._clean_text(row.get("canonical_machine_id"))
            for row in rows
            if self.gold._clean_text(row.get("canonical_machine_id"))
        }
        hour_values = {
            self.gold._clean_text(row.get("hour_ts"))
            for row in rows
            if self.gold._clean_text(row.get("hour_ts"))
        }
        return {
            "stage_output_row_count": len(rows),
            "stage_output_machine_count": len(machine_ids),
            "stage_output_hour_count": len(hour_values),
            "rows_with_csi_source": sum(
                1 for row in rows if self.gold._clean_text(row.get("csi_source_row_hash"))
            ),
            "rows_with_mes_source": sum(
                1 for row in rows if self.gold._clean_text(row.get("mes_source_row_hash"))
            ),
            "rows_with_quantity": sum(
                1
                for row in rows
                if row.get("good_qty") is not None or row.get("scrap_qty") is not None
            ),
            "rows_with_same_hour_maintenance": sum(
                1
                for row in rows
                if bool(
                    self.gold._float_or_none(row.get("maintenance_txn_in_hour"))
                    or self.gold._load_source_flags(row.get("source_flags")).get("maintenance_txn_in_hour")
                )
            ),
            "rows_with_maintenance_state": sum(
                1 for row in rows if self.gold._clean_text(row.get("machine_state")) == "maintenance"
            ),
        }

    def _count_gold_month_rows(
        self,
        bounds: MonthBounds,
        *,
        rows: list[dict[str, object]] | None = None,
    ) -> int:
        if rows is not None:
            return len(rows)
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM fact_machine_hour
                WHERE hour_ts >= ? AND hour_ts < ?
                """,
                (bounds.start.isoformat(), bounds.end.isoformat()),
            ).fetchone()
            return int(row[0] if row else 0)
        finally:
            conn.close()

    def _query_available_gold_months(self) -> list[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT substr(hour_ts, 1, 7) AS month_key
                FROM fact_machine_hour
                WHERE hour_ts IS NOT NULL
                  AND trim(hour_ts) <> ''
                ORDER BY month_key DESC
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()
        return [self._month_key_to_label(str(month_key)) for month_key, in rows]

    def _apply_csi_quantity(
        self,
        target_rows: list[dict[str, object]],
        existing_other_gold_df: pd.DataFrame,
        csi_df: pd.DataFrame,
    ) -> list[dict[str, object]]:
        csi_event_by_hash = {}
        for _, csi_row in csi_df.iterrows():
            source_row_hash = self.gold._clean_text(csi_row.get("source_row_hash"))
            if source_row_hash:
                csi_event_by_hash[source_row_hash] = csi_row

        basis_rows = []
        if not existing_other_gold_df.empty:
            basis_rows.extend(existing_other_gold_df.to_dict(orient="records"))
        basis_rows.extend(row.copy() for row in target_rows)

        rows_by_csi_hash: dict[str, list[dict[str, object]]] = {}
        for row in basis_rows:
            source_row_hash = self.gold._clean_text(row.get("csi_source_row_hash"))
            if source_row_hash:
                rows_by_csi_hash.setdefault(source_row_hash, []).append(row)

        basis_minutes_by_hash = {
            source_row_hash: sum(
                quantity_basis_minutes
                for quantity_basis_minutes in [
                    self.gold._csi_quantity_basis_minutes_from_row(row) for row in rows
                ]
                if quantity_basis_minutes is not None and quantity_basis_minutes > 0
            )
            for source_row_hash, rows in rows_by_csi_hash.items()
        }

        updated_rows = []
        for row in target_rows:
            original_row = row.copy()
            updated_row = original_row.copy()
            self.gold._reset_csi_quantity_fields(updated_row)
            source_row_hash = self.gold._clean_text(updated_row.get("csi_source_row_hash"))
            quantity_basis_minutes = self.gold._csi_quantity_basis_minutes_from_row(updated_row)
            audit_quantity_basis_minutes, _ = (
                self.gold._reconstruct_csi_quantity_audit_basis_minutes(original_row)
            )
            audit_basis_minutes = sum(
                reconstructed_basis_minutes
                for reconstructed_basis_minutes, _ in [
                    self.gold._reconstruct_csi_quantity_audit_basis_minutes(basis_row)
                    for basis_row in rows_by_csi_hash.get(source_row_hash or "", [])
                ]
                if reconstructed_basis_minutes is not None and reconstructed_basis_minutes > 0
            )
            quantity_updates = self.gold._build_csi_quantity_updates(
                updated_row=updated_row,
                csi_row=csi_event_by_hash.get(source_row_hash or ""),
                source_row_hash=source_row_hash,
                quantity_basis_minutes=quantity_basis_minutes,
                basis_minutes=basis_minutes_by_hash.get(source_row_hash or "", 0.0),
                audit_quantity_basis_minutes=audit_quantity_basis_minutes,
                audit_basis_minutes=audit_basis_minutes,
            )
            updated_row["good_qty"] = quantity_updates["good_qty"]
            updated_row["scrap_qty"] = quantity_updates["scrap_qty"]
            for column_name in self.gold._csi_quantity_audit_columns():
                updated_row[column_name] = quantity_updates[column_name]
            updated_row["source_flags"] = self.gold._merge_source_flags(
                updated_row.get("source_flags"),
                quantity_updates["source_flags"],
                remove_keys=self.gold._csi_quantity_source_flag_keys(),
            )
            updated_rows.append(updated_row)

        return updated_rows

    def _replace_silver_month_partition(
        self,
        table_name: str,
        fresh_rows: list[dict[str, object]],
        bounds: MonthBounds,
    ) -> None:
        insert_rows = [row.copy() for row in fresh_rows]
        self._delete_month_partition(table_name, bounds, self.SILVER_MONTH_SQL)
        self._insert_rows(table_name, insert_rows)

    def _replace_gold_month_partition(self, fresh_rows: list[dict[str, object]], bounds: MonthBounds) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM fact_machine_hour
            WHERE hour_ts >= ? AND hour_ts < ?
            """,
            (bounds.start.isoformat(), bounds.end.isoformat()),
        )
        if fresh_rows:
            columns = list(fresh_rows[0].keys())
            column_list = ", ".join(columns)
            placeholders = ", ".join("?" for _ in columns)
            cursor.executemany(
                f"INSERT INTO fact_machine_hour ({column_list}) VALUES ({placeholders})",
                [tuple(row[column] for column in columns) for row in fresh_rows],
            )
        conn.commit()
        conn.close()

    def _delete_rows_by_source_row_hash(self, table_name: str, row_hashes: list[str]) -> None:
        if not row_hashes:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ", ".join("?" for _ in row_hashes)
        cursor.execute(
            f"DELETE FROM {table_name} WHERE source_row_hash IN ({placeholders})",
            row_hashes,
        )
        conn.commit()
        conn.close()

    def _delete_month_partition(
        self,
        table_name: str,
        bounds: MonthBounds,
        table_sql: dict[str, str],
    ) -> None:
        month_expression = table_sql.get(table_name)
        if not month_expression:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"""
            DELETE FROM {table_name}
            WHERE {month_expression} = ?
            """,
            (bounds.month_key,),
        )
        conn.commit()
        conn.close()

    def _upsert_rows_by_source_row_hash(self, table_name: str, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        columns = list(rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)
        update_clause = ", ".join(
            f"{column}=excluded.{column}"
            for column in columns
            if column != "source_row_hash"
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            f"""
            INSERT INTO {table_name} ({column_list})
            VALUES ({placeholders})
            ON CONFLICT(source_row_hash) DO UPDATE SET
            {update_clause}
            """,
            [tuple(row[column] for column in columns) for row in rows],
        )
        conn.commit()
        conn.close()

    def _insert_rows(self, table_name: str, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        columns = list(rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        column_list = ", ".join(columns)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany(
            f"""
            INSERT INTO {table_name} ({column_list})
            VALUES ({placeholders})
            """,
            [tuple(row[column] for column in columns) for row in rows],
        )
        conn.commit()
        conn.close()

    def _filter_bronze_rows(self, table_name: str, bounds: MonthBounds) -> pd.DataFrame:
        return self._read_month_partition(table_name, bounds, self.BRONZE_MONTH_SQL)

    def _filter_silver_rows(self, table_name: str, bounds: MonthBounds) -> pd.DataFrame:
        return self._read_month_partition(table_name, bounds, self.SILVER_MONTH_SQL)

    def _read_table(self, table_name: str) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _read_month_partition(
        self,
        table_name: str,
        bounds: MonthBounds,
        table_sql: dict[str, str],
    ) -> pd.DataFrame:
        month_expression = table_sql.get(table_name)
        if not month_expression:
            return self._read_table(table_name)

        conn = sqlite3.connect(self.db_path)
        try:
            select_sql = self.BRONZE_MONTH_SELECT_SQL.get(table_name)
            if select_sql is not None:
                query = select_sql.format(month_expression=month_expression)
            else:
                query = f"""
                    SELECT *
                    FROM {table_name}
                    WHERE {month_expression} = ?
                """
            return pd.read_sql_query(
                query,
                conn,
                params=(bounds.month_key,),
            )
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _summarize_month_counts(self, table_sql: dict[str, str]) -> list[dict[str, object]]:
        summary_rows: list[dict[str, object]] = []
        for table_name, month_expression in table_sql.items():
            summary_rows.extend(self._query_month_counts(table_name, month_expression))
        return summary_rows

    def _query_month_counts(self, table_name: str, month_expression: str) -> list[dict[str, object]]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                f"""
                SELECT month, COUNT(*) AS row_count
                FROM (
                    SELECT {month_expression} AS month
                    FROM {table_name}
                )
                WHERE month IS NOT NULL
                  AND trim(month) <> ''
                GROUP BY month
                ORDER BY month
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

        return [
            {
                "table_name": table_name,
                "month": month,
                "month_label": self._month_key_to_label(str(month)),
                "row_count": int(row_count),
            }
            for month, row_count in rows
        ]

    @staticmethod
    def _month_key_to_label(month_key: str) -> str:
        parsed = datetime.strptime(month_key.strip(), "%Y-%m")
        return parsed.strftime("%B %Y")

    def _bronze_row_in_month(self, table_name: str, row: pd.Series, bounds: MonthBounds) -> bool:
        if table_name == "raw_energy_hourly":
            return self._timestamp_in_month(row.get("raw_timestamp"), bounds)
        if table_name == "raw_csi_event":
            payload = self._load_payload(row.get("raw_payload_json"))
            return self._any_in_month(
                bounds,
                row.get("raw_start_time"),
                row.get("raw_end_time"),
                row.get("raw_prep_end_time"),
                payload.get("班次內日期"),
            )
        if table_name == "raw_mes_report":
            payload = self._load_payload(row.get("raw_payload_json"))
            return self._timestamp_in_month(payload.get("報工時間"), bounds)
        if table_name == "raw_maintenance_txn":
            return self._timestamp_in_month(row.get("raw_transaction_date"), bounds)
        return False

    def _silver_row_in_month(self, table_name: str, row: pd.Series, bounds: MonthBounds) -> bool:
        if table_name == "energy_meter_hour":
            return self._timestamp_in_month(row.get("hour_ts"), bounds)
        if table_name == "csi_job_event":
            return self._any_in_month(
                bounds,
                row.get("prod_start_ts"),
                row.get("prod_end_ts"),
                row.get("prep_end_ts"),
                row.get("shift_date"),
            )
        if table_name == "mes_report_event":
            return self._timestamp_in_month(row.get("report_ts"), bounds)
        if table_name == "maintenance_txn_event":
            return self._timestamp_in_month(row.get("txn_ts"), bounds)
        return False

    @staticmethod
    def _load_payload(raw_payload_json: object) -> dict[str, object]:
        if raw_payload_json is None:
            return {}
        try:
            if pd.isna(raw_payload_json):
                return {}
        except TypeError:
            pass
        try:
            parsed = json.loads(str(raw_payload_json))
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _any_in_month(bounds: MonthBounds, *values: object) -> bool:
        return any(CanonicalMaterializer._timestamp_in_month(value, bounds) for value in values)

    @staticmethod
    def _timestamp_in_month(value: object, bounds: MonthBounds) -> bool:
        parsed = CanonicalMaterializer._parse_timestamp(value)
        if parsed is None:
            return False
        return bounds.start <= parsed < bounds.end

    @staticmethod
    def _parse_timestamp(value: object) -> pd.Timestamp | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        parsed = pd.to_datetime(str(value).strip(), errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed

    @staticmethod
    def _parse_month_bounds(month_year: str) -> MonthBounds:
        parsed = datetime.strptime(month_year.strip(), "%B %Y")
        start = pd.Timestamp(year=parsed.year, month=parsed.month, day=1)
        if parsed.month == 12:
            end = pd.Timestamp(year=parsed.year + 1, month=1, day=1)
        else:
            end = pd.Timestamp(year=parsed.year, month=parsed.month + 1, day=1)
        return MonthBounds(
            label=month_year.strip(),
            start=start,
            end=end,
            month_key=start.strftime("%Y-%m"),
        )
