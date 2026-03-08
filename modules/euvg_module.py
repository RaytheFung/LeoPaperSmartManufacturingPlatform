#!/usr/bin/env python3
"""
Enhanced Unified View Generator (EUVG)
Transforms three-way matched data into ML-ready hourly dataset
Incorporates all discovered features from CSI, MES, and Energy systems
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

MIN_PRODUCTION_THRESHOLD = 0.5  # Minimum units required to treat output as real production


class EnhancedUnifiedViewGenerator:
    def __init__(self, etl_pipeline=None, production_floor: float = MIN_PRODUCTION_THRESHOLD):
        """
        Initialize EUVG with existing ETL pipeline
        
        Args:
            etl_pipeline: Instance of EnhancedSmartManufacturingETL with loaded data
        """
        self.etl_pipeline = etl_pipeline
        self.unified_view = None
        self.feature_stats = {}
        self.energy_attribution = {}
        self.baseline_engine = DynamicBaselineEngine()
        self.team_analyzer = TeamSynergyAnalyzer()
        self.scheduler = IntelligentScheduler()
        self.production_floor = production_floor
        
    def load_from_files(self, energy_files: List[str], csi_file: str, mes_file: str, 
                       mappings_file: str = None):
        """
        Load data directly if ETL pipeline not provided
        """
        if not self.etl_pipeline:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from core.enhanced_etl_solution_CURRENT import EnhancedSmartManufacturingETL
            self.etl_pipeline = EnhancedSmartManufacturingETL()
            
        # Extract and create mappings
        self.etl_pipeline.extract_all_sources(energy_files, csi_file, mes_file)
        
        if mappings_file:
            # Load pre-computed mappings
            with open(mappings_file, 'r', encoding='utf-8') as f:
                mappings_data = json.load(f)
                self.three_way_matches = mappings_data['three_way_matches']
        else:
            # Create new mappings
            self.etl_pipeline.create_comprehensive_mapping()
            self.three_way_matches = self.etl_pipeline.machine_mapping['three_way_matches']
    
    def parse_csi_datetime(self, date_str) -> Optional[pd.Timestamp]:
        """Parse CSI datetime handling various formats"""
        if pd.isna(date_str):
            return None
            
        try:
            # Try pandas first
            return pd.to_datetime(date_str)
        except:
            # Try manual parsing for problematic formats
            try:
                if isinstance(date_str, str):
                    # Handle formats like "2025/6/1 7:00:00"
                    return pd.to_datetime(date_str, format='%Y/%m/%d %H:%M:%S')
            except:
                return None
    
    def allocate_production_hourly(self, row: pd.Series) -> List[Dict]:
        """
        Allocate production data to hourly buckets
        Handles multi-hour production spans
        """
        allocations = []
        
        # Parse start and end times (handle legacy and new column names)
        start_raw = row.get('開始時間')
        end_raw = row.get('結束時間')

        if start_raw is None or pd.isna(start_raw):
            start_raw = row.get('工程開始時間')
        if end_raw is None or pd.isna(end_raw):
            end_raw = row.get('工程結束時間')

        start_time = self.parse_csi_datetime(start_raw)
        end_time = self.parse_csi_datetime(end_raw)
        
        if not start_time or not end_time or end_time <= start_time:
            return allocations
        
        # Get production quantity
        total_qty = row.get('正品數量', 0) or 0
        if total_qty <= 0:
            return allocations
        
        # Generate hourly buckets
        current_hour = start_time.replace(minute=0, second=0, microsecond=0)
        
        while current_hour < end_time:
            next_hour = current_hour + timedelta(hours=1)
            
            # Calculate overlap for this hour
            hour_start = max(current_hour, start_time)
            hour_end = min(next_hour, end_time)
            
            if hour_end > hour_start:
                # Calculate proportion of production in this hour
                hour_duration = (hour_end - hour_start).total_seconds()
                total_duration = (end_time - start_time).total_seconds()
                
                proportion = hour_duration / total_duration if total_duration > 0 else 0
                hourly_qty = total_qty * proportion

                # Ignore numerical noise that creates tiny positive quantities
                if hourly_qty < self.production_floor:
                    hourly_qty = 0
                    proportion = 0

                allocations.append({
                    'hour': current_hour,
                    'production_qty': hourly_qty,
                    'proportion': proportion,
                    'duration_minutes': hour_duration / 60
                })
            
            current_hour = next_hour
        
        return allocations
    
    def extract_enhanced_features(self, csi_row: pd.Series, mes_row: pd.Series) -> Dict:
        """
        Extract all discovered features from CSI and MES data
        """
        features = {}
        
        # Material tracking
        features['material_code'] = csi_row.get('物料') or mes_row.get('物料', 'UNKNOWN')
        features['material_desc'] = csi_row.get('物料说明') or mes_row.get('物料說明', '')
        
        # Task type from MES
        features['task_type'] = mes_row.get('任務', 'UNKNOWN')
        
        # Setup time detection
        setup_start = self.parse_csi_datetime(csi_row.get('準備開始時間'))
        setup_end = self.parse_csi_datetime(csi_row.get('準備結束時間'))
        features['is_setup_time'] = 0
        features['setup_minutes'] = 0
        
        if setup_start and setup_end and setup_end > setup_start:
            features['setup_minutes'] = (setup_end - setup_start).total_seconds() / 60
            # Will be marked during allocation if hour overlaps with setup
        
        # Performance metrics from CSI
        features['efficiency_percent'] = csi_row.get('效率', np.nan)
        features['actual_speed'] = csi_row.get('實際速度_本_時', np.nan)
        
        # Production status
        features['production_status'] = csi_row.get('工程狀態', 'UNKNOWN')
        features['mes_status'] = mes_row.get('狀態', 'UNKNOWN')
        
        # Order information
        features['order_id'] = csi_row.get('作业') or mes_row.get('作業', 'UNKNOWN')
        features['planned_qty'] = mes_row.get('要求生產數量', 0)
        features['cumulative_qty'] = mes_row.get('累計生產數量', 0)
        
        # Machine utilization
        if pd.notna(csi_row.get('實際生產時間')):
            features['production_time_hours'] = csi_row.get('實際生產時間', 0) / 60
        else:
            features['production_time_hours'] = 0
        
        # Quality metrics (even though 廢品數量 is unreliable, track if available)
        features['reported_defects'] = csi_row.get('廢品數量', 0)
        
        return features
    
    def create_unified_hourly_view(self) -> pd.DataFrame:
        """
        Main method to create the enhanced unified view
        Integrates energy, CSI, and MES data at hourly granularity
        """
        print("\n=== CREATING ENHANCED UNIFIED VIEW ===")
        
        # Initialize components
        energy_attributor = EnergyAttributionSystem()
        
        unified_records = []
        
        # Process each three-way matched machine
        for i, match in enumerate(self.three_way_matches):
            machine_id = match['machine_id']
            csi_id = match['csi']
            mes_id = match['mes']
            
            print(f"\nProcessing machine {i+1}/{len(self.three_way_matches)}: {machine_id}")
            
            # Get energy data for this machine
            energy_data = self.etl_pipeline.energy_data[
                self.etl_pipeline.energy_data['pattern'] == machine_id
            ].copy()
            energy_data['datetime'] = pd.to_datetime(energy_data['datetime'])
            energy_data = energy_data.set_index('datetime').sort_index()
            
            # Get CSI data
            csi_data = self.etl_pipeline.csi_data[
                self.etl_pipeline.csi_data['機台編號'] == csi_id
            ].copy()
            
            # Get MES data
            mes_data = self.etl_pipeline.mes_data[
                self.etl_pipeline.mes_data['資源'] == mes_id
            ].copy()
            
            # Process each CSI production record
            for _, csi_row in csi_data.iterrows():
                # Find matching MES record
                order_id = csi_row.get('作业')
                mes_matches = mes_data[mes_data['作業'] == order_id]
                
                if mes_matches.empty:
                    mes_row = pd.Series()  # Empty series for missing MES data
                else:
                    mes_row = mes_matches.iloc[0]  # Take first match
                
                # Extract enhanced features
                features = self.extract_enhanced_features(csi_row, mes_row)
                
                # Extract team information
                team_info = self.team_analyzer.extract_team_info(csi_row)
                
                # Allocate production to hourly buckets
                hourly_allocations = self.allocate_production_hourly(csi_row)
                
                # Create records for each hour
                for allocation in hourly_allocations:
                    hour = allocation['hour']
                    
                    # Get energy data for this hour
                    energy_mask = (energy_data.index.floor('H') == hour)
                    hour_energy = energy_data[energy_mask]['electricity_kwh'].sum()
                    
                    # Attribute energy to categories
                    energy_attribution = energy_attributor.attribute_energy_for_period(
                        machine_id, energy_data, csi_data, hour
                    )
                    
                    # Create context for baseline calculation
                    context = {
                        'task_type': features['task_type'],
                        'material_code': features['material_code'],
                        'hour_of_day': hour.hour,
                        'team_size': team_info['size']
                    }
                    
                    # Calculate dynamic baseline
                    expected_efficiency = self.baseline_engine.calculate_baseline(context)
                    
                    # Create unified record
                    record = {
                        'datetime': hour,
                        'machine_id': machine_id,
                        'energy_id': machine_id,
                        'csi_id': csi_id,
                        'mes_id': mes_id,
                        
                        # Energy metrics
                        'energy_kwh': hour_energy,
                        
                        # Energy attribution
                        'setup_energy': energy_attribution['setup_energy'],
                        'production_energy': energy_attribution['production_energy'],
                        'idle_energy': energy_attribution['idle_energy'],
                        'transition_energy': energy_attribution['transition_energy'],
                        'maintenance_energy': energy_attribution['maintenance_energy'],
                        
                        # Production metrics
                        'production_qty': allocation['production_qty'],
                        'production_minutes': allocation['duration_minutes'],
                        
                        # Team information
                        'team_leader': team_info['leader'],
                        'team_members': ', '.join(team_info['members']),
                        'team_composition': team_info['composition'],
                        'team_size': team_info['size'],
                        
                        # Enhanced features
                        **features,
                        
                        # Dynamic baseline
                        'expected_kwh_per_unit': expected_efficiency,
                        
                        # Hourly specific
                        'hour_of_day': hour.hour,
                        'day_of_week': hour.dayofweek,
                        'is_weekend': hour.dayofweek >= 5,
                    }
                    
                    # Treat tiny positive quantities as zero-output hours
                    if record['production_qty'] < self.production_floor:
                        record['production_qty'] = 0
                        record['is_near_zero_output'] = 1
                    else:
                        record['is_near_zero_output'] = 0

                    # Calculate energy efficiency
                    if record['production_qty'] >= self.production_floor and hour_energy > 0:
                        record['kwh_per_unit'] = hour_energy / record['production_qty']
                        record['efficiency_vs_baseline'] = record['kwh_per_unit'] / expected_efficiency
                    else:
                        record['kwh_per_unit'] = np.nan
                        record['efficiency_vs_baseline'] = np.nan
                    
                    # Mark setup hours
                    setup_start = self.parse_csi_datetime(csi_row.get('準備開始時間'))
                    setup_end = self.parse_csi_datetime(csi_row.get('準備結束時間'))
                    if setup_start and setup_end:
                        if setup_start <= hour < setup_end:
                            record['is_setup_time'] = 1
                    
                    # Check for material transitions
                    if i > 0 and 'material_code' in unified_records[-1]:
                        if unified_records[-1]['material_code'] != record['material_code']:
                            record['material_transition'] = 1
                        else:
                            record['material_transition'] = 0
                    else:
                        record['material_transition'] = 0
                    
                    unified_records.append(record)
        
        # Create DataFrame
        self.unified_view = pd.DataFrame(unified_records)
        
        # Sort by datetime and machine
        self.unified_view = self.unified_view.sort_values(['datetime', 'machine_id'])
        
        # Calculate feature statistics
        self._calculate_feature_stats()
        
        # Fit baseline engine on historical data
        self.baseline_engine.fit_on_historical_data(self.unified_view)
        
        # Analyze team performance
        self.team_performance_analysis = self.team_analyzer.analyze_team_performance(self.unified_view)
        
        print(f"\n✅ Created unified view with {len(self.unified_view)} hourly records")
        print(f"   Date range: {self.unified_view['datetime'].min()} to {self.unified_view['datetime'].max()}")
        print(f"   Unique machines: {self.unified_view['machine_id'].nunique()}")
        print(f"   Unique teams: {self.unified_view['team_composition'].nunique()}")
        
        return self.unified_view
    
    def _calculate_feature_stats(self):
        """Calculate statistics for all features"""
        if self.unified_view is None or len(self.unified_view) == 0:
            return
        
        # Numeric features
        numeric_cols = self.unified_view.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            non_null = self.unified_view[col].dropna()
            if len(non_null) > 0:
                self.feature_stats[col] = {
                    'mean': non_null.mean(),
                    'std': non_null.std(),
                    'min': non_null.min(),
                    'max': non_null.max(),
                    'null_rate': self.unified_view[col].isnull().mean()
                }
        
        # Categorical features
        categorical_cols = ['material_code', 'task_type', 'team_composition', 
                           'production_status', 'mes_status', 'team_leader']
        
        for col in categorical_cols:
            if col in self.unified_view.columns:
                value_counts = self.unified_view[col].value_counts()
                self.feature_stats[col] = {
                    'unique_values': len(value_counts),
                    'top_5': dict(value_counts.head()),
                    'null_rate': self.unified_view[col].isnull().mean()
                }
    
    def add_engineered_features(self) -> pd.DataFrame:
        """Add additional engineered features for ML"""
        if self.unified_view is None:
            raise ValueError("Must create unified view first")
        
        df = self.unified_view.copy()
        
        # Shift features (previous hour's data)
        for col in ['energy_kwh', 'production_qty', 'kwh_per_unit']:
            if col in df.columns:
                df[f'{col}_lag1h'] = df.groupby('machine_id')[col].shift(1)
        
        # Rolling averages
        for window in [4, 8, 24]:  # 4hr, 8hr, 24hr
            for col in ['energy_kwh', 'production_qty']:
                if col in df.columns:
                    df[f'{col}_ma{window}h'] = df.groupby('machine_id')[col].transform(
                        lambda x: x.rolling(window, min_periods=1).mean()
                    )
        
        # Time-based features
        df['shift'] = pd.cut(df['hour_of_day'], 
                            bins=[0, 8, 16, 24], 
                            labels=['night', 'morning', 'afternoon'])
        
        # Production intensity
        df['production_intensity'] = df['production_qty'] / (df['production_minutes'] / 60)
        
        # Energy efficiency ranking by hour
        df['efficiency_rank_hourly'] = df.groupby('datetime')['kwh_per_unit'].rank(
            method='dense', ascending=True
        )
        
        self.unified_view = df
        return df
    
    def save_unified_view(self, output_file: str = 'unified_view.csv'):
        """Save the unified view to CSV"""
        if self.unified_view is None:
            raise ValueError("No unified view to save")
        
        self.unified_view.to_csv(output_file, index=False)
        print(f"\n💾 Saved unified view to {output_file}")
        
        # Also save feature statistics
        stats_file = output_file.replace('.csv', '_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            # Convert numpy types for JSON serialization
            stats_serializable = {}
            for key, value in self.feature_stats.items():
                if isinstance(value, dict):
                    stats_serializable[key] = {
                        k: float(v) if isinstance(v, (np.integer, np.floating)) else v
                        for k, v in value.items()
                    }
                else:
                    stats_serializable[key] = value
            
            json.dump(stats_serializable, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved feature statistics to {stats_file}")
    
    def get_ml_ready_dataset(self, 
                           target_col: str = 'kwh_per_unit',
                           exclude_cols: List[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare dataset for ML training
        
        Returns:
            X: Feature matrix
            y: Target variable
        """
        if self.unified_view is None:
            raise ValueError("Must create unified view first")
        
        # Default columns to exclude
        if exclude_cols is None:
            exclude_cols = ['datetime', 'machine_id', 'energy_id', 'csi_id', 'mes_id',
                           'order_id', 'reported_defects',  # excluding unreliable data
                           'team_leader', 'team_members']  # exclude raw names
        
        # Add target to exclude list
        exclude_cols.append(target_col)
        
        # Filter to records with valid target
        valid_data = self.unified_view[self.unified_view[target_col].notna()].copy()
        
        # Select features
        feature_cols = [col for col in valid_data.columns if col not in exclude_cols]
        
        # Handle categorical variables
        categorical_cols = ['material_code', 'task_type', 'team_composition', 
                           'production_status', 'mes_status', 'shift']
        
        for col in categorical_cols:
            if col in feature_cols:
                # Create dummy variables
                dummies = pd.get_dummies(valid_data[col], prefix=col, drop_first=True)
                valid_data = pd.concat([valid_data, dummies], axis=1)
                feature_cols.remove(col)
                feature_cols.extend(dummies.columns.tolist())
        
        # Prepare final datasets
        X = valid_data[feature_cols].fillna(0)  # Simple imputation for now
        y = valid_data[target_col]
        
        print(f"\n📊 ML-ready dataset prepared:")
        print(f"   Features: {X.shape[1]}")
        print(f"   Samples: {X.shape[0]}")
        print(f"   Target: {target_col}")
        
        return X, y


