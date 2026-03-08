#!/usr/bin/env python3
"""
Manufacturing Data Processing Script for January to June 2025
Processes all monthly data files using the existing ETL pipeline in chronological order.
"""

import os
import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import sqlite3

# Add the parent directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the existing ETL solution and module
from core.enhanced_etl_solution_CURRENT import EnhancedSmartManufacturingETL
from modules.etl_module import ETLPipelineModule

class ManufacturingDataProcessor:
    def __init__(self, data_root_path):
        """
        Initialize the processor with data root path
        
        Args:
            data_root_path: Root path to the 2025 DataSet(JAN to JUN) directory
        """
        self.data_root_path = Path(data_root_path)
        self.energy_dir = self.data_root_path / "Energy Usage 1hr Interval(JAN to JUN)"
        self.csi_dir = self.data_root_path / "CSI Monthly(JAN to JUN)"
        self.mes_dir = self.data_root_path / "MES Monthly(JAN to JUN)"
        
        # Initialize ETL components
        self.etl_pipeline = ETLPipelineModule()
        
        # Define months in chronological order
        self.months = [
            "January", "February", "March", "April", "May", "June"
        ]
        
        # Define file mappings for each month
        self.file_mappings = self._create_file_mappings()
        
    def _create_file_mappings(self):
        """Create mappings between months and their corresponding data files"""
        mappings = {}
        
        # Energy files mapping (multiple files per month)
        energy_files = {
            "January": [
                "能耗、費用報表Jan(1-10).xlsx",
                "能耗、費用報表Jan(11-21).xlsx", 
                "能耗、費用報表Jan(22-31).xlsx"
            ],
            "February": [
                "能耗、費用報表Feb(1-10).xlsx",
                "能耗、費用報表Feb(11-21).xlsx",
                "能耗、費用報表Feb(22-28).xlsx"
            ],
            "March": [
                "能耗、費用報表March(1-10).xlsx",
                "能耗、費用報表March(11-21).xlsx",
                "能耗、費用報表March(22-31).xlsx"
            ],
            "April": [
                "能耗、費用報表April(1-10).xlsx",
                "能耗、費用報表April(11-21).xlsx",
                "能耗、費用報表April(22-30).xlsx"
            ],
            "May": [
                "能耗、費用報表May(1-31).xlsx"
            ],
            "June": [
                "能耗、費用報表June(1-30).xlsx"
            ]
        }
        
        # CSI files mapping (one file per month)
        csi_files = {
            "January": "CSI印刷心電圖報表Jan.xlsx",
            "February": "CSI印刷心電圖報表Feb.xlsx",
            "March": "CSI印刷心電圖報表March.xlsx",
            "April": "CSI印刷心電圖報表April.xlsx",
            "May": "CSI印刷心電圖報表May.xlsx",
            "June": "CSI印刷心電圖報表June.xlsx"
        }
        
        # MES files mapping (one file per month)
        mes_files = {
            "January": "MES生產數據Jan(Printer).xlsx",
            "February": "MES生產數據Feb(Printer).xlsx",
            "March": "MES生產數據March(Printer).xlsx",
            "April": "MES生產數據April(Printer).xlsx",
            "May": "MES生產數據May(Printer).xlsx",
            "June": "MES生產數據June(Printer).xlsx"
        }
        
        # Combine all mappings
        for month in self.months:
            mappings[month] = {
                "energy": energy_files[month],
                "csi": csi_files[month],
                "mes": mes_files[month]
            }
            
        return mappings
    
    def list_all_files(self):
        """List all Excel files in each directory and verify file structure"""
        print("=" * 80)
        print("MANUFACTURING DATA FILES INVENTORY")
        print("=" * 80)
        
        # Energy files
        print("\n1. ENERGY USAGE FILES:")
        print(f"   Directory: {self.energy_dir}")
        if self.energy_dir.exists():
            energy_files = sorted([f.name for f in self.energy_dir.glob("*.xlsx") if not f.name.startswith("~$")])
            for i, file in enumerate(energy_files, 1):
                print(f"   {i:2d}. {file}")
            print(f"   Total: {len(energy_files)} files")
        else:
            print("   ERROR: Directory not found!")
        
        # CSI files
        print("\n2. CSI PRODUCTION FILES:")
        print(f"   Directory: {self.csi_dir}")
        if self.csi_dir.exists():
            csi_files = sorted([f.name for f in self.csi_dir.glob("*.xlsx") if not f.name.startswith("~$")])
            for i, file in enumerate(csi_files, 1):
                print(f"   {i:2d}. {file}")
            print(f"   Total: {len(csi_files)} files")
        else:
            print("   ERROR: Directory not found!")
        
        # MES files
        print("\n3. MES PLANNING FILES:")
        print(f"   Directory: {self.mes_dir}")
        if self.mes_dir.exists():
            mes_files = sorted([f.name for f in self.mes_dir.glob("*.xlsx") if not f.name.startswith("~$")])
            for i, file in enumerate(mes_files, 1):
                print(f"   {i:2d}. {file}")
            print(f"   Total: {len(mes_files)} files")
        else:
            print("   ERROR: Directory not found!")
    
    def identify_monthly_files(self):
        """Identify which files correspond to each month"""
        print("\n" + "=" * 80)
        print("MONTHLY FILE IDENTIFICATION")
        print("=" * 80)
        
        for month in self.months:
            print(f"\n{month.upper()} 2025:")
            print("-" * 40)
            
            # Energy files for this month
            energy_files = self.file_mappings[month]["energy"]
            print(f"Energy Files ({len(energy_files)}):")
            for i, file in enumerate(energy_files, 1):
                file_path = self.energy_dir / file
                status = "✓ EXISTS" if file_path.exists() else "✗ MISSING"
                print(f"  {i}. {file} - {status}")
            
            # CSI file for this month
            csi_file = self.file_mappings[month]["csi"]
            file_path = self.csi_dir / csi_file
            status = "✓ EXISTS" if file_path.exists() else "✗ MISSING"
            print(f"CSI File: {csi_file} - {status}")
            
            # MES file for this month
            mes_file = self.file_mappings[month]["mes"]
            file_path = self.mes_dir / mes_file
            status = "✓ EXISTS" if file_path.exists() else "✗ MISSING"
            print(f"MES File: {mes_file} - {status}")
    
    def validate_all_files(self):
        """Validate that all required files exist"""
        missing_files = []
        
        for month in self.months:
            # Check energy files
            for energy_file in self.file_mappings[month]["energy"]:
                file_path = self.energy_dir / energy_file
                if not file_path.exists():
                    missing_files.append(f"{month} Energy: {energy_file}")
            
            # Check CSI file
            csi_file = self.file_mappings[month]["csi"]
            file_path = self.csi_dir / csi_file
            if not file_path.exists():
                missing_files.append(f"{month} CSI: {csi_file}")
            
            # Check MES file
            mes_file = self.file_mappings[month]["mes"]
            file_path = self.mes_dir / mes_file
            if not file_path.exists():
                missing_files.append(f"{month} MES: {mes_file}")
        
        return missing_files
    
    def process_single_month(self, month, year=2025):
        """Process data for a single month"""
        print(f"\n{'='*60}")
        print(f"PROCESSING {month.upper()} {year}")
        print(f"{'='*60}")
        
        try:
            # Get file paths for this month
            energy_files = self.file_mappings[month]["energy"]
            csi_file = self.file_mappings[month]["csi"]
            mes_file = self.file_mappings[month]["mes"]
            
            # Build full file paths
            energy_paths = [str(self.energy_dir / f) for f in energy_files]
            csi_path = str(self.csi_dir / csi_file)
            mes_path = str(self.mes_dir / mes_file)
            
            print(f"Energy files: {len(energy_paths)} files")
            for i, path in enumerate(energy_paths, 1):
                print(f"  {i}. {Path(path).name}")
            print(f"CSI file: {Path(csi_path).name}")
            print(f"MES file: {Path(mes_path).name}")
            
            # Initialize ETL pipeline
            etl = EnhancedSmartManufacturingETL()
            
            # Extract data from files
            print("\n1. Extracting data from files...")
            etl.extract_all_sources(energy_paths, csi_path, mes_path)
            
            # Create machine mappings
            print("2. Creating machine mappings...")
            mapping_results = etl.create_comprehensive_mapping()
            
            # Save results to database
            month_year = f"{month} {year}"
            print("3. Saving results to database...")
            self.etl_pipeline.save_etl_results(mapping_results, month_year)
            
            # Generate reports
            print("4. Generating reports...")
            report_filename = f"{month.lower()}_{year}_etl_report.xlsx"
            etl.generate_enhanced_report(report_filename)
            
            # Save mapping results as JSON
            json_filename = f"{month.lower()}_{year}_etl_report_mappings.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                # Convert numpy types to native Python types for JSON serialization
                serializable_results = self._convert_to_serializable(mapping_results)
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            
            # Print summary
            stats = mapping_results['mapping_stats']
            print(f"\n✓ {month} {year} Processing Complete!")
            print(f"   - Energy records: {stats['energy_original_rows']:,}")
            print(f"   - Three-way matches: {stats['three_way_matches']}")
            print(f"   - MES coverage: {stats['mes_coverage_percent']}")
            print(f"   - Excel report: {report_filename}")
            print(f"   - JSON mappings: {json_filename}")
            
            return mapping_results, etl
            
        except Exception as e:
            print(f"❌ Error processing {month} {year}: {str(e)}")
            raise
    
    def _convert_to_serializable(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
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
    
    def process_all_months(self, year=2025):
        """Process all months from January to June in chronological order"""
        print("\n" + "="*80)
        print("STARTING COMPREHENSIVE DATA PROCESSING")
        print("Processing months: January to June 2025")
        print("="*80)
        
        # Validate all files first
        missing_files = self.validate_all_files()
        if missing_files:
            print("\n❌ ERROR: Missing required files:")
            for file in missing_files:
                print(f"   - {file}")
            print("\nPlease ensure all files are present before processing.")
            return False
        
        print("\n✓ All required files found. Beginning processing...")
        
        results_summary = []
        total_start_time = datetime.now()
        
        # Process each month
        for i, month in enumerate(self.months, 1):
            month_start_time = datetime.now()
            
            try:
                print(f"\n[{i}/6] Processing {month}...")
                mapping_results, etl = self.process_single_month(month, year)
                
                # Track results
                stats = mapping_results['mapping_stats']
                month_duration = datetime.now() - month_start_time
                
                results_summary.append({
                    'month': month,
                    'year': year,
                    'energy_records': stats['energy_original_rows'],
                    'three_way_matches': stats['three_way_matches'],
                    'mes_coverage': stats['mes_coverage_percent'],
                    'processing_time': str(month_duration).split('.')[0],
                    'status': 'SUCCESS'
                })
                
                print(f"✓ {month} completed in {month_duration}")
                
            except Exception as e:
                print(f"❌ Failed to process {month}: {str(e)}")
                results_summary.append({
                    'month': month,
                    'year': year,
                    'status': 'FAILED',
                    'error': str(e)
                })
                # Continue with other months even if one fails
                continue
        
        # Generate final summary
        total_duration = datetime.now() - total_start_time
        self._generate_processing_summary(results_summary, total_duration)
        
        return results_summary
    
    def _generate_processing_summary(self, results_summary, total_duration):
        """Generate and display processing summary"""
        print("\n" + "="*80)
        print("PROCESSING SUMMARY")
        print("="*80)
        
        successful = [r for r in results_summary if r['status'] == 'SUCCESS']
        failed = [r for r in results_summary if r['status'] == 'FAILED']
        
        print(f"Total processing time: {str(total_duration).split('.')[0]}")
        print(f"Months processed successfully: {len(successful)}/6")
        print(f"Months failed: {len(failed)}/6")
        
        if successful:
            print(f"\n✓ SUCCESSFUL MONTHS:")
            total_records = 0
            total_matches = 0
            
            for result in successful:
                total_records += result['energy_records']
                total_matches += result['three_way_matches']
                print(f"   {result['month']} {result['year']}: "
                      f"{result['energy_records']:,} records, "
                      f"{result['three_way_matches']} matches, "
                      f"{result['mes_coverage']} coverage, "
                      f"({result['processing_time']})")
            
            print(f"\n   TOTALS: {total_records:,} energy records, {total_matches} three-way matches")
        
        if failed:
            print(f"\n❌ FAILED MONTHS:")
            for result in failed:
                print(f"   {result['month']} {result['year']}: {result['error']}")
        
        # Generate summary CSV
        summary_df = pd.DataFrame(results_summary)
        summary_filename = f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        summary_df.to_csv(summary_filename, index=False)
        print(f"\n📊 Processing summary saved to: {summary_filename}")
    
    def get_database_summary(self):
        """Get summary of all processed data from database"""
        try:
            conn = sqlite3.connect(self.etl_pipeline.db_path)
            
            # Get all ETL runs
            runs_df = pd.read_sql_query("""
                SELECT month_processed, run_date, three_way_matches, match_rate, details
                FROM etl_runs
                ORDER BY run_date
            """, conn)
            
            # Get machine inventory
            inventory_df = pd.read_sql_query("""
                SELECT system_type, COUNT(DISTINCT machine_id) as machine_count
                FROM machine_inventory
                WHERE is_active = 1
                GROUP BY system_type
            """, conn)
            
            # Get three-way matches
            matches_df = pd.read_sql_query("""
                SELECT COUNT(*) as total_matches
                FROM three_way_matches
            """, conn)
            
            conn.close()
            
            print("\n" + "="*60)
            print("DATABASE SUMMARY")
            print("="*60)
            
            print(f"\nProcessed months: {len(runs_df)}")
            for _, run in runs_df.iterrows():
                print(f"  {run['month_processed']}: {run['three_way_matches']} matches ({run['match_rate']:.1f}%)")
            
            print(f"\nActive machine inventory:")
            for _, inv in inventory_df.iterrows():
                print(f"  {inv['system_type']}: {inv['machine_count']} machines")
            
            print(f"\nTotal unique three-way matches: {matches_df.iloc[0]['total_matches']}")
            
            return runs_df, inventory_df, matches_df
            
        except Exception as e:
            print(f"Error accessing database: {str(e)}")
            return None, None, None


def main():
    """Main execution function"""
    # Define the data root path
    data_root_path = "/Users/rayfung/Documents/VCC/LeoPaper/2025 DataSet(JAN to JUN)"
    
    # Initialize processor
    processor = ManufacturingDataProcessor(data_root_path)
    
    print("MANUFACTURING DATA PROCESSOR")
    print("Processing January to June 2025 data")
    print(f"Data source: {data_root_path}")
    
    # Step 1: List all files
    processor.list_all_files()
    
    # Step 2: Identify monthly file mappings
    processor.identify_monthly_files()
    
    # Step 3: Process all months
    results = processor.process_all_months()
    
    # Step 4: Show database summary
    processor.get_database_summary()
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE!")
    print("="*80)
    print("Check the generated files:")
    print("- Excel reports: *_etl_report.xlsx")
    print("- JSON mappings: *_etl_report_mappings.json")
    print("- Processing summary: processing_summary_*.csv")
    print("- Database: manufacturing_data.db")


if __name__ == "__main__":
    main()