import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
import json
from datetime import datetime, timedelta

def prepare_ml_data(unified_view: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare data for ML models
    
    Args:
        unified_view: The unified hourly view dataframe
        
    Returns:
        X: Feature matrix
        y: Target variable (kwh_per_unit)
    """
    # Remove rows with missing target
    valid_data = unified_view[unified_view['kwh_per_unit'].notna()].copy()
    
    # Select features
    feature_cols = [
        'hour_of_day', 'day_of_week', 'is_weekend',
        'production_qty', 'production_minutes',
        'setup_energy', 'production_energy', 'idle_energy',
        'team_size', 'efficiency_vs_baseline',
        'material_transition', 'is_setup_time'
    ]
    
    # Filter to only available columns
    available_features = [col for col in feature_cols if col in valid_data.columns]
    
    # Add lag features if available
    lag_features = ['energy_kwh_lag1h', 'production_qty_lag1h', 'kwh_per_unit_lag1h']
    available_features.extend([col for col in lag_features if col in valid_data.columns])
    
    # Add moving average features if available
    ma_features = [col for col in valid_data.columns if '_ma' in col]
    available_features.extend(ma_features)
    
    if not available_features:
        return pd.DataFrame(), pd.Series()
    
    X = valid_data[available_features].fillna(0)
    y = valid_data['kwh_per_unit']
    
    return X, y

def format_large_number(num: float) -> str:
    """
    Format large numbers with K/M suffix
    
    Args:
        num: Number to format
        
    Returns:
        Formatted string with suffix
    """
    if pd.isna(num):
        return "N/A"
    
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num:.0f}"

def calculate_energy_savings(baseline_energy: float, optimized_energy: float) -> Dict[str, float]:
    """
    Calculate energy savings metrics
    
    Args:
        baseline_energy: Energy consumption before optimization
        optimized_energy: Energy consumption after optimization
        
    Returns:
        Dictionary with savings metrics
    """
    if baseline_energy <= 0:
        return {
            'absolute_savings': 0,
            'percentage_savings': 0,
            'cost_savings': 0
        }
    
    absolute_savings = baseline_energy - optimized_energy
    percentage_savings = (absolute_savings / baseline_energy) * 100
    
    # Assume average electricity cost (adjust as needed)
    electricity_cost_per_kwh = 0.15  # USD per kWh
    cost_savings = absolute_savings * electricity_cost_per_kwh
    
    return {
        'absolute_savings': absolute_savings,
        'percentage_savings': percentage_savings,
        'cost_savings': cost_savings
    }

def detect_anomalies(data: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.Series:
    """
    Detect anomalies using z-score method
    
    Args:
        data: DataFrame containing the data
        column: Column name to check for anomalies
        threshold: Z-score threshold for anomaly detection
        
    Returns:
        Boolean series indicating anomalies
    """
    if column not in data.columns:
        return pd.Series([False] * len(data), index=data.index)
    
    # Calculate z-scores
    mean = data[column].mean()
    std = data[column].std()
    
    if std == 0:
        return pd.Series([False] * len(data), index=data.index)
    
    z_scores = np.abs((data[column] - mean) / std)
    
    return z_scores > threshold

def create_shift_schedule(unified_view: pd.DataFrame) -> pd.DataFrame:
    """
    Create a shift schedule summary from the unified view
    
    Args:
        unified_view: The unified hourly view dataframe
        
    Returns:
        DataFrame with shift schedule summary
    """
    if 'shift' not in unified_view.columns:
        # Create shift column if not exists
        unified_view['shift'] = pd.cut(
            unified_view['hour_of_day'], 
            bins=[0, 8, 16, 24], 
            labels=['Night', 'Morning', 'Afternoon']
        )
    
    # Aggregate by shift
    shift_summary = unified_view.groupby('shift').agg({
        'energy_kwh': ['sum', 'mean'],
        'production_qty': ['sum', 'mean'],
        'kwh_per_unit': 'mean'
    }).round(2)
    
    # Flatten column names
    shift_summary.columns = ['_'.join(col).strip() for col in shift_summary.columns.values]
    
    return shift_summary

def calculate_oee_metrics(unified_view: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate Overall Equipment Effectiveness (OEE) metrics
    
    Args:
        unified_view: The unified hourly view dataframe
        
    Returns:
        Dictionary with OEE metrics
    """
    total_hours = len(unified_view)
    
    # Availability: Hours with production / Total hours
    production_hours = len(unified_view[unified_view['production_qty'] > 0])
    availability = (production_hours / total_hours * 100) if total_hours > 0 else 0
    
    # Performance: Actual production / Expected production
    # Using efficiency_percent if available
    if 'efficiency_percent' in unified_view.columns:
        performance = unified_view['efficiency_percent'].mean()
    else:
        performance = 85.0  # Default assumption
    
    # Quality: Good units / Total units (assuming all are good since no defect data)
    quality = 98.0  # Default assumption
    
    # OEE = Availability × Performance × Quality
    oee = (availability * performance * quality) / 10000
    
    return {
        'availability': availability,
        'performance': performance,
        'quality': quality,
        'oee': oee
    }

def generate_optimization_recommendations(unified_view: pd.DataFrame, 
                                        team_analysis: Dict) -> List[Dict[str, str]]:
    """
    Generate optimization recommendations based on analysis
    
    Args:
        unified_view: The unified hourly view dataframe
        team_analysis: Team performance analysis results
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Check for high idle energy periods
    if 'idle_energy' in unified_view.columns:
        idle_pct = (unified_view['idle_energy'].sum() / unified_view['energy_kwh'].sum() * 100)
        if idle_pct > 15:
            recommendations.append({
                'category': 'Energy Efficiency',
                'issue': f'High idle energy consumption ({idle_pct:.1f}%)',
                'recommendation': 'Implement automated shutdown procedures during non-production hours',
                'potential_savings': f'{idle_pct * 0.7:.1f}% energy reduction'
            })
    
    # Check for material transition inefficiencies
    if 'material_transition' in unified_view.columns:
        transition_count = unified_view['material_transition'].sum()
        if transition_count > len(unified_view) * 0.1:  # More than 10% transitions
            recommendations.append({
                'category': 'Production Planning',
                'issue': f'Frequent material transitions ({transition_count} times)',
                'recommendation': 'Batch similar materials together to reduce changeover time',
                'potential_savings': '15-20% reduction in setup time'
            })
    
    # Check team performance variations
    if team_analysis and 'detailed_metrics' in team_analysis:
        efficiencies = [m.get('avg_kwh_per_unit', 0) for m in team_analysis['detailed_metrics'].values()]
        if efficiencies:
            efficiency_std = np.std(efficiencies)
            if efficiency_std > np.mean(efficiencies) * 0.2:  # High variation
                recommendations.append({
                    'category': 'Team Training',
                    'issue': 'High variation in team performance',
                    'recommendation': 'Implement best practice sharing from top-performing teams',
                    'potential_savings': '10-15% improvement in average efficiency'
                })
    
    # Check for weekend/night shift inefficiencies
    if 'is_weekend' in unified_view.columns and 'kwh_per_unit' in unified_view.columns:
        weekend_eff = unified_view[unified_view['is_weekend']]['kwh_per_unit'].mean()
        weekday_eff = unified_view[~unified_view['is_weekend']]['kwh_per_unit'].mean()
        
        if weekend_eff > weekday_eff * 1.2:  # 20% worse on weekends
            recommendations.append({
                'category': 'Scheduling',
                'issue': 'Weekend shifts less efficient than weekdays',
                'recommendation': 'Review weekend staffing and supervision levels',
                'potential_savings': f'{(weekend_eff/weekday_eff - 1) * 100:.1f}% efficiency gain'
            })
    
    return recommendations

def export_report_data(etl, euvg, unified_view: pd.DataFrame, 
                      output_path: str = 'manufacturing_report.xlsx'):
    """
    Export comprehensive report data to Excel
    
    Args:
        etl: ETL pipeline instance
        euvg: EUVG instance
        unified_view: The unified hourly view dataframe
        output_path: Path to save the Excel file
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Summary statistics
        summary_stats = pd.DataFrame({
            'Metric': ['Total Machines', 'Total Energy (kWh)', 'Total Production', 
                      'Average Efficiency', 'Date Range'],
            'Value': [
                unified_view['machine_id'].nunique(),
                f"{unified_view['energy_kwh'].sum():,.0f}",
                f"{unified_view['production_qty'].sum():,.0f}",
                f"{unified_view['kwh_per_unit'].mean():.2f}",
                f"{unified_view['datetime'].min().date()} to {unified_view['datetime'].max().date()}"
            ]
        })
        summary_stats.to_excel(writer, sheet_name='Summary', index=False)
        
        # Machine mappings
        if hasattr(etl, 'machine_mapping') and 'three_way_matches' in etl.machine_mapping:
            matches_df = pd.DataFrame(etl.machine_mapping['three_way_matches'])
            matches_df.to_excel(writer, sheet_name='Machine Mappings', index=False)
        
        # Daily aggregates
        daily_stats = unified_view.groupby(pd.Grouper(key='datetime', freq='D')).agg({
            'energy_kwh': 'sum',
            'production_qty': 'sum',
            'kwh_per_unit': 'mean'
        }).round(2)
        daily_stats.to_excel(writer, sheet_name='Daily Statistics')
        
        # Team performance
        if hasattr(euvg, 'team_performance_analysis') and euvg.team_performance_analysis:
            if 'best_teams' in euvg.team_performance_analysis:
                team_df = pd.DataFrame(euvg.team_performance_analysis['best_teams'])
                team_df.to_excel(writer, sheet_name='Team Performance', index=False)
    
    print(f"Report exported to {output_path}")

def validate_data_quality(unified_view: pd.DataFrame) -> Dict[str, any]:
    """
    Validate data quality and return metrics
    
    Args:
        unified_view: The unified hourly view dataframe
        
    Returns:
        Dictionary with data quality metrics
    """
    metrics = {
        'total_records': len(unified_view),
        'date_range': f"{unified_view['datetime'].min()} to {unified_view['datetime'].max()}",
        'missing_values': {},
        'data_anomalies': {},
        'quality_score': 100.0
    }
    
    # Check missing values for key columns
    key_columns = ['energy_kwh', 'production_qty', 'kwh_per_unit', 'team_composition', 'material_code']
    
    for col in key_columns:
        if col in unified_view.columns:
            missing_pct = (unified_view[col].isna().sum() / len(unified_view) * 100)
            metrics['missing_values'][col] = f"{missing_pct:.1f}%"
            
            # Deduct from quality score
            metrics['quality_score'] -= missing_pct * 0.2
    
    # Check for anomalies
    if 'kwh_per_unit' in unified_view.columns:
        anomalies = detect_anomalies(unified_view, 'kwh_per_unit')
        anomaly_pct = (anomalies.sum() / len(unified_view) * 100)
        metrics['data_anomalies']['efficiency_outliers'] = f"{anomaly_pct:.1f}%"
        
        # Deduct from quality score
        metrics['quality_score'] -= anomaly_pct * 0.5
    
    # Ensure quality score doesn't go below 0
    metrics['quality_score'] = max(0, metrics['quality_score'])
    
    return metrics