class EnergyAttributionSystem:
    """Categorize energy consumption into meaningful components"""
    
    def __init__(self):
        self.attribution_cache = {}
    
    def attribute_energy_for_period(self, machine_id: str, energy_data: pd.DataFrame, 
                                   csi_data: pd.DataFrame, hour: pd.Timestamp) -> Dict:
        """
        Break down energy consumption for a specific hour
        """
        hour_energy = energy_data[energy_data.index.floor('H') == hour]['electricity_kwh'].sum()
        
        # Find all CSI records that overlap with this hour
        hour_end = hour + timedelta(hours=1)
        
        attribution = {
            'total_energy': hour_energy,
            'setup_energy': 0,
            'production_energy': 0,
            'idle_energy': 0,
            'transition_energy': 0,
            'maintenance_energy': 0
        }
        
        # Check if any production in this hour
        production_in_hour = False
        setup_in_hour = False
        
        for _, csi_row in csi_data.iterrows():
            # Check setup time overlap
            setup_start = pd.to_datetime(csi_row.get('準備開始時間'), errors='coerce')
            setup_end = pd.to_datetime(csi_row.get('準備結束時間'), errors='coerce')
            
            if setup_start and setup_end:
                if (setup_start < hour_end) and (setup_end > hour):
                    setup_in_hour = True
                    overlap = min(hour_end, setup_end) - max(hour, setup_start)
                    overlap_fraction = overlap.total_seconds() / 3600
                    attribution['setup_energy'] = hour_energy * overlap_fraction
            
            # Check production time overlap
            prod_start = pd.to_datetime(csi_row.get('開始時間'), errors='coerce')
            prod_end = pd.to_datetime(csi_row.get('結束時間'), errors='coerce')
            
            if prod_start and prod_end:
                if (prod_start < hour_end) and (prod_end > hour):
                    production_in_hour = True
                    overlap = min(hour_end, prod_end) - max(hour, prod_start)
                    overlap_fraction = overlap.total_seconds() / 3600
                    attribution['production_energy'] += hour_energy * overlap_fraction
        
        # If no production or setup, it's idle
        if not production_in_hour and not setup_in_hour:
            if hour_energy == 0:
                attribution['maintenance_energy'] = 0  # Planned maintenance
            else:
                attribution['idle_energy'] = hour_energy
        
        # Normalize to ensure total matches
        total_attributed = sum(v for k, v in attribution.items() if k != 'total_energy')
        if total_attributed > 0 and total_attributed != hour_energy:
            scale = hour_energy / total_attributed
            for k in attribution:
                if k != 'total_energy':
                    attribution[k] *= scale
        
        return attribution


