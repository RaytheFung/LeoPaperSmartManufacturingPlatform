"""
Maintenance Data Integration Module
Extends your existing ETL pipeline with predictive maintenance capabilities
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Tuple

from core.bronze_raw_store import BronzeRawStore
from core.machine_alias_registry import build_machine_resolution_metadata, load_machine_alias_registry
from core.runtime_paths import get_database_path

class MaintenanceDataIntegration:
    """
    Integrates maintenance records with existing three-way matched machines
    Enables predictive maintenance ML models
    """
    
    def __init__(self, db_path=None):
        self.db_path = str(db_path or get_database_path())
        self._machine_alias_registry = load_machine_alias_registry()
        self._bronze_store = BronzeRawStore(self.db_path)
        self.init_maintenance_tables()

    @staticmethod
    def _ensure_table_columns(cursor, table_name: str, columns: Dict[str, str]) -> None:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {column[1] for column in cursor.fetchall()}
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        
    def init_maintenance_tables(self):
        """Create maintenance-specific tables in your existing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main maintenance records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order TEXT,
                work_order_desc TEXT,
                work_order_type TEXT,  -- PM, AM, CM, EM
                transaction_date TIMESTAMP,
                transaction_type TEXT,  -- 發出/退回
                
                -- Machine identification (dual format!)
                asset_id TEXT,          -- MES format: 1024-00094
                asset_old_id TEXT,      -- Energy format: 024-094
                asset_desc TEXT,
                asset_type TEXT,
                
                -- Parts and materials
                material_code TEXT,
                material_desc TEXT,
                quantity REAL,
                unit TEXT,
                
                -- Organizational data
                cost_center TEXT,
                maintenance_team TEXT,
                maintenance_dept TEXT,
                approver TEXT,
                
                -- Linking to your existing system
                machine_id TEXT,        -- Your normalized format
                is_three_way_match INTEGER,
                canonical_machine_id TEXT,
                matched_on TEXT,
                matched_value TEXT,
                exception_applied INTEGER,
                source_system TEXT,
                scope_status TEXT,
                join_status TEXT,
                
                FOREIGN KEY (machine_id) REFERENCES three_way_matches(machine_id)
            )
        ''')
        self._ensure_table_columns(cursor, 'maintenance_records', {
            'canonical_machine_id': 'TEXT',
            'matched_on': 'TEXT',
            'matched_value': 'TEXT',
            'exception_applied': 'INTEGER',
            'source_system': 'TEXT',
            'scope_status': 'TEXT',
            'join_status': 'TEXT',
        })
        
        # Maintenance summary by machine
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_summary (
                machine_id TEXT PRIMARY KEY,
                total_maintenance_events INTEGER,
                preventive_count INTEGER,
                corrective_count INTEGER,
                emergency_count INTEGER,
                
                last_maintenance_date TIMESTAMP,
                next_scheduled_pm TIMESTAMP,
                
                mtbf_hours REAL,  -- Mean Time Between Failures
                mttr_hours REAL,  -- Mean Time To Repair
                availability_percent REAL,
                
                spare_parts_cost_total REAL,
                high_frequency_parts TEXT,  -- JSON list
                
                FOREIGN KEY (machine_id) REFERENCES three_way_matches(machine_id)
            )
        ''')
        
        # Predictive maintenance features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_ml_features (
                machine_id TEXT,
                date TIMESTAMP,
                
                -- Historical features
                days_since_last_maintenance INTEGER,
                maintenance_count_30d INTEGER,
                maintenance_count_90d INTEGER,
                
                -- Production intensity (from your unified view)
                production_hours_since_maintenance REAL,
                units_produced_since_maintenance REAL,
                energy_consumed_since_maintenance REAL,
                
                -- Failure patterns
                failure_risk_score REAL,  -- ML predicted
                recommended_action TEXT,
                
                PRIMARY KEY (machine_id, date)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_maintenance_data(self, maintenance_file: str, month_year: str):
        """Load and process maintenance Excel file"""
        print(f"\n=== LOADING MAINTENANCE DATA FOR {month_year} ===")
        
        # Read Excel with proper handling
        df = pd.read_excel(maintenance_file, skiprows=2)  # Skip filter rows
        
        # Standardize column names
        df.columns = [col.strip() for col in df.columns]
        
        print(f"Loaded {len(df)} maintenance records")
        
        # Filter for valid records
        df = df[df['工單'].notna()].copy()
        
        # Parse dates
        df['交易日期'] = pd.to_datetime(df['交易日期'], errors='coerce')
        df['source_file'] = str(maintenance_file)
        
        # Extract and normalize machine IDs
        df['normalized_id'] = df.apply(self._normalize_maintenance_id, axis=1)
        resolution_rows = [
            self._resolve_maintenance_machine(row)
            for _, row in df.iterrows()
        ]
        resolution_df = pd.DataFrame(resolution_rows, index=df.index)
        df = pd.concat([df, resolution_df], axis=1)
        self._bronze_store.write_maintenance_rows(df)
        
        return df

    def _resolve_maintenance_machine(self, row) -> Dict[str, object]:
        candidate_values = [
            row.get('資產', ''),
            row.get('資產老編號', ''),
            row.get('normalized_id', ''),
        ]
        for candidate in candidate_values:
            metadata = build_machine_resolution_metadata(
                candidate,
                'maintenance',
                registry=self._machine_alias_registry,
            )
            if metadata.get('canonical_machine_id'):
                return metadata
        return build_machine_resolution_metadata(
            '',
            'maintenance',
            registry=self._machine_alias_registry,
        )
    
    def _normalize_maintenance_id(self, row) -> str:
        """
        Convert maintenance IDs to your ETL format
        Handles both 資產 (1024-00094) and 資產老編號 (024-094)
        """
        # Try asset ID first (MES format)
        asset_id = row.get('資產', '')
        if asset_id and isinstance(asset_id, str):
            # Extract pattern: 1024-00094 → 024-094
            if asset_id.startswith('1') and len(asset_id.split('-')[0]) == 4:
                prefix = asset_id[1:4]  # Remove leading '1'
                suffix = asset_id.split('-')[1]
                if suffix.startswith('00'):
                    suffix = suffix[2:]  # Remove leading '00'
                return f"{prefix}-{suffix}"
        
        # Fallback to old asset ID (already in Energy format)
        old_id = row.get('資產老編號', '')
        if old_id and isinstance(old_id, str):
            return old_id
            
        return None
    
    def integrate_with_etl(self, maintenance_df: pd.DataFrame):
        """
        Link maintenance records with your three-way matched machines
        """
        conn = sqlite3.connect(self.db_path)
        
        # Get your three-way matches
        three_way = pd.read_sql_query("""
            SELECT machine_id, energy_pattern, csi_id, mes_id
            FROM three_way_matches
        """, conn)
        
        print(f"\nLinking with {len(three_way)} three-way matched machines...")
        
        # Create mapping dictionary
        machine_mapping = {
            row['machine_id']: row 
            for _, row in three_way.iterrows()
        }
        
        # Also map from MES format
        mes_mapping = {
            row['mes_id']: row['machine_id'] 
            for _, row in three_way.iterrows()
        }
        
        # Match maintenance records
        matches = 0
        unmatched = []
        
        for idx, maint_row in maintenance_df.iterrows():
            normalized = maint_row['normalized_id']
            asset_id = maint_row.get('資產', '')
            canonical_id = maint_row.get('canonical_machine_id')
            
            # Try canonical registry mapping first
            if canonical_id and canonical_id in machine_mapping:
                matches += 1
                maintenance_df.loc[idx, 'machine_id'] = canonical_id
                maintenance_df.loc[idx, 'is_three_way_match'] = 1
            # Fallback to legacy normalized ID
            elif normalized in machine_mapping:
                matches += 1
                maintenance_df.loc[idx, 'machine_id'] = normalized
                maintenance_df.loc[idx, 'is_three_way_match'] = 1
            # Try MES format
            elif asset_id in mes_mapping:
                matches += 1
                maintenance_df.loc[idx, 'machine_id'] = mes_mapping[asset_id]
                maintenance_df.loc[idx, 'is_three_way_match'] = 1
            else:
                maintenance_df.loc[idx, 'machine_id'] = canonical_id or normalized
                maintenance_df.loc[idx, 'is_three_way_match'] = 0
                unmatched.append(canonical_id or normalized)
        
        print(f"✅ Matched {matches}/{len(maintenance_df)} records to three-way machines")
        print(f"   Match rate: {matches/len(maintenance_df)*100:.1f}%")
        
        # Rename Chinese columns to English for database compatibility
        column_mapping = {
            '工單': 'work_order',
            '工單說明': 'work_order_desc',
            '工單描述': 'work_order_desc',  # Alternative column name
            '工單類型': 'work_order_type',
            '交易日期': 'transaction_date',
            '交易類型': 'transaction_type',
            '資產': 'asset_id',
            '資產老編號': 'asset_old_id',
            '資產說明': 'asset_desc',
            '資產類型': 'asset_type',
            '物料編碼': 'material_code',
            '物料說明': 'material_desc',
            '數量': 'quantity',
            '單位': 'unit',
            '成本中心': 'cost_center',
            '維護人員': 'maintenance_team',
            '維護部門': 'maintenance_dept',
            '核准者': 'approver',
        }
        
        # Rename columns that exist
        maintenance_df = maintenance_df.rename(columns=column_mapping)
        
        # These are the EXACT columns in the database table (from PRAGMA table_info)
        db_columns = [
            'work_order', 'work_order_desc', 'work_order_type',
            'transaction_date', 'transaction_type',
            'asset_id', 'asset_old_id', 'asset_desc', 'asset_type',
            'material_code', 'material_desc', 'quantity', 'unit',
            'cost_center', 'maintenance_team', 'maintenance_dept', 'approver',
            'machine_id', 'is_three_way_match',
            'canonical_machine_id', 'matched_on', 'matched_value',
            'exception_applied', 'source_system', 'scope_status', 'join_status',
        ]
        
        # Keep only columns that exist in both dataframe and database schema
        existing_cols = [col for col in db_columns if col in maintenance_df.columns]
        maintenance_df = maintenance_df[existing_cols]
        
        # Ensure required columns have default values if missing
        if 'machine_id' not in maintenance_df.columns:
            maintenance_df['machine_id'] = None
        if 'is_three_way_match' not in maintenance_df.columns:
            maintenance_df['is_three_way_match'] = 0
        if 'exception_applied' in maintenance_df.columns:
            maintenance_df['exception_applied'] = maintenance_df['exception_applied'].fillna(False).astype(int)
        
        conn.close()
        return maintenance_df
    
    def calculate_maintenance_metrics(self, maintenance_df: pd.DataFrame):
        """
        Calculate MTBF, MTTR, and other reliability metrics
        """
        metrics = {}
        
        # Group by machine
        group_col = 'machine_id' if 'machine_id' in maintenance_df.columns else 'normalized_id'
        
        for machine_id, group in maintenance_df.groupby(group_col):
            if not machine_id:
                continue
                
            # Sort by date
            group = group.sort_values('transaction_date')
            
            # Calculate metrics
            work_orders = group['work_order_type'].value_counts()
            
            # Failure events (CM + EM)
            failures = group[group['work_order_type'].isin(['CM', 'EM'])]
            
            # Calculate MTBF (Mean Time Between Failures)
            if len(failures) > 1:
                failure_dates = pd.to_datetime(failures['transaction_date'])
                time_between_failures = failure_dates.diff().dropna()
                mtbf_days = time_between_failures.dt.days.mean()
            else:
                mtbf_days = None
            
            # Calculate MTTR (simplified - time to return parts)
            returns = group[group['transaction_type'] == '退回']
            issues = group[group['transaction_type'] == '發出']
            
            metrics[machine_id] = {
                'total_events': len(group),
                'preventive': work_orders.get('PM', 0),
                'corrective': work_orders.get('CM', 0),
                'emergency': work_orders.get('EM', 0),
                'mtbf_days': mtbf_days,
                'last_maintenance': group['transaction_date'].max(),
                'unique_parts': group['material_code'].nunique()
            }
        
        # Convert to DataFrame and add machine_id column
        metrics_df = pd.DataFrame.from_dict(metrics, orient='index')
        metrics_df['machine_id'] = metrics_df.index
        
        # Convert MTBF from days to hours
        if 'mtbf_days' in metrics_df.columns:
            metrics_df['mtbf_hours'] = metrics_df['mtbf_days'] * 24
        
        return metrics_df
    
    def create_ml_features(self, maintenance_df: pd.DataFrame, unified_view_df: pd.DataFrame):
        """
        Create features for predictive maintenance ML models
        Combines maintenance history with production intensity
        """
        features = []
        
        # Get unique machines from unified view
        machines = unified_view_df['machine_id'].unique()
        
        for machine_id in machines:
            # Get maintenance history
            maint_history = maintenance_df[
                maintenance_df['machine_id'] == machine_id
            ].sort_values('transaction_date')
            
            # Get production data
            production = unified_view_df[
                unified_view_df['machine_id'] == machine_id
            ].sort_values('datetime')
            
            if len(maint_history) == 0:
                # No maintenance history - high risk!
                last_maintenance = pd.Timestamp('2025-01-01')
            else:
                last_maintenance = maint_history['transaction_date'].max()
            
            # Calculate cumulative production since last maintenance
            production_after = production[production['datetime'] > last_maintenance]
            
            features.append({
                'machine_id': machine_id,
                'days_since_last_maintenance': (datetime.now() - last_maintenance).days,
                'units_produced_since_maintenance': production_after['production_qty'].sum() if len(production_after) > 0 else 0,
                'energy_consumed_since_maintenance': production_after['energy_kwh'].sum() if len(production_after) > 0 else 0,
                'maintenance_count_total': len(maint_history),
                'failure_count': len(maint_history[maint_history['work_order_type'].isin(['CM', 'EM'])]) if len(maint_history) > 0 else 0,
                'preventive_count': len(maint_history[maint_history['work_order_type'] == 'PM']) if len(maint_history) > 0 else 0
            })
        
        return pd.DataFrame(features)
    
    def predict_maintenance_needs(self, ml_features: pd.DataFrame):
        """
        Simple rule-based prediction (to be replaced with ML model)
        """
        predictions = []
        
        for _, row in ml_features.iterrows():
            risk_score = 0
            recommendations = []
            
            # Rule 1: Days since maintenance
            days_since = row.get('days_since_last_maintenance', 0)
            if days_since > 90:
                risk_score += 40
                recommendations.append("Schedule preventive maintenance (>90 days)")
            elif days_since > 60:
                risk_score += 20
                
            # Rule 2: Production intensity
            energy_since = row.get('energy_consumed_since_maintenance', 0)
            if energy_since > 50000:  # High energy consumption
                risk_score += 30
                recommendations.append("High usage - inspect wear parts")
                
            # Rule 3: Failure history
            failure_count = row.get('failure_count', 0)
            preventive_count = row.get('preventive_count', 0)
            if failure_count > preventive_count:
                risk_score += 30
                recommendations.append("Increase PM frequency (reactive > preventive)")
            
            predictions.append({
                'machine_id': row['machine_id'],
                'date': datetime.now(),
                'failure_risk_score': min(risk_score, 100),
                'risk_level': 'HIGH' if risk_score > 60 else 'MEDIUM' if risk_score > 30 else 'LOW',
                'recommended_action': ' | '.join(recommendations) if recommendations else 'Continue normal operation',
                'days_since_last_maintenance': days_since,
                'units_produced_since_maintenance': row.get('units_produced_since_maintenance', 0),
                'energy_consumed_since_maintenance': energy_since
            })
        
        return pd.DataFrame(predictions)


