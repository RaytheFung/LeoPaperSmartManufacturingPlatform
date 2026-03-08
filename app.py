import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import io
import numpy as np
import os

# Import custom modules
from core.enhanced_etl_solution_CURRENT import EnhancedSmartManufacturingETL
from core.utils import prepare_ml_data  # Use centralized ML data preparation
from modules.euvg_module import EnhancedUnifiedViewGenerator
from modules.etl_module import render_etl_page as render_etl_upload_page
from modules.unified_view_module import render_unified_view_page
from modules.maintenance_module import render_maintenance_page
from modules.ml_module import render_ml_module
from modules.optimization_module import render_optimization_module

# Page config
st.set_page_config(
    page_title="Smart Manufacturing Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🏭 Smart Manufacturing ETL + ML Platform")
st.markdown("""
Transform 5+ hours of manual Excel work into 5-minute automated insights!
This platform integrates Energy, CSI, and MES systems for intelligent manufacturing optimization.
""")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Choose Analysis Module",
    ["🔄 ETL Pipeline", "📊 Unified View", "⚡ Energy Analysis", 
     "🔧 Maintenance", "🤖 Machine Learning", "🎯 Optimization"]
)

# Data loading function
@st.cache_data
def load_data():
    """Load and process data through ETL and EUVG pipelines"""
    try:
        # Initialize ETL
        etl = EnhancedSmartManufacturingETL()
        
        # Define data paths
        energy_files = ['data/能耗、費用報表June(1-30).xlsx']
        csi_file = 'data/CSI印刷心電圖報表June.xlsx'
        mes_file = 'data/MES生產數據JunePrinter.xlsx'
        mappings_file = 'data/june_enhanced_manufacturing_mappings_LATEST.json'
        
        # Extract data
        etl.extract_all_sources(energy_files, csi_file, mes_file)
        
        # Load or create mappings
        if os.path.exists(mappings_file):
            with open(mappings_file, 'r', encoding='utf-8') as f:
                mappings_data = json.load(f)
                # EnhancedSmartManufacturingETL exposes machine_mapping as read-only property;
                # assign into internal state to preserve backwards compatibility.
                etl.state.machine_mapping = mappings_data
        else:
            # Create new mappings using the modern façade
            etl.aggregate_energy_data()
            etl.create_comprehensive_mapping()
        
        # Initialize EUVG with ETL pipeline
        euvg = EnhancedUnifiedViewGenerator(etl)
        
        # Get three-way matches from ETL mapping
        if 'three_way_matches' in etl.machine_mapping:
            euvg.three_way_matches = etl.machine_mapping['three_way_matches']
        else:
            st.error("No three-way matches found in ETL mapping!")
            return None, None, None
        
        # Create unified view
        unified_view = euvg.create_unified_hourly_view()
        enhanced_view = euvg.add_engineered_features()
        
        return etl, euvg, enhanced_view
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.error("Please ensure all data files are in the 'data' folder")
        return None, None, None

# Initialize variables
etl, euvg, unified_view = None, None, None

# Special handling for pages that don't need data loading
if page in ["🔄 ETL Pipeline", "📊 Unified View", "🔧 Maintenance", "🤖 Machine Learning", "🎯 Optimization"]:
    # These pages use database directly or have their own data loading
    pass
else:
    # Load data for other pages that still need it
    with st.spinner("Loading and processing data..."):
        etl, euvg, unified_view = load_data()
    
    # Check if data loaded successfully
    if etl is None or euvg is None or unified_view is None:
        st.error("Failed to load data. Please check your data files.")
        st.stop()