class DynamicBaselineEngine:
    """Calculate context-aware efficiency baselines"""
    
    def __init__(self):
        self.baseline_cache = {}
        self.historical_data = None
    
    def calculate_baseline(self, context: Dict) -> float:
        """
        Calculate expected efficiency based on multiple factors
        """
        # Create a unique key for this context
        context_key = f"{context.get('task_type')}_{context.get('material_code')}_{context.get('hour_of_day')}"
        
        if context_key in self.baseline_cache:
            return self.baseline_cache[context_key]
        
        # For now, use simple logic - will be replaced by ML model
        baseline = 1.0  # Base efficiency
        
        # Adjust for task type
        task_adjustments = {
            'UV染/印色': 1.2,
            '印刷': 1.0,
            '過光': 0.8,
            'UNKNOWN': 1.1
        }
        baseline *= task_adjustments.get(context.get('task_type', 'UNKNOWN'), 1.0)
        
        # Adjust for time of day (night shift might be less efficient)
        hour = context.get('hour_of_day', 12)
        if 0 <= hour < 6:  # Night
            baseline *= 1.15
        elif 6 <= hour < 12:  # Morning
            baseline *= 0.95
        elif 12 <= hour < 18:  # Afternoon
            baseline *= 1.0
        else:  # Evening
            baseline *= 1.05
        
        # Adjust for team size
        team_size = context.get('team_size', 2)
        if team_size == 1:
            baseline *= 1.2  # Single operator less efficient
        elif team_size >= 4:
            baseline *= 0.9  # Larger teams more efficient
        
        self.baseline_cache[context_key] = baseline
        return baseline
    
    def fit_on_historical_data(self, unified_view: pd.DataFrame):
        """Train baseline model on historical data"""
        self.historical_data = unified_view.copy()
        # In future: train ML model here