# Integration function to add to your existing ETL pipeline
def integrate_maintenance_with_etl(
    maintenance_file: str,
    month_year: str,
    db_path: str | None = None,
):
    """
    Main integration function - call this after your ETL process
    """
    # Initialize maintenance module
    maint = MaintenanceDataIntegration(db_path=db_path)
    
    # Load maintenance data
    maint_df = maint.load_maintenance_data(maintenance_file, month_year)
    
    # Link with ETL three-way matches
    linked_df = maint.integrate_with_etl(maint_df)
    
    # Add month_year based on actual transaction dates
    linked_df['month_year'] = pd.to_datetime(linked_df['transaction_date']).dt.strftime('%B %Y')
    
    # Calculate reliability metrics
    metrics = maint.calculate_maintenance_metrics(linked_df)
    
    print("\n=== TOP 5 MACHINES BY MAINTENANCE FREQUENCY ===")
    top_machines = metrics.nlargest(5, 'total_events')
    for machine_id, row in top_machines.iterrows():
        print(f"{machine_id}: {row['total_events']} events (PM:{row['preventive']}, CM:{row['corrective']})")
    
    # Load unified view for ML features
    conn = sqlite3.connect(maint.db_path)
    unified_view = pd.read_sql_query("""
        SELECT * FROM unified_view 
        WHERE month_year = ?
    """, conn, params=(month_year,))
    conn.close()
    
    if not unified_view.empty:
        # Create ML features
        ml_features = maint.create_ml_features(linked_df, unified_view)
        
        # Generate predictions
        predictions = maint.predict_maintenance_needs(ml_features)
        
        print("\n=== MAINTENANCE RISK ASSESSMENT ===")
        high_risk = predictions[predictions['risk_level'] == 'HIGH']
        if not high_risk.empty:
            print(f"⚠️ {len(high_risk)} machines need immediate attention:")
            for _, machine in high_risk.iterrows():
                print(f"  {machine['machine_id']}: {machine['recommendations']}")
    
    return {
        'maintenance_records': linked_df,
        'metrics': metrics,
        'predictions': predictions if 'predictions' in locals() else None
    }


# Example usage
if __name__ == "__main__":
    # After your normal ETL process:
    result = integrate_maintenance_with_etl(
        'Maintenance RecordJan to Jul.xlsx',
        'June 2025'
    )
    
    print("\n✅ Maintenance integration complete!")
    print(f"   Processed {len(result['maintenance_records'])} maintenance records")
    print(f"   Generated predictions for {len(result['predictions'])} machines")
