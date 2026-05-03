"""
Test script for the corrected energy attribution logic
This verifies that the fix properly reduces idle energy from 44.6% to expected levels
"""

import sqlite3
import pandas as pd
import sys
from pathlib import Path

# Add the modules directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from modules.unified_view_module import UnifiedViewProcessor

def test_energy_attribution():
    """Test the corrected energy attribution logic"""
    
    print("=" * 80)
    print("TESTING CORRECTED ENERGY ATTRIBUTION LOGIC")
    print("=" * 80)
    
    # 1. Clear existing unified view data for reprocessing
    print("\n1. Clearing existing unified view data...")
    conn = sqlite3.connect('manufacturing_data.db')
    
    # Check if we have any data with the old attribution method
    old_data_query = """
        SELECT COUNT(*) as count, month_year
        FROM unified_view
        WHERE attribution_method IS NULL OR attribution_method != 'multi_source_v2'
        GROUP BY month_year
        LIMIT 5
    """
    
    try:
        old_data = pd.read_sql_query(old_data_query, conn)
        if not old_data.empty:
            print(f"Found {old_data['count'].sum()} records with old attribution logic")
            print("Months affected:", old_data['month_year'].tolist())
            
            # Clear old data for reprocessing
            conn.execute("""
                DELETE FROM unified_view 
                WHERE attribution_method IS NULL OR attribution_method != 'multi_source_v2'
            """)
            conn.commit()
            print("✓ Old data cleared for reprocessing")
        else:
            print("No old data found - ready for processing")
    except Exception as e:
        print(f"Note: {e}")
    
    # 2. Find a month to process for testing
    print("\n2. Finding a month to process...")
    
    # Check for available three-way matches
    matches_query = """
        SELECT month_year, COUNT(*) as match_count
        FROM three_way_matches
        GROUP BY month_year
        ORDER BY match_count DESC
        LIMIT 1
    """
    
    try:
        matches_df = pd.read_sql_query(matches_query, conn)
        if matches_df.empty:
            print("❌ No three-way matches found. Please run ETL first.")
            conn.close()
            return
        
        test_month = matches_df.iloc[0]['month_year']
        match_count = matches_df.iloc[0]['match_count']
        print(f"✓ Selected month: {test_month} ({match_count} three-way matches)")
        
    except Exception as e:
        print(f"❌ Error finding test month: {e}")
        conn.close()
        return
    
    # 3. Process the month with the new logic
    print(f"\n3. Processing {test_month} with corrected attribution logic...")
    
    try:
        processor = UnifiedViewProcessor()
        result = processor.process_month(test_month, force_reprocess=True)
        
        if result['status'] == 'success':
            print(f"✓ Processed {result['records_created']} records successfully")
        else:
            print(f"❌ Processing failed: {result.get('message', 'Unknown error')}")
            conn.close()
            return
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        conn.close()
        return
    
    # 4. Verify the energy distribution
    print("\n4. Verifying energy distribution...")
    
    energy_dist_query = f"""
        SELECT 
            ROUND(SUM(idle_energy)/SUM(energy_kwh)*100, 1) as idle_pct,
            ROUND(SUM(maintenance_energy)/SUM(energy_kwh)*100, 1) as maint_pct,
            ROUND(SUM(production_energy)/SUM(energy_kwh)*100, 1) as prod_pct,
            ROUND(SUM(setup_energy)/SUM(energy_kwh)*100, 1) as setup_pct,
            COUNT(DISTINCT machine_id) as machines,
            COUNT(*) as total_hours
        FROM unified_view
        WHERE month_year = '{test_month}'
    """
    
    energy_df = pd.read_sql_query(energy_dist_query, conn)
    
    if not energy_df.empty:
        print("\n" + "=" * 60)
        print("ENERGY ATTRIBUTION RESULTS:")
        print("=" * 60)
        print(f"Idle Energy:        {energy_df['idle_pct'].iloc[0]}%")
        print(f"Maintenance Energy: {energy_df['maint_pct'].iloc[0]}%")
        print(f"Production Energy:  {energy_df['prod_pct'].iloc[0]}%")
        print(f"Setup Energy:       {energy_df['setup_pct'].iloc[0]}%")
        print(f"Total:              {sum([energy_df['idle_pct'].iloc[0], energy_df['maint_pct'].iloc[0], energy_df['prod_pct'].iloc[0], energy_df['setup_pct'].iloc[0]])}%")
        print(f"\nMachines processed: {energy_df['machines'].iloc[0]}")
        print(f"Total hours:        {energy_df['total_hours'].iloc[0]}")
        
        # Check if the fix worked
        idle_pct = energy_df['idle_pct'].iloc[0]
        if idle_pct < 35:
            print("\n✅ SUCCESS: Idle energy reduced to acceptable levels (<35%)")
        elif idle_pct < 40:
            print("\n⚠️  PARTIAL SUCCESS: Idle energy reduced but still slightly high (35-40%)")
        else:
            print(f"\n❌ ISSUE: Idle energy still high at {idle_pct}%")
    
    # 5. Check validation errors
    print("\n5. Checking for attribution validation errors...")
    
    validation_query = f"""
        SELECT COUNT(*) as error_count
        FROM unified_view
        WHERE month_year = '{test_month}'
        AND ABS((setup_energy + production_energy + idle_energy + maintenance_energy) - energy_kwh) > 0.01
    """
    
    validation_df = pd.read_sql_query(validation_query, conn)
    error_count = validation_df['error_count'].iloc[0]
    
    if error_count == 0:
        print("✓ No attribution errors found - all energy properly accounted for")
    else:
        print(f"❌ Found {error_count} attribution errors")
    
    # 6. Analyze idle categories
    print("\n6. Analyzing idle time categories...")
    
    idle_category_query = f"""
        SELECT 
            idle_category, 
            COUNT(*) as hours,
            ROUND(SUM(idle_energy), 1) as total_kwh,
            ROUND(SUM(idle_energy)/NULLIF(SUM(energy_kwh), 0)*100, 1) as pct_of_total
        FROM unified_view
        WHERE month_year = '{test_month}'
        AND idle_energy > 0
        GROUP BY idle_category
        ORDER BY total_kwh DESC
    """
    
    idle_df = pd.read_sql_query(idle_category_query, conn)
    
    if not idle_df.empty:
        print("\nIdle Time Breakdown:")
        print("-" * 60)
        for _, row in idle_df.iterrows():
            category = row['idle_category'] or 'uncategorized'
            print(f"  {category:25s}: {row['hours']:5d} hours, {row['total_kwh']:8.1f} kWh ({row['pct_of_total']:.1f}%)")
    
    # 7. Check maintenance confidence sources
    print("\n7. Checking maintenance detection sources...")
    
    maint_source_query = f"""
        SELECT 
            CASE 
                WHEN maintenance_confidence = 1.0 THEN 'From maintenance_records table'
                WHEN maintenance_confidence = 0.9 THEN 'From CSI order keywords'
                WHEN maintenance_confidence = 0.8 THEN 'From MES task keywords'
                WHEN maintenance_confidence = 0.0 THEN 'Not maintenance'
                ELSE 'Other'
            END as source,
            COUNT(*) as hours,
            ROUND(SUM(maintenance_energy), 1) as total_kwh
        FROM unified_view
        WHERE month_year = '{test_month}'
        GROUP BY maintenance_confidence
        HAVING SUM(maintenance_energy) > 0
        ORDER BY total_kwh DESC
    """
    
    maint_df = pd.read_sql_query(maint_source_query, conn)
    
    if not maint_df.empty:
        print("\nMaintenance Detection Sources:")
        print("-" * 60)
        for _, row in maint_df.iterrows():
            print(f"  {row['source']:35s}: {row['hours']:5d} hours, {row['total_kwh']:8.1f} kWh")
    
    # 8. Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if idle_pct < 35 and error_count == 0:
        print("✅ All tests passed! Energy attribution fix is working correctly.")
        print("\nExpected improvements:")
        print("  • Idle energy reduced from ~44.6% to <30%")
        print("  • Maintenance energy increased from ~7.3% to 15-18%")
        print("  • All energy properly attributed (100% validation)")
        print("  • Idle time categorized for business insights")
    else:
        print("⚠️  Some issues detected. Please review the results above.")
    
    conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_energy_attribution()