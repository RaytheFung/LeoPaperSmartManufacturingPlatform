"""
Machine Learning Training Pipeline
Real-time model training with actual data from unified_view
"""

import pandas as pd
import numpy as np
import sqlite3
import pickle
from datetime import datetime
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("XGBoost not installed. Using Random Forest as primary model.")


class MLDataPreparer:
    """Prepare data from unified_view for ML training"""
    
    def __init__(self, db_path='manufacturing_data.db'):
        self.db_path = db_path
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.categorical_columns = ['machine_type', 'last_maintenance_type', 'team_leader', 'material_code']
        self.min_production = 1.0  # align with unified view production floor
        self.max_kwh_per_unit = 20.0  # guard against residual outliers
        self.feature_defaults = {}

    def load_data(self):
        """Load real data from unified_view"""
        conn = sqlite3.connect(self.db_path)

        # Load data with all maintenance context
        query = """
        SELECT 
            machine_id,
            datetime,
            energy_kwh,
            production_qty,
            kwh_per_unit,
            is_near_zero_output,
            team_leader,
            team_composition,
            team_size,
            material_code,
            task_type,
            hours_since_last_maintenance,
            days_since_last_maintenance,
            maintenance_in_hour,
            last_maintenance_type,
            maintenance_intensity_30d,
            cumulative_maintenance_count
        FROM unified_view
        WHERE machine_id IN (SELECT machine_id FROM three_way_matches)
        AND is_near_zero_output = 0
        AND energy_kwh > 0
        AND kwh_per_unit > 0
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        initial_rows = len(df)

        # Apply tighter anomaly guards
        df = df[df['production_qty'] >= self.min_production]
        df = df[df['kwh_per_unit'] <= self.max_kwh_per_unit]
        df = df[df['energy_kwh'] >= 0.25]

        # Drop remaining null targets
        df = df[df['kwh_per_unit'].notna()]

        filtered_rows = len(df)
        print(f"Loaded {initial_rows:,} unified_view rows; {filtered_rows:,} remain after filtering anomalies")
        return df.reset_index(drop=True)
    
    def engineer_features(self, df):
        """Create ML features from real data"""
        
        # Time-based features
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour_of_day'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek
        df['month'] = df['datetime'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_night_shift'] = df['hour_of_day'].isin(range(20, 24)) | df['hour_of_day'].isin(range(0, 7))
        df['is_night_shift'] = df['is_night_shift'].astype(int)
        
        # Machine features
        df['machine_type'] = df['machine_id'].str.split('-').str[0]
        df['machine_number'] = df['machine_id'].str.split('-').str[1].astype(int)
        
        # Maintenance features (already available)
        df['maintenance_urgency'] = df['hours_since_last_maintenance'].fillna(0) / 720  # Normalized by month
        df['needs_maintenance'] = (df['hours_since_last_maintenance'] > 1000).astype(int)
        
        # Team features
        df['team_size_category'] = pd.cut(
            df['team_size'].fillna(1), 
            bins=[0, 1, 3, 5, 100], 
            labels=['solo', 'small', 'medium', 'large']
        )
        
        # Task type encoding - using task_type instead of task_difficulty
        # Create numeric encoding for task types
        if 'task_type' in df.columns and df['task_type'].notna().any():
            # Encode based on task complexity if patterns are available
            task_complexity_map = {
                '印色': 2,  # Medium complexity
                '印色+光油': 3,  # High complexity
                '光油': 1,  # Low complexity
            }
            df['task_complexity'] = df['task_type'].map(task_complexity_map).fillna(2)
        else:
            # Default complexity if task_type is not available
            df['task_complexity'] = 2
        
        # Production efficiency metrics
        df['production_rate'] = df['production_qty'] / df['energy_kwh'].clip(lower=0.1)
        
        # Fill missing values
        df['maintenance_intensity_30d'] = df['maintenance_intensity_30d'].fillna(0)
        df['cumulative_maintenance_count'] = df['cumulative_maintenance_count'].fillna(0)
        df['hours_since_last_maintenance'] = df['hours_since_last_maintenance'].fillna(1000)
        df['days_since_last_maintenance'] = df['days_since_last_maintenance'].fillna(30)
        df['maintenance_in_hour'] = df['maintenance_in_hour'].fillna(0)

        return df
    
    def prepare_for_training(self, df):
        """Prepare features and target for ML"""
        
        # Select features for training
        feature_columns = [
            'hour_of_day', 'day_of_week', 'month', 'is_weekend', 'is_night_shift',
            'machine_type', 'machine_number',
            'team_size', 'task_complexity',
            'hours_since_last_maintenance', 'maintenance_urgency', 'needs_maintenance',
            'maintenance_intensity_30d', 'cumulative_maintenance_count',
            'production_qty'
        ]
        
        # Encode categorical variables
        for col in self.categorical_columns:
            if col in df.columns:
                le = LabelEncoder()
                # Handle missing values
                df[col] = df[col].fillna('unknown')
                df[col + '_encoded'] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
                if col in feature_columns:
                    feature_columns[feature_columns.index(col)] = col + '_encoded'
                else:
                    feature_columns.append(col + '_encoded')
        
        # Ensure all features exist
        feature_columns = [col for col in feature_columns if col in df.columns]
        
        # Prepare X and y
        X = df[feature_columns].copy()
        self.feature_defaults = X.median().to_dict()
        y = df['kwh_per_unit'].copy()
        
        # Handle any remaining missing values
        X = X.fillna(X.median())
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        X = pd.DataFrame(X_scaled, columns=feature_columns, index=X.index)
        
        self.feature_columns = feature_columns

        print(f"Prepared {len(feature_columns)} features for training")
        print(f"Target variable (kwh_per_unit) range: {y.min():.2f} - {y.max():.2f}")

        return X, y, feature_columns

    def save_preprocessor(self, filepath='models/production_preprocessor.pkl'):
        """Persist encoders, scaler, and feature metadata for inference"""
        package = {
            'feature_columns': self.feature_columns,
            'categorical_columns': self.categorical_columns,
            'label_encoders': self.label_encoders,
            'scaler': self.scaler,
            'feature_defaults': self.feature_defaults,
            'min_production': self.min_production,
            'max_kwh_per_unit': self.max_kwh_per_unit
        }

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'wb') as f:
            pickle.dump(package, f)

        print(f"Saved preprocessing bundle to {filepath}")


class MLModelTrainer:
    """Train multiple ML models and select the best"""
    
    def __init__(self):
        self.models = {}
        self.best_model = None
        self.best_model_name = None
        self.feature_importance = {}
        self.training_history = []
        
    def train_all_models(self, X_train, X_test, y_train, y_test):
        """Train multiple models and compare performance"""
        
        results = {}
        
        # 1. Linear Regression (Baseline)
        print("\nTraining Linear Regression...")
        lr_model = LinearRegression()
        lr_model.fit(X_train, y_train)
        lr_pred = lr_model.predict(X_test)
        lr_r2 = r2_score(y_test, lr_pred)
        lr_mae = mean_absolute_error(y_test, lr_pred)
        
        self.models['linear_regression'] = lr_model
        results['linear_regression'] = {
            'r2_score': lr_r2,
            'mae': lr_mae,
            'rmse': np.sqrt(mean_squared_error(y_test, lr_pred))
        }
        print(f"  R² Score: {lr_r2:.3f}, MAE: {lr_mae:.3f}")
        
        # 2. Random Forest
        print("\nTraining Random Forest...")
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        rf_r2 = r2_score(y_test, rf_pred)
        rf_mae = mean_absolute_error(y_test, rf_pred)
        
        self.models['random_forest'] = rf_model
        results['random_forest'] = {
            'r2_score': rf_r2,
            'mae': rf_mae,
            'rmse': np.sqrt(mean_squared_error(y_test, rf_pred))
        }
        print(f"  R² Score: {rf_r2:.3f}, MAE: {rf_mae:.3f}")
        
        # Extract feature importance from Random Forest
        self.feature_importance = dict(zip(
            X_train.columns,
            rf_model.feature_importances_
        ))
        
        # 3. XGBoost (if available)
        if XGBOOST_AVAILABLE:
            print("\nTraining XGBoost...")
            xgb_model = XGBRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
            xgb_model.fit(X_train, y_train)
            xgb_pred = xgb_model.predict(X_test)
            xgb_r2 = r2_score(y_test, xgb_pred)
            xgb_mae = mean_absolute_error(y_test, xgb_pred)
            
            self.models['xgboost'] = xgb_model
            results['xgboost'] = {
                'r2_score': xgb_r2,
                'mae': xgb_mae,
                'rmse': np.sqrt(mean_squared_error(y_test, xgb_pred))
            }
            print(f"  R² Score: {xgb_r2:.3f}, MAE: {xgb_mae:.3f}")
            
            # Update feature importance if XGBoost is better
            if xgb_r2 > rf_r2:
                self.feature_importance = dict(zip(
                    X_train.columns,
                    xgb_model.feature_importances_
                ))
        
        # Select best model based on R² score
        best_model_name = max(results, key=lambda x: results[x]['r2_score'])
        self.best_model = self.models[best_model_name]
        self.best_model_name = best_model_name
        
        print(f"\n✅ Best Model: {best_model_name.upper()} with R² = {results[best_model_name]['r2_score']:.3f}")
        
        # Store training history
        self.training_history.append({
            'timestamp': datetime.now(),
            'models': results,
            'best_model': best_model_name,
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        })
        
        return results
    
    def get_feature_importance_df(self):
        """Get feature importance as a sorted DataFrame"""
        if not self.feature_importance:
            return pd.DataFrame()
        
        importance_df = pd.DataFrame(
            list(self.feature_importance.items()),
            columns=['Feature', 'Importance']
        )
        importance_df = importance_df.sort_values('Importance', ascending=False)
        importance_df['Importance'] = importance_df['Importance'] * 100  # Convert to percentage
        
        return importance_df
    
    def save_model(self, filepath='models/best_model.pkl'):
        """Save the best model to disk"""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'model': self.best_model,
            'model_name': self.best_model_name,
            'feature_importance': self.feature_importance,
            'training_history': self.training_history,
            'timestamp': datetime.now()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
        
        # Also save to database
        self._save_to_database()
    
    def _save_to_database(self):
        """Save model metadata to database"""
        conn = sqlite3.connect('manufacturing_data.db')
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT,
            model_type TEXT,
            training_date TIMESTAMP,
            r2_score REAL,
            mae REAL,
            feature_count INTEGER
        )
        """)
        
        # Insert model info
        latest_results = self.training_history[-1]
        best_scores = latest_results['models'][self.best_model_name]
        
        cursor.execute("""
        INSERT INTO ml_models (model_name, model_type, training_date, r2_score, mae, feature_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"production_efficiency_{datetime.now().strftime('%Y%m%d_%H%M')}",
            self.best_model_name,
            datetime.now(),
            best_scores['r2_score'],
            best_scores['mae'],
            len(self.feature_importance)
        ))
        
        conn.commit()
        conn.close()


def train_production_model():
    """Main function to train the production efficiency model"""
    
    print("=" * 60)
    print("TRAINING PRODUCTION EFFICIENCY MODEL")
    print("=" * 60)
    
    # 1. Prepare data
    print("\n1. Loading and preparing data...")
    preparer = MLDataPreparer()
    df = preparer.load_data()
    df = preparer.engineer_features(df)
    X, y, feature_columns = preparer.prepare_for_training(df)
    
    # 2. Split data
    print("\n2. Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"   Training samples: {len(X_train):,}")
    print(f"   Test samples: {len(X_test):,}")
    
    # 3. Train models
    print("\n3. Training models...")
    trainer = MLModelTrainer()
    results = trainer.train_all_models(X_train, X_test, y_train, y_test)
    
    # 4. Display results
    print("\n4. Model Performance Summary:")
    print("-" * 40)
    for model_name, scores in results.items():
        print(f"{model_name.upper()}")
        print(f"  R² Score: {scores['r2_score']:.3f}")
        print(f"  MAE: {scores['mae']:.3f} kWh/unit")
        print(f"  RMSE: {scores['rmse']:.3f} kWh/unit")
        print()
    
    # 5. Feature importance
    print("5. Top 10 Most Important Features:")
    print("-" * 40)
    importance_df = trainer.get_feature_importance_df()
    for idx, row in importance_df.head(10).iterrows():
        print(f"  {row['Feature']}: {row['Importance']:.1f}%")
    
    # 6. Save model
    print("\n6. Saving model...")
    trainer.save_model('models/production_efficiency_model.pkl')
    preparer.save_preprocessor('models/production_preprocessor.pkl')

    print("\n" + "=" * 60)
    print("✅ MODEL TRAINING COMPLETE!")
    print("=" * 60)

    return trainer, preparer


if __name__ == "__main__":
    trainer, preparer = train_production_model()
