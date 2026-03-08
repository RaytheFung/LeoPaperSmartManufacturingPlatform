"""
Module 1: ETL Pipeline with File Upload
Allows users to upload monthly data files and process machine mappings
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime
import os
from pathlib import Path

# Import the existing ETL solution
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.enhanced_etl_solution_CURRENT import EnhancedSmartManufacturingETL


class ETLPipelineModule:
    def __init__(self, db_path='manufacturing_data.db'):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etl_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TIMESTAMP,
                month_processed TEXT,
                energy_files_count INTEGER,
                three_way_matches INTEGER,
                match_rate REAL,
                status TEXT,
                details TEXT,
                display_order INTEGER
            )
        ''')
        
        # Add display_order column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(etl_runs)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'display_order' not in columns:
            cursor.execute('ALTER TABLE etl_runs ADD COLUMN display_order INTEGER')
            # Set initial display order based on run_date
            cursor.execute('''
                UPDATE etl_runs 
                SET display_order = (
                    SELECT COUNT(*) 
                    FROM etl_runs AS e2 
                    WHERE e2.run_date <= etl_runs.run_date
                )
            ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS machine_inventory (
                machine_id TEXT,
                system_type TEXT,
                first_seen_date TEXT,
                last_seen_date TEXT,
                is_active INTEGER,
                PRIMARY KEY (machine_id, system_type)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS three_way_matches (
                machine_id TEXT PRIMARY KEY,
                energy_pattern TEXT,
                csi_id TEXT,
                mes_id TEXT,
                first_matched_date TEXT,
                last_confirmed_date TEXT
            )
        ''')
        
        # Create monthly presence tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS machine_monthly_presence (
                machine_id TEXT,
                month_year TEXT,
                system_type TEXT,
                is_three_way_match INTEGER DEFAULT 0,
                PRIMARY KEY (machine_id, month_year, system_type)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_etl_results(self, mapping_results, month_name, etl_instance=None):
        """Save ETL results to database including actual extracted data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables for storing actual ETL data if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etl_energy_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT,
                pattern TEXT,
                datetime TIMESTAMP,
                electricity_kwh REAL,
                machine_components TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etl_csi_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT,
                machine_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                setup_start TIMESTAMP,
                setup_end TIMESTAMP,
                material TEXT,
                order_id TEXT,
                good_qty REAL,
                efficiency REAL,
                actual_speed REAL,
                team_leader TEXT,
                team_member_1 TEXT,
                team_member_2 TEXT,
                team_member_3 TEXT,
                team_member_4 TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS etl_mes_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT,
                resource TEXT,
                task TEXT,
                order_number TEXT,
                material_code TEXT,
                planned_qty REAL,
                planned_start TIMESTAMP,
                planned_end TIMESTAMP
            )
        ''')
        
        # Store the actual data if ETL instance is provided
        if etl_instance:
            # Clear existing data for this month
            cursor.execute("DELETE FROM etl_energy_data WHERE month_year = ?", (month_name,))
            cursor.execute("DELETE FROM etl_csi_data WHERE month_year = ?", (month_name,))
            cursor.execute("DELETE FROM etl_mes_data WHERE month_year = ?", (month_name,))
            
            # Store energy data - use original energy_data with machine mappings
            if hasattr(etl_instance, 'energy_data') and etl_instance.energy_data is not None:
                # Create a mapping from original machine names to patterns
                machine_to_pattern = {}
                if hasattr(etl_instance, 'energy_aggregated'):
                    for machine_id, row in etl_instance.energy_aggregated.iterrows():
                        # Map each original name to the machine_id (which is the pattern)
                        for orig_name in row.get('original_names', []):
                            machine_to_pattern[orig_name] = machine_id
                
                # Save the detailed energy data with patterns
                for _, row in etl_instance.energy_data.iterrows():
                    machine_name = row.get('machine', '')
                    pattern = machine_to_pattern.get(machine_name, '')
                    
                    # Skip if no pattern found (non-matched machines)
                    if not pattern:
                        continue
                        
                    cursor.execute('''
                        INSERT INTO etl_energy_data 
                        (month_year, pattern, datetime, electricity_kwh, machine_components)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        month_name,
                        pattern,  # Use the mapped pattern
                        str(row.get('datetime', '')),  # Convert to string
                        float(row.get('electricity_kwh', 0)),  # Ensure float
                        json.dumps([machine_name])  # Store original name as component
                    ))
            
            # Store CSI data
            if hasattr(etl_instance, 'csi_data') and etl_instance.csi_data is not None:
                for _, row in etl_instance.csi_data.iterrows():
                    cursor.execute('''
                        INSERT INTO etl_csi_data 
                        (month_year, machine_id, start_time, end_time, setup_start, setup_end,
                         material, order_id, good_qty, efficiency, actual_speed,
                         team_leader, team_member_1, team_member_2, team_member_3, team_member_4)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        month_name,
                        row.get('機台編號', ''),
                        row.get('工程開始時間'),
                        row.get('工程結束時間'),
                        row.get('準備開始時間'),
                        row.get('準備結束時間'),
                        row.get('物料', ''),
                        row.get('作业', ''),
                        row.get('正品數量', 0),
                        row.get('效率', 0),
                        row.get('實際速度_本_時', 0),
                        row.get('機長姓名1', ''),
                        row.get('機組人員姓名1', ''),
                        row.get('機組人員姓名2', ''),
                        row.get('機組人員姓名3', ''),
                        row.get('機組人員姓名4', '')
                    ))
            
            # Store MES data
            if hasattr(etl_instance, 'mes_data') and etl_instance.mes_data is not None:
                for _, row in etl_instance.mes_data.iterrows():
                    cursor.execute('''
                        INSERT INTO etl_mes_data 
                        (month_year, resource, task, order_number, material_code,
                         planned_qty, planned_start, planned_end)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        month_name,
                        row.get('資源', ''),
                        row.get('任務', ''),
                        row.get('訂單號', ''),
                        row.get('物料編碼', ''),
                        row.get('計劃數量', 0),
                        row.get('計劃開始'),
                        row.get('計劃結束')
                    ))
        
        # Get the next display order
        cursor.execute('SELECT MAX(display_order) FROM etl_runs')
        max_order = cursor.fetchone()[0]
        next_order = (max_order or 0) + 1
        
        # Save run summary
        stats = mapping_results['mapping_stats']
        cursor.execute('''
            INSERT INTO etl_runs 
            (run_date, month_processed, energy_files_count, three_way_matches, match_rate, status, details, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            month_name,
            stats['energy_original_rows'],
            stats['three_way_matches'],
            float(stats['mes_coverage_percent'].strip('%')),
            'Success',
            json.dumps(stats),
            next_order
        ))
        
        # First, deactivate all machines for this month's processing
        # This ensures we only show machines that are actually present in the current data
        cursor.execute('''
            UPDATE machine_inventory 
            SET is_active = 0 
            WHERE last_seen_date != ?
        ''', (month_name,))
        
        # Collect all machines seen in this processing run
        all_seen_machines = set()
        
        # Update machine inventory for three-way matches
        for match in mapping_results['three_way_matches']:
            # Update three-way matches
            cursor.execute('''
                INSERT OR REPLACE INTO three_way_matches 
                (machine_id, energy_pattern, csi_id, mes_id, first_matched_date, last_confirmed_date)
                VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT first_matched_date FROM three_way_matches WHERE machine_id = ?), ?),
                    ?)
            ''', (
                match['machine_id'],
                match['machine_id'],
                match['csi'],
                match['mes'],
                match['machine_id'],
                month_name,
                month_name
            ))
            
            # Update inventory for each system
            for system, id_val in [('Energy', match['machine_id']), 
                                   ('CSI', match['csi']), 
                                   ('MES', match['mes'])]:
                all_seen_machines.add((id_val, system))
                cursor.execute('''
                    INSERT OR REPLACE INTO machine_inventory 
                    (machine_id, system_type, first_seen_date, last_seen_date, is_active)
                    VALUES (?, ?, 
                        COALESCE((SELECT first_seen_date FROM machine_inventory 
                                  WHERE machine_id = ? AND system_type = ?), ?),
                        ?, 1)
                ''', (id_val, system, id_val, system, month_name, month_name))
        
        # Also update inventory for machines in partial matches and single systems
        # to maintain accurate per-month data
        
        # Process partial matches
        if 'partial_matches' in mapping_results:
            for category, machines in mapping_results['partial_matches'].items():
                for machine_data in machines:
                    if category == 'energy_csi_only':
                        all_seen_machines.add((machine_data['machine_id'], 'Energy'))
                        all_seen_machines.add((machine_data['csi'], 'CSI'))
                    elif category == 'energy_mes_only':
                        all_seen_machines.add((machine_data['machine_id'], 'Energy'))
                        all_seen_machines.add((machine_data['mes'], 'MES'))
                    elif category == 'csi_mes_only':
                        all_seen_machines.add((machine_data['csi'], 'CSI'))
                        all_seen_machines.add((machine_data['mes'], 'MES'))
        
        # Process single system machines
        if 'single_system' in mapping_results:
            for system_key, machines in mapping_results['single_system'].items():
                system_map = {
                    'energy_only': 'Energy',
                    'csi_only': 'CSI',
                    'mes_only': 'MES'
                }
                if system_key in system_map:
                    system = system_map[system_key]
                    for machine in machines:
                        machine_id = machine if isinstance(machine, str) else str(machine)
                        all_seen_machines.add((machine_id, system))
        
        # Update all seen machines as active
        for machine_id, system in all_seen_machines:
            cursor.execute('''
                INSERT OR REPLACE INTO machine_inventory 
                (machine_id, system_type, first_seen_date, last_seen_date, is_active)
                VALUES (?, ?, 
                    COALESCE((SELECT first_seen_date FROM machine_inventory 
                              WHERE machine_id = ? AND system_type = ?), ?),
                    ?, 1)
            ''', (machine_id, system, machine_id, system, month_name, month_name))
        
        # Clear monthly presence for this month first (in case of re-processing)
        cursor.execute('DELETE FROM machine_monthly_presence WHERE month_year = ?', (month_name,))
        
        # Insert monthly presence for all seen machines
        for machine_id, system in all_seen_machines:
            # Check if this machine is in three-way matches
            is_three_way = 1 if any(m['machine_id'] == machine_id for m in mapping_results['three_way_matches']) else 0
            
            cursor.execute('''
                INSERT INTO machine_monthly_presence 
                (machine_id, month_year, system_type, is_three_way_match)
                VALUES (?, ?, ?, ?)
            ''', (machine_id, month_name, system, is_three_way))
        
        conn.commit()
        conn.close()
    
    def get_historical_summary(self, order_by='display_order'):
        """Get historical ETL run summary"""
        conn = sqlite3.connect(self.db_path)
        
        # Validate order_by parameter
        valid_orders = {
            'display_order': 'display_order ASC',
            'date_desc': 'run_date DESC',
            'date_asc': 'run_date ASC',
            'month': 'month_processed, run_date DESC',
            'match_rate': 'match_rate DESC'
        }
        order_clause = valid_orders.get(order_by, 'display_order ASC')
        
        query = f'''
            SELECT id, month_processed, run_date, three_way_matches, match_rate, display_order
            FROM etl_runs
            ORDER BY {order_clause}
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def delete_etl_run(self, run_id):
        """Delete a specific ETL run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the record before deletion for undo functionality
        cursor.execute('SELECT * FROM etl_runs WHERE id = ?', (run_id,))
        deleted_record = cursor.fetchone()
        
        # Delete the record
        cursor.execute('DELETE FROM etl_runs WHERE id = ?', (run_id,))
        
        # Reorder remaining records
        cursor.execute('''
            UPDATE etl_runs 
            SET display_order = (
                SELECT COUNT(*) 
                FROM etl_runs AS e2 
                WHERE e2.display_order <= etl_runs.display_order
            )
        ''')
        
        conn.commit()
        conn.close()
        return deleted_record
    
    def delete_multiple_runs(self, run_ids):
        """Delete multiple ETL runs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete the records
        placeholders = ','.join('?' * len(run_ids))
        cursor.execute(f'DELETE FROM etl_runs WHERE id IN ({placeholders})', run_ids)
        
        # Reorder remaining records
        cursor.execute('''
            UPDATE etl_runs 
            SET display_order = (
                SELECT COUNT(*) 
                FROM etl_runs AS e2 
                WHERE e2.display_order <= etl_runs.display_order
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_display_order(self, run_id, direction):
        """Move a record up or down in display order"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current order
        cursor.execute('SELECT display_order FROM etl_runs WHERE id = ?', (run_id,))
        current_order = cursor.fetchone()[0]
        
        if direction == 'up' and current_order > 1:
            # Swap with previous record
            cursor.execute('''
                UPDATE etl_runs 
                SET display_order = CASE 
                    WHEN id = ? THEN display_order - 1
                    WHEN display_order = ? THEN display_order + 1
                END
                WHERE id = ? OR display_order = ?
            ''', (run_id, current_order - 1, run_id, current_order - 1))
        
        elif direction == 'down':
            # Check if not last
            cursor.execute('SELECT MAX(display_order) FROM etl_runs')
            max_order = cursor.fetchone()[0]
            
            if current_order < max_order:
                # Swap with next record
                cursor.execute('''
                    UPDATE etl_runs 
                    SET display_order = CASE 
                        WHEN id = ? THEN display_order + 1
                        WHEN display_order = ? THEN display_order - 1
                    END
                    WHERE id = ? OR display_order = ?
                ''', (run_id, current_order + 1, run_id, current_order + 1))
        
        conn.commit()
        conn.close()
    
    def reset_display_order(self):
        """Reset display order to chronological order"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE etl_runs 
            SET display_order = (
                SELECT COUNT(*) 
                FROM etl_runs AS e2 
                WHERE e2.run_date <= etl_runs.run_date
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_machine_inventory_summary(self, active_only=True):
        """Get machine inventory summary"""
        conn = sqlite3.connect(self.db_path)
        if active_only:
            query = '''
                SELECT system_type, COUNT(DISTINCT machine_id) as machine_count
                FROM machine_inventory
                WHERE is_active = 1
                GROUP BY system_type
            '''
        else:
            query = '''
                SELECT system_type, COUNT(DISTINCT machine_id) as machine_count
                FROM machine_inventory
                GROUP BY system_type
            '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df


def render_etl_page():
    """Main function to render the ETL Pipeline page"""
    st.header("🔄 ETL Pipeline - Monthly Data Upload")
    
    # Initialize ETL module
    etl_module = ETLPipelineModule()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload New Data", "📊 Current Status", "📈 Historical Runs"])
    
    with tab1:
        render_upload_section(etl_module)
    
    with tab2:
        render_current_status(etl_module)
        
    with tab3:
        render_historical_runs(etl_module)


def render_upload_section(etl_module):
    """Render the file upload section"""
    # Check if we have processed results in session state
    if 'etl_results' in st.session_state and st.session_state.etl_results is not None:
        # Display the results instead of upload interface
        display_processing_results(st.session_state.etl_results['mapping_results'], 
                                 st.session_state.etl_results['etl'])
        generate_download_options(st.session_state.etl_results['mapping_results'], 
                                st.session_state.etl_results['etl'], 
                                st.session_state.etl_results['month_name'])
        
        # Add a button to clear results and return to upload
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🔄 Process New Month", type="primary"):
            st.session_state.etl_results = None
            st.rerun()
        return
    
    st.markdown("""
    ### Upload Monthly Manufacturing Data
    Please upload the three required files for the month you want to process:
    """)
    
    # Month and Year selection
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        month_name = st.selectbox(
            "Select Month",
            ["January", "February", "March", "April", "May", "June", "July", 
             "August", "September", "October", "November", "December"],
            index=5  # Default to June
        )
    
    with col2:
        current_year = datetime.now().year
        year = st.selectbox(
            "Select Year",
            list(range(current_year - 5, current_year + 2)),  # 5 years back, 1 year forward
            index=5  # Default to current year
        )
    
    # Combine month and year for processing
    month_year = f"{month_name} {year}"
    
    # File upload sections
    st.markdown("#### 1️⃣ Energy Consumption Files")
    energy_files = st.file_uploader(
        "Upload Energy files (能耗、費用報表)",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        key="energy_uploader",
        help="You can upload multiple energy files for different date ranges within the month"
    )
    
    st.markdown("#### 2️⃣ CSI Production File")
    csi_file = st.file_uploader(
        "Upload CSI file (CSI印刷心電圖報表)",
        type=['xlsx', 'xls'],
        accept_multiple_files=False,
        key="csi_uploader",
        help="Upload the monthly CSI production report"
    )
    
    st.markdown("#### 3️⃣ MES Planning File")
    mes_file = st.file_uploader(
        "Upload MES file (MES生產數據)",
        type=['xlsx', 'xls'],
        accept_multiple_files=False,
        key="mes_uploader",
        help="Upload the monthly MES planning data"
    )
    
    # Validation and processing
    if energy_files and csi_file and mes_file:
        st.success(f"✅ All files uploaded for {month_year}")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🚀 Process Data", type="primary"):
                process_uploaded_files(energy_files, csi_file, mes_file, month_year, etl_module)
    else:
        missing = []
        if not energy_files:
            missing.append("Energy files")
        if not csi_file:
            missing.append("CSI file")
        if not mes_file:
            missing.append("MES file")
        
        if missing:
            st.warning(f"⚠️ Missing: {', '.join(missing)}")


def process_uploaded_files(energy_files, csi_file, mes_file, month_year, etl_module):
    """Process the uploaded files using ETL pipeline"""
    try:
        with st.spinner(f"Processing {month_year} data..."):
            # Save uploaded files to persistent data directory for unified view
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            # Clean month name for file naming
            month_prefix = month_year.replace(' ', '_')
            
            # Save energy files with month-specific names
            energy_paths = []
            for i, file in enumerate(energy_files):
                # Use month-specific naming: e.g., "January_2025_energy_1.xlsx"
                path = data_dir / f"{month_prefix}_energy_{i+1}.xlsx"
                with open(path, "wb") as f:
                    f.write(file.getbuffer())
                energy_paths.append(str(path))
            
            # Save CSI file with month-specific name
            csi_path = data_dir / f"{month_prefix}_csi.xlsx"
            with open(csi_path, "wb") as f:
                f.write(csi_file.getbuffer())
            
            # Save MES file with month-specific name
            mes_path = data_dir / f"{month_prefix}_mes.xlsx"
            with open(mes_path, "wb") as f:
                f.write(mes_file.getbuffer())
            
            # Initialize ETL pipeline
            etl = EnhancedSmartManufacturingETL()
            
            # Process files
            st.info("Extracting data from files...")
            etl.extract_all_sources(energy_paths, str(csi_path), str(mes_path))
            
            st.info("Creating machine mappings...")
            mapping_results = etl.create_comprehensive_mapping()
            
            # Save results to database including actual data
            etl_module.save_etl_results(mapping_results, month_year, etl)
            
            # Auto-trigger Unified View processing
            st.info("🔄 Automatically creating Unified View...")
            try:
                from unified_view_module import auto_process_after_etl
                unified_result = auto_process_after_etl(month_year)
                
                if unified_result['status'] == 'success':
                    st.success(f"✅ Unified View created: {unified_result['records_created']} hourly records")
                else:
                    st.warning(f"⚠️ Unified View creation issue: {unified_result.get('message', 'Unknown')}")
            except Exception as e:
                st.warning(f"⚠️ Could not auto-create Unified View: {str(e)}")
                st.info("You can manually create it in the Unified View module")
            
            # Store results in session state
            st.session_state.etl_results = {
                'mapping_results': mapping_results,
                'etl': etl,
                'month_name': month_year
            }
            
            # Clean up temp files
            for path in energy_paths + [csi_path, mes_path]:
                os.remove(path)
            
            # Auto-trigger Maintenance Integration if file exists
            st.info("🔧 Checking for maintenance data...")
            
            # Try multiple file name patterns
            maintenance_patterns = [
                f"Maintenance Record{month_year.split()[0][:3]} to {month_year.split()[0][:3]}.xlsx",
                f"maintenance_{month_year.lower().replace(' ', '_')}.xlsx",
                f"Maintenance RecordJan to Jul.xlsx",  # Known file format
                "maintenance_data.xlsx"
            ]
            
            maintenance_file = None
            for pattern in maintenance_patterns:
                if os.path.exists(pattern):
                    maintenance_file = pattern
                    break
                # Also check in data directory
                data_path = Path("data") / pattern
                if data_path.exists():
                    maintenance_file = str(data_path)
                    break
            
            if maintenance_file:
                st.info(f"Found maintenance file: {maintenance_file}")
                try:
                    from core.maintenance_integration import integrate_maintenance_with_etl
                    
                    with st.spinner("Integrating maintenance data..."):
                        maint_result = integrate_maintenance_with_etl(maintenance_file, month_year)
                        
                        if maint_result:
                            # Count matched records
                            maintenance_df = maint_result['maintenance_records']
                            matched = len(maintenance_df[maintenance_df['is_three_way_match'] == 1])
                            total = len(maintenance_df)
                            
                            # Save to database
                            conn = sqlite3.connect('manufacturing_data.db')
                            maintenance_df.to_sql('maintenance_records', conn, if_exists='append', index=False)
                            
                            if maint_result['metrics'] is not None:
                                maint_result['metrics'].to_sql('maintenance_summary', conn, if_exists='replace')
                            
                            if maint_result['predictions'] is not None:
                                maint_result['predictions'].to_sql('maintenance_ml_features', conn, if_exists='replace', index=False)
                                
                                # Show high-risk machines
                                high_risk = maint_result['predictions'][
                                    maint_result['predictions']['risk_level'] == 'HIGH'
                                ]
                                
                                if not high_risk.empty:
                                    st.warning(f"""
                                    ⚠️ **Maintenance Alert**: {len(high_risk)} machines need immediate attention:
                                    {', '.join(high_risk['machine_id'].head(5).tolist())}
                                    """)
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"""
                            ✅ Integrated {matched}/{total} maintenance records ({matched/total*100:.1f}% match rate)
                            View details in the Maintenance module.
                            """)
                            
                except Exception as e:
                    st.warning(f"Could not integrate maintenance data: {str(e)}")
            else:
                st.info("No maintenance file found. You can upload it separately in the Maintenance module.")
            
            # Trigger a rerun to display results
            st.success(f"✅ Successfully processed {month_year} data!")
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Error processing files: {str(e)}")
        st.exception(e)