class TeamSynergyAnalyzer:
    """Analyze team performance and synergies (with actual names)"""
    
    def __init__(self):
        self.team_performance = {}
    
    def extract_team_info(self, csi_row: pd.Series) -> Dict:
        """Extract team composition with actual names"""
        team = {
            'leader': csi_row.get('機長姓名1', ''),
            'leader_id': csi_row.get('機長工號1', ''),
            'members': [],
            'member_ids': []
        }
        
        # Add team members
        for i in range(1, 5):
            member_name = csi_row.get(f'機組人員姓名{i}', '')
            member_id = csi_row.get(f'機組人員工號{i}', '')
            if pd.notna(member_name) and member_name:
                team['members'].append(member_name)
                team['member_ids'].append(member_id)
        
        team['size'] = 1 + len(team['members'])  # Leader + members
        team['composition'] = f"{team['leader']} + {', '.join(team['members'])}" if team['members'] else team['leader']
        
        return team
    
    def analyze_team_performance(self, unified_view: pd.DataFrame) -> Dict:
        """Analyze performance by team composition"""
        team_metrics = {}
        
        for _, row in unified_view.iterrows():
            team_comp = row.get('team_composition', 'UNKNOWN')
            if team_comp not in team_metrics:
                team_metrics[team_comp] = {
                    'total_production': 0,
                    'total_energy': 0,
                    'hours_worked': 0,
                    'task_types': [],
                    'efficiency_scores': []
                }
            
            team_metrics[team_comp]['total_production'] += row.get('production_qty', 0)
            team_metrics[team_comp]['total_energy'] += row.get('energy_kwh', 0)
            team_metrics[team_comp]['hours_worked'] += 1
            team_metrics[team_comp]['task_types'].append(row.get('task_type', 'UNKNOWN'))
            
            if row.get('kwh_per_unit', 0) > 0:
                team_metrics[team_comp]['efficiency_scores'].append(row['kwh_per_unit'])
        
        # Calculate summary statistics
        team_summary = {}
        for team, metrics in team_metrics.items():
            if metrics['total_production'] > 0:
                avg_efficiency = metrics['total_energy'] / metrics['total_production']
                team_summary[team] = {
                    'team_name': team,
                    'avg_kwh_per_unit': avg_efficiency,
                    'total_hours': metrics['hours_worked'],
                    'productivity': metrics['total_production'] / metrics['hours_worked'] if metrics['hours_worked'] > 0 else 0,
                    'primary_task': max(set(metrics['task_types']), key=metrics['task_types'].count),
                    'efficiency_variance': np.std(metrics['efficiency_scores']) if metrics['efficiency_scores'] else 0
                }
        
        # Rank teams
        ranked_teams = sorted(team_summary.values(), key=lambda x: x['avg_kwh_per_unit'])
        
        return {
            'team_rankings': ranked_teams,
            'best_teams': ranked_teams[:5] if len(ranked_teams) >= 5 else ranked_teams,
            'improvement_opportunities': ranked_teams[-5:] if len(ranked_teams) >= 5 else [],
            'detailed_metrics': team_summary
        }


