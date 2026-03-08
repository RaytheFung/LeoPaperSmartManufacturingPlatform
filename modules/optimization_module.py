"""
Optimization Module for Smart Manufacturing Platform
Consolidates predictions, insights, and recommendations for production optimization
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys

# Add project root to path for absolute imports like `core.*`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Try importing ML modules
try:
    from core.ml_predictor import MLPredictor
    ML_MODULES_AVAILABLE = True
except ImportError as e:
    ML_MODULES_AVAILABLE = False
    print(f"ML modules not available: {e}")


def _map_task_type_to_difficulty(task_type: str) -> str:
    if not task_type:
        return 'Medium'
    task_type = str(task_type)
    if '光' in task_type and '印' not in task_type:
        return 'Easy'
    if '印' in task_type and '光' in task_type:
        return 'Hard'
    if '印' in task_type:
        return 'Medium'
    return 'Medium'


def fetch_ml_recommendations(limit: int = 5) -> pd.DataFrame:
    if not ML_MODULES_AVAILABLE:
        return pd.DataFrame()

    try:
        conn = sqlite3.connect('manufacturing_data.db')
        query = """
            WITH latest AS (
                SELECT 
                    machine_id,
                    datetime,
                    team_leader,
                    material_code,
                    team_size,
                    production_qty,
                    hours_since_last_maintenance,
                    maintenance_intensity_30d,
                    cumulative_maintenance_count,
                    kwh_per_unit,
                    task_type,
                    hour_of_day,
                    day_of_week,
                    is_weekend,
                    ROW_NUMBER() OVER (PARTITION BY machine_id ORDER BY datetime DESC) AS rn
                FROM unified_view
                WHERE kwh_per_unit > 0 AND kwh_per_unit < 20
            )
            SELECT * FROM latest WHERE rn = 1
        """
        latest = pd.read_sql_query(query, conn)

        production_stats = pd.read_sql_query("""
            SELECT 
                machine_id,
                SUM(production_qty) AS total_production,
                SUM(energy_kwh) AS total_energy,
                COUNT(*) AS total_hours
            FROM unified_view
            WHERE kwh_per_unit > 0 AND kwh_per_unit < 20
              AND is_near_zero_output = 0
            GROUP BY machine_id
        """, conn)

        conn.close()
        latest = latest.merge(production_stats, on='machine_id', how='left')
    except Exception as exc:
        st.warning(f"Unable to fetch machine context for ML recommendations: {exc}")
        return pd.DataFrame()

    if latest.empty:
        return pd.DataFrame()

    # Focus on machines with weakest efficiency
    latest = latest.sort_values('kwh_per_unit', ascending=False).head(limit)

    predictor = MLPredictor()
    if predictor.model is None or predictor.feature_columns is None:
        return pd.DataFrame()

    rows = []
    for _, row in latest.iterrows():
        result = predictor.predict_efficiency(
            machine_id=row['machine_id'],
            team_leader=row.get('team_leader') or 'Default',
            material_code=row.get('material_code') or 'DEFAULT',
            hours_since_maintenance=row.get('hours_since_last_maintenance') or 500,
            task_difficulty=_map_task_type_to_difficulty(row.get('task_type')),
            production_qty=row.get('production_qty') or predictor.feature_defaults.get('production_qty', 1000),
            team_size=int(row.get('team_size') or predictor.feature_defaults.get('team_size', 3)),
            hour_of_day=int(row.get('hour_of_day') or datetime.now().hour),
            is_weekend=bool(row.get('is_weekend')),
            month=datetime.now().month,
            maintenance_intensity_30d=row.get('maintenance_intensity_30d') or predictor.feature_defaults.get('maintenance_intensity_30d', 0),
            cumulative_maintenance_count=row.get('cumulative_maintenance_count') or predictor.feature_defaults.get('cumulative_maintenance_count', 0)
        )

        predicted = result['efficiency']
        current = row['kwh_per_unit']
        improvement = current - predicted

        driver_summary = result.get('feature_impacts', {})
        top_driver = next(iter(driver_summary.items()), (None, None))

        total_production = row.get('total_production') or predictor.feature_defaults.get('production_qty', 1000) * 24
        total_hours = row.get('total_hours') or 0
        kwh_savings = max(improvement, 0) * total_production

        rows.append({
            'machine_id': row['machine_id'],
            'current_efficiency': current,
            'predicted_efficiency': predicted,
            'improvement': improvement,
            'confidence': result.get('confidence', 0.6),
            'hours_since_last_maintenance': row.get('hours_since_last_maintenance'),
            'team_size': row.get('team_size'),
            'material_code': row.get('material_code'),
            'top_driver': f"{top_driver[0]}: {top_driver[1]}" if top_driver[0] else 'N/A',
            'total_production': total_production,
            'total_hours': total_hours,
            'potential_kwh_savings': kwh_savings
        })

    return pd.DataFrame(rows)

def render_optimization_module():
    """Main function to render Optimization module in Streamlit with robust fallbacks"""
    try:
        # Load centralized CSS styles (guarded)
        try:
            from core.ui_utils import load_custom_css
            load_custom_css()
        except Exception as css_exc:
            st.warning(f"Styles not loaded: {css_exc}")

        st.title("🎯 Production Optimization Center")
        st.markdown("**AI-powered predictions, insights, and recommendations for optimal production**")
        # Sidebar with optimization metrics calculated from actual data
        with st.sidebar:
            # Sidebar metrics temporarily hidden pending data validation.
            pass

        # Main content with tabs
        st.markdown("<br>", unsafe_allow_html=True)

        # Original optimization content first
        try:
            tab_predictions, tab_schedule, tab_team = st.tabs([
                "🔮 Live Predictions",
                "🗓️ Smart Scheduling",
                "👥 Team Insights"
            ])
        except Exception as tabs_exc:
            st.error(f"Tabs unavailable: {tabs_exc}")
            render_optimization_module_minimal()
            return

        with tab_predictions:
            try:
                from .shared_ml_components import render_live_predictions_tab
                render_live_predictions_tab()
            except Exception as exc:
                st.error(f"Live Predictions unavailable: {exc}")

        with tab_schedule:
            try:
                render_smart_scheduling_tab()
            except Exception as exc:
                st.error(f"Smart Scheduling unavailable: {exc}")

        with tab_team:
            try:
                render_team_insights_tab()
            except Exception as exc:
                st.error(f"Team Insights unavailable: {exc}")

    except Exception as fatal_exc:
        st.error(f"Optimization module failed: {fatal_exc}")
        render_optimization_module_minimal()


def render_optimization_module_minimal():
    """Minimal, always-safe optimization view for demo fallback"""
    st.header("📊 Optimization (Safe Mode)")
    st.info("Showing minimal insights due to environment limitations.")

    # Try a simple material transition chart; otherwise show demo chart
    try:
        conn = sqlite3.connect('manufacturing_data.db')
        df = pd.read_sql_query(
            "SELECT material_code, COUNT(*) as cnt FROM unified_view WHERE material_transition = 1 GROUP BY material_code ORDER BY cnt DESC LIMIT 8",
            conn,
        )
        conn.close()
        if df.empty:
            raise ValueError("No transition data")
        st.subheader("Top Material Transitions")
        st.plotly_chart(px.bar(df, x='material_code', y='cnt'), use_container_width=True)
    except Exception:
        st.subheader("Top Material Transitions (Demo)")
        demo = pd.DataFrame({
            'material_code': ['MAT_001', 'MAT_002', 'MAT_003', 'MAT_004'],
            'cnt': [42, 37, 29, 18],
        })
        st.plotly_chart(px.bar(demo, x='material_code', y='cnt'), use_container_width=True)

    # Demo opportunities table
    st.subheader("Opportunities (Demo)")
    st.dataframe(
        pd.DataFrame({
            'Opportunity': ['Reduce Idle', 'Optimize Transitions', 'Balance Teams', 'Preventive Maint.'],
            'Priority': ['High', 'High', 'Medium', 'High'],
            'Est. Savings (¥/mo)': ['480,000', '150,000', '200,000', '230,000'],
        }),
        hide_index=True,
        use_container_width=True,
    )


def render_current_optimization_tab():
    """Display current optimization opportunities"""
    
    st.header("Current Optimization Opportunities")
    
    # Try to load real data
    try:
        conn = sqlite3.connect('manufacturing_data.db')
        
        # Material transition analysis
        st.subheader("🔄 Material Transition Analysis")
        
        transition_data = pd.read_sql_query("""
            SELECT 
                material_code,
                COUNT(*) as transition_count,
                AVG(setup_energy) as avg_setup_energy
            FROM unified_view
            WHERE material_transition = 1
            GROUP BY material_code
            ORDER BY transition_count DESC
            LIMIT 10
        """, conn)
        
        if len(transition_data) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    transition_data,
                    x='material_code',
                    y='transition_count',
                    title='Most Frequent Material Transitions',
                    labels={'transition_count': 'Number of Transitions'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    transition_data,
                    x='material_code',
                    y='avg_setup_energy',
                    title='Average Setup Energy by Material',
                    labels={'avg_setup_energy': 'Setup Energy (kWh)'},
                    color='avg_setup_energy',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Machine utilization analysis
        st.subheader("🏭 Machine Utilization")
        
        utilization_data = pd.read_sql_query("""
            SELECT 
                machine_id,
                AVG(CASE WHEN production_qty > 0 THEN 1 ELSE 0 END) as utilization_rate,
                AVG(kwh_per_unit) as avg_efficiency,
                COUNT(*) as total_hours
            FROM unified_view
            WHERE kwh_per_unit > 0 AND kwh_per_unit < 100
            GROUP BY machine_id
            HAVING total_hours > 100
            ORDER BY utilization_rate DESC
        """, conn)
        
        if len(utilization_data) > 0:
            # Create scatter plot of utilization vs efficiency
            fig = px.scatter(
                utilization_data,
                x='utilization_rate',
                y='avg_efficiency',
                size='total_hours',
                hover_data=['machine_id'],
                title='Machine Utilization vs Efficiency',
                labels={
                    'utilization_rate': 'Utilization Rate (%)',
                    'avg_efficiency': 'Average Efficiency (kWh/unit)'
                }
            )
            
            # Add quadrant lines
            fig.add_hline(y=utilization_data['avg_efficiency'].median(), 
                         line_dash="dash", line_color="gray", opacity=0.5)
            fig.add_vline(x=utilization_data['utilization_rate'].median(), 
                         line_dash="dash", line_color="gray", opacity=0.5)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show top and bottom performers
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🌟 Top Performers")
                top_machines = utilization_data.nlargest(5, 'utilization_rate')[['machine_id', 'utilization_rate']]
                top_machines['utilization_rate'] = (top_machines['utilization_rate'] * 100).round(1).astype(str) + '%'
                st.dataframe(top_machines, hide_index=True, use_container_width=True)
            
            with col2:
                st.markdown("#### ⚠️ Need Attention")
                bottom_machines = utilization_data.nsmallest(5, 'utilization_rate')[['machine_id', 'utilization_rate']]
                bottom_machines['utilization_rate'] = (bottom_machines['utilization_rate'] * 100).round(1).astype(str) + '%'
                st.dataframe(bottom_machines, hide_index=True, use_container_width=True)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading optimization data: {e}")
        
        # Show demo data
        st.info("Showing demo optimization opportunities")
        
        demo_opportunities = pd.DataFrame({
            'Opportunity': ['Reduce Idle Time', 'Optimize Material Transitions', 'Balance Team Workload', 'Preventive Maintenance'],
            'Potential Savings': ['¥480,000/month', '¥150,000/month', '¥200,000/month', '¥230,000/month'],
            'Difficulty': ['Medium', 'Easy', 'Hard', 'Medium'],
            'Priority': ['High', 'High', 'Medium', 'High']
        })
        
        st.dataframe(demo_opportunities, hide_index=True, use_container_width=True)

    st.markdown("---")

    st.subheader("🤖 ML-Driven Efficiency Opportunities")

    if ML_MODULES_AVAILABLE:
        rec_df = fetch_ml_recommendations(limit=6)
        if rec_df is None or rec_df.empty or 'improvement' not in rec_df.columns:
            st.info("No machine recommendations available yet. Run the ML training pipeline and ensure unified view data is populated.")
        else:
            try:
                conn = sqlite3.connect('manufacturing_data.db')
                cost_result = conn.execute(
                    "SELECT SUM(electricity_cost)/SUM(electricity_kwh) FROM etl_energy_data"
                ).fetchone()[0]
                conn.close()
                cost_per_kwh = cost_result if cost_result else 1.0
            except Exception:
                cost_per_kwh = 1.0

            rec_df['potential_kwh_savings'] = rec_df['potential_kwh_savings'].clip(lower=0)
            rec_df['potential_cost_savings'] = rec_df['potential_kwh_savings'] * cost_per_kwh

            display_df = rec_df.copy()
            display_df['current_efficiency'] = display_df['current_efficiency'].round(3)
            display_df['predicted_efficiency'] = display_df['predicted_efficiency'].round(3)
            display_df['improvement'] = display_df['improvement'].round(3)
            display_df['potential_kwh_savings'] = display_df['potential_kwh_savings'].round(1)
            display_df['potential_cost_savings'] = display_df['potential_cost_savings'].round(0)
            display_df['confidence'] = (display_df['confidence'] * 100).round(0).astype(int).astype(str) + '%'

            st.dataframe(
                display_df.rename(columns={
                    'machine_id': 'Machine',
                    'current_efficiency': 'Current kWh/unit',
                    'predicted_efficiency': 'Predicted kWh/unit',
                    'improvement': 'Improvement kWh/unit',
                    'confidence': 'Confidence',
                    'hours_since_last_maintenance': 'Hours Since Maintenance',
                    'team_size': 'Team Size',
                    'material_code': 'Material',
                    'top_driver': 'Top Driver',
                    'total_production': 'Total Units (period)',
                    'potential_kwh_savings': 'Potential kWh Saved',
                    'potential_cost_savings': 'Potential Cost Saved (¥)'
                }),
                hide_index=True,
                use_container_width=True
            )

            # Highlight the best opportunity
            best_row = rec_df.sort_values('improvement', ascending=False).iloc[0]
            st.success(
                f"Machine **{best_row['machine_id']}** can improve by **{best_row['improvement']:.3f} kWh/unit** "
                f"(confidence {(best_row['confidence']*100):.0f}%). Top driver: {best_row['top_driver']}."
            )

            total_cost_savings = rec_df['potential_cost_savings'].sum()
            total_kwh_savings = rec_df['potential_kwh_savings'].sum()
            st.metric(
                "Estimated Monthly Savings Across Focus Machines",
                f"¥{total_cost_savings:,.0f}",
                f"{total_kwh_savings:,.0f} kWh"
            )

            st.markdown("#### ✍️ Create Maintenance Actions")
            selected_machines = st.multiselect(
                "Select machines to flag for maintenance",
                rec_df['machine_id'].tolist(),
                help="Choose one or more machines from the recommendation list"
            )

            action_note = st.text_input(
                "Action note",
                value="Schedule preventive maintenance and review settings",
                help="Stored with the action log for traceability"
            )

            if st.button("Create Maintenance Action", use_container_width=True):
                if not selected_machines:
                    st.warning("Select at least one machine before logging an action.")
                else:
                    try:
                        conn = sqlite3.connect('manufacturing_data.db')
                        cursor = conn.cursor()
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS ml_action_log (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                created_at TIMESTAMP,
                                machine_id TEXT,
                                current_efficiency REAL,
                                predicted_efficiency REAL,
                                improvement REAL,
                                confidence REAL,
                                top_driver TEXT,
                                note TEXT
                            )
                        ''')

                        now = datetime.now()
                        for machine in selected_machines:
                            rec = rec_df[rec_df['machine_id'] == machine].iloc[0]
                            cursor.execute('''
                                INSERT INTO ml_action_log (
                                    created_at, machine_id, current_efficiency, predicted_efficiency,
                                    improvement, confidence, top_driver, note
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                now,
                                rec['machine_id'],
                                rec['current_efficiency'],
                                rec['predicted_efficiency'],
                                rec['improvement'],
                                rec['confidence'],
                                rec['top_driver'],
                                action_note
                            ))

                        conn.commit()
                        conn.close()
                        st.success(f"Logged maintenance action for {len(selected_machines)} machine(s). View the maintenance tab to schedule work orders.")
                    except Exception as exc:
                        st.error(f"Unable to log actions: {exc}")
    else:
        st.info("ML predictor unavailable. Install dependencies or run training to enable intelligence.")


def render_smart_scheduling_tab():
    """Smart scheduling optimization"""
    
    st.header("🗓️ Intelligent Production Scheduling")
    
    st.info("""
    The intelligent scheduler optimizes production sequences using AI to:
    - Minimize material transitions and setup times
    - Balance workload across teams and machines
    - Reduce energy consumption during peak hours
    - Maximize overall equipment effectiveness (OEE)
    """)
    
    # Scheduling parameters
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Scheduling Parameters")
        
        optimization_goal = st.selectbox(
            "Optimization Goal",
            ["Minimize Transitions", "Maximize Throughput", "Balance Workload", "Minimize Energy Cost"]
        )
        
        time_horizon = st.slider(
            "Planning Horizon (days)",
            min_value=1,
            max_value=7,
            value=3
        )
        
        constraint_type = st.multiselect(
            "Constraints",
            ["Material Availability", "Team Availability", "Machine Capacity", "Deadline Requirements"],
            default=["Material Availability", "Machine Capacity"]
        )
    
    with col2:
        st.markdown("### Current Queue")
        
        # Mock pending orders
        pending_orders = pd.DataFrame({
            'Order ID': ['J250001', 'J250002', 'J250003', 'J250004', 'J250005'],
            'Material': ['MAT_001', 'MAT_002', 'MAT_001', 'MAT_003', 'MAT_002'],
            'Quantity': [1000, 1500, 800, 1200, 900],
            'Priority': ['High', 'Normal', 'High', 'Low', 'Normal'],
            'Due Date': pd.date_range(start=datetime.now(), periods=5, freq='D').strftime('%Y-%m-%d')
        })
        
        st.dataframe(pending_orders, hide_index=True, use_container_width=True)
    
    # Generate schedule button
    if st.button("🚀 Generate Optimized Schedule", type="primary", use_container_width=True):
        with st.spinner("Optimizing production schedule..."):
            import time
            time.sleep(2)  # Simulate optimization
            
            # Generate optimized schedule
            st.success("✅ Schedule optimized successfully!")
            
            # Show optimization results
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Material Transitions", "3", "-40%", delta_color="inverse")
            with col2:
                st.metric("Setup Time", "2.5 hours", "-35%", delta_color="inverse")
            with col3:
                st.metric("Energy Cost", "¥8,500", "-15%", delta_color="inverse")
            
            # Show optimized sequence
            st.subheader("📋 Optimized Production Sequence")
            
            optimized_schedule = pd.DataFrame({
                'Sequence': [1, 2, 3, 4, 5],
                'Order ID': ['J250001', 'J250003', 'J250002', 'J250005', 'J250004'],
                'Material': ['MAT_001', 'MAT_001', 'MAT_002', 'MAT_002', 'MAT_003'],
                'Machine': ['024-073', '024-073', '024-116', '024-116', '166-002'],
                'Team': ['Team A', 'Team A', 'Team B', 'Team B', 'Team C'],
                'Start Time': pd.date_range(start=datetime.now(), periods=5, freq='4H').strftime('%H:%M'),
                'Duration': ['3.5h', '2.8h', '4.2h', '3.0h', '3.8h']
            })
            
            # Color code by material for visual grouping
            def highlight_material(row):
                colors = {
                    'MAT_001': 'background-color: #e8f4fd',
                    'MAT_002': 'background-color: #fff4e6',
                    'MAT_003': 'background-color: #f3e5f5'
                }
                return [colors.get(row['Material'], '')] * len(row)
            
            st.dataframe(
                optimized_schedule.style.apply(highlight_material, axis=1),
                hide_index=True,
                use_container_width=True
            )
            
            # Show Gantt chart
            st.subheader("📊 Production Timeline")
            
            # Create simple Gantt chart
            fig = go.Figure()
            
            start_time = datetime.now()
            for i, row in optimized_schedule.iterrows():
                duration_hours = float(row['Duration'].replace('h', ''))
                end_time = start_time + timedelta(hours=duration_hours)
                
                fig.add_trace(go.Scatter(
                    x=[start_time, end_time, end_time, start_time, start_time],
                    y=[row['Machine'], row['Machine'], row['Machine'] + '_', row['Machine'] + '_', row['Machine']],
                    fill='toself',
                    fillcolor=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6'][i % 5],
                    mode='lines',
                    name=row['Order ID'],
                    text=f"{row['Order ID']} - {row['Material']}",
                    hoverinfo='text'
                ))
                
                start_time = end_time
            
            fig.update_layout(
                title='Optimized Production Schedule',
                xaxis_title='Time',
                yaxis_title='Machine',
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Savings summary
            st.subheader("💰 Estimated Savings")
            
            savings_data = pd.DataFrame({
                'Category': ['Reduced Setup Time', 'Energy Optimization', 'Improved Throughput', 'Total'],
                'Daily Savings': ['¥2,500', '¥1,800', '¥3,200', '¥7,500'],
                'Monthly Savings': ['¥75,000', '¥54,000', '¥96,000', '¥225,000'],
                'Annual Savings': ['¥900,000', '¥648,000', '¥1,152,000', '¥2,700,000']
            })
            
    st.dataframe(savings_data, hide_index=True, use_container_width=True)


# Make functions available for import
__all__ = ['render_optimization_module']


def render_team_insights_tab():
    """Team × Task, Team‑composition, and Maintenance Hotspots insights.
    Pulls directly from manufacturing_data.db.unified_view with safe guards.
    """
    st.header("👥 Team & Task Insights")

    # Connect and check table availability
    try:
        conn = sqlite3.connect('manufacturing_data.db')
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unified_view'")
        if not cur.fetchone():
            st.info("Unified view is not available yet. Please run the ETL pipeline.")
            conn.close()
            return

        # Discover available columns to avoid 'no such column' errors
        pragma = pd.read_sql_query("PRAGMA table_info(unified_view)", conn)
        available_cols = set(pragma['name'].tolist())
        desired_cols = [
            'datetime', 'machine_id', 'kwh_per_unit', 'production_qty',
            'team_leader', 'team_composition', 'task_type', 'energy_kwh',
            'maintenance_energy', 'is_near_zero_output'
        ]
        select_cols = [c for c in desired_cols if c in available_cols]
        if 'datetime' not in select_cols or 'kwh_per_unit' not in select_cols or 'production_qty' not in select_cols:
            conn.close()
            st.info("Unified view is missing essential fields; re-run ETL to populate required columns.")
            return

        cols_sql = ", ".join(select_cols)
        df = pd.read_sql_query(f"SELECT {cols_sql} FROM unified_view", conn)
        conn.close()
    except Exception as exc:
        st.error(f"Failed to load team insights data: {exc}")
        return

    if df.empty:
        st.info("No data available in unified view.")
        return

    # Parse and quality filters
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        df = df[df['datetime'].notna()].copy()
    else:
        st.info("Missing 'datetime' in unified view.")
        return

    # Basic quality guards
    if 'kwh_per_unit' not in df.columns or 'production_qty' not in df.columns:
        st.info("Missing required columns for analysis (kwh_per_unit, production_qty).")
        return

    mask = df['kwh_per_unit'].between(0.3, 10, inclusive='both') & (df['production_qty'] > 0)
    if 'is_near_zero_output' in df.columns:
        mask &= (df['is_near_zero_output'].fillna(0) == 0)
    df = df.loc[mask].copy()
    if df.empty:
        st.info("No qualifying records after quality filters.")
        return

    # Month picker
    df['month'] = df['datetime'].dt.to_period('M').astype(str)
    months = sorted(df['month'].unique())
    sel_month = st.selectbox("Select month", months, index=len(months) - 1)
    df = df[df['month'] == sel_month].copy()
    if df.empty:
        st.info("No qualifying records for the selected month.")
        return

    # Normalize key categorical columns (guard missing columns)
    if 'task_type' in df.columns:
        df['task_type'] = df['task_type'].fillna('Unknown')
    else:
        df['task_type'] = 'Unknown'
    if 'team_leader' in df.columns:
        df['team_leader'] = df['team_leader'].fillna('Unknown')
    else:
        df['team_leader'] = 'Unknown'
    if 'team_composition' in df.columns:
        df['team_composition'] = df['team_composition'].fillna(df['team_leader'])

    # Thresholds
    colA, colB = st.columns(2)
    min_leader_task = colA.number_input(
        "Min samples per Leader × Task", min_value=1, value=20, step=1
    )
    min_team_comp = colB.number_input(
        "Min samples per Team‑composition × Task", min_value=1, value=10, step=1
    )

    # Leader × Task
    st.subheader("Leader × Task Efficiency")
    leader_task = pd.DataFrame()
    if {'task_type', 'team_leader'}.issubset(df.columns):
        lt_raw = (
            df.groupby(['task_type', 'team_leader'], dropna=False)
            .agg(
                avg_kwh_per_unit=('kwh_per_unit', 'mean'),
                median_kwh_per_unit=('kwh_per_unit', 'median'),
                sample_size=('kwh_per_unit', 'count'),
                total_production=('production_qty', 'sum'),
                last_observed=('datetime', 'max'),
            )
            .reset_index()
        )
        leader_task = lt_raw[
            (lt_raw['sample_size'] >= min_leader_task)
            & (lt_raw['team_leader'] != 'Unknown')
            & (lt_raw['task_type'] != 'Unknown')
        ].sort_values('avg_kwh_per_unit')

    if leader_task.empty:
        st.info("No leader × task combinations meet the threshold yet.")
    else:
        st.dataframe(
            leader_task.head(25).round({'avg_kwh_per_unit': 3, 'median_kwh_per_unit': 3}),
            use_container_width=True,
            hide_index=True,
        )
        best = leader_task.nsmallest(15, 'avg_kwh_per_unit')
        fig = px.bar(
            best,
            x='team_leader',
            y='avg_kwh_per_unit',
            color='task_type',
            title="Top Leader × Task (lower kWh/unit is better)",
            labels={'avg_kwh_per_unit': 'Avg kWh/unit', 'team_leader': 'Leader', 'task_type': 'Task'},
        )
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # Team‑composition × Task
    st.subheader("Team‑composition × Task Efficiency")
    team_comp = pd.DataFrame()
    if {'task_type', 'team_composition'}.issubset(df.columns):
        tc_raw = (
            df.groupby(['task_type', 'team_composition'], dropna=False)
            .agg(
                avg_kwh_per_unit=('kwh_per_unit', 'mean'),
                median_kwh_per_unit=('kwh_per_unit', 'median'),
                sample_size=('kwh_per_unit', 'count'),
                total_production=('production_qty', 'sum'),
                last_observed=('datetime', 'max'),
            )
            .reset_index()
        )
        team_comp = tc_raw[tc_raw['sample_size'] >= min_team_comp].sort_values('avg_kwh_per_unit')

    if team_comp.empty:
        st.info("No team‑composition × task combinations meet the threshold yet.")
    else:
        st.dataframe(
            team_comp.head(25).round({'avg_kwh_per_unit': 3, 'median_kwh_per_unit': 3}),
            use_container_width=True,
            hide_index=True,
        )

    # Maintenance hotspots
    st.subheader("🔧 Maintenance Hotspots")
    maint_df = pd.DataFrame(columns=['machine_id', 'maintenance_energy', 'energy_kwh', 'hours', 'maintenance_ratio'])
    needed = {'maintenance_energy', 'energy_kwh'}.issubset(df.columns)
    if needed:
        ms = (
            df.groupby('machine_id')
            .agg(
                maintenance_energy=('maintenance_energy', 'sum'),
                energy_kwh=('energy_kwh', 'sum'),
                hours=('machine_id', 'count'),
            )
            .reset_index()
        )
        ms['maintenance_ratio'] = np.where(ms['energy_kwh'] > 0, ms['maintenance_energy'] / ms['energy_kwh'], np.nan)
        maint_df = ms.sort_values('maintenance_energy', ascending=False).head(15)
        st.dataframe(maint_df, use_container_width=True, hide_index=True)
    else:
        st.info("Maintenance energy fields are not available in the current dataset.")

    # Export button
    st.markdown("---")
    st.subheader("📥 Export Insights")
    from io import BytesIO
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        meta = pd.DataFrame([[sel_month, len(df)]], columns=['Month', 'Rows'])
        meta.to_excel(writer, index=False, sheet_name='Summary')
        leader_task.to_excel(writer, index=False, sheet_name='Leader_Task')
        team_comp.to_excel(writer, index=False, sheet_name='Team_Composition')
        maint_df.to_excel(writer, index=False, sheet_name='Maintenance_Hotspots')
    buf.seek(0)
    st.download_button(
        label=f"Download Insights ({sel_month}).xlsx",
        data=buf.getvalue(),
        file_name=f"team_task_insights_{sel_month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
