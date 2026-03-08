"""
Maintenance Module - Predictive Maintenance Analytics UI
Integrates maintenance records with production data for risk predictions
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from pathlib import Path

# Import the maintenance integration module
import sys
sys.path.append(str(Path(__file__).parent.parent))
from core.maintenance_integration import MaintenanceDataIntegration, integrate_maintenance_with_etl

def render_maintenance_page():
    """Main function to render the Predictive Maintenance page"""
    st.header("🔧 Predictive Maintenance Analytics")
    
    # Initialize
    maint = MaintenanceDataIntegration()
    conn = sqlite3.connect('manufacturing_data.db')
    
    # Load predictions if exist
    try:
        # Check if maintenance tables exist
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='maintenance_ml_features'
        """)
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Load predictions
            predictions = pd.read_sql_query("""
                SELECT m.*, ms.total_maintenance_events, ms.mtbf_hours
                FROM maintenance_ml_features m
                LEFT JOIN maintenance_summary ms ON m.machine_id = ms.machine_id
                ORDER BY m.failure_risk_score DESC
            """, conn)
            
            if not predictions.empty:
                # Risk distribution metrics
                st.markdown("### 📊 Risk Distribution Overview")
                col1, col2, col3, col4 = st.columns(4)
                
                high_risk = len(predictions[predictions['failure_risk_score'] > 60])
                med_risk = len(predictions[(predictions['failure_risk_score'] > 30) & 
                                          (predictions['failure_risk_score'] <= 60)])
                low_risk = len(predictions[predictions['failure_risk_score'] <= 30])
                total_machines = len(predictions)
                
                col1.metric("🔴 High Risk", high_risk, f"{high_risk/total_machines*100:.1f}%")
                col2.metric("🟡 Medium Risk", med_risk, f"{med_risk/total_machines*100:.1f}%")
                col3.metric("🟢 Low Risk", low_risk, f"{low_risk/total_machines*100:.1f}%")
                col4.metric("📊 Total Monitored", total_machines)
                
                # High-risk machines detail
                st.markdown("### ⚠️ Machines Requiring Immediate Attention")
                high_risk_df = predictions[predictions['failure_risk_score'] > 60].head(10)
                
                if not high_risk_df.empty:
                    for idx, machine in high_risk_df.iterrows():
                        risk_color = "🔴" if machine['failure_risk_score'] > 80 else "🟠"
                        with st.expander(f"{risk_color} Machine {machine['machine_id']} - Risk Score: {machine['failure_risk_score']:.0f}%"):
                            col1, col2, col3 = st.columns(3)
                            
                            col1.metric("Days Since Maintenance", 
                                       f"{machine.get('days_since_last_maintenance', 'N/A')}")
                            col2.metric("Production Since Maintenance", 
                                       f"{machine.get('units_produced_since_maintenance', 0):.0f} units")
                            col3.metric("Energy Since Maintenance", 
                                       f"{machine.get('energy_consumed_since_maintenance', 0):.0f} kWh")
                            
                            # Recommendation
                            st.info(f"**Recommended Action**: {machine.get('recommended_action', 'Schedule inspection')}")
                            
                            # MTBF if available
                            if pd.notna(machine.get('mtbf_hours')):
                                st.caption(f"Mean Time Between Failures: {machine['mtbf_hours']:.0f} hours")
                
                # Maintenance pattern analysis
                st.markdown("### 📈 Maintenance Pattern Analysis")
                
                # Get work order distribution
                work_orders = pd.read_sql_query("""
                    SELECT work_order_type, COUNT(*) as count
                    FROM maintenance_records
                    GROUP BY work_order_type
                """, conn)
                
                if not work_orders.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Pie chart of maintenance types
                        fig = px.pie(work_orders, values='count', names='work_order_type',
                                   title='Maintenance Type Distribution',
                                   color_discrete_map={
                                       'PM': '#2ecc71',  # Green - Preventive
                                       'AM': '#e74c3c',  # Red - After failure
                                       'CM': '#f39c12',  # Orange - Corrective
                                       'EM': '#c0392b'   # Dark Red - Emergency
                                   })
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Calculate optimization metrics
                        total = work_orders['count'].sum()
                        reactive = work_orders[work_orders['work_order_type'].isin(['AM', 'CM', 'EM'])]['count'].sum()
                        preventive = work_orders[work_orders['work_order_type'] == 'PM']['count'].sum() if 'PM' in work_orders['work_order_type'].values else 0
                        reactive_pct = (reactive / total * 100) if total > 0 else 0
                        
                        st.markdown("#### 💡 Optimization Opportunity")
                        st.metric("Current Reactive Rate", f"{reactive_pct:.1f}%", 
                                 f"-{reactive_pct - 40:.1f}% vs target" if reactive_pct > 40 else "✅ At target")
                        
                        # Savings calculation
                        if reactive_pct > 40:
                            potential_reduction = reactive_pct - 40
                            monthly_savings = potential_reduction * 1000  # $1000 per percentage point
                            annual_savings = monthly_savings * 12
                            
                            st.success(f"""
                            **Potential Savings:**
                            - Monthly: ${monthly_savings:,.0f}
                            - Annual: ${annual_savings:,.0f}
                            - Strategy: Increase PM frequency for high-risk machines
                            """)
                
                # Machine reliability trends
                st.markdown("### 🔄 Machine Reliability Trends")
                
                # Get monthly maintenance trends
                monthly_trends = pd.read_sql_query("""
                    SELECT 
                        strftime('%Y-%m', transaction_date) as month,
                        work_order_type,
                        COUNT(*) as count
                    FROM maintenance_records
                    WHERE transaction_date IS NOT NULL
                    GROUP BY month, work_order_type
                    ORDER BY month
                """, conn)
                
                if not monthly_trends.empty:
                    # Pivot for stacked bar chart
                    trends_pivot = monthly_trends.pivot(index='month', columns='work_order_type', values='count').fillna(0)
                    
                    fig = go.Figure()
                    colors = {'PM': '#2ecc71', 'AM': '#e74c3c', 'CM': '#f39c12', 'EM': '#c0392b'}
                    
                    for maint_type in trends_pivot.columns:
                        fig.add_trace(go.Bar(
                            name=maint_type,
                            x=trends_pivot.index,
                            y=trends_pivot[maint_type],
                            marker_color=colors.get(maint_type, '#95a5a6')
                        ))
                    
                    fig.update_layout(
                        title='Maintenance Events Over Time',
                        xaxis_title='Month',
                        yaxis_title='Number of Events',
                        barmode='stack',
                        showlegend=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Top maintenance consumers
                st.markdown("### 🏭 Top Maintenance Consumers")
                
                top_machines = pd.read_sql_query("""
                    SELECT 
                        machine_id,
                        COUNT(*) as total_events,
                        SUM(CASE WHEN work_order_type = 'PM' THEN 1 ELSE 0 END) as preventive,
                        SUM(CASE WHEN work_order_type IN ('AM', 'CM', 'EM') THEN 1 ELSE 0 END) as reactive
                    FROM maintenance_records
                    WHERE is_three_way_match = 1
                    GROUP BY machine_id
                    ORDER BY total_events DESC
                    LIMIT 10
                """, conn)
                
                if not top_machines.empty:
                    # Add ratio calculation
                    top_machines['PM_ratio'] = (top_machines['preventive'] / top_machines['total_events'] * 100).round(1)

                    # Display as table with color coding
                    st.dataframe(
                        top_machines.style.background_gradient(subset=['total_events'], cmap='Reds'),
                        use_container_width=True
                    )

                    # Alert for machines with low PM ratio
                    low_pm = top_machines[top_machines['PM_ratio'] < 20]
                    if not low_pm.empty:
                        st.warning(f"⚠️ {len(low_pm)} machines have <20% preventive maintenance ratio - consider increasing PM frequency")

                # Efficiency degradation curve based on unified view data
                st.markdown("### ⚙️ Efficiency vs Maintenance Age")

                try:
                    efficiency_data = pd.read_sql_query("""
                        SELECT 
                            hours_since_last_maintenance,
                            kwh_per_unit
                        FROM unified_view
                        WHERE kwh_per_unit > 0 AND kwh_per_unit < 20
                          AND hours_since_last_maintenance IS NOT NULL
                          AND is_near_zero_output = 0
                    """, conn)

                    if not efficiency_data.empty:
                        efficiency_data['bucket'] = pd.cut(
                            efficiency_data['hours_since_last_maintenance'],
                            bins=[0, 200, 500, 800, 1200, 2000, 4000],
                            labels=['0-200h', '200-500h', '500-800h', '800-1200h', '1200-2000h', '2000h+']
                        )

                        bucket_stats = efficiency_data.groupby('bucket')['kwh_per_unit'].agg(['mean', 'count']).reset_index()
                        bucket_stats = bucket_stats[bucket_stats['count'] > 20]

                        if not bucket_stats.empty:
                            fig = px.line(
                                bucket_stats,
                                x='bucket',
                                y='mean',
                                markers=True,
                                title='Efficiency degradation as maintenance is delayed',
                                labels={'bucket': 'Hours Since Maintenance', 'mean': 'Avg kWh/unit'}
                            )
                            fig.add_hline(y=bucket_stats['mean'].min(), line_dash='dash', line_color='green', annotation_text='Best observed')
                            st.plotly_chart(fig, use_container_width=True)

                            worst_bucket = bucket_stats.sort_values('mean', ascending=False).iloc[0]
                            st.info(
                                f"Machines operating {worst_bucket['bucket']} since maintenance consume {worst_bucket['mean']:.2f} kWh/unit on average. "
                                "Schedule PM before reaching that bucket to stay in optimum efficiency bands."
                            )
                except Exception as exc:
                    st.warning(f"Could not compute efficiency degradation curve: {exc}")

            else:
                st.info("No maintenance predictions available yet. Process maintenance data through ETL first.")

        else:
            st.info("Maintenance tables not initialized. Upload maintenance data to begin analysis.")

    except Exception as e:
        st.info("No maintenance data processed yet. Upload maintenance records through the section below.")
    
    finally:
        conn.close()
    
    # File upload section
    st.markdown("---")
    st.markdown("### 📤 Upload Maintenance Records")
    
    with st.expander("Upload New Maintenance Data", expanded=False):
        st.info("""
        Upload monthly maintenance Excel files with the following columns:
        - 工單 (Work Order)
        - 工單類型 (PM/AM/CM/EM)
        - 資產 (Asset ID - MES format)
        - 資產老編號 (Old Asset ID - Energy format)
        - 交易日期 (Transaction Date)
        - 物料編碼 (Material Code)
        """)
        
        uploaded_file = st.file_uploader(
            "Choose Maintenance Excel File", 
            type=['xlsx', 'xls'],
            help="Upload monthly maintenance records for analysis"
        )
        
        if uploaded_file is not None:
            # Get processing month
            month_col1, month_col2 = st.columns(2)
            
            with month_col1:
                month_options = ['January', 'February', 'March', 'April', 'May', 'June', 
                                'July', 'August', 'September', 'October', 'November', 'December']
                selected_month = st.selectbox("Select Month", month_options, index=5)  # Default to June
            
            with month_col2:
                selected_year = st.number_input("Select Year", min_value=2024, max_value=2026, value=2025)
            
            month_year = f"{selected_month} {selected_year}"
            
            # Upload mode selection
            upload_mode = st.radio(
                "Upload Mode",
                ["Replace Month Data", "Append New Records"],
                help="Replace: Remove existing records for this month before uploading. Append: Add to existing records (duplicates will be skipped).",
                horizontal=True
            )
            
            # Check for existing records and show warning
            conn = sqlite3.connect('manufacturing_data.db')
            try:
                # Count total existing records
                total_existing = pd.read_sql_query(
                    "SELECT COUNT(*) as cnt FROM maintenance_records",
                    conn
                ).iloc[0]['cnt']
                
                if upload_mode == "Replace Month Data":
                    st.warning(f"""
                    ⚠️ **Replace Mode Selected**
                    - Current database has {total_existing:,} total maintenance records
                    - The uploaded file will replace ALL months it contains
                    - Records for other months will be preserved
                    """)
                else:
                    st.info(f"""
                    ℹ️ **Append Mode Selected**  
                    - Current database has {total_existing:,} total maintenance records
                    - New unique records will be added
                    - Duplicates will be automatically skipped
                    """)
            except:
                # Column might not exist in old databases
                pass
            finally:
                conn.close()
            
            if st.button("🚀 Process Maintenance Data", type="primary"):
                try:
                    # Save uploaded file temporarily
                    temp_path = Path("temp_uploads") / uploaded_file.name
                    temp_path.parent.mkdir(exist_ok=True)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process with maintenance integration
                    with st.spinner(f"Processing maintenance data for {month_year}..."):
                        result = integrate_maintenance_with_etl(str(temp_path), month_year)
                        
                        if result:
                            # Save to database
                            conn = sqlite3.connect('manufacturing_data.db')
                            cursor = conn.cursor()
                            
                            maintenance_df = result['maintenance_records']
                            
                            # Get all unique months in the uploaded data
                            unique_months = maintenance_df['month_year'].unique()
                            st.info(f"📅 File contains data for: {', '.join(sorted(unique_months))}")
                            
                            if upload_mode == "Replace Month Data":
                                # Delete ALL months that exist in the uploaded file
                                total_deleted = 0
                                for month in unique_months:
                                    cursor.execute("DELETE FROM maintenance_records WHERE month_year = ?", (month,))
                                    total_deleted += cursor.rowcount
                                
                                if total_deleted > 0:
                                    st.info(f"Replaced {total_deleted:,} existing records across {len(unique_months)} months")
                                
                                # Save all new records
                                maintenance_df.to_sql('maintenance_records', conn, if_exists='append', index=False)
                                
                            else:  # Append mode with duplicate checking
                                # Get existing records for comparison (from ALL months in the file)
                                placeholders = ','.join(['?' for _ in unique_months])
                                existing_df = pd.read_sql_query(
                                    f"SELECT work_order, transaction_date, asset_id, material_code FROM maintenance_records WHERE month_year IN ({placeholders})",
                                    conn, params=tuple(unique_months)
                                )
                                
                                # Create composite key for duplicate checking
                                existing_df['composite_key'] = (
                                    existing_df['work_order'].astype(str) + '_' +
                                    existing_df['transaction_date'].astype(str) + '_' +
                                    existing_df['asset_id'].fillna('').astype(str) + '_' +
                                    existing_df['material_code'].fillna('').astype(str)
                                )
                                existing_keys = set(existing_df['composite_key'])
                                
                                # Create composite key for new records
                                maintenance_df['composite_key'] = (
                                    maintenance_df['work_order'].astype(str) + '_' +
                                    maintenance_df['transaction_date'].astype(str) + '_' +
                                    maintenance_df['asset_id'].fillna('').astype(str) + '_' +
                                    maintenance_df['material_code'].fillna('').astype(str)
                                )
                                
                                # Filter out duplicates
                                new_records = maintenance_df[~maintenance_df['composite_key'].isin(existing_keys)]
                                new_records = new_records.drop(columns=['composite_key'])
                                
                                if len(new_records) > 0:
                                    new_records.to_sql('maintenance_records', conn, if_exists='append', index=False)
                                    st.info(f"Added {len(new_records):,} new records ({len(maintenance_df) - len(new_records):,} duplicates skipped)")
                                else:
                                    st.warning("All records already exist. No new records added.")
                            
                            # Save metrics
                            if result['metrics'] is not None:
                                result['metrics'].to_sql('maintenance_summary', conn, if_exists='replace', index=False)
                            
                            # Save predictions
                            if result['predictions'] is not None:
                                result['predictions'].to_sql('maintenance_ml_features', conn, if_exists='replace', index=False)
                            
                            conn.commit()
                            conn.close()
                            
                            # Show success metrics
                            total_records = len(maintenance_df)
                            matched_records = len(maintenance_df[maintenance_df['is_three_way_match'] == 1])
                            match_rate = (matched_records / total_records * 100) if total_records > 0 else 0
                            
                            st.success(f"""
                            ✅ Successfully processed maintenance data!
                            - Total records: {total_records:,}
                            - Matched with production: {matched_records:,} ({match_rate:.1f}%)
                            - High-risk machines identified: {len(result['predictions'][result['predictions']['risk_level'] == 'HIGH']) if result['predictions'] is not None else 0}
                            """)
                            
                            # Clean up temp file
                            temp_path.unlink()
                            
                            # Refresh page
                            st.rerun()
                        
                        else:
                            st.error("Failed to process maintenance data. Please check the file format.")
                    
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
                    st.exception(e)
    
    # Integration status
    st.markdown("---")
    st.markdown("### 🔗 Integration Status")
    
    conn = sqlite3.connect('manufacturing_data.db')
    
    # Check integration metrics
    integration_metrics = {}
    
    try:
        # Count maintenance records
        maint_count = pd.read_sql_query(
            "SELECT COUNT(*) as cnt FROM maintenance_records", conn
        ).iloc[0]['cnt']
        integration_metrics['Total Maintenance Records'] = f"{maint_count:,}"
        
        # Count matched machines
        matched_machines = pd.read_sql_query("""
            SELECT COUNT(DISTINCT machine_id) as cnt 
            FROM maintenance_records 
            WHERE is_three_way_match = 1
        """, conn).iloc[0]['cnt']
        integration_metrics['Matched Machines'] = matched_machines
        
        # Count three-way matches
        three_way_count = pd.read_sql_query(
            "SELECT COUNT(*) as cnt FROM three_way_matches", conn
        ).iloc[0]['cnt']
        integration_metrics['Three-Way Matches Available'] = three_way_count
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Maintenance Records", integration_metrics.get('Total Maintenance Records', '0'))
        
        with col2:
            st.metric("Integrated Machines", integration_metrics.get('Matched Machines', 0))
        
        with col3:
            match_coverage = (integration_metrics.get('Matched Machines', 0) / three_way_count * 100) if three_way_count > 0 else 0
            st.metric("Integration Coverage", f"{match_coverage:.1f}%")
        
    except:
        st.info("Maintenance module ready. Upload data to begin integration.")
    
    finally:
        conn.close()
    
    # Database Viewer Section
    st.markdown("---")
    st.markdown("### 🔍 Database Viewer")
    
    viewer_tabs = st.tabs(["📊 Browse Records", "🏭 Machine History", "📈 Statistics"])
    
    with viewer_tabs[0]:
        st.markdown("#### Browse Maintenance Records")
        
        conn = sqlite3.connect('manufacturing_data.db')
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get available months
            months_df = pd.read_sql_query("""
                SELECT DISTINCT month_year 
                FROM maintenance_records 
                ORDER BY month_year
            """, conn)
            
            selected_months = st.multiselect(
                "Filter by Month",
                options=months_df['month_year'].tolist(),
                default=None
            )
        
        with col2:
            # Get machine list
            machines_df = pd.read_sql_query("""
                SELECT DISTINCT machine_id 
                FROM maintenance_records 
                WHERE machine_id IS NOT NULL 
                ORDER BY machine_id
            """, conn)
            
            selected_machine = st.selectbox(
                "Filter by Machine",
                options=['All'] + machines_df['machine_id'].tolist(),
                index=0
            )
        
        with col3:
            work_types = ['All', 'PM', 'CM', 'EM', 'AM']
            selected_type = st.selectbox(
                "Filter by Type",
                options=work_types,
                index=0
            )
        
        # Build query
        query = "SELECT * FROM maintenance_records WHERE 1=1"
        params = []
        
        if selected_months:
            placeholders = ','.join(['?' for _ in selected_months])
            query += f" AND month_year IN ({placeholders})"
            params.extend(selected_months)
        
        if selected_machine != 'All':
            query += " AND machine_id = ?"
            params.append(selected_machine)
        
        if selected_type != 'All':
            query += " AND work_order_type = ?"
            params.append(selected_type)
        
        query += " ORDER BY transaction_date DESC LIMIT 100"
        
        # Execute query
        records_df = pd.read_sql_query(query, conn, params=params)
        
        if len(records_df) > 0:
            st.info(f"Showing {len(records_df)} records (limited to 100)")
            
            # Display key columns
            display_cols = ['machine_id', 'transaction_date', 'work_order', 'work_order_type', 
                          'material_code', 'month_year', 'is_three_way_match']
            display_df = records_df[display_cols].copy()
            display_df['is_three_way_match'] = display_df['is_three_way_match'].map({1: '✅', 0: '❌'})
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export option
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"maintenance_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No records found with selected filters")
        
        conn.close()
    
    with viewer_tabs[1]:
        st.markdown("#### Machine Maintenance History")
        
        conn = sqlite3.connect('manufacturing_data.db')
        
        # Machine selector
        machines_with_maint = pd.read_sql_query("""
            SELECT DISTINCT machine_id, COUNT(*) as count
            FROM machine_maintenance_history
            GROUP BY machine_id
            ORDER BY count DESC
        """, conn)
        
        if len(machines_with_maint) > 0:
            machine_options = [f"{row['machine_id']} ({row['count']} events)" 
                              for _, row in machines_with_maint.iterrows()]
            machine_ids = machines_with_maint['machine_id'].tolist()
            
            selected_idx = st.selectbox(
                "Select Machine",
                options=range(len(machine_options)),
                format_func=lambda x: machine_options[x],
                index=0
            )
            
            selected_machine_id = machine_ids[selected_idx]
            
            # Get machine history
            history_df = pd.read_sql_query("""
                SELECT 
                    maintenance_datetime,
                    work_order,
                    work_order_type,
                    material_code,
                    days_since_prev,
                    maintenance_seq
                FROM machine_maintenance_history
                WHERE machine_id = ?
                ORDER BY maintenance_datetime DESC
                LIMIT 50
            """, conn, params=(selected_machine_id,))
            
            if len(history_df) > 0:
                # Calculate statistics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_events = machines_with_maint[machines_with_maint['machine_id'] == selected_machine_id]['count'].values[0]
                    st.metric("Total Events", int(total_events))
                
                with col2:
                    avg_interval = history_df['days_since_prev'].mean()
                    st.metric("Avg Days Between", f"{avg_interval:.1f}" if pd.notna(avg_interval) else "N/A")
                
                with col3:
                    type_counts = history_df['work_order_type'].value_counts()
                    pm_ratio = (type_counts.get('PM', 0) / len(history_df) * 100) if len(history_df) > 0 else 0
                    st.metric("PM Ratio", f"{pm_ratio:.1f}%")
                
                with col4:
                    last_maint = history_df['maintenance_datetime'].iloc[0] if len(history_df) > 0 else None
                    if last_maint:
                        days_ago = (pd.Timestamp.now() - pd.to_datetime(last_maint)).days
                        st.metric("Days Since Last", days_ago)
                
                # Show history table
                st.markdown("##### Recent Maintenance History")
                display_history = history_df[['maintenance_datetime', 'work_order_type', 'material_code', 'days_since_prev']].copy()
                display_history['maintenance_datetime'] = pd.to_datetime(display_history['maintenance_datetime']).dt.strftime('%Y-%m-%d %H:%M')
                display_history.columns = ['Date/Time', 'Type', 'Material', 'Days Since Previous']
                
                st.dataframe(display_history, use_container_width=True)
        else:
            st.info("No maintenance history available")
        
        conn.close()
    
    with viewer_tabs[2]:
        st.markdown("#### Maintenance Statistics")
        
        conn = sqlite3.connect('manufacturing_data.db')
        
        # Overall statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Records by Month")
            monthly_stats = pd.read_sql_query("""
                SELECT month_year, COUNT(*) as count
                FROM maintenance_records
                GROUP BY month_year
                ORDER BY month_year
            """, conn)
            
            if len(monthly_stats) > 0:
                st.bar_chart(monthly_stats.set_index('month_year')['count'])
        
        with col2:
            st.markdown("##### Work Order Types")
            type_stats = pd.read_sql_query("""
                SELECT work_order_type, COUNT(*) as count
                FROM maintenance_records
                WHERE work_order_type IS NOT NULL
                GROUP BY work_order_type
            """, conn)
            
            if len(type_stats) > 0:
                import plotly.express as px
                fig = px.pie(type_stats, values='count', names='work_order_type', 
                           title="Distribution of Maintenance Types")
                st.plotly_chart(fig, use_container_width=True)
        
        # Top machines by maintenance
        st.markdown("##### Top 10 Machines by Maintenance Frequency")
        top_machines = pd.read_sql_query("""
            SELECT machine_id, COUNT(*) as maintenance_count
            FROM maintenance_records
            WHERE is_three_way_match = 1 AND machine_id IS NOT NULL
            GROUP BY machine_id
            ORDER BY maintenance_count DESC
            LIMIT 10
        """, conn)
        
        if len(top_machines) > 0:
            st.bar_chart(top_machines.set_index('machine_id')['maintenance_count'])
        
        conn.close()