def display_processing_results(mapping_results, etl):
    """Display the processing results"""
    st.markdown("## 📊 Processing Results")
    st.markdown("---")
    
    # Summary metrics with better spacing
    stats = mapping_results['mapping_stats']
    
    # Use container for better visual grouping with proper spacing
    with st.container():
        st.markdown("### 📈 Data Volume Statistics")
        # Use 2 columns for wider display
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Energy Records", f"{stats['energy_original_rows']:,}", 
                     help="Total raw energy data records")
        with col2:
            st.metric("Energy Machines", stats['energy_unique_machines'],
                     help="Unique machines in Energy system")
        
        # Second row
        col3, col4 = st.columns(2)
        
        with col3:
            st.metric("CSI Machines", stats['csi_machines'],
                     help="Unique machines in CSI system")
        with col4:
            st.metric("MES Machines", stats['mes_machines'],
                     help="Unique machines in MES system")
    
    # Add space between sections
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Matching statistics with visual indicators
    with st.container():
        st.markdown("### 🎯 Matching Analysis")
        # First row of matching metrics - 2 columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Three-way Matches", stats['three_way_matches'], 
                     help="Machines found in all three systems")
        
        with col2:
            # Calculate two-way matches
            two_way = (len(etl.partial_matches.get('energy_csi_only', [])) +
                      len(etl.partial_matches.get('energy_mes_only', [])) +
                      len(etl.partial_matches.get('csi_mes_only', [])))
            st.metric("Two-way Matches", two_way,
                     help="Machines found in exactly two systems")
        
        # Second row - 2 columns
        col3, col4 = st.columns(2)
        
        with col3:
            single = (len(etl.single_system.get('energy_only', [])) +
                     len(etl.single_system.get('csi_only', [])) +
                     len(etl.single_system.get('mes_only', [])))
            st.metric("Single System Only", single,
                     help="Machines found in only one system")
        
        with col4:
            st.metric("MES Coverage", stats['mes_coverage_percent'],
                     help="Percentage of MES machines with matches")
        
        # Third row - 2 columns
        col5, col6 = st.columns(2)
        
        with col5:
            # Add completeness metric
            completeness = round(stats['three_way_matches'] / stats['mes_machines'] * 100, 1)
            st.metric("System Completeness", f"{completeness}%",
                     help="Three-way matches vs total MES machines")
        
        with col6:
            # Add total unique machines
            total_unique = stats['energy_unique_machines'] + stats['csi_machines'] + stats['mes_machines']
            st.metric("Total Machines", total_unique,
                     help="Sum of machines across all systems")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Display matches in parallel layout
    st.markdown("## 🔗 Machine Matching Details")
    st.markdown("---")
    
    # Create two columns for Three-way and Partial matches
    col_three_way, col_partial = st.columns([1, 1])
    
    with col_three_way:
        st.markdown("### 🎯 Three-way Machine Matches")
        if mapping_results['three_way_matches']:
            matches_df = pd.DataFrame(mapping_results['three_way_matches'])
            display_df = matches_df[['machine_id', 'csi', 'mes', 'total_kwh']].copy()
            display_df['total_kwh'] = display_df['total_kwh'].round(2)
            
            st.dataframe(
                display_df,  # Show all matches
                use_container_width=True,
                hide_index=True,
                height=600,  # Increased height for better viewing
                column_config={
                    "machine_id": st.column_config.TextColumn("Energy ID"),
                    "csi": st.column_config.TextColumn("CSI ID"),
                    "mes": st.column_config.TextColumn("MES ID"),
                    "total_kwh": st.column_config.NumberColumn("kWh", format="%.0f")
                }
            )
            st.caption(f"Total: {len(display_df)} three-way matches")
        else:
            st.info("No three-way matches found")
    
    with col_partial:
        st.markdown("### 🔀 Partial Matches")
        
        # Create tabs for different partial match types
        tab1, tab2, tab3 = st.tabs(["Energy-CSI", "Energy-MES", "CSI-MES"])
        
        with tab1:
            if etl.partial_matches.get('energy_csi_only'):
                partial_df = pd.DataFrame(etl.partial_matches['energy_csi_only'])
                display_cols = ['energy', 'csi']
                if 'total_kwh' in partial_df.columns:
                    display_cols.append('total_kwh')
                    partial_df['total_kwh'] = partial_df['total_kwh'].round(0)
                st.dataframe(
                    partial_df[display_cols],  # Show all matches
                    hide_index=True,
                    use_container_width=True,
                    height=500  # Increased height
                )
                st.caption(f"Total: {len(partial_df)} Energy-CSI matches")
            else:
                st.info("No Energy-CSI matches")
        
        with tab2:
            if etl.partial_matches.get('energy_mes_only'):
                partial_df = pd.DataFrame(etl.partial_matches['energy_mes_only'])
                display_cols = ['energy', 'mes']
                if 'total_kwh' in partial_df.columns:
                    display_cols.append('total_kwh')
                    partial_df['total_kwh'] = partial_df['total_kwh'].round(0)
                st.dataframe(
                    partial_df[display_cols],  # Show all matches
                    hide_index=True,
                    use_container_width=True,
                    height=500  # Increased height
                )
                st.caption(f"Total: {len(partial_df)} Energy-MES matches")
            else:
                st.info("No Energy-MES matches")
        
        with tab3:
            if etl.partial_matches.get('csi_mes_only'):
                partial_df = pd.DataFrame(etl.partial_matches['csi_mes_only'])
                st.dataframe(
                    partial_df[['csi', 'mes']],  # Show all matches
                    hide_index=True,
                    use_container_width=True,
                    height=500  # Increased height
                )
                st.caption(f"Total: {len(partial_df)} CSI-MES matches")
            else:
                st.info("No CSI-MES matches")
    
    # Single System Machines section - Full width layout
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## 🔍 Single System Machines")
    st.markdown("---")
    st.markdown("**Machines found in only one system with no matches across other systems:**")
    
    # Create tabs for better organization
    tab_energy, tab_csi, tab_mes = st.tabs(["⚡ Energy Only", "🏭 CSI Only", "📋 MES Only"])
    
    with tab_energy:
        if etl.single_system.get('energy_only'):
            energy_only = etl.single_system['energy_only']
            
            # Display total count as simple text
            st.info(f"Found {len(energy_only)} unmatched Energy machines")
            
            # Display all machines in a scrollable dataframe
            # Extract clean machine IDs if they are stored as complex objects
            clean_ids = []
            for item in energy_only:
                if isinstance(item, dict):
                    clean_ids.append(item.get('machine_id', str(item)))
                elif isinstance(item, str):
                    clean_ids.append(item)
                else:
                    clean_ids.append(str(item))
            
            energy_df = pd.DataFrame({
                'Machine ID': clean_ids,
                'System': ['Energy'] * len(clean_ids),
                'Status': ['Unmatched'] * len(clean_ids)
            })
            st.dataframe(
                energy_df,
                hide_index=True,
                use_container_width=True,
                height=400  # Fixed height with scroll
            )
            st.caption(f"Total: {len(energy_only)} unmatched Energy machines")
        else:
            st.success("✅ All Energy machines have matches!")
    
    with tab_csi:
        if etl.single_system.get('csi_only'):
            csi_only = etl.single_system['csi_only']
            
            # Display total count as simple text
            st.info(f"Found {len(csi_only)} unmatched CSI machines")
            
            # Display all machines in a scrollable dataframe
            # Extract clean machine IDs if they are stored as complex objects
            clean_ids = []
            for item in csi_only:
                if isinstance(item, dict):
                    clean_ids.append(item.get('machine_id', str(item)))
                elif isinstance(item, str):
                    clean_ids.append(item)
                else:
                    clean_ids.append(str(item))
            
            csi_df = pd.DataFrame({
                'Machine ID': clean_ids,
                'System': ['CSI'] * len(clean_ids),
                'Status': ['Unmatched'] * len(clean_ids)
            })
            st.dataframe(
                csi_df,
                hide_index=True,
                use_container_width=True,
                height=400  # Fixed height with scroll
            )
            st.caption(f"Total: {len(csi_only)} unmatched CSI machines")
        else:
            st.success("✅ All CSI machines have matches!")
    
    with tab_mes:
        if etl.single_system.get('mes_only'):
            mes_only = etl.single_system['mes_only']
            
            # Display total count as simple text
            st.info(f"Found {len(mes_only)} unmatched MES machines")
            
            # Display all machines in a scrollable dataframe
            # Extract clean machine IDs if they are stored as complex objects
            clean_ids = []
            for item in mes_only:
                if isinstance(item, dict):
                    clean_ids.append(item.get('machine_id', str(item)))
                elif isinstance(item, str):
                    clean_ids.append(item)
                else:
                    clean_ids.append(str(item))
            
            mes_df = pd.DataFrame({
                'Machine ID': clean_ids,
                'System': ['MES'] * len(clean_ids),
                'Status': ['Unmatched'] * len(clean_ids)
            })
            st.dataframe(
                mes_df,
                hide_index=True,
                use_container_width=True,
                height=400  # Fixed height with scroll
            )
            st.caption(f"Total: {len(mes_only)} unmatched MES machines")
        else:
            st.success("✅ All MES machines have matches!")