class IntelligentScheduler:
    """Suggest optimal production scheduling based on patterns"""
    
    def __init__(self):
        self.transition_costs = {}
        self.material_patterns = {}
    
    def calculate_material_transition_cost(self, from_material: str, to_material: str, 
                                         historical_data: pd.DataFrame) -> float:
        """Calculate energy cost of transitioning between materials"""
        key = f"{from_material}->{to_material}"
        
        if key in self.transition_costs:
            return self.transition_costs[key]
        
        # Find historical transitions
        transitions = []
        for i in range(1, len(historical_data)):
            if (historical_data.iloc[i-1]['material_code'] == from_material and 
                historical_data.iloc[i]['material_code'] == to_material):
                # Check if this was a setup period
                if historical_data.iloc[i].get('is_setup_time', 0) == 1:
                    transitions.append(historical_data.iloc[i]['setup_energy'])
        
        if transitions:
            avg_cost = np.mean(transitions)
        else:
            # Default estimate
            avg_cost = 5.0 if from_material != to_material else 0.0
        
        self.transition_costs[key] = avg_cost
        return avg_cost
    
    def optimize_production_sequence(self, pending_orders: List[Dict], 
                                   current_material: str = None) -> List[Dict]:
        """
        Optimize order sequence to minimize total energy
        """
        if not pending_orders:
            return []
        
        # Simple greedy algorithm for now
        optimized_sequence = []
        remaining_orders = pending_orders.copy()
        current_mat = current_material
        
        while remaining_orders:
            # Find order with minimum transition cost
            min_cost = float('inf')
            best_order = None
            best_idx = -1
            
            for idx, order in enumerate(remaining_orders):
                if current_mat:
                    cost = self.transition_costs.get(
                        f"{current_mat}->{order['material_code']}", 
                        5.0 if current_mat != order['material_code'] else 0.0
                    )
                else:
                    cost = 0
                
                if cost < min_cost:
                    min_cost = cost
                    best_order = order
                    best_idx = idx
            
            if best_order:
                optimized_sequence.append(best_order)
                current_mat = best_order['material_code']
                remaining_orders.pop(best_idx)
        
        return optimized_sequence


