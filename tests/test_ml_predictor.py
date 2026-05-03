import pickle
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from sklearn.preprocessing import LabelEncoder

from core.ml_predictor import MLPredictor
from core.ml_trainer import TRAINING_FEATURE_COLUMNS
from core.runtime_paths import get_database_path


class ConstantModel:
    def __init__(self, value):
        self.value = float(value)

    def predict(self, features):
        return np.array([self.value] * len(features))


class IdentityScaler:
    def transform(self, features):
        return features


def _encoder(*values):
    encoder = LabelEncoder()
    encoder.fit(list(values))
    return encoder


class MLPredictorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.model_path = Path(self.temp_dir.name) / "model.pkl"
        self.preprocessor_path = Path(self.temp_dir.name) / "preprocessor.pkl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_artifacts(self, prediction_value):
        with open(self.model_path, "wb") as file_obj:
            pickle.dump(
                {
                    "model": ConstantModel(prediction_value),
                    "model_name": "constant_model",
                    "feature_importance": {},
                },
                file_obj,
            )

        with open(self.preprocessor_path, "wb") as file_obj:
            pickle.dump(
                {
                    "feature_columns": list(TRAINING_FEATURE_COLUMNS),
                    "categorical_columns": [
                        "machine_type",
                        "last_maintenance_type",
                        "team_leader",
                        "material_code",
                    ],
                    "label_encoders": {
                        "machine_type": _encoder("024", "unknown"),
                        "last_maintenance_type": _encoder("PM", "unknown"),
                        "team_leader": _encoder("Leader A", "unknown"),
                        "material_code": _encoder("MAT-001", "unknown"),
                    },
                    "scaler": IdentityScaler(),
                    "feature_defaults": {
                        "team_size": 3.0,
                        "production_qty": 100.0,
                        "maintenance_intensity_30d": 1.0,
                        "cumulative_maintenance_count": 5.0,
                        "hours_since_last_maintenance": 12.0,
                        "machine_number": 7.0,
                        "task_complexity": 1.5,
                    },
                    "min_production": 1.0,
                    "max_kwh_per_unit": 20.0,
                },
                file_obj,
            )

    def test_predict_efficiency_accepts_low_positive_model_output(self):
        self._write_artifacts(0.05)
        predictor = MLPredictor(
            model_path=str(self.model_path),
            preprocessor_path=str(self.preprocessor_path),
        )

        prediction = predictor.predict_efficiency(
            machine_id="024-001",
            team_leader="Leader A",
            material_code="MAT-001",
            hours_since_maintenance=24.0,
            task_difficulty="Medium",
            production_qty=120.0,
            team_size=3.0,
            hour_of_day=9,
            is_weekend=False,
            month=6,
            last_maintenance_type="PM",
            maintenance_intensity_30d=1.0,
            cumulative_maintenance_count=5.0,
        )

        self.assertEqual(prediction["source"], "model")
        self.assertAlmostEqual(prediction["efficiency"], 0.05, places=6)

    def test_prepare_features_uses_unknown_categories_and_learned_defaults(self):
        self._write_artifacts(0.05)
        predictor = MLPredictor(
            model_path=str(self.model_path),
            preprocessor_path=str(self.preprocessor_path),
        )

        features = predictor._prepare_features(
            machine_id="",
            team_leader="",
            material_code="",
            hours_since_maintenance=12.0,
            task_difficulty=None,
            production_qty=100.0,
            team_size=3.0,
            hour_of_day=9,
            day_of_week=0,
            month=6,
            is_weekend=0,
            last_maintenance_type="",
            maintenance_intensity_30d=1.0,
            cumulative_maintenance_count=5.0,
        )

        self.assertEqual(features.loc[0, "machine_type_encoded"], 1)
        self.assertEqual(features.loc[0, "team_leader_encoded"], 1)
        self.assertEqual(features.loc[0, "material_code_encoded"], 1)
        self.assertEqual(features.loc[0, "last_maintenance_type_encoded"], 1)
        self.assertEqual(features.loc[0, "machine_number"], 7)
        self.assertEqual(features.loc[0, "task_complexity"], 1.5)

    def test_legacy_lookup_db_path_resolves_repo_local_database(self):
        self._write_artifacts(0.05)
        predictor = MLPredictor(
            model_path=str(self.model_path),
            preprocessor_path=str(self.preprocessor_path),
        )

        self.assertEqual(predictor._legacy_lookup_db_path(), get_database_path())

    def test_get_machine_list_uses_repo_local_runtime_path_for_legacy_lookup(self):
        self._write_artifacts(0.05)
        predictor = MLPredictor(
            model_path=str(self.model_path),
            preprocessor_path=str(self.preprocessor_path),
        )

        with patch("core.ml_predictor.sqlite3.connect", side_effect=sqlite3.OperationalError("blocked")) as connect:
            machines = predictor.get_machine_list()

        self.assertEqual(connect.call_args.args[0], str(get_database_path()))
        self.assertEqual(machines, ["024-060", "024-073", "024-091"])


if __name__ == "__main__":
    unittest.main()