def generate_download_options(mapping_results, etl, month_name):
    """Generate downloadable reports"""
    st.markdown("### 💾 Download Results")
    
    # Use wider columns with specific widths
    col1, col2, col3 = st.columns([1.2, 1, 1])
    
    with col1:
        # Generate Excel report in memory if not already done
        excel_key = f"excel_report_{month_name}"
        if excel_key not in st.session_state:
            with st.spinner("Preparing Excel report..."):
                report_name = f"{month_name.lower()}_etl_report.xlsx"
                etl.generate_enhanced_report(report_name)
                
                # Read the file and store in session state
                with open(report_name, "rb") as f:
                    st.session_state[excel_key] = f.read()
                
                # Clean up temp file
                os.remove(report_name)
        
        # Provide download button
        st.download_button(
            label="📊 Excel Report",
            data=st.session_state[excel_key],
            file_name=f"{month_name.lower()}_etl_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="excel_download"
        )
    
    with col2:
        # Convert numpy types to Python native types for JSON serialization
        def convert_to_serializable(obj):
            """Convert numpy types to Python native types"""
            import numpy as np
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            else:
                return obj
        
        # Convert mapping results to be JSON serializable
        serializable_results = convert_to_serializable(mapping_results)
        json_data = json.dumps(serializable_results, indent=2, ensure_ascii=False)
        
        st.download_button(
            label="📥 JSON Data",
            data=json_data,
            file_name=f"{month_name.lower()}_mappings.json",
            mime="application/json"
        )
    
    with col3:
        # Download integrated metrics
        if hasattr(etl, 'integrated_metrics') and len(etl.integrated_metrics) > 0:
            csv_data = etl.integrated_metrics.to_csv(index=False)
            st.download_button(
                label="📥 CSV Metrics",
                data=csv_data,
                file_name=f"{month_name.lower()}_integrated_metrics.csv",
                mime="text/csv"
            )


