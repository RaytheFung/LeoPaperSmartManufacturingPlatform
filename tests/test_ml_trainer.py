import builtins
import importlib
import inspect
import json
import pickle
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import core.ml_trainer as ml_trainer_module
from core.canonical_ml_reader import (
    CanonicalMLReader,
    MISSING_POSITIVE_GOOD_QTY_INSUFFICIENT_CONTEXT_REASON,
    MISSING_POSITIVE_GOOD_QTY_NONPRODUCTIVE_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
    MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON,
)
from core.gold_fact_builder import GoldFactBuilder
from core.ml_predictor import MLPredictor
from core.ml_trainer import (
    DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME,
    DEFAULT_RETRAINING_TASK_TAG,
    MLDataPreparer,
    TRAINING_FEATURE_COLUMNS,
    get_canonical_retraining_status,
    run_canonical_retraining,
    train_production_model,
)


class MLTrainerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "ml_trainer.db"
        self.model_path = Path(self.temp_dir.name) / "models" / "production_efficiency_model.pkl"
        self.preprocessor_path = (
            Path(self.temp_dir.name) / "models" / "production_preprocessor.pkl"
        )
        GoldFactBuilder(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_preprocessor_defaults(self, *, team_size=4.0, cumulative_maintenance_count=9.0):
        self.preprocessor_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.preprocessor_path, "wb") as file_obj:
            pickle.dump(
                {
                    "feature_defaults": {
                        "team_size": team_size,
                        "cumulative_maintenance_count": cumulative_maintenance_count,
                    }
                },
                file_obj,
            )

    def _insert_fact_rows(self, rows):
        defaults = {
            "canonical_machine_id": None,
            "hour_ts": None,
            "machine_state": None,
            "state_confidence": None,
            "energy_total_kwh": None,
            "energy_total_cost": None,
            "energy_main_kwh": None,
            "energy_uv_kwh": None,
            "energy_ir_kwh": None,
            "energy_motor_kwh": None,
            "source_flags": json.dumps({}, sort_keys=True),
            "energy_total_source_method": "aggregate_total_preferred",
            "energy_source_row_count": 1,
            "energy_source_row_hashes_json": json.dumps(["energy-hash"]),
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
            "hours_since_last_maintenance": None,
            "days_since_last_maintenance": None,
            "attribution_method": "energy_csi_overlay",
        }
        prepared_rows = []
        for row in rows:
            merged = dict(defaults)
            merged.update(row)
            prepared_rows.append(merged)

        conn = sqlite3.connect(self.db_path)
        pd.DataFrame(prepared_rows).to_sql("fact_machine_hour", conn, if_exists="append", index=False)
        conn.close()

    def _build_training_rows(self):
        rows = []
        for index in range(6):
            rows.append(
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": f"2025-06-01T0{index}:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 30.0 + index * 2.0,
                    "good_qty": 12.0 + index,
                    "team_leader": "Leader A",
                    "team_size": None if index % 2 == 0 else 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-001",
                    "task_name": "印刷" if index % 2 == 0 else "印刷+光油",
                    "hours_since_last_maintenance": 24.0 + index,
                    "days_since_last_maintenance": (24.0 + index) / 24.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_txn_in_hour": 0,
                    "maintenance_distinct_work_order_count_30d": 2,
                    "cumulative_maintenance_count": 5,
                    "source_flags": json.dumps(
                        {
                            "maintenance_distinct_work_order_count_30d": 2,
                            "maintenance_last_work_order_type": "PM",
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            )
            rows.append(
                {
                    "canonical_machine_id": "024-002",
                    "hour_ts": f"2025-06-02T0{index}:00:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 24.0 + index * 1.5,
                    "good_qty": 14.0 + index,
                    "team_leader": "Leader B",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": "MAT-002",
                    "task_name": "光油",
                    "hours_since_last_maintenance": 48.0 + index * 2.0,
                    "days_since_last_maintenance": (48.0 + index * 2.0) / 24.0,
                    "last_maintenance_work_order_type": "Corrective",
                    "maintenance_txn_in_hour": 0,
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 3,
                    "source_flags": json.dumps(
                        {
                            "maintenance_distinct_work_order_count_30d": 1,
                            "maintenance_last_work_order_type": "Corrective",
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                }
            )
        return rows

    def _build_multi_month_training_rows(self):
        rows = []
        month_starts = ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"]
        for month_offset, month_start in enumerate(month_starts):
            for hour_offset in range(3):
                rows.append(
                    {
                        "canonical_machine_id": "024-001",
                        "hour_ts": f"{month_start}T0{hour_offset}:00:00",
                        "machine_state": "production",
                        "energy_total_kwh": 18.0 + month_offset * 2.0 + hour_offset,
                        "good_qty": 9.0 + month_offset + hour_offset,
                        "team_leader": "Leader A",
                        "team_size": 3.0,
                        "manpower": 3.0,
                        "material_code": "MAT-001",
                        "task_name": "印刷",
                        "hours_since_last_maintenance": 24.0 + month_offset * 10.0 + hour_offset,
                        "days_since_last_maintenance": (24.0 + month_offset * 10.0 + hour_offset) / 24.0,
                        "last_maintenance_work_order_type": "PM",
                        "maintenance_txn_in_hour": 0,
                        "maintenance_distinct_work_order_count_30d": 1 + month_offset,
                        "cumulative_maintenance_count": 2 + month_offset,
                    }
                )
                rows.append(
                    {
                        "canonical_machine_id": "024-002",
                        "hour_ts": f"{month_start}T1{hour_offset}:00:00",
                        "machine_state": "setup_changeover",
                        "energy_total_kwh": 16.0 + month_offset * 1.5 + hour_offset,
                        "good_qty": 8.0 + month_offset + hour_offset,
                        "team_leader": "Leader B",
                        "team_size": 2.0,
                        "manpower": 2.0,
                        "material_code": "MAT-002",
                        "task_name": "光油",
                        "hours_since_last_maintenance": 48.0 + month_offset * 8.0 + hour_offset,
                        "days_since_last_maintenance": (48.0 + month_offset * 8.0 + hour_offset) / 24.0,
                        "last_maintenance_work_order_type": "Corrective",
                        "maintenance_txn_in_hour": 0,
                        "maintenance_distinct_work_order_count_30d": 2 + month_offset,
                        "cumulative_maintenance_count": 3 + month_offset,
                    }
                )
        return rows

    def test_load_data_uses_fact_machine_hour_and_applies_adapter_rules(self):
        self._write_preprocessor_defaults(team_size=4.0, cumulative_maintenance_count=9.0)
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-010",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 25.0,
                    "good_qty": 10.0,
                    "team_leader": None,
                    "team_size": None,
                    "manpower": None,
                    "material_code": None,
                    "task_name": "光油",
                    "hours_since_last_maintenance": 36.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_txn_in_hour": 1,
                    "maintenance_distinct_work_order_count_30d": 2,
                    "cumulative_maintenance_count": 9,
                    "source_flags": json.dumps(
                        {
                            "maintenance_distinct_work_order_count_30d": 99,
                            "maintenance_last_work_order_type": "Corrective",
                            "maintenance_txn_in_hour": False,
                        },
                        sort_keys=True,
                    ),
                },
                {
                    "canonical_machine_id": "024-011",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 20.0,
                    "good_qty": 0.0,
                    "hours_since_last_maintenance": 10.0,
                },
                {
                    "canonical_machine_id": "024-013",
                    "hour_ts": "2025-06-01T10:30:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 14.0,
                    "good_qty": 0.0,
                    "hours_since_last_maintenance": 11.0,
                },
                {
                    "canonical_machine_id": "024-012",
                    "hour_ts": "2025-06-01T11:00:00",
                    "energy_total_kwh": None,
                    "good_qty": 8.0,
                    "hours_since_last_maintenance": 12.0,
                },
            ]
        )

        preparer = MLDataPreparer(
            db_path=self.db_path,
            preprocessor_path=self.preprocessor_path,
            min_training_rows=1,
            min_machine_count=1,
        )
        training_df = preparer.load_data()

        self.assertEqual(len(training_df), 1)
        row = training_df.iloc[0]
        self.assertEqual(row["machine_id"], "024-010")
        self.assertEqual(row["task_difficulty"], "Easy")
        self.assertEqual(row["team_size"], 4.0)
        self.assertEqual(row["last_maintenance_type"], "PM")
        self.assertEqual(row["maintenance_intensity_30d"], 2.0)
        self.assertEqual(row["cumulative_maintenance_count"], 9.0)
        self.assertEqual(row["maintenance_in_hour"], 1)
        self.assertEqual(row["team_leader"], "unknown")
        self.assertEqual(row["material_code"], "unknown")
        self.assertAlmostEqual(row["kwh_per_unit"], 2.5)
        self.assertIn(
            "missing_positive_good_qty_production_state",
            preparer.last_blocked_df["blocked_reason"].tolist(),
        )
        self.assertIn(
            "missing_positive_good_qty_nonproductive_state",
            preparer.last_blocked_df["blocked_reason"].tolist(),
        )
        self.assertIn(
            "missing_positive_energy_total_kwh",
            preparer.last_blocked_df["blocked_reason"].tolist(),
        )
        self.assertEqual(
            preparer.last_team_size_fallback_summary["rows_using_team_size_from_preprocessor_default"],
            1,
        )
        self.assertEqual(
            preparer.last_team_size_fallback_summary[
                "distinct_machines_using_team_size_from_preprocessor_default"
            ],
            1,
        )
        self.assertEqual(
            preparer.last_team_size_fallback_summary[
                "monthly_rows_using_team_size_from_preprocessor_default"
            ],
            {"2025-06": 1},
        )
        self.assertEqual(
            preparer.last_team_size_fallback_summary["rows_using_team_size_from_manpower"],
            0,
        )

    def test_missing_positive_good_qty_taxonomy_stays_mirrored_between_reader_and_trainer(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-100",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 18.0,
                    "good_qty": 0.0,
                    "team_leader": "Leader A",
                    "team_size": 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-001",
                    "task_name": "印刷",
                    "order_id": "JOB-100",
                    "production_minutes": 0.5,
                    "planned_stop_minutes": 59.5,
                    "hours_since_last_maintenance": 24.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 2,
                },
                {
                    "canonical_machine_id": "024-101",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "setup_changeover",
                    "energy_total_kwh": 16.0,
                    "good_qty": 0.0,
                    "team_leader": "Leader B",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": "MAT-002",
                    "task_name": "光油",
                    "order_id": "JOB-101",
                    "hours_since_last_maintenance": 36.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 3,
                },
                {
                    "canonical_machine_id": "024-102",
                    "hour_ts": "2025-06-01T11:00:00",
                    "machine_state": None,
                    "energy_total_kwh": 14.0,
                    "good_qty": None,
                    "team_leader": "Leader C",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": None,
                    "task_name": None,
                    "hours_since_last_maintenance": 48.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 4,
                },
                {
                    "canonical_machine_id": "024-103",
                    "hour_ts": "2025-06-01T12:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 20.0,
                    "good_qty": 0.0,
                    "team_leader": "Leader D",
                    "team_size": 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-003",
                    "task_name": "印刷",
                    "order_id": "JOB-103",
                    "production_minutes": 60.0,
                    "hours_since_last_maintenance": 12.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 5,
                },
                {
                    "canonical_machine_id": "024-104",
                    "hour_ts": "2025-06-01T13:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 19.0,
                    "good_qty": 0.0,
                    "team_leader": "Leader E",
                    "team_size": 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-004",
                    "task_name": "印刷",
                    "order_id": "JOB-104",
                    "production_minutes": 40.0,
                    "planned_stop_minutes": 20.0,
                    "unplanned_stop_minutes": 5.0,
                    "csi_qty_alignment_status": "material_misaligned",
                    "csi_qty_material_misalignment_flag": 1,
                    "hours_since_last_maintenance": 18.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 5,
                },
                {
                    "canonical_machine_id": "024-105",
                    "hour_ts": "2025-06-01T14:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 17.0,
                    "good_qty": 0.0,
                    "team_leader": "Leader F",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": "MAT-005",
                    "task_name": "印刷",
                    "order_id": "JOB-105",
                    "production_minutes": 8.0,
                    "planned_stop_minutes": 12.0,
                    "csi_qty_alignment_status": "missing_positive_row_basis_minutes",
                    "csi_qty_minute_budget_anomaly_flag": 1,
                    "source_flags": json.dumps(
                        {"csi_qty_allocation_warning": "csi_qty_no_positive_production_minutes"},
                        sort_keys=True,
                    ),
                    "hours_since_last_maintenance": 22.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 5,
                },
                {
                    "canonical_machine_id": "024-106",
                    "hour_ts": "2025-06-01T15:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 15.0,
                    "good_qty": 0.0,
                    "team_leader": "Leader G",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": None,
                    "task_name": "印刷",
                    "order_id": None,
                    "production_minutes": None,
                    "hours_since_last_maintenance": 30.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 5,
                },
                {
                    "canonical_machine_id": "024-107",
                    "hour_ts": "2025-06-01T16:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 22.0,
                    "good_qty": 11.0,
                    "team_leader": "Leader H",
                    "team_size": 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-006",
                    "task_name": "印刷",
                    "order_id": "JOB-107",
                    "hours_since_last_maintenance": 12.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 5,
                },
            ]
        )

        reader = CanonicalMLReader(db_path=self.db_path)
        input_df = reader.build_month_input_dataframe("June 2025")
        blocked_input_reasons = set(
            input_df.loc[input_df["eligible_for_inference"] == 0, "blocked_reason"].dropna().tolist()
        )
        self.assertEqual(int((input_df["eligible_for_inference"] == 1).sum()), 1)

        preparer = MLDataPreparer(
            db_path=self.db_path,
            preprocessor_path=self.preprocessor_path,
            min_training_rows=1,
            min_machine_count=1,
        )
        training_df = preparer.load_data()
        blocked_training_reasons = set(preparer.last_blocked_df["blocked_reason"].dropna().tolist())
        self.assertEqual(len(training_df), 1)

        expected_reasons = {
            MISSING_POSITIVE_GOOD_QTY_NONPRODUCTIVE_REASON,
            MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_LABEL_CONTRADICTION_REASON,
            MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_QUANTITY_OVERLAY_GAP_REASON,
            MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_ORDER_OR_MATERIAL_CONTEXT_CONFLICT_REASON,
            MISSING_POSITIVE_GOOD_QTY_PRODUCTION_STATE_SOURCE_QUALITY_OR_ANOMALY_REASON,
            MISSING_POSITIVE_GOOD_QTY_PRODUCTION_REASON,
            MISSING_POSITIVE_GOOD_QTY_INSUFFICIENT_CONTEXT_REASON,
        }
        self.assertTrue(expected_reasons.issubset(blocked_input_reasons))
        self.assertTrue(expected_reasons.issubset(blocked_training_reasons))

    def test_prepare_for_training_preserves_feature_contract(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(self._build_training_rows())

        preparer = MLDataPreparer(
            db_path=self.db_path,
            preprocessor_path=self.preprocessor_path,
            min_training_rows=4,
            min_machine_count=2,
        )
        training_df = preparer.load_data()
        engineered_df = preparer.engineer_features(training_df)
        X, y, feature_columns = preparer.prepare_for_training(engineered_df)

        self.assertEqual(feature_columns, TRAINING_FEATURE_COLUMNS)
        self.assertEqual(list(X.columns), TRAINING_FEATURE_COLUMNS)
        self.assertEqual(len(X), len(y))
        self.assertEqual(preparer.feature_columns, TRAINING_FEATURE_COLUMNS)
        self.assertIn("machine_type", preparer.label_encoders)
        self.assertIn("last_maintenance_type", preparer.label_encoders)
        self.assertIn("team_leader", preparer.label_encoders)
        self.assertIn("material_code", preparer.label_encoders)
        self.assertEqual(preparer.last_month_coverage, ["June 2025"])
        self.assertEqual(
            preparer.last_team_size_fallback_summary["rows_using_team_size_from_manpower"],
            3,
        )
        self.assertEqual(
            preparer.last_team_size_fallback_summary[
                "distinct_machines_using_team_size_from_manpower"
            ],
            1,
        )

    def test_load_data_blocks_unmapped_task_name_instead_of_defaulting_medium(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-020",
                    "hour_ts": "2025-06-01T09:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 18.0,
                    "good_qty": 9.0,
                    "team_leader": "Leader A",
                    "team_size": 3.0,
                    "manpower": 3.0,
                    "material_code": "MAT-001",
                    "task_name": "UV(染)",
                    "hours_since_last_maintenance": 24.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 2,
                },
                {
                    "canonical_machine_id": "024-021",
                    "hour_ts": "2025-06-01T10:00:00",
                    "machine_state": "production",
                    "energy_total_kwh": 20.0,
                    "good_qty": 10.0,
                    "team_leader": "Leader B",
                    "team_size": 2.0,
                    "manpower": 2.0,
                    "material_code": "MAT-002",
                    "task_name": "未知工序",
                    "hours_since_last_maintenance": 36.0,
                    "last_maintenance_work_order_type": "PM",
                    "maintenance_distinct_work_order_count_30d": 1,
                    "cumulative_maintenance_count": 3,
                },
            ]
        )

        preparer = MLDataPreparer(
            db_path=self.db_path,
            preprocessor_path=self.preprocessor_path,
            min_training_rows=1,
            min_machine_count=1,
        )
        training_df = preparer.load_data()

        self.assertEqual(len(training_df), 1)
        self.assertEqual(training_df.iloc[0]["task_difficulty"], "Easy")
        self.assertIn("unmapped_task_name", preparer.last_blocked_df["blocked_reason"].tolist())
        self.assertIn(
            "task_difficulty_unmapped",
            preparer.last_blocked_df["adapter_notes"].fillna("").tolist()[0],
        )

    def test_load_data_fails_honestly_when_too_few_rows_remain(self):
        self._insert_fact_rows(
            [
                {
                    "canonical_machine_id": "024-001",
                    "hour_ts": "2025-06-01T00:00:00",
                    "energy_total_kwh": 12.0,
                    "good_qty": 6.0,
                    "task_name": "光油",
                    "hours_since_last_maintenance": 10.0,
                },
                {
                    "canonical_machine_id": "024-002",
                    "hour_ts": "2025-06-01T01:00:00",
                    "energy_total_kwh": 11.0,
                    "good_qty": 5.0,
                    "task_name": "光油",
                    "hours_since_last_maintenance": 12.0,
                },
            ]
        )

        preparer = MLDataPreparer(db_path=self.db_path)
        with self.assertRaisesRegex(ValueError, "too few eligible rows remain after filtering"):
            preparer.load_data()

    def test_train_production_model_writes_artifacts_and_predictor_loads_them(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(self._build_training_rows())

        trainer, preparer = train_production_model(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
            test_size=0.25,
            random_state=42,
        )

        self.assertTrue(self.model_path.exists())
        self.assertTrue(self.preprocessor_path.exists())
        self.assertIsNotNone(trainer.best_model_name)
        self.assertEqual(preparer.feature_columns, TRAINING_FEATURE_COLUMNS)

        conn = sqlite3.connect(self.db_path)
        metadata_count = conn.execute("SELECT COUNT(*) FROM ml_models").fetchone()[0]
        conn.close()
        self.assertEqual(metadata_count, 1)

        predictor = MLPredictor(
            model_path=str(self.model_path),
            preprocessor_path=str(self.preprocessor_path),
        )
        prediction = predictor.predict_efficiency(
            machine_id="024-001",
            team_leader="Leader A",
            material_code="MAT-001",
            hours_since_maintenance=30.0,
            task_difficulty="Medium",
            production_qty=12.0,
            team_size=3.0,
            hour_of_day=9,
            is_weekend=False,
            month=6,
            last_maintenance_type="PM",
            maintenance_intensity_30d=2.0,
            cumulative_maintenance_count=9.0,
        )

        self.assertTrue(predictor.loaded_model)
        self.assertTrue(predictor.loaded_preprocessor)
        self.assertEqual(prediction["source"], "model")

    def test_retraining_status_reports_legacy_artifacts_without_provenance_as_absent(self):
        self._write_preprocessor_defaults()
        status = get_canonical_retraining_status(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
        )

        self.assertTrue(status["artifact_status"]["preprocessor_exists"])
        self.assertFalse(status["artifact_status"]["model_exists"])
        self.assertEqual(status["artifact_status"]["preprocessor_provenance_state"], "absent")

    def test_run_canonical_retraining_promotes_candidate_and_writes_manifests(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(self._build_multi_month_training_rows())
        with open(self.model_path, "wb") as file_obj:
            pickle.dump(
                {
                    "model": "legacy-placeholder",
                    "model_name": "legacy",
                    "feature_importance": {},
                    "training_history": [],
                    "timestamp": "legacy",
                },
                file_obj,
            )

        result = run_canonical_retraining(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
            test_size=0.25,
            random_state=42,
        )

        self.assertTrue(result["promotion_success"])
        self.assertTrue(result["promotion_gate"]["passed"])
        self.assertTrue(result["predictor_smoke"]["passed"])
        self.assertEqual(result["predictor_smoke"]["prediction_source"], "model")
        self.assertEqual(result["feature_contract_version"], "canonical_fact_machine_hour_ml_v1")
        self.assertEqual(
            result["month_coverage"],
            ["January 2025", "February 2025", "March 2025", "April 2025"],
        )
        self.assertEqual(result["evaluation_strategy"], "time_aware_multi_month_holdout")
        self.assertEqual(result["train_months"], ["January 2025", "February 2025"])
        self.assertEqual(result["eval_months"], ["March 2025", "April 2025"])
        self.assertTrue(self.model_path.exists())
        self.assertTrue(self.preprocessor_path.exists())
        self.assertTrue(Path(result["candidate_paths"]["model_path"]).exists())
        self.assertTrue(Path(result["candidate_paths"]["preprocessor_path"]).exists())
        self.assertTrue(Path(result["candidate_paths"]["model_manifest_path"]).exists())
        self.assertTrue(Path(result["candidate_paths"]["preprocessor_manifest_path"]).exists())
        self.assertIsNotNone(result["backup_paths"]["model_path"])
        self.assertIsNotNone(result["backup_paths"]["preprocessor_path"])
        self.assertTrue(Path(result["backup_paths"]["model_path"]).exists())
        self.assertTrue(Path(result["backup_paths"]["preprocessor_path"]).exists())

        model_manifest = json.loads(self.model_path.with_suffix(".provenance.json").read_text())
        preprocessor_manifest = json.loads(
            self.preprocessor_path.with_suffix(".provenance.json").read_text()
        )
        self.assertEqual(model_manifest["artifact_role"], "model")
        self.assertEqual(preprocessor_manifest["artifact_role"], "preprocessor")
        self.assertEqual(model_manifest["task_tag"], DEFAULT_RETRAINING_TASK_TAG)
        self.assertEqual(model_manifest["evaluation_strategy"], "time_aware_multi_month_holdout")
        self.assertEqual(preprocessor_manifest["feature_columns"], TRAINING_FEATURE_COLUMNS)
        self.assertTrue(model_manifest["promotion_success"])
        self.assertTrue(preprocessor_manifest["promotion_success"])
        self.assertEqual(model_manifest["predictor_smoke"]["prediction_source"], "model")
        self.assertTrue(model_manifest["predictor_smoke"]["passed"])
        self.assertIn(DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME, result["candidate_paths"]["model_path"])
        self.assertIn(
            DEFAULT_RETRAINING_ARTIFACT_ARCHIVE_DIRNAME,
            result["candidate_paths"]["preprocessor_path"],
        )

        status = get_canonical_retraining_status(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
        )
        self.assertTrue(status["artifact_status"]["model_loadable"])
        self.assertTrue(status["artifact_status"]["preprocessor_loadable"])
        self.assertEqual(status["artifact_status"]["model_provenance_state"], "present")
        self.assertEqual(status["artifact_status"]["preprocessor_provenance_state"], "present")

    def test_run_canonical_retraining_blocks_promotion_when_predictor_smoke_fails(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(self._build_multi_month_training_rows())

        with patch.object(
            ml_trainer_module,
            "_run_candidate_predictor_smoke",
            return_value={
                "passed": False,
                "failure_reason": "candidate_predictor_returned_non_model_source",
                "prediction_source": "fallback",
            },
        ):
            result = run_canonical_retraining(
                db_path=self.db_path,
                model_path=self.model_path,
                preprocessor_path=self.preprocessor_path,
                test_size=0.25,
                random_state=42,
            )
        self.assertFalse(result["promotion_success"])
        self.assertEqual(result["artifact_decision"], "retained_prior_active")
        self.assertIn("promotion_gate_failed", result["artifact_decision_reason"])

    def test_run_canonical_retraining_supports_task_tag_and_archive_override(self):
        self._write_preprocessor_defaults()
        self._insert_fact_rows(self._build_multi_month_training_rows())

        result = run_canonical_retraining(
            db_path=self.db_path,
            model_path=self.model_path,
            preprocessor_path=self.preprocessor_path,
            task_tag="Task 4N",
            artifact_archive_dirname="task4n_artifacts",
        )

        self.assertEqual(result["training_provenance"]["task_tag"], "Task 4N")
        self.assertIn("task4n_artifacts", result["candidate_paths"]["model_path"])
        self.assertIn("task4n_artifacts", result["candidate_paths"]["preprocessor_path"])
        candidate_model_manifest = json.loads(
            Path(result["candidate_paths"]["model_manifest_path"]).read_text()
        )
        self.assertEqual(candidate_model_manifest["task_tag"], "Task 4N")

    def test_trainer_source_contains_no_legacy_unified_view_or_three_way_matches(self):
        source = inspect.getsource(ml_trainer_module)
        self.assertNotIn("unified_view", source)
        self.assertNotIn("three_way_matches", source)

    def test_xgboost_native_load_failures_are_treated_as_optional(self):
        original_import = builtins.__import__

        def _import_with_xgboost_failure(name, *args, **kwargs):
            if name == "xgboost":
                raise RuntimeError("libomp missing for xgboost")
            return original_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=_import_with_xgboost_failure):
                reloaded_module = importlib.reload(ml_trainer_module)
            self.assertFalse(reloaded_module.XGBOOST_AVAILABLE)
            self.assertEqual(
                reloaded_module.XGBOOST_IMPORT_FAILURE_REASON,
                "libomp missing for xgboost",
            )
        finally:
            importlib.reload(ml_trainer_module)


if __name__ == "__main__":
    unittest.main()