# Updated main class method to use new components
def create_unified_hourly_view(self) -> pd.DataFrame:
    """Example of how to use the EUVG"""
    # Initialize EUVG
    euvg = EnhancedUnifiedViewGenerator()
    
    # Load June data (adjust paths as needed)
    energy_files = ['能耗、費用報表June130.xlsx']
    csi_file = 'CSI印刷心電圖報表June.xlsx'
    mes_file = 'MES生產數據JunePrinter.xlsx'
    mappings_file = 'june_enhanced_manufacturing_mappings_LATEST.json'
    
    # Load data and create unified view
    euvg.load_from_files(energy_files, csi_file, mes_file, mappings_file)
    unified_view = euvg.create_unified_hourly_view()
    
    # Add engineered features
    enhanced_view = euvg.add_engineered_features()
    
    # Save results
    euvg.save_unified_view('june_unified_view.csv')
    
    # Prepare for ML
    X, y = euvg.get_ml_ready_dataset()
    
    return euvg, X, y


if __name__ == "__main__":
    print("Enhanced Unified View Generator ready with advanced features!")
    print("\nKey features:")
    print("- Energy Attribution: Breaks down energy into setup/production/idle/maintenance")
    print("- Dynamic Baselines: Context-aware efficiency expectations")
    print("- Team Performance: Analyzes actual team compositions and performance")
    print("- Material Transitions: Tracks changeover costs between materials")
    print("- Intelligent Scheduling: Suggests optimal production sequences")
    print("- Rich Feature Engineering: 40+ features for ML models")
    print("\nAll correlations from CSI discovery integrated!")