# Page implementations
def show_overview_page(etl, euvg, unified_view):
    """Display overview metrics and key insights"""
    st.header("📊 Manufacturing Analytics Overview")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_machines = len(euvg.three_way_matches) if hasattr(euvg, 'three_way_matches') else 0
        total_mes = etl.machine_mapping.get('mapping_stats', {}).get('mes_machines', 88)
        coverage_pct = (total_machines/total_mes*100) if total_mes > 0 else 0
        st.metric("Three-way Matches", f"{total_machines}/{total_mes}", 
                 f"{coverage_pct:.1f}%")
    
    with col2:
        total_energy = unified_view['energy_kwh'].sum()
        st.metric("Total Energy (June)", f"{total_energy:,.0f} kWh")
    
    with col3:
        total_production = unified_view['production_qty'].sum()
        st.metric("Total Production", f"{total_production:,.0f} units")
    
    with col4:
        avg_efficiency = unified_view['kwh_per_unit'].mean()
        st.metric("Avg Efficiency", f"{avg_efficiency:.2f} kWh/unit")
    
    # Energy attribution pie chart
    st.subheader("Energy Attribution Breakdown")
    
    # Define consistent colors for each energy type
    energy_color_map = {
        'Setup Energy': '#3498db',      # Blue
        'Production Energy': '#2ecc71',  # Green
        'Idle Energy': '#e74c3c',       # Red
        'Maintenance Energy': '#f39c12'  # Orange
    }
    
    # Calculate energy breakdown
    energy_cols = ['setup_energy', 'production_energy', 'idle_energy', 'maintenance_energy']
    energy_breakdown = {}
    for col in energy_cols:
        if col in unified_view.columns:
            energy_breakdown[col.replace('_', ' ').title()] = unified_view[col].sum()
    
    if energy_breakdown:
        fig = px.pie(values=list(energy_breakdown.values()), 
                     names=list(energy_breakdown.keys()),
                     title="Where Does Energy Go?",
                     color_discrete_map=energy_color_map)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # Daily production trend
    st.subheader("Daily Production Trend")
    daily_stats = unified_view.groupby(pd.Grouper(key='datetime', freq='D')).agg({
        'production_qty': 'sum',
        'energy_kwh': 'sum'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily_stats['datetime'], y=daily_stats['production_qty'],
                         name='Production Quantity', yaxis='y'))
    fig.add_trace(go.Scatter(x=daily_stats['datetime'], y=daily_stats['energy_kwh'],
                            name='Energy Consumption', yaxis='y2', line=dict(color='red')))
    
    fig.update_layout(
        title='Daily Production vs Energy Consumption',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Production Quantity', side='left'),
        yaxis2=dict(title='Energy (kWh)', side='right', overlaying='y'),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

def show_etl_page(etl):
    """Display ETL pipeline status and mapping results"""
    st.header("🔄 ETL Pipeline Status")
    
    # Show mapping statistics
    stats = etl.machine_mapping.get('mapping_stats', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Data Volume")
        st.write(f"- Energy Records: {stats.get('energy_original_rows', 0):,}")
        st.write(f"- Energy Machines: {stats.get('energy_unique_machines', 0)}")
        st.write(f"- CSI Machines: {stats.get('csi_machines', 0)}")
        st.write(f"- MES Machines: {stats.get('mes_machines', 0)}")
    
    with col2:
        st.subheader("Matching Results")
        st.write(f"- Three-way Matches: {stats.get('three_way_matches', 0)}")
        st.write(f"- MES Coverage: {stats.get('mes_coverage_percent', 'N/A')}")
    
    # Show three-way matches table
    st.subheader("Three-way Machine Matches")
    if 'three_way_matches' in etl.machine_mapping:
        matches_df = pd.DataFrame(etl.machine_mapping['three_way_matches'])
        
        # Select columns to display
        display_cols = ['machine_id', 'csi', 'mes', 'total_kwh']
        if all(col in matches_df.columns for col in display_cols):
            st.dataframe(matches_df[display_cols].round(2), 
                        use_container_width=True)
        else:
            st.dataframe(matches_df, use_container_width=True)

def show_unified_view_page():
    """Display the unified hourly view data"""
    render_unified_view_page()

def show_energy_analysis_page(unified_view, euvg):
    """Display energy analysis dashboard"""
    st.header("⚡ Energy Analysis Dashboard")
    
    # Energy Attribution Analysis - Moved from Unified View for better UX
    st.subheader("⚡ Energy Attribution Analysis")
    
    # Define consistent colors for each energy type
    energy_color_map = {
        'Setup Energy': '#3498db',      # Blue
        'Production Energy': '#2ecc71',  # Green
        'Idle Energy': '#e74c3c',       # Red (waste)
        'Maintenance Energy': '#9b59b6'  # Purple (necessary non-production)
    }
    
    energy_cols = ['setup_energy', 'production_energy', 'idle_energy', 'maintenance_energy']
    energy_data = []
    energy_labels = []
    energy_colors = []
    
    for col in energy_cols:
        if col in unified_view.columns:
            value = unified_view[col].sum()
            if value > 0:  # Only include non-zero values
                label = col.replace('_', ' ').title()
                energy_data.append(value)
                energy_labels.append(label)
                energy_colors.append(energy_color_map.get(label, '#95a5a6'))
    
    if energy_data:
        fig = go.Figure(data=[go.Pie(
            labels=energy_labels,
            values=energy_data,
            marker=dict(colors=energy_colors),
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Energy: %{value:,.2f} kWh<br>Percentage: %{percent}<extra></extra>'
        )])
        fig.update_layout(
            title="Energy Distribution Overview",
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Show energy breakdown metrics
        col1, col2, col3, col4 = st.columns(4)
        total_energy = sum(energy_data)
        
        with col1:
            production_pct = (energy_data[energy_labels.index('Production Energy')] / total_energy * 100) if 'Production Energy' in energy_labels else 0
            st.metric("Production Energy", f"{production_pct:.1f}%", "Value-adding")
        
        with col2:
            idle_pct = (energy_data[energy_labels.index('Idle Energy')] / total_energy * 100) if 'Idle Energy' in energy_labels else 0
            st.metric("Idle Energy", f"{idle_pct:.1f}%", "Optimization target", delta_color="inverse")
        
        with col3:
            maintenance_pct = (energy_data[energy_labels.index('Maintenance Energy')] / total_energy * 100) if 'Maintenance Energy' in energy_labels else 0
            st.metric("Maintenance Energy", f"{maintenance_pct:.1f}%", "Necessary")
        
        with col4:
            waste_kwh = energy_data[energy_labels.index('Idle Energy')] if 'Idle Energy' in energy_labels else 0
            st.metric("Potential Savings", f"{waste_kwh:,.0f} kWh", "Reducible waste")
    
    # Time series plot of energy attribution
    st.subheader("Energy Usage Over Time")
    
    # Daily energy by category
    energy_cols = ['setup_energy', 'production_energy', 'idle_energy', 'maintenance_energy']
    available_energy_cols = [col for col in energy_cols if col in unified_view.columns]
    
    if available_energy_cols:
        daily_energy = unified_view.groupby(
            pd.Grouper(key='datetime', freq='D')
        )[available_energy_cols].sum()
        
        fig = go.Figure()
        for col in available_energy_cols:
            fig.add_trace(go.Scatter(
                x=daily_energy.index,
                y=daily_energy[col],
                name=col.replace('_', ' ').title(),
                stackgroup='one'
            ))
        
        fig.update_layout(
            title="Daily Energy Attribution",
            xaxis_title="Date",
            yaxis_title="Energy (kWh)",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Machine efficiency ranking
    st.subheader("Machine Efficiency Ranking")
    
    machine_eff = unified_view[unified_view['kwh_per_unit'].notna()].groupby('machine_id').agg({
        'kwh_per_unit': 'mean',
        'production_qty': 'sum',
        'energy_kwh': 'sum'
    }).sort_values('kwh_per_unit')
    
    # Top 20 most efficient machines
    if len(machine_eff) > 0:
        fig = px.bar(
            machine_eff.head(20).reset_index(), 
            x='machine_id', 
            y='kwh_per_unit',
            title="Top 20 Most Efficient Machines",
            labels={'kwh_per_unit': 'kWh per Unit', 'machine_id': 'Machine ID'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Energy by hour of day pattern
    st.subheader("Energy Usage Pattern by Hour")
    
    hourly_pattern = unified_view.groupby('hour_of_day')['energy_kwh'].agg(['mean', 'sum'])
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hourly_pattern.index, y=hourly_pattern['mean'],
                        name='Average Energy'))
    
    fig.update_layout(
        title="Average Energy Consumption by Hour of Day",
        xaxis_title="Hour of Day",
        yaxis_title="Average Energy (kWh)"
    )
    st.plotly_chart(fig, use_container_width=True)

def show_team_performance_page(euvg, unified_view):
    """Display team performance analysis"""
    st.header("👥 Team Performance Analysis")

    if unified_view is None or unified_view.empty:
        st.info("Unified view data not available. Please run the ETL pipeline first.")
        return

    required_columns = {'kwh_per_unit', 'production_qty', 'datetime'}
    missing_columns = required_columns - set(unified_view.columns)
    if missing_columns:
        st.warning(f"Unified view is missing required columns: {', '.join(sorted(missing_columns))}.")
        return

    # Filter to meaningful production records
    analysis_df = unified_view.copy()
    mask = analysis_df['kwh_per_unit'].between(0.3, 10, inclusive='both')
    mask &= analysis_df['production_qty'] > 0
    if 'is_near_zero_output' in analysis_df.columns:
        mask &= analysis_df['is_near_zero_output'] == 0
    analysis_df = analysis_df.loc[mask].copy()

    if analysis_df.empty:
        st.info("No qualifying production records found (after quality filters).")
        return

    analysis_df['month_period'] = analysis_df['datetime'].dt.to_period('M')
    if analysis_df['month_period'].empty:
        st.info("No month information available in the unified view.")
        return

    month_options = sorted(analysis_df['month_period'].unique())
    default_index = len(month_options) - 1
    selected_month = st.selectbox(
        "Select month",
        month_options,
        index=default_index,
        format_func=lambda p: str(p),
    )

    analysis_df = analysis_df[analysis_df['month_period'] == selected_month].copy()
    if analysis_df.empty:
        st.info("No qualifying production records for the selected month.")
        return

    month_label = str(selected_month)

    if 'task_type' not in analysis_df.columns:
        analysis_df['task_type'] = 'Unknown'
    else:
        analysis_df['task_type'] = analysis_df['task_type'].fillna('Unknown')

    if 'team_leader' not in analysis_df.columns:
        analysis_df['team_leader'] = 'Unknown'
    else:
        analysis_df['team_leader'] = analysis_df['team_leader'].fillna('Unknown')

    if 'team_composition' in analysis_df.columns:
        analysis_df['team_composition'] = analysis_df['team_composition'].fillna(analysis_df['team_leader'])

    # Configure sample thresholds
    config_col1, config_col2 = st.columns(2)
    leader_task_min = config_col1.number_input(
        "Minimum samples per leader × task",
        min_value=1,
        value=20,
        step=1,
        help="Only show leader-task combinations with at least this many qualifying hours."
    )
    team_comp_min = config_col2.number_input(
        "Minimum samples per team composition × task",
        min_value=1,
        value=10,
        step=1,
        help="Only show team composition-task combinations with at least this many qualifying hours."
    )

    # Leader × Task analytics
    st.subheader("Leader × Task Efficiency")
    leader_task_columns = [
        'task_type',
        'team_leader',
        'avg_kwh_per_unit',
        'median_kwh_per_unit',
        'sample_size',
        'total_production',
        'last_observed',
    ]
    leader_task_group = pd.DataFrame(columns=leader_task_columns)
    if 'team_leader' in analysis_df.columns:
        raw_leader_task = (
            analysis_df.groupby(['task_type', 'team_leader'], dropna=False)
            .agg(
                avg_kwh_per_unit=('kwh_per_unit', 'mean'),
                median_kwh_per_unit=('kwh_per_unit', 'median'),
                sample_size=('kwh_per_unit', 'count'),
                total_production=('production_qty', 'sum'),
                last_observed=('datetime', 'max')
            )
            .reset_index()
        )
        if not raw_leader_task.empty:
            leader_task_group = raw_leader_task[
                (raw_leader_task['sample_size'] >= leader_task_min)
                & (raw_leader_task['team_leader'] != 'Unknown')
                & (raw_leader_task['task_type'] != 'Unknown')
            ].sort_values('avg_kwh_per_unit')

    if leader_task_group.empty:
        st.info("No leader × task combinations meet the minimum sample threshold yet.")
    else:
        st.dataframe(
            leader_task_group.head(25).round({
                'avg_kwh_per_unit': 3,
                'median_kwh_per_unit': 3
            }),
            use_container_width=True,
            hide_index=True
        )

        best_leader_chart = leader_task_group.nsmallest(15, 'avg_kwh_per_unit')
        fig = px.bar(
            best_leader_chart,
            x='team_leader',
            y='avg_kwh_per_unit',
            color='task_type',
            title="Top Leader × Task Combinations (Lower kWh/unit is better)",
            labels={'avg_kwh_per_unit': 'Avg kWh/unit', 'team_leader': 'Team Leader', 'task_type': 'Task'}
        )
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    if hasattr(euvg, 'team_performance_analysis') and euvg.team_performance_analysis:
        team_analysis = euvg.team_performance_analysis
        
        # Top teams table
        st.subheader("🏆 Top Performing Teams")
        
        if 'best_teams' in team_analysis and team_analysis['best_teams']:
            top_teams_df = pd.DataFrame(team_analysis['best_teams'])
            
            # Select columns to display
            display_cols = ['team_name', 'avg_kwh_per_unit', 'productivity', 'primary_task']
            available_cols = [col for col in display_cols if col in top_teams_df.columns]
            
            if available_cols:
                st.dataframe(
                    top_teams_df[available_cols].round(2), 
                    use_container_width=True
                )
        
        # Team efficiency comparison
        st.subheader("Team Efficiency by Task Type")
        
        if 'detailed_metrics' in team_analysis:
            # Create visualization showing team performance by task type
            team_task_data = []
            for team_name, metrics in team_analysis['detailed_metrics'].items():
                if isinstance(metrics, dict):
                    team_task_data.append({
                        'Team': team_name[:30] + '...' if len(team_name) > 30 else team_name,
                        'Efficiency': metrics.get('avg_kwh_per_unit', 0),
                        'Task Type': metrics.get('primary_task', 'Unknown'),
                        'Hours Worked': metrics.get('total_hours', 0)
                    })
            
            if team_task_data:
                team_task_df = pd.DataFrame(team_task_data)
                
                # Filter out teams with zero efficiency
                team_task_df = team_task_df[team_task_df['Efficiency'] > 0]
                
                if len(team_task_df) > 0:
                    fig = px.scatter(
                        team_task_df, 
                        x='Hours Worked', 
                        y='Efficiency', 
                        color='Task Type',
                        hover_data=['Team'],
                        title="Team Efficiency vs Experience",
                        labels={'Efficiency': 'kWh per Unit (Lower is Better)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Team ranking bar chart
                st.subheader("Team Efficiency Ranking")
                
                # Get top 20 teams by efficiency
                top_20_teams = team_task_df.nsmallest(20, 'Efficiency')
                
                if len(top_20_teams) > 0:
                    fig = px.bar(
                        top_20_teams,
                        x='Team',
                        y='Efficiency',
                        color='Task Type',
                        title="Top 20 Teams by Efficiency"
                    )
                    fig.update_xaxis(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Team performance analysis artifacts not available. Live analytics below use unified view data.")

    team_comp_columns = [
        'task_type',
        'team_composition',
        'avg_kwh_per_unit',
        'median_kwh_per_unit',
        'sample_size',
        'total_production',
        'last_observed',
        'median_team_size',
    ]
    team_comp_group = pd.DataFrame(columns=team_comp_columns)
    # Team composition × Task analytics
    if 'team_composition' in analysis_df.columns:
        st.subheader("Team Composition × Task Efficiency")
        comp_df = analysis_df[analysis_df['team_composition'].notna()]
        comp_df = comp_df[comp_df['team_composition'] != 'Unknown']

        if comp_df.empty:
            st.info("No team composition data available after filtering.")
        else:
            aggregation_kwargs = dict(
                avg_kwh_per_unit=('kwh_per_unit', 'mean'),
                median_kwh_per_unit=('kwh_per_unit', 'median'),
                sample_size=('kwh_per_unit', 'count'),
                total_production=('production_qty', 'sum'),
                last_observed=('datetime', 'max')
            )
            if 'team_size' in comp_df.columns:
                aggregation_kwargs['median_team_size'] = ('team_size', 'median')

            team_comp_group = (
                comp_df.groupby(['task_type', 'team_composition'], dropna=False)
                .agg(**aggregation_kwargs)
                .reset_index()
            )
            team_comp_group = team_comp_group[
                (team_comp_group['sample_size'] >= team_comp_min)
                & (team_comp_group['task_type'] != 'Unknown')
            ].sort_values('avg_kwh_per_unit')

            if team_comp_group.empty:
                st.info("No team composition × task combinations meet the minimum sample threshold yet.")
            else:
                st.dataframe(
                    team_comp_group.head(25).round({
                        'avg_kwh_per_unit': 3,
                        'median_kwh_per_unit': 3
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                best_team_comp_chart = team_comp_group.nsmallest(15, 'avg_kwh_per_unit')
                fig = px.bar(
                    best_team_comp_chart,
                    x='team_composition',
                    y='avg_kwh_per_unit',
                    color='task_type',
                    title="Top Team Composition × Task Combinations",
                    labels={'avg_kwh_per_unit': 'Avg kWh/unit', 'team_composition': 'Team Composition'}
                )
                fig.update_layout(xaxis_tickangle=-35)
                st.plotly_chart(fig, use_container_width=True)

    # Monthly insights export
    st.subheader("Monthly Insights Report")

    avg_efficiency = analysis_df['kwh_per_unit'].dropna().mean()
    summary_rows = [
        ("Month", month_label),
        ("Hours analyzed", f"{len(analysis_df):,}"),
        ("Total production (units)", f"{analysis_df['production_qty'].sum():,.0f}"),
        ("Average kWh/unit", f"{avg_efficiency:.3f}" if not np.isnan(avg_efficiency) else "N/A"),
        ("Unique machines", analysis_df['machine_id'].nunique()),
        ("Unique leaders", analysis_df['team_leader'].nunique()),
        ("Unique tasks", analysis_df['task_type'].nunique()),
    ]

    if not leader_task_group.empty:
        best_combo = leader_task_group.iloc[0]
        summary_rows.append(
            ("Top leader × task", f"{best_combo['team_leader']} ({best_combo['task_type']})")
        )
        summary_rows.append(
            ("Top leader × task kWh/unit", f"{best_combo['avg_kwh_per_unit']:.3f}")
        )
        worst_combo = leader_task_group.iloc[-1]
        summary_rows.append(
            (
                "Largest improvement (leader × task)",
                f"{worst_combo['team_leader']} ({worst_combo['task_type']})",
            )
        )
        summary_rows.append(
            ("Improvement kWh/unit", f"{worst_combo['avg_kwh_per_unit']:.3f}")
        )

    if not team_comp_group.empty:
        best_team = team_comp_group.iloc[0]
        summary_rows.append(
            ("Top team composition", f"{best_team['team_composition']} ({best_team['task_type']})")
        )
        summary_rows.append(
            ("Top team kWh/unit", f"{best_team['avg_kwh_per_unit']:.3f}")
        )

    summary_df = pd.DataFrame(summary_rows, columns=['Metric', 'Value'])

    if not leader_task_group.empty:
        opportunities_df = leader_task_group.nlargest(
            min(len(leader_task_group), 15), 'avg_kwh_per_unit'
        ).reset_index(drop=True)
    else:
        opportunities_df = pd.DataFrame(
            columns=['task_type', 'team_leader', 'avg_kwh_per_unit', 'median_kwh_per_unit',
                     'sample_size', 'total_production', 'last_observed']
        )

    maintenance_df = pd.DataFrame(
        columns=['machine_id', 'maintenance_energy', 'energy_kwh', 'hours', 'maintenance_ratio']
    )
    if {'maintenance_energy', 'energy_kwh'}.issubset(analysis_df.columns):
        maintenance_summary = (
            analysis_df.groupby('machine_id')
            .agg(
                maintenance_energy=('maintenance_energy', 'sum'),
                energy_kwh=('energy_kwh', 'sum'),
                hours=('machine_id', 'count'),
            )
            .reset_index()
        )
        maintenance_summary['maintenance_ratio'] = np.where(
            maintenance_summary['energy_kwh'] > 0,
            maintenance_summary['maintenance_energy'] / maintenance_summary['energy_kwh'],
            np.nan,
        )
        maintenance_df = maintenance_summary.sort_values(
            'maintenance_energy', ascending=False
        ).head(15)

    detail_columns = [
        'datetime',
        'machine_id',
        'team_leader',
        'team_composition',
        'task_type',
        'production_qty',
        'energy_kwh',
        'kwh_per_unit',
        'maintenance_energy',
        'is_near_zero_output',
    ]
    detail_cols_present = [col for col in detail_columns if col in analysis_df.columns]
    detail_df = analysis_df[detail_cols_present].copy()
    if 'datetime' in detail_df.columns:
        detail_df['datetime'] = detail_df['datetime'].astype(str)
    if 'kwh_per_unit' in detail_df.columns:
        detail_df['kwh_per_unit'] = detail_df['kwh_per_unit'].round(3)

    insights_buffer = io.BytesIO()
    with pd.ExcelWriter(insights_buffer, engine='openpyxl') as writer:
        summary_df.to_excel(writer, index=False, sheet_name='Summary')
        leader_task_group.to_excel(writer, index=False, sheet_name='Leader_Task')
        team_comp_group.to_excel(writer, index=False, sheet_name='Team_Composition')
        opportunities_df.to_excel(writer, index=False, sheet_name='Opportunities')
        maintenance_df.to_excel(writer, index=False, sheet_name='Maintenance_Hotspots')
        detail_df.to_excel(writer, index=False, sheet_name='Detail')

    insights_buffer.seek(0)
    st.download_button(
        label=f"Download {month_label} Insights (XLSX)",
        data=insights_buffer.getvalue(),
        file_name=f"monthly_insights_{month_label}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def show_ml_module():
    """Display the Machine Learning module"""
    render_ml_module()

def show_optimization_page(euvg, unified_view):
    """Display production optimization insights"""
    st.header("🎯 Production Optimization")
    
    # Material transition analysis
    st.subheader("Material Transition Costs")
    
    # Find material transitions
    if 'material_transition' in unified_view.columns:
        transitions = unified_view[unified_view['material_transition'] == 1]
        
        if len(transitions) > 0 and 'setup_energy' in transitions.columns:
            transition_energy = transitions.groupby('material_code')['setup_energy'].mean()
            
            if len(transition_energy) > 0:
                fig = px.bar(
                    transition_energy.sort_values(ascending=False).head(10).reset_index(),
                    x='material_code',
                    y='setup_energy',
                    title="Average Setup Energy by Material"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Schedule optimization demo
    st.subheader("Intelligent Scheduling")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("""
        The intelligent scheduler optimizes production sequences to:
        - Minimize material transitions
        - Reduce setup times
        - Maximize machine utilization
        - Balance workload across teams
        """)
    
    with col2:
        if st.button("Generate Optimized Schedule", type="primary"):
            # Mock pending orders
            pending_orders = [
                {'order_id': 'J250001', 'material_code': 'MAT001', 'quantity': 1000},
                {'order_id': 'J250002', 'material_code': 'MAT002', 'quantity': 1500},
                {'order_id': 'J250003', 'material_code': 'MAT001', 'quantity': 800},
                {'order_id': 'J250004', 'material_code': 'MAT003', 'quantity': 1200},
                {'order_id': 'J250005', 'material_code': 'MAT002', 'quantity': 900},
            ]
            
            if hasattr(euvg, 'scheduler'):
                optimized = euvg.scheduler.optimize_production_sequence(pending_orders)
                
                st.success("✅ Optimized sequence minimizes material transitions!")
                
                # Display optimized sequence
                st.subheader("Optimized Production Sequence")
                
                opt_df = pd.DataFrame(optimized)
                opt_df['Sequence'] = range(1, len(opt_df) + 1)
                
                st.dataframe(
                    opt_df[['Sequence', 'order_id', 'material_code', 'quantity']], 
                    use_container_width=True
                )
                
                # Calculate actual savings based on optimization
                st.subheader("Estimated Savings")
                
                # Calculate actual transitions from the optimized sequence
                original_transitions = len(set([order['material_code'] for order in pending_orders])) - 1
                optimized_transitions = 0
                prev_material = None
                for order in optimized:
                    if prev_material and order['material_code'] != prev_material:
                        optimized_transitions += 1
                    prev_material = order['material_code']
                
                # Calculate energy savings based on actual transition reduction
                avg_setup_energy = 50  # kWh per transition (should be from actual data)
                energy_saved = (original_transitions - optimized_transitions) * avg_setup_energy
                
                col1, col2 = st.columns(2)
                with col1:
                    reduction_pct = ((original_transitions - optimized_transitions) / original_transitions * 100) if original_transitions > 0 else 0
                    st.metric("Reduced Transitions", 
                             f"{original_transitions} → {optimized_transitions}", 
                             f"-{reduction_pct:.0f}%")
                with col2:
                    energy_pct = (energy_saved / (original_transitions * avg_setup_energy) * 100) if original_transitions > 0 else 0
                    st.metric("Energy Saved", 
                             f"{energy_saved:.0f} kWh", 
                             f"-{energy_pct:.0f}%")

# Note: prepare_ml_data function is imported from core.utils to avoid duplication

# Page routing
if page == "🔄 ETL Pipeline":
    render_etl_upload_page()
elif page == "📊 Unified View":
    show_unified_view_page()
elif page == "⚡ Energy Analysis":
    if unified_view is not None:
        show_energy_analysis_page(unified_view, euvg)
    else:
        st.warning("Please process data through ETL Pipeline first, then use Unified View to generate the dataset.")
elif page == "🔧 Maintenance":
    render_maintenance_page()
elif page == "🤖 Machine Learning":
    show_ml_module()
elif page == "🎯 Optimization":
    # Use the new optimization module which includes predictions, insights, and recommendations
    try:
        render_optimization_module()
    except Exception as exc:
        st.error(f"Optimization module unavailable: {exc}")
        # Fallback to simplified optimization derived from unified view
        try:
            if unified_view is not None and euvg is not None:
                st.info("Showing simplified optimization view as fallback.")
                show_optimization_page(euvg, unified_view)
            else:
                st.warning("Please process data through ETL Pipeline first to enable optimization insights.")
        except Exception as inner_exc:
            st.error(f"Fallback optimization failed: {inner_exc}")