def render_current_status(etl_module):
    """Render current machine inventory status"""
    st.markdown("### 🏭 Machine Inventory Status")
    
    # Add view selector
    view_option = st.radio(
        "Select View",
        ["Latest Month", "Cumulative (All Time)"],
        horizontal=True,
        help="Latest Month shows data from the most recent processing. Cumulative shows all machines ever seen."
    )
    
    if view_option == "Latest Month":
        # Get the latest month processed
        conn = sqlite3.connect(etl_module.db_path)
        latest_month_query = """
            SELECT month_processed, run_date, three_way_matches, 
                   energy_files_count, match_rate
            FROM etl_runs 
            ORDER BY run_date DESC 
            LIMIT 1
        """
        latest_run = pd.read_sql_query(latest_month_query, conn)
        
        if not latest_run.empty:
            month = latest_run.iloc[0]['month_processed']
            st.info(f"📅 Showing data for: **{month}**")
            
            # Get details from the latest run
            details_str = pd.read_sql_query(
                "SELECT details FROM etl_runs WHERE month_processed = ? ORDER BY run_date DESC LIMIT 1",
                conn,
                params=(month,)
            )['details'].iloc[0]
            
            details = json.loads(details_str)
            
            # Display metrics from the latest month
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Energy Machines", details.get('energy_unique_machines', 0))
            with col2:
                st.metric("CSI Machines", details.get('csi_machines', 0))
            with col3:
                st.metric("MES Machines", details.get('mes_machines', 0))
            
            st.metric("Three-way Matches (This Month)", latest_run.iloc[0]['three_way_matches'])
            
            # Show match rate
            st.metric("Match Rate", f"{latest_run.iloc[0]['match_rate']:.1f}%")
        else:
            st.info("No data processed yet. Please upload files to begin.")
        
        conn.close()
        
    else:  # Cumulative view
        # Get inventory summary - all machines ever seen
        inventory_df = etl_module.get_machine_inventory_summary(active_only=False)
        
        if not inventory_df.empty:
            st.info("📊 Showing cumulative data from all processed months")
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            
            for idx, row in inventory_df.iterrows():
                if row['system_type'] == 'Energy':
                    with col1:
                        st.metric("Energy Machines (All Time)", row['machine_count'])
                elif row['system_type'] == 'CSI':
                    with col2:
                        st.metric("CSI Machines (All Time)", row['machine_count'])
                elif row['system_type'] == 'MES':
                    with col3:
                        st.metric("MES Machines (All Time)", row['machine_count'])
            
            # Get three-way match count
            conn = sqlite3.connect(etl_module.db_path)
            match_count = pd.read_sql_query(
                "SELECT COUNT(*) as count FROM three_way_matches", 
                conn
            )['count'][0]
            
            # Get list of all months processed
            months_processed = pd.read_sql_query(
                "SELECT DISTINCT month_processed FROM etl_runs ORDER BY month_processed",
                conn
            )['month_processed'].tolist()
            
            st.metric("Unique Three-way Matched Machines (All Time)", match_count)
            st.caption(f"Data accumulated from: {', '.join(months_processed)}")
            
            # Add historical machines dropdown
            st.markdown("### 🔍 Historical Machine Analysis")
            
            # Get the latest month
            latest_month_query = """
                SELECT month_processed FROM etl_runs 
                ORDER BY run_date DESC LIMIT 1
            """
            latest_month_result = pd.read_sql_query(latest_month_query, conn)
            
            if not latest_month_result.empty:
                latest_month = latest_month_result.iloc[0]['month_processed']
                
                # Query for machines that were historically matched but not in current month
                historical_not_current_query = f"""
                    SELECT DISTINCT m.machine_id, 
                           GROUP_CONCAT(m.month_year, ', ') as appeared_in_months
                    FROM machine_monthly_presence m
                    WHERE m.is_three_way_match = 1
                    AND m.system_type = 'Energy'
                    AND m.machine_id NOT IN (
                        SELECT machine_id 
                        FROM machine_monthly_presence 
                        WHERE month_year = '{latest_month}'
                        AND is_three_way_match = 1
                        AND system_type = 'Energy'
                    )
                    GROUP BY m.machine_id
                """
                
                historical_machines = pd.read_sql_query(historical_not_current_query, conn)
                
                if not historical_machines.empty:
                    with st.expander(f"📋 View machines not in {latest_month} ({len(historical_machines)} machines)"):
                        st.markdown(f"These machines were historically matched but are not present in {latest_month}:")
                        
                        # Display as a nice table
                        display_df = historical_machines.rename(columns={
                            'machine_id': 'Machine ID',
                            'appeared_in_months': 'Appeared In'
                        })
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        # Download option
                        csv = display_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Historical Machines CSV",
                            data=csv,
                            file_name=f"historical_machines_not_in_{latest_month.replace(' ', '_')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.success(f"✅ All historically matched machines are present in {latest_month}")
            
            conn.close()
            
        else:
            st.info("No data processed yet. Please upload files to begin.")
    
    # Add machine changes section only for Latest Month view
    if view_option == "Latest Month":
        st.markdown("### 🔄 Three-Way Match Changes Between Months")
        st.caption("Tracking machines that gained or lost three-way match status")
        
        conn = sqlite3.connect(etl_module.db_path)
        
        # Get all months in order (now includes year)
        months_df = pd.read_sql_query(
            "SELECT DISTINCT month_processed, run_date FROM etl_runs ORDER BY run_date",
            conn
        )
        
        if len(months_df) >= 2:
            # Compare last two months
            last_two_months = months_df['month_processed'].tail(2).tolist()
            prev_month, curr_month = last_two_months[0], last_two_months[1]
            
            # Find machines that appeared/disappeared using monthly presence table
            query_new = f"""
                SELECT DISTINCT machine_id 
                FROM machine_monthly_presence 
                WHERE month_year = '{curr_month}'
                AND system_type = 'Energy'
                AND is_three_way_match = 1
                AND machine_id NOT IN (
                    SELECT machine_id FROM machine_monthly_presence 
                    WHERE month_year = '{prev_month}'
                    AND system_type = 'Energy'
                    AND is_three_way_match = 1
                )
            """
            
            query_lost = f"""
                SELECT DISTINCT machine_id 
                FROM machine_monthly_presence 
                WHERE month_year = '{prev_month}'
                AND system_type = 'Energy'
                AND is_three_way_match = 1
                AND machine_id NOT IN (
                    SELECT machine_id FROM machine_monthly_presence 
                    WHERE month_year = '{curr_month}'
                    AND system_type = 'Energy'
                    AND is_three_way_match = 1
                )
            """
            
            new_machines = pd.read_sql_query(query_new, conn)
            lost_machines = pd.read_sql_query(query_lost, conn)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success(f"✅ New three-way matches in {curr_month}: {len(new_machines)} machine{'s' if len(new_machines) != 1 else ''}")
                if len(new_machines) > 0:
                    with st.expander("View new three-way matches"):
                        st.write(new_machines['machine_id'].tolist())
            
            with col2:
                st.warning(f"⚠️ Lost three-way matches from {prev_month}: {len(lost_machines)} machine{'s' if len(lost_machines) != 1 else ''}")
                if len(lost_machines) > 0:
                    with st.expander("View lost three-way matches"):
                        st.write(lost_machines['machine_id'].tolist())
        else:
            st.info("Process at least 2 months to see changes between months")
        
        conn.close()


