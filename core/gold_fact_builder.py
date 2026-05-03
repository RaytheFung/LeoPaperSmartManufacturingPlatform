"""Gold fact-machine-hour builder for the staged Gold rebuild.

The Gold table is still anchored on one row per
`canonical_machine_id x hour_ts`, with additive overlays layered on top:
- energy builds the backbone
- CSI adds setup / production context
- MES adds report-level manpower context
"""

from __future__ import annotations

import json
import sqlite3
import time
from bisect import bisect_left
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

from core.runtime_paths import get_database_path

CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES = 0.5
CSI_MINUTE_BUDGET_TOLERANCE_MINUTES = 0.5
CSI_OVERLAY_PROFILE_STEP_NAMES = (
    "per_machine_preparation_seconds",
    "gold_hour_row_prep_sort_seconds",
    "csi_event_window_prep_sort_seconds",
    "active_event_window_maintenance_seconds",
    "overlap_candidate_construction_seconds",
    "dominant_event_selection_seconds",
    "row_mutation_seconds",
    "source_flag_json_seconds",
)


class GoldFactBuilder:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_database_path())
        self.ensure_tables()

    def ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_machine_hour (
                canonical_machine_id TEXT NOT NULL,
                hour_ts TEXT NOT NULL,
                machine_state TEXT,
                state_confidence TEXT,
                energy_total_kwh REAL,
                energy_total_cost REAL,
                energy_main_kwh REAL,
                energy_uv_kwh REAL,
                energy_ir_kwh REAL,
                energy_motor_kwh REAL,
                source_flags TEXT,
                energy_total_source_method TEXT,
                energy_source_row_count INTEGER,
                energy_source_row_hashes_json TEXT,
                order_id TEXT,
                order_suffix TEXT,
                material_code TEXT,
                task_name TEXT,
                setup_minutes REAL,
                production_minutes REAL,
                planned_stop_minutes REAL,
                unplanned_stop_minutes REAL,
                maintenance_minutes REAL,
                idle_minutes REAL,
                good_qty REAL,
                scrap_qty REAL,
                csi_qty_basis_method TEXT,
                csi_qty_row_basis_minutes REAL,
                csi_qty_event_basis_minutes REAL,
                csi_qty_minutes_vs_production_diff REAL,
                csi_qty_minutes_vs_production_abs_diff REAL,
                csi_qty_alignment_status TEXT,
                csi_qty_material_misalignment_flag INTEGER,
                csi_qty_minute_budget_anomaly_flag INTEGER,
                csi_qty_minute_budget_anomaly_reason TEXT,
                actual_speed_per_hour REAL,
                team_leader TEXT,
                csi_source_row_hash TEXT,
                csi_overlap_minutes REAL,
                multiple_csi_overlap_flag INTEGER,
                setup_inference_method TEXT,
                setup_confidence TEXT,
                mes_source_row_hash TEXT,
                mes_report_ts TEXT,
                mes_match_method TEXT,
                mes_match_confidence TEXT,
                last_maintenance_txn_ts TEXT,
                last_maintenance_source_row_hash TEXT,
                last_maintenance_work_order_type TEXT,
                team_size REAL,
                manpower REAL,
                has_maintenance_history INTEGER,
                maintenance_txn_in_hour INTEGER,
                maintenance_distinct_work_order_count_7d INTEGER,
                maintenance_distinct_work_order_count_30d INTEGER,
                maintenance_distinct_work_order_in_hour_count INTEGER,
                cumulative_maintenance_count INTEGER,
                hours_since_last_maintenance REAL,
                days_since_last_maintenance REAL,
                attribution_method TEXT,
                PRIMARY KEY (canonical_machine_id, hour_ts)
            )
            """
        )
        self._ensure_table_columns(
            cursor,
            "fact_machine_hour",
            {
                "csi_source_row_hash": "TEXT",
                "csi_overlap_minutes": "REAL",
                "multiple_csi_overlap_flag": "INTEGER",
                "csi_qty_basis_method": "TEXT",
                "csi_qty_row_basis_minutes": "REAL",
                "csi_qty_event_basis_minutes": "REAL",
                "csi_qty_minutes_vs_production_diff": "REAL",
                "csi_qty_minutes_vs_production_abs_diff": "REAL",
                "csi_qty_alignment_status": "TEXT",
                "csi_qty_material_misalignment_flag": "INTEGER",
                "csi_qty_minute_budget_anomaly_flag": "INTEGER",
                "csi_qty_minute_budget_anomaly_reason": "TEXT",
                "setup_inference_method": "TEXT",
                "setup_confidence": "TEXT",
                "order_suffix": "TEXT",
                "mes_source_row_hash": "TEXT",
                "mes_report_ts": "TEXT",
                "mes_match_method": "TEXT",
                "mes_match_confidence": "TEXT",
                "last_maintenance_txn_ts": "TEXT",
                "last_maintenance_source_row_hash": "TEXT",
                "last_maintenance_work_order_type": "TEXT",
                "has_maintenance_history": "INTEGER",
                "maintenance_txn_in_hour": "INTEGER",
                "maintenance_distinct_work_order_count_7d": "INTEGER",
                "maintenance_distinct_work_order_count_30d": "INTEGER",
                "maintenance_distinct_work_order_in_hour_count": "INTEGER",
                "cumulative_maintenance_count": "INTEGER",
            },
        )
        conn.commit()
        conn.close()

    def build_fact_machine_hour(self) -> pd.DataFrame:
        energy_df = self._read_silver_energy()
        gold_rows = self.build_gold_rows_from_energy_dataframe(energy_df)
        if not gold_rows:
            self._replace_rows([])
            return pd.DataFrame()

        self._replace_rows(gold_rows)
        return pd.DataFrame(gold_rows)

    def build_gold_rows_from_energy_dataframe(self, energy_df: pd.DataFrame) -> list[dict[str, object]]:
        if energy_df.empty:
            return []

        records = []
        for row in energy_df.to_dict(orient="records"):
            canonical_machine_id = str(row.get("canonical_machine_id") or "").strip()
            hour_ts = str(row.get("hour_ts") or "").strip()
            if not canonical_machine_id or not hour_ts:
                continue
            records.append(
                {
                    "canonical_machine_id": canonical_machine_id,
                    "hour_ts": hour_ts,
                    "meter_component": str(row.get("meter_component") or "").strip(),
                    "kwh": self._float_or_none(row.get("kwh")),
                    "cost": self._float_or_none(row.get("cost")),
                    "source_row_hash": str(row.get("source_row_hash") or "").strip(),
                }
            )

        if not records:
            return []

        records.sort(key=lambda row: (row["canonical_machine_id"], row["hour_ts"]))

        gold_rows = []
        current_key: tuple[str, str] | None = None
        current_records: list[dict[str, object]] = []
        for row in records:
            row_key = (row["canonical_machine_id"], row["hour_ts"])
            if current_key is not None and row_key != current_key:
                gold_rows.append(self._build_gold_row_from_records(current_key[0], current_key[1], current_records))
                current_records = []
            current_key = row_key
            current_records.append(row)

        if current_key is not None and current_records:
            gold_rows.append(self._build_gold_row_from_records(current_key[0], current_key[1], current_records))

        return gold_rows

    @staticmethod
    def build_csi_overlay_profile() -> dict[str, object]:
        return {
            "machine_runtime_distribution": [],
            "internal_step_totals": {
                step_name: 0.0 for step_name in CSI_OVERLAY_PROFILE_STEP_NAMES
            },
            "total_machine_groups_processed": 0,
            "total_gold_rows_processed": 0,
            "total_csi_events_processed": 0,
            "total_hours_profiled": 0,
            "total_candidate_overlap_count": 0,
            "total_rows_with_csi_overlap": 0,
        }

    @classmethod
    def summarize_csi_overlay_profile(
        cls,
        profile: dict[str, object],
        *,
        total_overlay_seconds: float | None = None,
        top_n: int = 10,
    ) -> dict[str, object]:
        machine_runtime_distribution = sorted(
            profile.get("machine_runtime_distribution", []),
            key=lambda item: (
                -float(item.get("overlay_seconds") or 0.0),
                -int(item.get("gold_row_count") or 0),
                item.get("canonical_machine_id") or "",
            ),
        )
        total_overlay_seconds = (
            float(total_overlay_seconds)
            if total_overlay_seconds is not None
            else sum(
                float(machine_profile.get("overlay_seconds") or 0.0)
                for machine_profile in machine_runtime_distribution
            )
        )
        total_hours_profiled = int(profile.get("total_hours_profiled") or 0)
        total_candidate_overlap_count = int(profile.get("total_candidate_overlap_count") or 0)
        top_n_slowest = machine_runtime_distribution[:top_n]
        top_n_share = (
            sum(float(item.get("overlay_seconds") or 0.0) for item in top_n_slowest)
            / total_overlay_seconds
            if total_overlay_seconds > 0
            else 0.0
        )

        return {
            "total_machine_groups_processed": int(profile.get("total_machine_groups_processed") or 0),
            "total_gold_rows_processed": int(profile.get("total_gold_rows_processed") or 0),
            "total_csi_events_processed": int(profile.get("total_csi_events_processed") or 0),
            "total_rows_with_csi_overlap": int(profile.get("total_rows_with_csi_overlap") or 0),
            "total_overlay_seconds": round(total_overlay_seconds, 3),
            "internal_step_totals": {
                step_name: round(float(seconds), 3)
                for step_name, seconds in profile.get("internal_step_totals", {}).items()
            },
            "average_candidate_overlap_count": (
                round(total_candidate_overlap_count / total_hours_profiled, 6)
                if total_hours_profiled > 0
                else 0.0
            ),
            "slowest_top_n_share_of_overlay_seconds": round(top_n_share, 6),
            "runtime_distribution_shape": (
                "dominated_by_small_number_of_pathological_machine_groups"
                if top_n_share >= 0.5
                else "globally_expensive_across_most_machines"
            ),
            "top_slowest_machine_groups": top_n_slowest,
            "machine_runtime_distribution": machine_runtime_distribution,
        }

    @classmethod
    def _new_csi_overlay_machine_profile(
        cls,
        canonical_machine_id: str | None,
        gold_row_count: int,
    ) -> dict[str, object]:
        return {
            "canonical_machine_id": canonical_machine_id,
            "gold_row_count": int(gold_row_count),
            "csi_event_count": 0,
            "overlay_seconds": 0.0,
            "step_seconds": {
                step_name: 0.0 for step_name in CSI_OVERLAY_PROFILE_STEP_NAMES
            },
            "hours_profiled": 0,
            "candidate_overlap_count_total": 0,
            "avg_candidate_overlap_count": 0.0,
            "max_candidate_overlap_count": 0,
            "max_active_event_count": 0,
            "rows_with_csi_overlap": 0,
        }

    @staticmethod
    def _record_csi_overlay_profile_step(
        machine_profile: dict[str, object] | None,
        step_name: str,
        duration_seconds: float,
    ) -> None:
        if machine_profile is None:
            return
        machine_profile["step_seconds"][step_name] += float(duration_seconds)

    @classmethod
    def _append_csi_overlay_machine_profile(
        cls,
        profile: dict[str, object] | None,
        machine_profile: dict[str, object] | None,
    ) -> None:
        if profile is None or machine_profile is None:
            return

        hours_profiled = int(machine_profile["hours_profiled"] or 0)
        candidate_overlap_count_total = int(machine_profile["candidate_overlap_count_total"] or 0)
        machine_profile["avg_candidate_overlap_count"] = (
            round(candidate_overlap_count_total / hours_profiled, 6)
            if hours_profiled > 0
            else 0.0
        )
        machine_profile["overlay_seconds"] = round(float(machine_profile["overlay_seconds"]), 6)
        machine_profile["step_seconds"] = {
            step_name: round(float(seconds), 6)
            for step_name, seconds in machine_profile["step_seconds"].items()
        }

        profile["machine_runtime_distribution"].append(machine_profile)
        profile["total_machine_groups_processed"] += 1
        profile["total_gold_rows_processed"] += int(machine_profile["gold_row_count"] or 0)
        profile["total_csi_events_processed"] += int(machine_profile["csi_event_count"] or 0)
        profile["total_hours_profiled"] += hours_profiled
        profile["total_candidate_overlap_count"] += candidate_overlap_count_total
        profile["total_rows_with_csi_overlap"] += int(machine_profile["rows_with_csi_overlap"] or 0)
        for step_name, seconds in machine_profile["step_seconds"].items():
            profile["internal_step_totals"][step_name] += float(seconds)

    def _build_gold_row(
        self,
        canonical_machine_id: str,
        hour_ts: str,
        group: pd.DataFrame,
    ) -> dict[str, object]:
        return self._build_gold_row_from_records(
            canonical_machine_id,
            hour_ts,
            group.to_dict(orient="records"),
        )

    def _build_gold_row_from_records(
        self,
        canonical_machine_id: str,
        hour_ts: str,
        records: list[dict[str, object]],
    ) -> dict[str, object]:
        component_sums = {
            "main": [],
            "uv": [],
            "ir": [],
            "motor": [],
        }
        aggregate_kwh = []
        aggregate_cost = []
        component_kwh = []
        component_cost = []
        combo_present = False
        unknown_present = False
        components_present = set()
        source_row_hashes = set()

        for row in records:
            meter_component = str(row.get("meter_component") or "").strip()
            kwh = self._float_or_none(row.get("kwh"))
            cost = self._float_or_none(row.get("cost"))
            source_row_hash = str(row.get("source_row_hash") or "").strip()

            if meter_component:
                components_present.add(meter_component)
            if source_row_hash:
                source_row_hashes.add(source_row_hash)

            if meter_component == "aggregate_total":
                if kwh is not None:
                    aggregate_kwh.append(kwh)
                if cost is not None:
                    aggregate_cost.append(cost)
            elif meter_component in component_sums:
                if kwh is not None:
                    component_sums[meter_component].append(kwh)
                    component_kwh.append(kwh)
                if cost is not None:
                    component_cost.append(cost)
            elif meter_component == "combo":
                combo_present = True
            elif meter_component == "unknown":
                unknown_present = True

        energy_main_kwh = sum(component_sums["main"]) if component_sums["main"] else None
        energy_uv_kwh = sum(component_sums["uv"]) if component_sums["uv"] else None
        energy_ir_kwh = sum(component_sums["ir"]) if component_sums["ir"] else None
        energy_motor_kwh = sum(component_sums["motor"]) if component_sums["motor"] else None

        if aggregate_kwh or aggregate_cost:
            energy_total_kwh = sum(aggregate_kwh) if aggregate_kwh else None
            energy_total_cost = sum(aggregate_cost) if aggregate_cost else None
            energy_total_source_method = "aggregate_total_preferred"
        elif component_kwh or component_cost:
            energy_total_kwh = sum(component_kwh) if component_kwh else None
            energy_total_cost = sum(component_cost) if component_cost else None
            energy_total_source_method = "component_sum_fallback"
        elif combo_present:
            energy_total_kwh = None
            energy_total_cost = None
            energy_total_source_method = "combo_present_no_safe_total"
        else:
            energy_total_kwh = None
            energy_total_cost = None
            energy_total_source_method = "no_usable_energy_rows"

        source_flags = {
            "components_present": sorted(components_present),
            "has_aggregate_total": bool(aggregate_kwh or aggregate_cost),
            "has_combo_meter": combo_present,
            "has_unknown_meter": unknown_present,
            "combo_rows_excluded_from_total": combo_present,
        }

        return {
            "canonical_machine_id": canonical_machine_id,
            "hour_ts": hour_ts,
            "machine_state": "energy_only",
            "state_confidence": "low",
            "energy_total_kwh": energy_total_kwh,
            "energy_total_cost": energy_total_cost,
            "energy_main_kwh": energy_main_kwh,
            "energy_uv_kwh": energy_uv_kwh,
            "energy_ir_kwh": energy_ir_kwh,
            "energy_motor_kwh": energy_motor_kwh,
            "source_flags": json.dumps(source_flags, ensure_ascii=False, sort_keys=True),
            "energy_total_source_method": energy_total_source_method,
            "energy_source_row_count": len(records),
            "energy_source_row_hashes_json": json.dumps(sorted(source_row_hashes), ensure_ascii=False),
            "order_id": None,
            "order_suffix": None,
            "material_code": None,
            "task_name": None,
            "setup_minutes": None,
            "production_minutes": None,
            "planned_stop_minutes": None,
            "unplanned_stop_minutes": None,
            "maintenance_minutes": None,
            "idle_minutes": None,
            "good_qty": None,
            "scrap_qty": None,
            "csi_qty_basis_method": None,
            "csi_qty_row_basis_minutes": None,
            "csi_qty_event_basis_minutes": None,
            "csi_qty_minutes_vs_production_diff": None,
            "csi_qty_minutes_vs_production_abs_diff": None,
            "csi_qty_alignment_status": None,
            "csi_qty_material_misalignment_flag": None,
            "csi_qty_minute_budget_anomaly_flag": None,
            "csi_qty_minute_budget_anomaly_reason": None,
            "actual_speed_per_hour": None,
            "team_leader": None,
            "csi_source_row_hash": None,
            "csi_overlap_minutes": None,
            "multiple_csi_overlap_flag": 0,
            "setup_inference_method": None,
            "setup_confidence": None,
            "mes_source_row_hash": None,
            "mes_report_ts": None,
            "mes_match_method": None,
            "mes_match_confidence": None,
            "last_maintenance_txn_ts": None,
            "last_maintenance_source_row_hash": None,
            "last_maintenance_work_order_type": None,
            "team_size": None,
            "manpower": None,
            "has_maintenance_history": 0,
            "maintenance_txn_in_hour": 0,
            "maintenance_distinct_work_order_count_7d": 0,
            "maintenance_distinct_work_order_count_30d": 0,
            "maintenance_distinct_work_order_in_hour_count": 0,
            "cumulative_maintenance_count": 0,
            "hours_since_last_maintenance": None,
            "days_since_last_maintenance": None,
            "attribution_method": "energy_only_projection",
        }

    def overlay_csi_on_fact_machine_hour(self) -> pd.DataFrame:
        fact_df = self._read_fact_machine_hour()
        if fact_df.empty:
            return pd.DataFrame()

        csi_df = self._read_csi_events()
        csi_by_machine = self._build_csi_event_groups(csi_df)

        updated_rows = []
        fact_rows = (
            fact_df.sort_values(["canonical_machine_id", "hour_ts"])
            .to_dict(orient="records")
        )
        current_machine_id = None
        machine_rows: list[dict[str, object]] = []
        for row in fact_rows:
            machine_id = row["canonical_machine_id"]
            if current_machine_id is not None and machine_id != current_machine_id:
                updated_rows.extend(
                    self._overlay_machine_rows_with_csi(
                        machine_rows,
                        csi_by_machine.get(current_machine_id, []),
                    )
                )
                machine_rows = []
            current_machine_id = machine_id
            machine_rows.append(row)

        if current_machine_id is not None and machine_rows:
            updated_rows.extend(
                self._overlay_machine_rows_with_csi(
                    machine_rows,
                    csi_by_machine.get(current_machine_id, []),
                )
            )

        self._replace_rows(updated_rows)
        return pd.DataFrame(updated_rows)

    def _overlay_fact_row_with_csi(
        self,
        fact_row: pd.Series,
        csi_group,
    ) -> dict[str, object]:
        updated_row = self._fact_row_to_dict(fact_row)
        self._reset_csi_overlay_fields(updated_row)

        hour_start = updated_row.get("_hour_ts_dt")
        if hour_start is None or pd.isna(hour_start):
            hour_start = self._parse_timestamp(updated_row.get("hour_ts"))
        csi_events = self._prepare_csi_group(csi_group)
        if hour_start is None:
            return self._mark_row_without_csi_overlap(updated_row)
        if not csi_events:
            return self._mark_row_without_csi_overlap(updated_row)

        hour_end = hour_start + timedelta(hours=1)
        updated_row, _ = self._overlay_prepared_csi_events_on_row(
            updated_row,
            csi_events,
            hour_start,
            hour_end,
        )
        return updated_row

    def _overlay_machine_rows_with_csi(
        self,
        fact_rows: list[dict[str, object]],
        csi_group,
        profiler: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        if not fact_rows:
            return []

        machine_started_at = time.perf_counter()
        machine_profile = None
        machine_prep_started_at = time.perf_counter()
        machine_id = self._clean_text(fact_rows[0].get("canonical_machine_id"))
        if profiler is not None:
            machine_profile = self._new_csi_overlay_machine_profile(machine_id, len(fact_rows))
        self._record_csi_overlay_profile_step(
            machine_profile,
            "per_machine_preparation_seconds",
            time.perf_counter() - machine_prep_started_at,
        )

        gold_row_prep_started_at = time.perf_counter()
        prepared_fact_rows = []
        for fact_row in fact_rows:
            updated_row = self._fact_row_to_dict(fact_row)
            self._reset_csi_overlay_fields(updated_row)
            hour_start = updated_row.get("_hour_ts_dt")
            if hour_start is None or pd.isna(hour_start):
                hour_start = self._parse_timestamp(updated_row.get("hour_ts"))
            prepared_fact_rows.append(
                (
                    hour_start if hour_start is not None else pd.Timestamp.max,
                    self._clean_text(updated_row.get("hour_ts")) or "",
                    updated_row,
                    hour_start,
                )
            )
        prepared_fact_rows.sort(key=lambda item: (item[0], item[1]))
        self._record_csi_overlay_profile_step(
            machine_profile,
            "gold_hour_row_prep_sort_seconds",
            time.perf_counter() - gold_row_prep_started_at,
        )

        csi_prep_started_at = time.perf_counter()
        csi_events = sorted(
            self._prepare_csi_group(csi_group),
            key=lambda event: (
                event.get("event_window_start_ts") or pd.Timestamp.max,
                event.get("event_window_end_ts") or pd.Timestamp.max,
                event.get("source_row_hash") or "",
            ),
        )
        if machine_profile is not None:
            machine_profile["csi_event_count"] = len(csi_events)
        self._record_csi_overlay_profile_step(
            machine_profile,
            "csi_event_window_prep_sort_seconds",
            time.perf_counter() - csi_prep_started_at,
        )

        updated_rows = []
        active_events: list[dict[str, object]] = []
        next_event_index = 0

        for _, _, updated_row, hour_start in prepared_fact_rows:
            if hour_start is None:
                source_flag_started_at = time.perf_counter()
                updated_rows.append(self._mark_row_without_csi_overlap(updated_row))
                self._record_csi_overlay_profile_step(
                    machine_profile,
                    "source_flag_json_seconds",
                    time.perf_counter() - source_flag_started_at,
                )
                continue

            hour_end = hour_start + timedelta(hours=1)
            active_window_started_at = time.perf_counter()
            while next_event_index < len(csi_events):
                event = csi_events[next_event_index]
                event_window_start_ts = event.get("event_window_start_ts")
                if event_window_start_ts is None or event_window_start_ts >= hour_end:
                    break
                active_events.append(event)
                next_event_index += 1

            if active_events:
                active_events = [
                    event
                    for event in active_events
                    if (event.get("event_window_end_ts") is not None and event.get("event_window_end_ts") > hour_start)
                ]
            self._record_csi_overlay_profile_step(
                machine_profile,
                "active_event_window_maintenance_seconds",
                time.perf_counter() - active_window_started_at,
            )
            if machine_profile is not None:
                machine_profile["max_active_event_count"] = max(
                    int(machine_profile["max_active_event_count"]),
                    len(active_events),
                )

            overlaid_row, _ = self._overlay_prepared_csi_events_on_row(
                updated_row,
                active_events,
                hour_start,
                hour_end,
                profiler_bucket=machine_profile,
            )
            updated_rows.append(overlaid_row)

        if machine_profile is not None:
            machine_profile["overlay_seconds"] = time.perf_counter() - machine_started_at
            self._append_csi_overlay_machine_profile(profiler, machine_profile)
        return updated_rows

    def _overlay_prepared_csi_events_on_row(
        self,
        updated_row: dict[str, object],
        csi_events: list[dict[str, object]],
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
        *,
        profiler_bucket: dict[str, object] | None = None,
    ) -> tuple[dict[str, object], int]:
        if not csi_events:
            source_flag_started_at = time.perf_counter()
            updated_row = self._mark_row_without_csi_overlap(updated_row)
            self._record_csi_overlay_profile_step(
                profiler_bucket,
                "source_flag_json_seconds",
                time.perf_counter() - source_flag_started_at,
            )
            return updated_row, 0

        overlap_started_at = time.perf_counter()
        overlaps = []
        for csi_event in csi_events:
            overlap = self._build_csi_overlap_from_prepared_event(csi_event, hour_start, hour_end)
            if overlap["total_overlap_minutes"] > 0:
                overlaps.append(overlap)
        self._record_csi_overlay_profile_step(
            profiler_bucket,
            "overlap_candidate_construction_seconds",
            time.perf_counter() - overlap_started_at,
        )
        if profiler_bucket is not None:
            profiler_bucket["hours_profiled"] += 1
            profiler_bucket["candidate_overlap_count_total"] += len(overlaps)
            profiler_bucket["max_candidate_overlap_count"] = max(
                int(profiler_bucket["max_candidate_overlap_count"]),
                len(overlaps),
            )

        source_flag_started_at = time.perf_counter()
        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "has_csi_overlap": bool(overlaps),
                "multiple_csi_overlap_flag": len(overlaps) > 1,
                "csi_overlap_event_count": len(overlaps),
            },
            remove_keys=self._csi_source_flag_keys(),
        )
        self._record_csi_overlay_profile_step(
            profiler_bucket,
            "source_flag_json_seconds",
            time.perf_counter() - source_flag_started_at,
        )
        updated_row["multiple_csi_overlap_flag"] = int(len(overlaps) > 1)

        if not overlaps:
            return updated_row, 0

        if profiler_bucket is not None:
            profiler_bucket["rows_with_csi_overlap"] += 1

        dominant_selection_started_at = time.perf_counter()
        dominant = min(
            overlaps,
            key=lambda item: (
                -item["total_overlap_minutes"],
                -item["production_overlap_minutes"],
                item["source_row_hash"],
            ),
        )
        minute_contract = self._build_csi_row_minute_contract(overlaps)
        machine_state = self._resolve_machine_state_from_minutes(
            setup_minutes=minute_contract["setup_minutes"],
            production_minutes=minute_contract["production_minutes"],
            planned_stop_minutes=minute_contract["planned_stop_minutes"],
            unplanned_stop_minutes=minute_contract["unplanned_stop_minutes"],
        )
        self._record_csi_overlay_profile_step(
            profiler_bucket,
            "dominant_event_selection_seconds",
            time.perf_counter() - dominant_selection_started_at,
        )

        row_mutation_started_at = time.perf_counter()
        updated_row["order_id"] = dominant["order_id"]
        updated_row["order_suffix"] = self._normalize_order_suffix(dominant["suffix"])
        updated_row["material_code"] = dominant["material_code"]
        updated_row["task_name"] = dominant["task_name"]
        updated_row["team_leader"] = dominant["team_leader"]
        if dominant["team_size"] is not None and dominant["team_size"] > 0:
            updated_row["team_size"] = dominant["team_size"]
        updated_row["actual_speed_per_hour"] = dominant["actual_speed_per_hour"]
        updated_row["setup_minutes"] = self._none_if_zero(minute_contract["setup_minutes"])
        updated_row["production_minutes"] = self._none_if_zero(minute_contract["production_minutes"])
        updated_row["planned_stop_minutes"] = self._none_if_zero(minute_contract["planned_stop_minutes"])
        updated_row["unplanned_stop_minutes"] = self._none_if_zero(minute_contract["unplanned_stop_minutes"])
        updated_row["csi_source_row_hash"] = dominant["source_row_hash"]
        updated_row["csi_overlap_minutes"] = minute_contract["coverage_minutes"]
        updated_row["setup_inference_method"] = dominant["setup_inference_method"]
        updated_row["setup_confidence"] = dominant["setup_confidence"]
        updated_row["attribution_method"] = "energy_csi_overlay"
        updated_row["machine_state"] = machine_state
        if machine_state is not None:
            updated_row["state_confidence"] = "medium" if len(overlaps) > 1 else "high"
        self._record_csi_overlay_profile_step(
            profiler_bucket,
            "row_mutation_seconds",
            time.perf_counter() - row_mutation_started_at,
        )

        source_flag_started_at = time.perf_counter()
        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "dominant_csi_source_row_hash": dominant["source_row_hash"],
                "csi_machine_state": machine_state,
                "order_suffix_from_csi": self._normalize_order_suffix(dominant["suffix"]),
                "csi_minute_attribution_method": dominant["minute_attribution_method"],
                "csi_minute_reconciliation_warning": dominant["minute_reconciliation_warning"],
                "csi_totals_exceed_window": dominant["totals_exceed_window"],
                "csi_used_wall_clock_fallback": dominant["used_wall_clock_fallback"],
                "csi_dominant_production_minutes": dominant["production_minutes"],
                "csi_row_minute_contract": minute_contract["minute_contract"],
                "csi_row_raw_assigned_minutes": minute_contract["raw_assigned_minutes"],
                "csi_row_competing_overlap": minute_contract["competing_overlap"],
                "csi_row_minute_scale_factor": minute_contract["scale_factor"],
                "csi_all_minutes_fractional": minute_contract["all_minutes_fractional"],
                "csi_any_event_totals_exceed_window": minute_contract["any_totals_exceed_window"],
            },
        )
        self._record_csi_overlay_profile_step(
            profiler_bucket,
            "source_flag_json_seconds",
            time.perf_counter() - source_flag_started_at,
        )
        return updated_row, len(overlaps)

    def _mark_row_without_csi_overlap(self, updated_row: dict[str, object]) -> dict[str, object]:
        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "has_csi_overlap": False,
                "multiple_csi_overlap_flag": False,
                "csi_overlap_event_count": 0,
            },
            remove_keys=self._csi_source_flag_keys(),
        )
        return updated_row

    def _build_csi_overlap(
        self,
        csi_row: pd.Series,
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
    ) -> dict[str, object]:
        return self._build_csi_overlap_from_prepared_event(
            self._prepare_csi_event(csi_row),
            hour_start,
            hour_end,
        )

    def _build_csi_overlap_from_prepared_event(
        self,
        csi_event: dict[str, object],
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
    ) -> dict[str, object]:
        setup_overlap_minutes = self._overlap_minutes(
            csi_event.get("setup_start_ts"),
            csi_event.get("setup_end_ts"),
            hour_start,
            hour_end,
        )
        production_overlap_minutes = self._overlap_minutes(
            csi_event.get("production_start_ts"),
            csi_event.get("prod_end_ts"),
            hour_start,
            hour_end,
        )
        minute_reconciliation = self._reconcile_csi_minutes_values(
            actual_prod_minutes=csi_event.get("actual_prod_minutes"),
            planned_stop_minutes=csi_event.get("planned_stop_minutes"),
            unplanned_stop_minutes=csi_event.get("unplanned_stop_minutes"),
            prep_end_ts=csi_event.get("prep_end_ts"),
            prod_end_ts=csi_event.get("prod_end_ts"),
            production_start_ts=csi_event.get("production_start_ts"),
            hour_start=hour_start,
            hour_end=hour_end,
            production_overlap_minutes=production_overlap_minutes,
        )

        return {
            "source_row_hash": csi_event.get("source_row_hash") or "",
            "order_id": csi_event.get("order_id"),
            "suffix": csi_event.get("suffix"),
            "material_code": csi_event.get("material_code"),
            "task_name": csi_event.get("task_name"),
            "team_leader": csi_event.get("team_leader"),
            "team_size": csi_event.get("team_size"),
            "actual_speed_per_hour": csi_event.get("actual_speed_per_hour"),
            "setup_overlap_minutes": setup_overlap_minutes,
            "production_overlap_minutes": production_overlap_minutes,
            "total_overlap_minutes": setup_overlap_minutes + production_overlap_minutes,
            "setup_inference_method": csi_event.get("setup_inference_method"),
            "setup_confidence": csi_event.get("setup_confidence"),
            "production_minutes": minute_reconciliation["production_minutes"],
            "planned_stop_minutes": minute_reconciliation["planned_stop_minutes"],
            "unplanned_stop_minutes": minute_reconciliation["unplanned_stop_minutes"],
            "minute_attribution_method": minute_reconciliation["minute_attribution_method"],
            "minute_reconciliation_warning": minute_reconciliation["minute_reconciliation_warning"],
            "totals_exceed_window": minute_reconciliation["totals_exceed_window"],
            "used_wall_clock_fallback": minute_reconciliation["used_wall_clock_fallback"],
            "coverage_intervals": self._build_csi_coverage_intervals(
                csi_event,
                hour_start,
                hour_end,
            ),
        }

    def _build_csi_event_groups(self, csi_df: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
        if csi_df.empty:
            return {}

        prepared_csi_df = self._prepare_csi_dataframe(csi_df)
        csi_by_machine: dict[str, list[dict[str, object]]] = {}
        for csi_row in prepared_csi_df.to_dict(orient="records"):
            canonical_machine_id = self._clean_text(csi_row.get("canonical_machine_id"))
            if canonical_machine_id is None:
                continue
            csi_by_machine.setdefault(canonical_machine_id, []).append(self._prepare_csi_event(csi_row))
        return csi_by_machine

    def _prepare_csi_group(self, csi_group) -> list[dict[str, object]]:
        if isinstance(csi_group, list):
            return csi_group
        if isinstance(csi_group, pd.DataFrame):
            prepared_csi_df = self._prepare_csi_dataframe(csi_group)
            return [self._prepare_csi_event(row) for row in prepared_csi_df.to_dict(orient="records")]
        return []

    @staticmethod
    def _prepare_csi_dataframe(csi_df: pd.DataFrame) -> pd.DataFrame:
        if csi_df.empty:
            return csi_df

        prepared_df = csi_df.copy()
        for column_name in ("prep_end_ts", "prod_end_ts", "prod_start_ts"):
            if column_name not in prepared_df.columns:
                continue
            prepared_df[column_name] = pd.to_datetime(
                prepared_df[column_name],
                errors="coerce",
            )
        return prepared_df

    def _prepare_csi_event(self, csi_row: pd.Series | dict[str, object]) -> dict[str, object]:
        prep_end_ts = self._parse_timestamp(csi_row.get("prep_end_ts"))
        prod_end_ts = self._parse_timestamp(csi_row.get("prod_end_ts"))
        prod_start_ts = self._parse_timestamp(csi_row.get("prod_start_ts"))
        actual_changeover_minutes = self._float_or_none(csi_row.get("actual_changeover_minutes"))

        setup_inference_method = None
        setup_confidence = None
        setup_start_ts = None
        setup_end_ts = prep_end_ts
        if prep_end_ts is not None and actual_changeover_minutes is not None and actual_changeover_minutes >= 0:
            setup_start_ts = prep_end_ts - timedelta(minutes=actual_changeover_minutes)
            setup_inference_method = "csi_prep_end_minus_actual_changeover_minutes"
            setup_confidence = "high"

        production_start_ts = prep_end_ts or prod_start_ts
        event_window_candidates = [
            timestamp
            for timestamp in [setup_start_ts, production_start_ts]
            if timestamp is not None
        ]
        event_window_end_candidates = [
            timestamp
            for timestamp in [setup_end_ts, prod_end_ts]
            if timestamp is not None
        ]

        return {
            "source_row_hash": self._clean_text(csi_row.get("source_row_hash")),
            "order_id": self._clean_text(csi_row.get("order_id")),
            "suffix": self._clean_text(csi_row.get("suffix")),
            "material_code": self._clean_text(csi_row.get("material_code")),
            "task_name": self._clean_text(csi_row.get("task_name")),
            "team_leader": self._clean_text(csi_row.get("team_leader")),
            "team_size": self._team_size_from_csi_roster(
                csi_row.get("team_leader"),
                csi_row.get("team_members_raw"),
            ),
            "actual_speed_per_hour": self._float_or_none(csi_row.get("actual_speed_per_hour")),
            "actual_prod_minutes": self._float_or_none(csi_row.get("actual_prod_minutes")),
            "planned_stop_minutes": self._float_or_none(csi_row.get("planned_stop_minutes")),
            "unplanned_stop_minutes": self._float_or_none(csi_row.get("unplanned_stop_minutes")),
            "prep_end_ts": prep_end_ts,
            "prod_end_ts": prod_end_ts,
            "production_start_ts": production_start_ts,
            "setup_start_ts": setup_start_ts,
            "setup_end_ts": setup_end_ts,
            "setup_inference_method": setup_inference_method,
            "setup_confidence": setup_confidence,
            "event_window_start_ts": min(event_window_candidates) if event_window_candidates else None,
            "event_window_end_ts": max(event_window_end_candidates) if event_window_end_candidates else None,
        }

    @staticmethod
    def _prepared_csi_event_may_overlap(
        csi_event: dict[str, object],
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
    ) -> bool:
        event_window_start_ts = csi_event.get("event_window_start_ts")
        event_window_end_ts = csi_event.get("event_window_end_ts")
        if event_window_start_ts is None or event_window_end_ts is None:
            return False
        return event_window_start_ts < hour_end and event_window_end_ts > hour_start

    def _reconcile_csi_minutes(
        self,
        csi_row: pd.Series,
        prep_end_ts: pd.Timestamp | None,
        prod_end_ts: pd.Timestamp | None,
        production_start_ts: pd.Timestamp | None,
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
        production_overlap_minutes: float,
    ) -> dict[str, object]:
        return self._reconcile_csi_minutes_values(
            actual_prod_minutes=self._float_or_none(csi_row.get("actual_prod_minutes")),
            planned_stop_minutes=self._float_or_none(csi_row.get("planned_stop_minutes")),
            unplanned_stop_minutes=self._float_or_none(csi_row.get("unplanned_stop_minutes")),
            prep_end_ts=prep_end_ts,
            prod_end_ts=prod_end_ts,
            production_start_ts=production_start_ts,
            hour_start=hour_start,
            hour_end=hour_end,
            production_overlap_minutes=production_overlap_minutes,
        )

    @staticmethod
    def _reconcile_csi_minutes_values(
        actual_prod_minutes: float | None,
        planned_stop_minutes: float | None,
        unplanned_stop_minutes: float | None,
        prep_end_ts: pd.Timestamp | None,
        prod_end_ts: pd.Timestamp | None,
        production_start_ts: pd.Timestamp | None,
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
        production_overlap_minutes: float,
    ) -> dict[str, object]:
        del production_start_ts

        valid_post_setup_window = (
            prep_end_ts is not None
            and prod_end_ts is not None
            and prod_end_ts > prep_end_ts
        )
        if valid_post_setup_window:
            event_window_minutes = (prod_end_ts - prep_end_ts).total_seconds() / 60.0
            hour_post_setup_overlap_minutes = GoldFactBuilder._overlap_minutes(
                prep_end_ts,
                prod_end_ts,
                hour_start,
                hour_end,
            )
        else:
            event_window_minutes = None
            hour_post_setup_overlap_minutes = 0.0

        if (
            valid_post_setup_window
            and actual_prod_minutes is not None
            and planned_stop_minutes is not None
            and unplanned_stop_minutes is not None
            and event_window_minutes is not None
            and event_window_minutes > 0
        ):
            minute_total = actual_prod_minutes + planned_stop_minutes + unplanned_stop_minutes
            tolerance = max(5.0, event_window_minutes * 0.05)
            if minute_total - event_window_minutes <= tolerance:
                overlap_fraction = hour_post_setup_overlap_minutes / event_window_minutes
                return {
                    "production_minutes": actual_prod_minutes * overlap_fraction,
                    "planned_stop_minutes": planned_stop_minutes * overlap_fraction,
                    "unplanned_stop_minutes": unplanned_stop_minutes * overlap_fraction,
                    "minute_attribution_method": "csi_fractional_minute_reconciliation",
                    "minute_reconciliation_warning": None,
                    "totals_exceed_window": False,
                    "used_wall_clock_fallback": False,
                }
            return {
                "production_minutes": production_overlap_minutes,
                "planned_stop_minutes": None,
                "unplanned_stop_minutes": None,
                "minute_attribution_method": "csi_wall_clock_overlap_fallback",
                "minute_reconciliation_warning": "csi_totals_exceed_window_tolerance",
                "totals_exceed_window": True,
                "used_wall_clock_fallback": True,
            }

        if valid_post_setup_window:
            warning = "csi_minute_totals_missing_for_reconciliation"
        else:
            warning = "csi_invalid_post_setup_window"
        return {
            "production_minutes": production_overlap_minutes,
            "planned_stop_minutes": None,
            "unplanned_stop_minutes": None,
            "minute_attribution_method": "csi_wall_clock_overlap_fallback",
            "minute_reconciliation_warning": warning,
            "totals_exceed_window": False,
            "used_wall_clock_fallback": True,
        }

    def _build_csi_quantity_updates(
        self,
        updated_row: dict[str, object],
        csi_row: pd.Series | None,
        source_row_hash: str | None,
        quantity_basis_minutes: float | None,
        basis_minutes: float,
        audit_quantity_basis_minutes: float | None,
        audit_basis_minutes: float | None,
    ) -> dict[str, object]:
        source_flags = self._load_source_flags(updated_row.get("source_flags"))
        minute_method = self._clean_text(source_flags.get("csi_minute_attribution_method"))
        if minute_method == "csi_fractional_minute_reconciliation":
            allocation_confidence = "high"
        elif minute_method == "csi_wall_clock_overlap_fallback":
            allocation_confidence = "medium"
        else:
            allocation_confidence = None

        allocation_method = None
        allocation_warning = None
        good_qty = None
        scrap_qty = None

        if source_row_hash is None:
            allocation_warning = "csi_qty_missing_source_row_hash"
        elif csi_row is None:
            allocation_warning = "csi_qty_missing_event"
        elif quantity_basis_minutes is None or quantity_basis_minutes <= 0:
            allocation_warning = "csi_qty_no_positive_production_minutes"
        elif basis_minutes <= 0:
            allocation_warning = "csi_qty_non_positive_event_basis"
        else:
            event_good_qty = self._float_or_none(csi_row.get("good_qty"))
            event_scrap_qty = self._float_or_none(csi_row.get("scrap_qty"))
            if event_good_qty is None and event_scrap_qty is None:
                allocation_warning = "csi_qty_missing_all"
            else:
                ratio = quantity_basis_minutes / basis_minutes
                allocation_method = "csi_production_minutes_share_by_dominant_event"
                if event_good_qty is not None:
                    good_qty = event_good_qty * ratio
                if event_scrap_qty is not None:
                    scrap_qty = event_scrap_qty * ratio
                if event_good_qty is None:
                    allocation_warning = "csi_qty_missing_good_qty"
                elif event_scrap_qty is None:
                    allocation_warning = "csi_qty_missing_scrap_qty"

        audit_fields = self._build_csi_quantity_audit_fields(
            row=updated_row,
            source_row_hash=source_row_hash,
            quantity_basis_minutes=audit_quantity_basis_minutes,
            basis_minutes=(
                audit_basis_minutes
                if source_row_hash and audit_basis_minutes is not None and audit_basis_minutes > 0
                else None
            ),
            has_allocated_quantity=(good_qty is not None or scrap_qty is not None),
        )
        return {
            "good_qty": good_qty,
            "scrap_qty": scrap_qty,
            **audit_fields,
            "source_flags": {
                "csi_qty_allocation_method": allocation_method,
                "csi_qty_allocation_confidence": allocation_confidence if allocation_method else None,
                "csi_qty_source_row_hash": source_row_hash,
                "csi_qty_basis_minutes": basis_minutes if source_row_hash else None,
                "csi_qty_allocation_warning": allocation_warning,
            },
        }

    @classmethod
    def _csi_quantity_basis_minutes_from_row(cls, row: dict[str, object]) -> float | None:
        source_flags = cls._load_source_flags(row.get("source_flags"))
        dominant_production_minutes = cls._float_or_none(source_flags.get("csi_dominant_production_minutes"))
        if dominant_production_minutes is not None:
            return dominant_production_minutes
        return cls._float_or_none(row.get("production_minutes"))

    @classmethod
    def _reconstruct_csi_quantity_audit_basis_minutes(
        cls,
        row: dict[str, object],
    ) -> tuple[float | None, str]:
        source_row_hash = cls._clean_text(row.get("csi_source_row_hash"))
        if source_row_hash is None:
            return None, "missing_source_row_hash"

        landed_basis_minutes = cls._float_or_none(row.get("csi_qty_row_basis_minutes"))
        if landed_basis_minutes is not None and landed_basis_minutes > 0:
            return landed_basis_minutes, "preserved_existing_landed_positive_basis"

        anomaly_flag = cls._float_or_none(row.get("csi_qty_minute_budget_anomaly_flag"))
        if anomaly_flag is None:
            anomaly_flag, _ = cls._csi_quantity_minute_budget_anomaly(row, source_row_hash)
        if int(anomaly_flag or 0) == 1:
            return None, "excluded_minute_budget_anomaly"

        source_flags = cls._load_source_flags(row.get("source_flags"))
        dominant_production_minutes = cls._float_or_none(
            source_flags.get("csi_dominant_production_minutes")
        )
        multiple_overlap = int(cls._float_or_none(row.get("multiple_csi_overlap_flag")) or 0) == 1
        flagged_dominant_source_row_hash = cls._clean_text(
            source_flags.get("dominant_csi_source_row_hash")
        )
        if (
            dominant_production_minutes is not None
            and dominant_production_minutes > 0
            and flagged_dominant_source_row_hash is not None
            and flagged_dominant_source_row_hash != source_row_hash
            and multiple_overlap
        ):
            return None, "blocked_dominant_identity_conflict"
        if dominant_production_minutes is not None and dominant_production_minutes > 0:
            if flagged_dominant_source_row_hash is None:
                return (
                    dominant_production_minutes,
                    "reconstructed_from_source_flags_missing_dominant_hash_flag",
                )
            return dominant_production_minutes, "reconstructed_from_source_flags_matching_dominant_hash"

        if multiple_overlap:
            return None, "missing_positive_dominant_basis_evidence"

        production_minutes = cls._float_or_none(row.get("production_minutes"))
        if production_minutes is not None and production_minutes > 0:
            return production_minutes, "single_event_row_production_minutes"

        return None, "missing_positive_dominant_basis_evidence"

    @classmethod
    def _build_csi_quantity_audit_fields(
        cls,
        row: dict[str, object],
        source_row_hash: str | None,
        quantity_basis_minutes: float | None,
        basis_minutes: float | None,
        has_allocated_quantity: bool,
    ) -> dict[str, object]:
        if source_row_hash is None:
            return {
                column_name: None for column_name in cls._csi_quantity_audit_columns()
            }

        production_minutes = cls._float_or_none(row.get("production_minutes"))
        minutes_diff = None
        minutes_abs_diff = None
        if production_minutes is not None and quantity_basis_minutes is not None:
            minutes_diff = production_minutes - quantity_basis_minutes
            minutes_abs_diff = abs(minutes_diff)

        if quantity_basis_minutes is None or quantity_basis_minutes <= 0:
            alignment_status = "missing_positive_row_basis_minutes"
        elif production_minutes is None:
            alignment_status = "missing_row_production_minutes"
        elif not has_allocated_quantity:
            alignment_status = "no_quantity_allocated"
        elif (
            minutes_abs_diff is not None
            and minutes_abs_diff > CSI_QTY_MATERIAL_DIFF_THRESHOLD_MINUTES
        ):
            alignment_status = "material_misaligned"
        else:
            alignment_status = "aligned"

        anomaly_flag, anomaly_reason = cls._csi_quantity_minute_budget_anomaly(row, source_row_hash)
        return {
            "csi_qty_basis_method": "csi_dominant_event_production_minutes_share",
            "csi_qty_row_basis_minutes": quantity_basis_minutes,
            "csi_qty_event_basis_minutes": basis_minutes,
            "csi_qty_minutes_vs_production_diff": minutes_diff,
            "csi_qty_minutes_vs_production_abs_diff": minutes_abs_diff,
            "csi_qty_alignment_status": alignment_status,
            "csi_qty_material_misalignment_flag": int(alignment_status == "material_misaligned"),
            "csi_qty_minute_budget_anomaly_flag": anomaly_flag,
            "csi_qty_minute_budget_anomaly_reason": anomaly_reason,
        }

    @classmethod
    def _csi_quantity_minute_budget_anomaly(
        cls,
        row: dict[str, object],
        source_row_hash: str | None,
    ) -> tuple[int | None, str | None]:
        if source_row_hash is None:
            return None, None

        setup_minutes = cls._float_or_none(row.get("setup_minutes"))
        production_minutes = cls._float_or_none(row.get("production_minutes"))
        planned_stop_minutes = cls._float_or_none(row.get("planned_stop_minutes"))
        unplanned_stop_minutes = cls._float_or_none(row.get("unplanned_stop_minutes"))
        operational_minutes = [
            setup_minutes,
            production_minutes,
            planned_stop_minutes,
            unplanned_stop_minutes,
        ]

        if production_minutes is not None and production_minutes > 60.0:
            return 1, "production_minutes_gt_60"
        if any(
            value is not None and value < -CSI_MINUTE_BUDGET_TOLERANCE_MINUTES
            for value in operational_minutes
        ):
            return 1, "negative_operational_minutes"

        assigned_operational_minutes = sum(value or 0.0 for value in operational_minutes)
        if (
            any(value is not None for value in operational_minutes)
            and assigned_operational_minutes > 60.0 + CSI_MINUTE_BUDGET_TOLERANCE_MINUTES
        ):
            return 1, "operational_minutes_exceed_hour_budget"
        return 0, None

    @classmethod
    def _build_csi_row_minute_contract(cls, overlaps: list[dict[str, object]]) -> dict[str, object]:
        setup_minutes = sum(
            cls._float_or_none(overlap.get("setup_overlap_minutes")) or 0.0
            for overlap in overlaps
        )
        production_minutes = sum(
            cls._float_or_none(overlap.get("production_minutes")) or 0.0
            for overlap in overlaps
        )
        planned_stop_minutes = sum(
            cls._float_or_none(overlap.get("planned_stop_minutes")) or 0.0
            for overlap in overlaps
        )
        unplanned_stop_minutes = sum(
            cls._float_or_none(overlap.get("unplanned_stop_minutes")) or 0.0
            for overlap in overlaps
        )
        raw_assigned_minutes = (
            setup_minutes
            + production_minutes
            + planned_stop_minutes
            + unplanned_stop_minutes
        )
        coverage_minutes = cls._coverage_minutes_from_intervals(
            interval
            for overlap in overlaps
            for interval in overlap.get("coverage_intervals", [])
        )

        if raw_assigned_minutes > coverage_minutes + 1e-9 and raw_assigned_minutes > 0:
            scale_factor = coverage_minutes / raw_assigned_minutes
            minute_contract = "multi_event_sum_capped_to_coverage_budget"
            competing_overlap = True
        elif len(overlaps) > 1:
            scale_factor = 1.0
            minute_contract = "multi_event_sum_within_coverage_budget"
            competing_overlap = False
        else:
            scale_factor = 1.0
            minute_contract = "dominant_event_passthrough"
            competing_overlap = False

        return {
            "setup_minutes": setup_minutes * scale_factor,
            "production_minutes": production_minutes * scale_factor,
            "planned_stop_minutes": planned_stop_minutes * scale_factor,
            "unplanned_stop_minutes": unplanned_stop_minutes * scale_factor,
            "coverage_minutes": coverage_minutes,
            "raw_assigned_minutes": raw_assigned_minutes,
            "scale_factor": scale_factor,
            "competing_overlap": competing_overlap,
            "minute_contract": minute_contract,
            "all_minutes_fractional": all(
                overlap.get("minute_attribution_method") == "csi_fractional_minute_reconciliation"
                and not overlap.get("used_wall_clock_fallback")
                and not overlap.get("totals_exceed_window")
                for overlap in overlaps
            ),
            "any_totals_exceed_window": any(
                bool(overlap.get("totals_exceed_window"))
                for overlap in overlaps
            ),
        }

    @staticmethod
    def _build_csi_coverage_intervals(
        csi_event: dict[str, object],
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
    ) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
        intervals = []
        for start_ts, end_ts in [
            (csi_event.get("setup_start_ts"), csi_event.get("setup_end_ts")),
            (csi_event.get("production_start_ts"), csi_event.get("prod_end_ts")),
        ]:
            clipped = GoldFactBuilder._clip_interval_to_hour(start_ts, end_ts, hour_start, hour_end)
            if clipped is not None:
                intervals.append(clipped)
        return intervals

    @staticmethod
    def _clip_interval_to_hour(
        start_ts: pd.Timestamp | None,
        end_ts: pd.Timestamp | None,
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
    ) -> tuple[pd.Timestamp, pd.Timestamp] | None:
        if start_ts is None or end_ts is None:
            return None
        clipped_start = max(start_ts, hour_start)
        clipped_end = min(end_ts, hour_end)
        if clipped_end <= clipped_start:
            return None
        return clipped_start, clipped_end

    @staticmethod
    def _coverage_minutes_from_intervals(
        intervals: Iterable[tuple[pd.Timestamp, pd.Timestamp]],
    ) -> float:
        ordered_intervals = sorted(intervals, key=lambda item: (item[0], item[1]))
        if not ordered_intervals:
            return 0.0

        total_minutes = 0.0
        current_start, current_end = ordered_intervals[0]
        for start_ts, end_ts in ordered_intervals[1:]:
            if start_ts <= current_end:
                if end_ts > current_end:
                    current_end = end_ts
                continue
            total_minutes += (current_end - current_start).total_seconds() / 60.0
            current_start, current_end = start_ts, end_ts

        total_minutes += (current_end - current_start).total_seconds() / 60.0
        return min(60.0, total_minutes)

    @staticmethod
    def _resolve_machine_state_from_minutes(
        setup_minutes: float | None,
        production_minutes: float | None,
        planned_stop_minutes: float | None,
        unplanned_stop_minutes: float | None,
    ) -> str | None:
        if (setup_minutes or 0.0) > 0:
            return "setup_changeover"
        if (production_minutes or 0.0) > 0:
            return "production"
        if (planned_stop_minutes or 0.0) > 0:
            return "planned_stop"
        if (unplanned_stop_minutes or 0.0) > 0:
            return "unplanned_stop"
        return None

    def overlay_mes_on_fact_machine_hour(self) -> pd.DataFrame:
        fact_df = self._read_fact_machine_hour()
        if fact_df.empty:
            return pd.DataFrame()

        mes_df = self._read_mes_events()
        mes_by_machine = self._build_mes_event_groups(mes_df)
        csi_team_size_by_hash = self._build_csi_team_size_lookup(self._read_csi_events())

        updated_rows = []
        for _, row in fact_df.iterrows():
            mes_group = mes_by_machine.get(row["canonical_machine_id"], {"candidates_by_key": {}})
            updated_rows.append(
                self._overlay_fact_row_with_mes(
                    row,
                    mes_group,
                    csi_team_size_by_hash,
                )
            )

        self._replace_rows(updated_rows)
        return pd.DataFrame(updated_rows)

    def _overlay_fact_row_with_mes(
        self,
        fact_row: pd.Series,
        mes_group: pd.DataFrame,
        csi_team_size_by_hash: dict[str, float | None],
    ) -> dict[str, object]:
        updated_row = self._fact_row_to_dict(fact_row)
        self._reset_mes_overlay_fields(
            updated_row,
            csi_team_size=self._resolve_csi_team_size(updated_row, csi_team_size_by_hash),
        )

        hour_start = updated_row.get("_hour_ts_dt")
        if hour_start is None or pd.isna(hour_start):
            hour_start = self._parse_timestamp(updated_row.get("hour_ts"))
        mes_context = self._prepare_mes_group(mes_group)
        if hour_start is None or not mes_context["candidates_by_key"]:
            updated_row["source_flags"] = self._merge_source_flags(
                updated_row.get("source_flags"),
                {
                    "has_mes_match": False,
                    "mes_match_candidate_count": 0,
                },
                remove_keys=self._mes_source_flag_keys(),
            )
            return updated_row

        candidate_context = self._select_mes_candidate(updated_row, mes_context, hour_start)
        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "has_mes_match": candidate_context["candidate"] is not None,
                "mes_match_candidate_count": candidate_context["candidate_count"],
            },
            remove_keys=self._mes_source_flag_keys(),
        )

        candidate = candidate_context["candidate"]
        if candidate is None:
            return updated_row

        updated_row["manpower"] = candidate["manpower"]
        mes_team_size = self._team_size_from_manpower(candidate["manpower"])
        if mes_team_size is not None:
            updated_row["team_size"] = mes_team_size
        updated_row["mes_source_row_hash"] = candidate["source_row_hash"]
        updated_row["mes_report_ts"] = candidate["report_ts"]
        updated_row["mes_match_method"] = candidate_context["match_method"]
        updated_row["mes_match_confidence"] = candidate_context["match_confidence"]
        updated_row["attribution_method"] = "energy_csi_mes_overlay"
        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "mes_csi_upload_status": candidate["csi_upload_status"],
                "mes_match_used_order_suffix": bool(updated_row.get("order_suffix")),
                "mes_prep_hours_candidate": candidate["prep_hours"],
                "mes_report_type": candidate["report_type"],
                "mes_resource_id_raw": candidate["resource_id_raw"],
            },
        )
        return updated_row

    def overlay_maintenance_context_on_fact_machine_hour(self) -> pd.DataFrame:
        fact_df = self._read_fact_machine_hour()
        if fact_df.empty:
            return pd.DataFrame()

        maintenance_df = self._read_maintenance_events()
        maintenance_by_machine = self._build_maintenance_event_groups(maintenance_df)

        updated_rows = []
        for _, row in fact_df.iterrows():
            maintenance_group = maintenance_by_machine.get(
                row["canonical_machine_id"],
                {"events": [], "txn_ts_values": []},
            )
            updated_rows.append(self._overlay_fact_row_with_maintenance(row, maintenance_group))

        self._replace_rows(updated_rows)
        return pd.DataFrame(updated_rows)

    def overlay_csi_quantity_on_fact_machine_hour(self) -> pd.DataFrame:
        fact_df = self._read_fact_machine_hour()
        if fact_df.empty:
            return pd.DataFrame()

        csi_df = self._read_csi_events()
        csi_event_by_hash = {}
        for _, csi_row in csi_df.iterrows():
            source_row_hash = self._clean_text(csi_row.get("source_row_hash"))
            if source_row_hash:
                csi_event_by_hash[source_row_hash] = csi_row

        updated_rows = []
        rows_by_csi_hash: dict[str, list[dict[str, object]]] = {}
        original_rows_by_key: dict[tuple[str | None, str | None], dict[str, object]] = {}
        for _, fact_row in fact_df.iterrows():
            original_row = fact_row.to_dict()
            row_key = (
                self._clean_text(original_row.get("canonical_machine_id")),
                self._clean_text(original_row.get("hour_ts")),
            )
            original_rows_by_key[row_key] = original_row.copy()
            updated_row = original_row.copy()
            self._reset_csi_quantity_fields(updated_row)
            updated_rows.append(updated_row)

            source_row_hash = self._clean_text(updated_row.get("csi_source_row_hash"))
            if source_row_hash:
                rows_by_csi_hash.setdefault(source_row_hash, []).append(updated_row)

        basis_minutes_by_hash = {
            source_row_hash: sum(
                quantity_basis_minutes
                for quantity_basis_minutes in [
                    self._csi_quantity_basis_minutes_from_row(row) for row in rows
                ]
                if quantity_basis_minutes is not None and quantity_basis_minutes > 0
            )
            for source_row_hash, rows in rows_by_csi_hash.items()
        }
        audit_basis_minutes_by_hash = {
            source_row_hash: sum(
                audit_basis_minutes
                for audit_basis_minutes, _ in [
                    self._reconstruct_csi_quantity_audit_basis_minutes(
                        original_rows_by_key[
                            (
                                self._clean_text(row.get("canonical_machine_id")),
                                self._clean_text(row.get("hour_ts")),
                            )
                        ]
                    )
                    for row in rows
                ]
                if audit_basis_minutes is not None and audit_basis_minutes > 0
            )
            for source_row_hash, rows in rows_by_csi_hash.items()
        }

        for updated_row in updated_rows:
            source_row_hash = self._clean_text(updated_row.get("csi_source_row_hash"))
            original_row = original_rows_by_key[
                (
                    self._clean_text(updated_row.get("canonical_machine_id")),
                    self._clean_text(updated_row.get("hour_ts")),
                )
            ]
            quantity_basis_minutes = self._csi_quantity_basis_minutes_from_row(updated_row)
            audit_quantity_basis_minutes, _ = self._reconstruct_csi_quantity_audit_basis_minutes(
                original_row
            )
            csi_row = csi_event_by_hash.get(source_row_hash or "")
            basis_minutes = basis_minutes_by_hash.get(source_row_hash or "", 0.0)
            quantity_updates = self._build_csi_quantity_updates(
                updated_row=updated_row,
                csi_row=csi_row,
                source_row_hash=source_row_hash,
                quantity_basis_minutes=quantity_basis_minutes,
                basis_minutes=basis_minutes,
                audit_quantity_basis_minutes=audit_quantity_basis_minutes,
                audit_basis_minutes=audit_basis_minutes_by_hash.get(source_row_hash or "", 0.0),
            )
            updated_row["good_qty"] = quantity_updates["good_qty"]
            updated_row["scrap_qty"] = quantity_updates["scrap_qty"]
            for column_name in self._csi_quantity_audit_columns():
                updated_row[column_name] = quantity_updates[column_name]
            updated_row["source_flags"] = self._merge_source_flags(
                updated_row.get("source_flags"),
                quantity_updates["source_flags"],
                remove_keys=self._csi_quantity_source_flag_keys(),
            )

        self._replace_rows(updated_rows)
        return pd.DataFrame(updated_rows)

    def overlay_idle_on_fact_machine_hour(self) -> pd.DataFrame:
        fact_df = self._read_fact_machine_hour()
        if fact_df.empty:
            return pd.DataFrame()

        updated_rows = []
        for _, fact_row in fact_df.iterrows():
            updated_rows.append(self._overlay_fact_row_with_idle(fact_row))

        self._replace_rows(updated_rows)
        return pd.DataFrame(updated_rows)

    def overlay_maintenance_state_review_on_fact_machine_hour(self) -> pd.DataFrame:
        fact_df = self._read_fact_machine_hour()
        if fact_df.empty:
            return pd.DataFrame()

        updated_rows = []
        for _, fact_row in fact_df.iterrows():
            updated_rows.append(self._overlay_fact_row_with_maintenance_state_review(fact_row))

        self._replace_rows(updated_rows)
        return pd.DataFrame(updated_rows)

    def _overlay_fact_row_with_maintenance(
        self,
        fact_row: pd.Series,
        maintenance_group,
    ) -> dict[str, object]:
        updated_row = self._fact_row_to_dict(fact_row)
        self._reset_maintenance_overlay_fields(updated_row)

        hour_start = updated_row.get("_hour_ts_dt")
        if hour_start is None or pd.isna(hour_start):
            hour_start = self._parse_timestamp(updated_row.get("hour_ts"))
        maintenance_context = self._prepare_maintenance_group(maintenance_group)
        maintenance_events = maintenance_context["events"]
        if hour_start is None or not maintenance_events:
            updated_row["source_flags"] = self._merge_source_flags(
                updated_row.get("source_flags"),
                self._build_maintenance_flag_updates([], [], None),
                remove_keys=self._maintenance_source_flag_keys(),
            )
            return updated_row

        hour_end = hour_start + timedelta(hours=1)
        txn_ts_values = maintenance_context["txn_ts_values"]
        history_end_index = bisect_left(txn_ts_values, hour_start)
        current_hour_end_index = bisect_left(txn_ts_values, hour_end, lo=history_end_index)

        history_events = maintenance_events[:history_end_index]
        current_hour_events = maintenance_events[history_end_index:current_hour_end_index]
        last_30d_start_index = bisect_left(
            txn_ts_values,
            hour_start - timedelta(days=30),
            hi=history_end_index,
        )
        last_7d_start_index = bisect_left(
            txn_ts_values,
            hour_start - timedelta(days=7),
            hi=history_end_index,
        )
        last_30d_events = maintenance_events[last_30d_start_index:history_end_index]
        last_7d_events = maintenance_events[last_7d_start_index:history_end_index]
        operational_updates = self._build_maintenance_operational_updates(
            history_events,
            current_hour_events,
            hour_start,
            last_7d_events=last_7d_events,
            last_30d_events=last_30d_events,
        )
        updated_row.update(
            operational_updates
        )

        latest_prior = None
        if history_end_index > 0:
            latest_prior = maintenance_events[history_end_index - 1]
            updated_row["last_maintenance_txn_ts"] = latest_prior["txn_ts"].isoformat()
            updated_row["last_maintenance_source_row_hash"] = latest_prior["source_row_hash"]
            updated_row["last_maintenance_work_order_type"] = latest_prior["work_order_type"]
            hours_since = (hour_start - latest_prior["txn_ts"]).total_seconds() / 3600.0
            updated_row["hours_since_last_maintenance"] = hours_since
            updated_row["days_since_last_maintenance"] = hours_since / 24.0

        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            self._build_maintenance_flag_updates(
                history_events,
                current_hour_events,
                latest_prior,
                hour_start,
                operational_updates=operational_updates,
            ),
            remove_keys=self._maintenance_source_flag_keys(),
        )
        return updated_row

    def _overlay_fact_row_with_idle(self, fact_row: pd.Series) -> dict[str, object]:
        updated_row = self._fact_row_to_dict(fact_row)
        self._reset_idle_overlay_fields(updated_row)

        source_flags = self._load_source_flags(updated_row.get("source_flags"))
        source_row_hash = self._clean_text(updated_row.get("csi_source_row_hash"))
        maintenance_in_hour = bool(
            self._float_or_none(updated_row.get("maintenance_txn_in_hour"))
            or source_flags.get("maintenance_txn_in_hour")
        )
        all_minutes_fractional = bool(source_flags.get("csi_all_minutes_fractional"))
        csi_overlap_minutes = self._float_or_none(updated_row.get("csi_overlap_minutes"))
        full_hour_csi_coverage = (
            csi_overlap_minutes is not None and csi_overlap_minutes >= 59.5
        )

        idle_attribution_method = None
        idle_match_confidence = None
        idle_assigned_minutes_basis = None
        idle_attribution_warning = None
        idle_skipped_reason = None

        if source_row_hash is None:
            idle_skipped_reason = "idle_missing_csi_source"
        elif maintenance_in_hour:
            idle_skipped_reason = "idle_same_hour_maintenance"
        elif not all_minutes_fractional:
            idle_skipped_reason = "idle_non_fractional_csi_minutes"
        elif not full_hour_csi_coverage:
            idle_skipped_reason = "idle_partial_csi_coverage"
        else:
            setup_minutes = self._float_or_none(updated_row.get("setup_minutes")) or 0.0
            production_minutes = self._float_or_none(updated_row.get("production_minutes")) or 0.0
            planned_stop_minutes = self._float_or_none(updated_row.get("planned_stop_minutes")) or 0.0
            unplanned_stop_minutes = self._float_or_none(updated_row.get("unplanned_stop_minutes")) or 0.0
            idle_assigned_minutes_basis = (
                setup_minutes
                + production_minutes
                + planned_stop_minutes
                + unplanned_stop_minutes
            )
            idle_minutes_raw = 60.0 - idle_assigned_minutes_basis
            idle_attribution_method = "residual_minutes_after_fractional_csi_full_hour_coverage"
            idle_match_confidence = "high"

            if abs(idle_minutes_raw) < 0.5:
                updated_row["idle_minutes"] = 0.0
            elif idle_minutes_raw < 0:
                idle_attribution_warning = "idle_negative_residual"
                idle_skipped_reason = "idle_negative_residual"
            else:
                updated_row["idle_minutes"] = idle_minutes_raw
                if (
                    setup_minutes <= 0
                    and production_minutes <= 0
                    and planned_stop_minutes <= 0
                    and unplanned_stop_minutes <= 0
                ):
                    updated_row["machine_state"] = "idle"
                    updated_row["state_confidence"] = "high"

        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "idle_attribution_method": idle_attribution_method,
                "idle_match_confidence": idle_match_confidence,
                "idle_full_hour_csi_coverage": full_hour_csi_coverage,
                "idle_assigned_minutes_basis": idle_assigned_minutes_basis,
                "idle_attribution_warning": idle_attribution_warning,
                "idle_skipped_reason": idle_skipped_reason,
            },
            remove_keys=self._idle_source_flag_keys(),
        )
        return updated_row

    def _overlay_fact_row_with_maintenance_state_review(
        self,
        fact_row: pd.Series,
    ) -> dict[str, object]:
        updated_row = self._fact_row_to_dict(fact_row)
        self._reset_maintenance_state_review_fields(updated_row)

        source_flags = self._load_source_flags(updated_row.get("source_flags"))
        maintenance_in_hour = bool(
            self._float_or_none(updated_row.get("maintenance_txn_in_hour"))
            or source_flags.get("maintenance_txn_in_hour")
        )
        work_order_count = int(
            self._float_or_none(updated_row.get("maintenance_distinct_work_order_in_hour_count"))
            or source_flags.get("maintenance_distinct_work_order_in_hour_count")
            or 0
        )
        current_hour_work_order_types = source_flags.get("maintenance_current_hour_work_order_types")
        if not isinstance(current_hour_work_order_types, list):
            current_hour_work_order_types = []

        multiple_overlap = int(updated_row.get("multiple_csi_overlap_flag") or 0)
        current_state = self._clean_text(updated_row.get("machine_state"))
        csi_source_row_hash = self._clean_text(updated_row.get("csi_source_row_hash"))
        csi_overlap_minutes = self._float_or_none(updated_row.get("csi_overlap_minutes"))

        blocked_reason = None
        if not maintenance_in_hour:
            blocked_reason = "maintenance_state_no_same_hour_maintenance"
        elif work_order_count < 1:
            blocked_reason = "maintenance_state_missing_work_order_in_hour"
        elif multiple_overlap != 0:
            blocked_reason = "maintenance_state_multiple_csi_overlap"
        elif self._row_has_positive_operational_minutes(updated_row):
            blocked_reason = "maintenance_state_conflicting_operational_minutes"
        elif self._row_has_positive_quantity(updated_row):
            blocked_reason = "maintenance_state_conflicting_quantity"
        elif current_state not in {None, "idle"}:
            blocked_reason = "maintenance_state_existing_non_idle_state"
        elif csi_source_row_hash is not None and csi_overlap_minutes is not None and csi_overlap_minutes >= 1.0:
            blocked_reason = "maintenance_state_existing_csi_overlap"
        else:
            updated_row["machine_state"] = "maintenance"
            updated_row["state_confidence"] = "low"

        promotion_method = None
        promotion_confidence = None
        review_passed = False
        if blocked_reason is None:
            promotion_method = "same_hour_maintenance_txn_without_conflicting_operational_evidence"
            promotion_confidence = "low"
            review_passed = True

        updated_row["source_flags"] = self._merge_source_flags(
            updated_row.get("source_flags"),
            {
                "maintenance_state_promotion_method": promotion_method,
                "maintenance_state_confidence": promotion_confidence,
                "maintenance_state_review_passed": review_passed,
                "maintenance_state_blocked_reason": blocked_reason,
                "maintenance_state_same_hour_work_order_count": work_order_count,
                "maintenance_state_current_hour_work_order_types": current_hour_work_order_types,
            },
            remove_keys=self._maintenance_state_review_source_flag_keys(),
        )
        return updated_row

    def _select_mes_candidate(
        self,
        fact_row: dict[str, object],
        mes_group,
        hour_start: pd.Timestamp,
    ) -> dict[str, object]:
        order_id = self._clean_text(fact_row.get("order_id"))
        order_suffix = self._normalize_order_suffix(fact_row.get("order_suffix"))
        if order_id is None or order_suffix is None:
            return {
                "candidate": None,
                "candidate_count": 0,
                "match_method": None,
                "match_confidence": None,
            }

        mes_candidates_by_key = self._prepare_mes_group(mes_group)["candidates_by_key"]
        hour_end = hour_start + timedelta(hours=1)
        same_day_matches = mes_candidates_by_key.get(
            (order_id, order_suffix, hour_start.date().isoformat()),
            [],
        )

        if not same_day_matches:
            return {
                "candidate": None,
                "candidate_count": 0,
                "match_method": None,
                "match_confidence": None,
            }

        positive_manpower_matches = [
            item
            for item in same_day_matches
            if item["manpower"] is not None and item["manpower"] > 0
        ]
        candidate_pool = positive_manpower_matches or same_day_matches
        candidate = sorted(
            candidate_pool,
            key=lambda item: (
                abs((item["report_ts_dt"] - hour_end).total_seconds()),
                item["source_row_hash"],
            ),
        )[0]
        return {
            "candidate": candidate,
            "candidate_count": len(same_day_matches),
            "match_method": (
                "canonical_order_suffix_same_date_prefer_positive_manpower_then_closest_hour_end"
                if positive_manpower_matches
                else "canonical_order_suffix_same_date_closest_hour_end"
            ),
            "match_confidence": "high",
        }

    def _build_mes_event_groups(self, mes_df: pd.DataFrame) -> dict[str, dict[str, object]]:
        if mes_df.empty:
            return {}

        mes_by_machine: dict[str, list[dict[str, object]]] = {}
        for mes_row in mes_df.to_dict(orient="records"):
            canonical_machine_id = self._clean_text(mes_row.get("canonical_machine_id"))
            if canonical_machine_id is None:
                continue
            mes_by_machine.setdefault(canonical_machine_id, []).append(mes_row)
        return {
            canonical_machine_id: self._prepare_mes_group(rows)
            for canonical_machine_id, rows in mes_by_machine.items()
        }

    def _prepare_mes_group(self, mes_group) -> dict[str, object]:
        if isinstance(mes_group, dict) and "candidates_by_key" in mes_group:
            return mes_group

        if isinstance(mes_group, pd.DataFrame):
            mes_rows = mes_group.to_dict(orient="records")
        elif isinstance(mes_group, list):
            mes_rows = mes_group
        else:
            mes_rows = []

        candidates_by_key: dict[tuple[str, str, str], list[dict[str, object]]] = {}
        for mes_row in mes_rows:
            mes_event = self._prepare_mes_event(mes_row)
            if (
                mes_event["order_id"] is None
                or mes_event["suffix"] is None
                or mes_event["report_date"] is None
            ):
                continue
            key = (mes_event["order_id"], mes_event["suffix"], mes_event["report_date"])
            candidates_by_key.setdefault(key, []).append(mes_event)

        return {"candidates_by_key": candidates_by_key}

    def _build_csi_team_size_lookup(self, csi_df: pd.DataFrame) -> dict[str, float | None]:
        if csi_df.empty:
            return {}

        prepared_csi_df = self._prepare_csi_dataframe(csi_df)
        csi_team_size_by_hash: dict[str, float | None] = {}
        for csi_row in prepared_csi_df.to_dict(orient="records"):
            prepared_event = self._prepare_csi_event(csi_row)
            source_row_hash = self._clean_text(prepared_event.get("source_row_hash"))
            if source_row_hash is None:
                continue
            csi_team_size_by_hash[source_row_hash] = prepared_event.get("team_size")
        return csi_team_size_by_hash

    def _prepare_mes_event(self, mes_row: dict[str, object]) -> dict[str, object]:
        report_ts = self._parse_timestamp(mes_row.get("report_ts"))
        return {
            "source_row_hash": self._clean_text(mes_row.get("source_row_hash")) or "",
            "report_ts": report_ts.isoformat() if report_ts is not None else None,
            "report_ts_dt": report_ts,
            "report_date": report_ts.date().isoformat() if report_ts is not None else None,
            "order_id": self._clean_text(mes_row.get("order_id")),
            "suffix": self._normalize_order_suffix(mes_row.get("suffix")),
            "manpower": self._float_or_none(mes_row.get("manpower")),
            "report_type": self._clean_text(mes_row.get("report_type")),
            "csi_upload_status": self._clean_text(mes_row.get("csi_upload_status")),
            "resource_id_raw": self._clean_text(mes_row.get("resource_id_raw")),
            "prep_hours": self._float_or_none(mes_row.get("prep_hours")),
        }

    def _build_maintenance_event_groups(self, maintenance_df: pd.DataFrame) -> dict[str, dict[str, object]]:
        if maintenance_df.empty:
            return {}

        maintenance_by_machine: dict[str, list[dict[str, object]]] = {}
        for maintenance_row in maintenance_df.to_dict(orient="records"):
            canonical_machine_id = self._clean_text(maintenance_row.get("canonical_machine_id"))
            if canonical_machine_id is None:
                continue
            maintenance_by_machine.setdefault(canonical_machine_id, []).append(maintenance_row)
        return {
            canonical_machine_id: self._prepare_maintenance_group(rows)
            for canonical_machine_id, rows in maintenance_by_machine.items()
        }

    def _prepare_maintenance_group(self, maintenance_group) -> dict[str, object]:
        if isinstance(maintenance_group, dict) and "events" in maintenance_group:
            return maintenance_group

        if isinstance(maintenance_group, pd.DataFrame):
            maintenance_rows = maintenance_group.to_dict(orient="records")
        elif isinstance(maintenance_group, list):
            maintenance_rows = maintenance_group
        else:
            maintenance_rows = []

        maintenance_events = []
        for maintenance_row in maintenance_rows:
            maintenance_event = self._prepare_maintenance_event(maintenance_row)
            if maintenance_event is not None:
                maintenance_events.append(maintenance_event)

        maintenance_events.sort(
            key=lambda event: (event["txn_ts"], event["source_row_hash"]),
        )
        return {
            "events": maintenance_events,
            "txn_ts_values": [event["txn_ts"] for event in maintenance_events],
        }

    def _prepare_maintenance_event(
        self,
        maintenance_row: dict[str, object],
    ) -> dict[str, object] | None:
        txn_ts = self._parse_timestamp(maintenance_row.get("txn_ts"))
        if txn_ts is None:
            return None
        return {
            "txn_ts": txn_ts,
            "source_row_hash": self._clean_text(maintenance_row.get("source_row_hash")) or "",
            "work_order_id": self._clean_text(maintenance_row.get("work_order_id")),
            "work_order_type": self._clean_text(maintenance_row.get("work_order_type")),
            "txn_type": self._clean_text(maintenance_row.get("txn_type")),
        }

    def _read_silver_energy(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query("SELECT * FROM energy_meter_hour", conn)
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _read_fact_machine_hour(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query("SELECT * FROM fact_machine_hour", conn)
        finally:
            conn.close()

    def _read_csi_events(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query("SELECT * FROM csi_job_event", conn)
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _read_mes_events(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query("SELECT * FROM mes_report_event", conn)
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _read_maintenance_events(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql_query("SELECT * FROM maintenance_txn_event", conn)
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def _replace_rows(self, rows: Iterable[dict[str, object]]) -> None:
        rows = list(rows)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fact_machine_hour")
        if rows:
            columns = list(rows[0].keys())
            placeholders = ", ".join("?" for _ in columns)
            column_list = ", ".join(columns)
            cursor.executemany(
                f"INSERT INTO fact_machine_hour ({column_list}) VALUES ({placeholders})",
                [tuple(row[column] for column in columns) for row in rows],
            )
        conn.commit()
        conn.close()

    @staticmethod
    def _fact_row_to_dict(fact_row: pd.Series | dict[str, object]) -> dict[str, object]:
        if isinstance(fact_row, dict):
            return fact_row.copy()
        return fact_row.to_dict()

    @staticmethod
    def _sum_or_none(series: pd.Series) -> float | None:
        non_null = series.dropna()
        if non_null.empty:
            return None
        return float(non_null.sum())

    @staticmethod
    def _ensure_table_columns(cursor, table_name: str, columns: dict[str, str]) -> None:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {column[1] for column in cursor.fetchall()}
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    @staticmethod
    def _parse_timestamp(value: object) -> pd.Timestamp | None:
        if value is None:
            return None
        if isinstance(value, pd.Timestamp):
            if pd.isna(value):
                return None
            return value
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
    def _overlap_minutes(
        start_ts: pd.Timestamp | None,
        end_ts: pd.Timestamp | None,
        hour_start: pd.Timestamp,
        hour_end: pd.Timestamp,
    ) -> float:
        if start_ts is None or end_ts is None or end_ts <= start_ts:
            return 0.0
        overlap_start = max(start_ts, hour_start)
        overlap_end = min(end_ts, hour_end)
        if overlap_end <= overlap_start:
            return 0.0
        return (overlap_end - overlap_start).total_seconds() / 60.0

    @staticmethod
    def _clean_text(value: object) -> str | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        cleaned = str(value).strip()
        return cleaned or None

    @classmethod
    def _normalize_order_suffix(cls, value: object) -> str | None:
        cleaned = cls._clean_text(value)
        if cleaned is None:
            return None
        if cleaned.endswith(".0") and cleaned.replace(".", "", 1).isdigit():
            return cleaned.split(".", 1)[0]
        return cleaned

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        return float(value)

    @classmethod
    def _team_size_from_manpower(cls, manpower: object) -> float | None:
        manpower_value = cls._float_or_none(manpower)
        if manpower_value is None or manpower_value <= 0:
            return None
        return float(round(manpower_value))

    @classmethod
    def _team_size_from_csi_roster(
        cls,
        team_leader: object,
        team_members_raw: object,
    ) -> float | None:
        team_members = cls._load_team_member_list(team_members_raw)
        team_leader_present = cls._clean_text(team_leader) is not None
        team_size = (1 if team_leader_present else 0) + len(team_members)
        if team_size <= 0:
            return None
        return float(team_size)

    @classmethod
    def _load_team_member_list(cls, team_members_raw: object) -> list[str]:
        if isinstance(team_members_raw, list):
            raw_members = team_members_raw
        else:
            cleaned = cls._clean_text(team_members_raw)
            if cleaned is None:
                return []
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                return []
            raw_members = parsed if isinstance(parsed, list) else []

        members = []
        for member in raw_members:
            cleaned_member = cls._clean_text(member)
            if cleaned_member is not None:
                members.append(cleaned_member)
        return members

    @staticmethod
    def _count_distinct_work_orders(events: list[dict[str, object]]) -> int:
        work_order_ids = sorted(
            {
                work_order_id
                for work_order_id in [event.get("work_order_id") for event in events]
                if work_order_id
            }
        )
        if work_order_ids:
            return len(work_order_ids)
        return len(events)

    @classmethod
    def _build_maintenance_operational_updates(
        cls,
        history_events: list[dict[str, object]],
        current_hour_events: list[dict[str, object]],
        hour_start: pd.Timestamp | None = None,
        *,
        last_7d_events: list[dict[str, object]] | None = None,
        last_30d_events: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        if last_30d_events is None:
            last_30d_events = history_events
            if hour_start is not None:
                last_30d_events = [
                    event for event in history_events if event["txn_ts"] >= hour_start - timedelta(days=30)
                ]
        if last_7d_events is None:
            last_7d_events = history_events
            if hour_start is not None:
                last_7d_events = [
                    event for event in history_events if event["txn_ts"] >= hour_start - timedelta(days=7)
                ]

        return {
            "has_maintenance_history": int(bool(history_events)),
            "maintenance_txn_in_hour": int(bool(current_hour_events)),
            "maintenance_distinct_work_order_count_30d": cls._count_distinct_work_orders(last_30d_events),
            "maintenance_distinct_work_order_count_7d": cls._count_distinct_work_orders(last_7d_events),
            "maintenance_distinct_work_order_in_hour_count": cls._count_distinct_work_orders(current_hour_events),
            "cumulative_maintenance_count": cls._count_distinct_work_orders(history_events),
        }

    @classmethod
    def _build_maintenance_flag_updates(
        cls,
        history_events: list[dict[str, object]],
        current_hour_events: list[dict[str, object]],
        latest_prior: dict[str, object] | None,
        hour_start: pd.Timestamp | None = None,
        *,
        operational_updates: dict[str, object] | None = None,
    ) -> dict[str, object]:
        operational_updates = operational_updates or cls._build_maintenance_operational_updates(
            history_events,
            current_hour_events,
            hour_start,
        )

        return {
            "has_maintenance_history": bool(operational_updates["has_maintenance_history"]),
            "maintenance_txn_in_hour": bool(operational_updates["maintenance_txn_in_hour"]),
            "maintenance_distinct_work_order_count_30d": operational_updates[
                "maintenance_distinct_work_order_count_30d"
            ],
            "maintenance_distinct_work_order_count_7d": operational_updates[
                "maintenance_distinct_work_order_count_7d"
            ],
            "maintenance_distinct_work_order_in_hour_count": operational_updates[
                "maintenance_distinct_work_order_in_hour_count"
            ],
            "maintenance_last_work_order_type": latest_prior.get("work_order_type") if latest_prior else None,
            "maintenance_current_hour_work_order_types": sorted(
                {
                    work_order_type
                    for work_order_type in [event.get("work_order_type") for event in current_hour_events]
                    if work_order_type
                }
            ),
            "maintenance_current_hour_txn_types": sorted(
                {
                    txn_type
                    for txn_type in [event.get("txn_type") for event in current_hour_events]
                    if txn_type
                }
            ),
        }

    @classmethod
    def _reset_csi_overlay_fields(cls, row: dict[str, object]) -> None:
        row.update(
            {
                "machine_state": None,
                "state_confidence": None,
                "order_id": None,
                "order_suffix": None,
                "material_code": None,
                "task_name": None,
                "team_leader": None,
                "actual_speed_per_hour": None,
                "setup_minutes": None,
                "production_minutes": None,
                "planned_stop_minutes": None,
                "unplanned_stop_minutes": None,
                "csi_source_row_hash": None,
                "csi_overlap_minutes": None,
                "multiple_csi_overlap_flag": 0,
                "setup_inference_method": None,
                "setup_confidence": None,
                "attribution_method": "energy_only_projection",
            }
        )
        row["source_flags"] = cls._merge_source_flags(
            row.get("source_flags"),
            {},
            remove_keys=cls._csi_source_flag_keys(),
        )

    @classmethod
    def _reset_mes_overlay_fields(
        cls,
        row: dict[str, object],
        csi_team_size: float | None = None,
    ) -> None:
        row["mes_source_row_hash"] = None
        row["mes_report_ts"] = None
        row["mes_match_method"] = None
        row["mes_match_confidence"] = None
        row["team_size"] = csi_team_size
        row["manpower"] = None
        row["source_flags"] = cls._merge_source_flags(
            row.get("source_flags"),
            {},
            remove_keys=cls._mes_source_flag_keys(),
        )
        if row.get("attribution_method") == "energy_csi_mes_overlay":
            row["attribution_method"] = (
                "energy_csi_overlay"
                if cls._clean_text(row.get("csi_source_row_hash"))
                else "energy_only_projection"
            )

    @classmethod
    def _resolve_csi_team_size(
        cls,
        row: dict[str, object],
        csi_team_size_by_hash: dict[str, float | None],
    ) -> float | None:
        csi_source_row_hash = cls._clean_text(row.get("csi_source_row_hash"))
        if csi_source_row_hash is None:
            return None
        csi_team_size = cls._float_or_none(csi_team_size_by_hash.get(csi_source_row_hash))
        if csi_team_size is None or csi_team_size <= 0:
            return None
        return csi_team_size

    @classmethod
    def _reset_maintenance_overlay_fields(cls, row: dict[str, object]) -> None:
        row["last_maintenance_txn_ts"] = None
        row["last_maintenance_source_row_hash"] = None
        row["last_maintenance_work_order_type"] = None
        row["has_maintenance_history"] = 0
        row["maintenance_txn_in_hour"] = 0
        row["maintenance_distinct_work_order_count_7d"] = 0
        row["maintenance_distinct_work_order_count_30d"] = 0
        row["maintenance_distinct_work_order_in_hour_count"] = 0
        row["cumulative_maintenance_count"] = 0
        row["hours_since_last_maintenance"] = None
        row["days_since_last_maintenance"] = None
        row["source_flags"] = cls._merge_source_flags(
            row.get("source_flags"),
            {},
            remove_keys=cls._maintenance_source_flag_keys(),
        )

    @classmethod
    def _reset_csi_quantity_fields(cls, row: dict[str, object]) -> None:
        row["good_qty"] = None
        row["scrap_qty"] = None
        for column_name in cls._csi_quantity_audit_columns():
            row[column_name] = None
        row["source_flags"] = cls._merge_source_flags(
            row.get("source_flags"),
            {},
            remove_keys=cls._csi_quantity_source_flag_keys(),
        )

    @classmethod
    def _reset_idle_overlay_fields(cls, row: dict[str, object]) -> None:
        row["idle_minutes"] = None
        if cls._clean_text(row.get("machine_state")) == "idle":
            row["machine_state"] = None
            row["state_confidence"] = None
        row["source_flags"] = cls._merge_source_flags(
            row.get("source_flags"),
            {},
            remove_keys=cls._idle_source_flag_keys(),
        )

    @classmethod
    def _reset_maintenance_state_review_fields(cls, row: dict[str, object]) -> None:
        source_flags = cls._load_source_flags(row.get("source_flags"))
        if (
            cls._clean_text(row.get("machine_state")) == "maintenance"
            and cls._clean_text(source_flags.get("maintenance_state_promotion_method")) is not None
        ):
            row["machine_state"] = None
            row["state_confidence"] = None
        row["source_flags"] = cls._merge_source_flags(
            row.get("source_flags"),
            {},
            remove_keys=cls._maintenance_state_review_source_flag_keys(),
        )

    @staticmethod
    def _mes_source_flag_keys() -> list[str]:
        return [
            "has_mes_match",
            "mes_match_candidate_count",
            "mes_csi_upload_status",
            "mes_match_used_order_suffix",
            "mes_prep_hours_candidate",
            "mes_report_type",
            "mes_resource_id_raw",
        ]

    @staticmethod
    def _csi_source_flag_keys() -> list[str]:
        return [
            "has_csi_overlap",
            "multiple_csi_overlap_flag",
            "csi_overlap_event_count",
            "dominant_csi_source_row_hash",
            "csi_machine_state",
            "order_suffix_from_csi",
            "csi_minute_attribution_method",
            "csi_minute_reconciliation_warning",
            "csi_totals_exceed_window",
            "csi_used_wall_clock_fallback",
            "csi_dominant_production_minutes",
            "csi_row_minute_contract",
            "csi_row_raw_assigned_minutes",
            "csi_row_competing_overlap",
            "csi_row_minute_scale_factor",
            "csi_all_minutes_fractional",
            "csi_any_event_totals_exceed_window",
        ]

    @staticmethod
    def _maintenance_source_flag_keys() -> list[str]:
        return [
            "has_maintenance_history",
            "maintenance_txn_in_hour",
            "maintenance_distinct_work_order_count_30d",
            "maintenance_distinct_work_order_count_7d",
            "maintenance_distinct_work_order_in_hour_count",
            "maintenance_last_work_order_type",
            "maintenance_current_hour_work_order_types",
            "maintenance_current_hour_txn_types",
        ]

    @staticmethod
    def _csi_quantity_source_flag_keys() -> list[str]:
        return [
            "csi_qty_allocation_method",
            "csi_qty_allocation_confidence",
            "csi_qty_source_row_hash",
            "csi_qty_basis_minutes",
            "csi_qty_allocation_warning",
        ]

    @staticmethod
    def _csi_quantity_audit_columns() -> list[str]:
        return [
            "csi_qty_basis_method",
            "csi_qty_row_basis_minutes",
            "csi_qty_event_basis_minutes",
            "csi_qty_minutes_vs_production_diff",
            "csi_qty_minutes_vs_production_abs_diff",
            "csi_qty_alignment_status",
            "csi_qty_material_misalignment_flag",
            "csi_qty_minute_budget_anomaly_flag",
            "csi_qty_minute_budget_anomaly_reason",
        ]

    @staticmethod
    def _idle_source_flag_keys() -> list[str]:
        return [
            "idle_attribution_method",
            "idle_match_confidence",
            "idle_full_hour_csi_coverage",
            "idle_assigned_minutes_basis",
            "idle_attribution_warning",
            "idle_skipped_reason",
        ]

    @staticmethod
    def _maintenance_state_review_source_flag_keys() -> list[str]:
        return [
            "maintenance_state_promotion_method",
            "maintenance_state_confidence",
            "maintenance_state_review_passed",
            "maintenance_state_blocked_reason",
            "maintenance_state_same_hour_work_order_count",
            "maintenance_state_current_hour_work_order_types",
        ]

    @classmethod
    def _row_has_positive_operational_minutes(cls, row: dict[str, object]) -> bool:
        return any(
            (cls._float_or_none(row.get(column_name)) or 0.0) > 0
            for column_name in [
                "setup_minutes",
                "production_minutes",
                "planned_stop_minutes",
                "unplanned_stop_minutes",
            ]
        )

    @classmethod
    def _row_has_positive_quantity(cls, row: dict[str, object]) -> bool:
        return any(
            (cls._float_or_none(row.get(column_name)) or 0.0) > 0
            for column_name in [
                "good_qty",
                "scrap_qty",
            ]
        )

    @staticmethod
    def _none_if_zero(value: float | None) -> float | None:
        if value is None:
            return None
        return None if abs(value) < 1e-9 else value

    @staticmethod
    def _merge_source_flags(
        existing_json: object,
        updates: dict[str, object],
        remove_keys: Iterable[str] | None = None,
    ) -> object:
        existing = GoldFactBuilder._load_source_flags(existing_json)
        for key in remove_keys or []:
            existing.pop(key, None)
        existing.update(updates)
        if isinstance(existing_json, dict):
            return existing
        return json.dumps(existing, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _load_source_flags(existing_json: object) -> dict[str, object]:
        if isinstance(existing_json, dict):
            return existing_json.copy()
        existing = {}
        if isinstance(existing_json, str) and existing_json.strip():
            try:
                parsed = json.loads(existing_json)
                if isinstance(parsed, dict):
                    existing = parsed
            except json.JSONDecodeError:
                existing = {}
        return existing