def render_historical_runs(etl_module):
    """Render historical ETL runs with delete and reorder functionality"""
    st.markdown("### 📈 Historical Processing Runs")
    
    # Initialize session state for bulk selection
    if 'selected_runs' not in st.session_state:
        st.session_state.selected_runs = []
    if 'bulk_select_mode' not in st.session_state:
        st.session_state.bulk_select_mode = False
    
    # Toolbar
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        if st.button("🔄 Bulk Select", type="secondary" if not st.session_state.bulk_select_mode else "primary"):
            st.session_state.bulk_select_mode = not st.session_state.bulk_select_mode
            st.session_state.selected_runs = []
    
    with col2:
        sort_option = st.selectbox(
            "Sort By",
            ["Custom Order", "Date (Newest)", "Date (Oldest)", "Month", "Match Rate"],
            key="sort_option"
        )
        
        # Map sort options to order_by parameter
        sort_mapping = {
            "Custom Order": "display_order",
            "Date (Newest)": "date_desc",
            "Date (Oldest)": "date_asc",
            "Month": "month",
            "Match Rate": "match_rate"
        }
        order_by = sort_mapping[sort_option]
    
    with col3:
        if st.button("↺ Reset Order"):
            etl_module.reset_display_order()
            st.success("Order reset to chronological!")
            st.rerun()
    
    with col4:
        if st.session_state.bulk_select_mode and len(st.session_state.selected_runs) > 0:
            if st.button(f"🗑️ Delete Selected ({len(st.session_state.selected_runs)})", type="primary"):
                st.session_state.confirm_bulk_delete = True
    
    # Bulk delete confirmation dialog
    if st.session_state.get('confirm_bulk_delete', False):
        st.warning(f"⚠️ Are you sure you want to delete {len(st.session_state.selected_runs)} selected records?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, Delete All", type="primary", key="confirm_yes"):
                etl_module.delete_multiple_runs(st.session_state.selected_runs)
                st.success(f"Deleted {len(st.session_state.selected_runs)} records!")
                st.session_state.selected_runs = []
                st.session_state.bulk_select_mode = False
                st.session_state.confirm_bulk_delete = False
                st.rerun()
        with col_no:
            if st.button("Cancel", key="confirm_no"):
                st.session_state.confirm_bulk_delete = False
                st.rerun()
    
    # Get data
    history_df = etl_module.get_historical_summary(order_by=order_by)
    
    if not history_df.empty:
        # Format the dataframe
        history_df['run_date_formatted'] = pd.to_datetime(history_df['run_date']).dt.strftime('%Y-%m-%d %H:%M')
        history_df['match_rate_formatted'] = history_df['match_rate'].apply(lambda x: f"{x:.1f}%")
        
        # Display records with actions
        for idx, row in history_df.iterrows():
            col_check, col_data, col_actions = st.columns([0.5, 8, 1.5])
            
            # Checkbox for bulk selection
            with col_check:
                if st.session_state.bulk_select_mode:
                    if st.checkbox("", key=f"select_{row['id']}", value=row['id'] in st.session_state.selected_runs):
                        if row['id'] not in st.session_state.selected_runs:
                            st.session_state.selected_runs.append(row['id'])
                    else:
                        if row['id'] in st.session_state.selected_runs:
                            st.session_state.selected_runs.remove(row['id'])
            
            # Data display
            with col_data:
                # Create a container for better formatting
                with st.container():
                    data_cols = st.columns([2, 3, 1.5, 1.5])
                    with data_cols[0]:
                        st.write(f"**{row['month_processed']}**")
                    with data_cols[1]:
                        st.write(row['run_date_formatted'])
                    with data_cols[2]:
                        st.write(f"Matches: {row['three_way_matches']}")
                    with data_cols[3]:
                        st.write(f"Rate: {row['match_rate_formatted']}")
            
            # Action buttons
            with col_actions:
                if not st.session_state.bulk_select_mode:
                    action_cols = st.columns(3)
                    
                    # Up button
                    with action_cols[0]:
                        if st.button("↑", key=f"up_{row['id']}", help="Move up"):
                            etl_module.update_display_order(row['id'], 'up')
                            st.rerun()
                    
                    # Down button
                    with action_cols[1]:
                        if st.button("↓", key=f"down_{row['id']}", help="Move down"):
                            etl_module.update_display_order(row['id'], 'down')
                            st.rerun()
                    
                    # Delete button
                    with action_cols[2]:
                        if st.button("🗑️", key=f"del_{row['id']}", help="Delete"):
                            # Store the ID to delete in session state
                            st.session_state[f"confirm_delete_{row['id']}"] = True
                            st.rerun()
            
            # Confirmation dialog for individual deletion
            if st.session_state.get(f"confirm_delete_{row['id']}", False):
                with st.container():
                    st.warning(f"Are you sure you want to delete the {row['month_processed']} run from {row['run_date_formatted']}?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, Delete", key=f"yes_del_{row['id']}", type="primary"):
                            etl_module.delete_etl_run(row['id'])
                            st.success("Record deleted!")
                            del st.session_state[f"confirm_delete_{row['id']}"]
                            st.rerun()
                    with col_no:
                        if st.button("Cancel", key=f"no_del_{row['id']}"):
                            del st.session_state[f"confirm_delete_{row['id']}"]
                            st.rerun()
            
            st.divider()
        
        # Summary statistics
        st.markdown("#### 📊 Summary Statistics")
        
        # Calculate statistics
        total_runs = len(history_df)
        avg_match_rate = history_df['match_rate'].mean()
        
        stat_cols = st.columns(2)
        with stat_cols[0]:
            st.metric("Total Runs", total_runs)
        with stat_cols[1]:
            st.metric("Average Match Rate", f"{avg_match_rate:.1f}%")
        
        # Trend chart
        if len(history_df) > 1:
            st.markdown("#### 📈 Match Rate Trend")
            # Create a proper dataframe for the chart
            chart_df = history_df.copy()
            chart_df['match_rate_num'] = chart_df['match_rate']
            
            # Parse month_processed to create a proper date for x-axis
            def parse_month_year(month_str):
                """Convert 'Month Year' or 'Month' to a date object"""
                if ' ' in month_str:
                    # Already has year
                    month, year = month_str.split(' ')
                else:
                    # Just month, assume current year
                    month = month_str
                    year = str(datetime.now().year)
                
                # Convert month name to number
                month_num = datetime.strptime(month, '%B').month
                # Create date object (first day of the month)
                return datetime(int(year), month_num, 1)
            
            chart_df['month_date'] = chart_df['month_processed'].apply(parse_month_year)
            chart_df = chart_df.sort_values('month_date')  # Ensure chronological order
            
            # Use altair for better control
            import altair as alt
            
            chart = alt.Chart(chart_df).mark_line(point=True).encode(
                x=alt.X('month_date:T', 
                    title='Month',
                    axis=alt.Axis(format='%b %Y')  # Show as "Jan 2025", "Feb 2025", etc.
                ),
                y=alt.Y('match_rate_num:Q', 
                    title='Match Rate (%)', 
                    scale=alt.Scale(domain=[0, 100])
                ),
                tooltip=[
                    alt.Tooltip('month_processed:N', title='Month'),
                    alt.Tooltip('run_date_formatted:N', title='Processed On'),
                    alt.Tooltip('match_rate_formatted:N', title='Match Rate'),
                    alt.Tooltip('three_way_matches:Q', title='Three-way Matches')
                ]
            ).properties(
                height=300
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
        
        # Export option
        st.markdown("#### 💾 Export Data")
        csv = history_df[['month_processed', 'run_date', 'three_way_matches', 'match_rate']].to_csv(index=False)
        st.download_button(
            label="📥 Download History as CSV",
            data=csv,
            file_name="etl_run_history.csv",
            mime="text/csv"
        )
        
    else:
        st.info("No historical runs yet. Process your first month to see history.")


# Module ready for import
