# 🏭 Smart Manufacturing ETL + ML Platform

Transform 5+ hours of manual Excel work into 5-minute automated insights!
This Streamlit application integrates Energy, CSI, and MES systems for intelligent manufacturing optimization.

## 🚀 Features

- **ETL Pipeline**: Automated data extraction and machine matching across three systems
- **Energy Analysis**: Detailed energy attribution and efficiency tracking
- **Production Optimization**: Material transition analysis, intelligent scheduling, and team insights
- **ML-Ready**: Prepared infrastructure for predictive analytics (Stage 3)

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## 🛠️ Installation

1. Navigate to the app directory:
```bash
cd smart_manufacturing_app
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## 🏃 Running the Application

Quick launch (recommended)
```bash
bash scripts/bootstrap_py311_and_run.sh
```
Then open:
```
http://localhost:8502
```

Alternative
```bash
streamlit run app.py
```
(The app is configured to use port 8502 via `.streamlit/config.toml`.)

## 📊 Application Pages

### 🏠 Overview
- Key metrics dashboard
- Energy attribution pie chart
- Daily production trends

### 🔄 ETL Pipeline
- Data volume statistics
- Machine matching results
- Three-way matches table

### 📊 Unified View
- Hourly integrated data
- Feature statistics
- Data quality metrics

### ⚡ Energy Analysis
- Energy usage patterns over time
- Machine efficiency rankings
- Hourly consumption patterns

### 📈 ML Predictions
- Trains & serves the production-efficiency RandomForest model (R² ≈ 0.75)
- Live scoring with driver insights and confidence bands
- Logs recommended maintenance actions to `ml_action_log`

### 🎯 Optimization
- Live production predictions with driver narratives
- Intelligent production scheduling with estimated savings
- Team × Task insights and maintenance hotspots

## 📁 Project Structure

```
smart_manufacturing_app/
│
├── 📱 app.py                    # Main Streamlit application
├── 🗄️ manufacturing_data.db     # SQLite database with all processed data
├── 📋 requirements.txt          # Python dependencies
├── 🚀 run_app.sh               # Shell script to run the application
│
├── 📂 modules/                  # Core application modules
│   ├── etl_module.py           # ETL processing with UI
│   ├── unified_view_module.py  # Unified view with speed-based allocation
│   ├── euvg_module.py          # Energy Usage Visualization Grid
│   ├── ml_module.py            # Machine Learning module
│   └── overview_module.py      # System overview module
│
├── 📂 core/                     # Core business logic
│   ├── enhanced_etl_solution_CURRENT.py  # ETL processing engine
│   └── utils.py                # Utility functions
│
├── 📂 scripts/                  # Batch processing scripts
│   └── process_jan_to_june_2025.py  # Historical data processing
│
├── 📂 data/                     # Sample data files
│   ├── CSI印刷心電圖報表June.xlsx
│   ├── MES生產數據JunePrinter.xlsx
│   └── 能耗、費用報表June(1-30).xlsx
│
├── 📂 etl_outputs/              # ETL processing results
│   ├── [month]_2025_etl_report.xlsx     # Monthly ETL reports
│   ├── [month]_2025_etl_report_mappings.json
│   └── old_versions/           # Archived older ETL reports
│
├── 📂 docs/                     # Documentation
│   ├── CLAUDE.md               # AI assistant context
│   └── [other documentation]
│
├── 📂 backups/                  # Database backups
│   └── unified_view_backup.db
│
├── 📂 archived_files/           # Archived/deprecated files
│   ├── test_scripts/           # Development & test scripts
│   └── old_reports/            # Old report versions
│
└── 📂 temp_uploads/            # Temporary file uploads
```

## 🔧 Configuration

The app uses June 2025 data by default. To use different data:

1. Place your data files in the `data/` folder
2. Update file paths in `app.py` (lines 44-47)
3. Ensure files follow the same format as sample data

## 📈 Data Requirements

### Energy Data (Excel)
- Skip first 6 rows
- Columns: machine, datetime, electricity_kwh, electricity_cost

### CSI Data (Excel)
- Machine ID column: 機台編號
- Production columns: 開始時間, 結束時間, 正品數量
- Team columns: 機長姓名1, 機組人員姓名1-4

### MES Data (Excel)
- Resource column: 資源
- Order column: 作業
- Status and task information

## 🚨 Troubleshooting

### macOS segfault when launching Streamlit
- Symptom: `Segmentation fault: 11` when importing `streamlit`, `numpy`, etc.
- Fix: Use the provided Python 3.11 environment.
  - Run: `bash scripts/bootstrap_py311_and_run.sh`
  - Or manually: `.conda311/bin/streamlit run app.py --server.port 8502 --server.address 0.0.0.0`

### "Failed to load data" error
- Check all data files exist in the `data/` folder
- Verify file formats match expected structure
- Ensure file paths are correct

### Slow performance
- The initial data load is cached
- Clearing Streamlit cache (`st.cache_data.clear()`) can recover from corrupted states

## ✅ Verification Checklist

Run these commands after updating data or code to ensure the intelligent pipeline is healthy:

```bash
# 1. Regenerate unified view (if ETL inputs changed)
python3 scripts/process_jan_to_june_2025.py

# 2. Retrain and persist the production-efficiency model
python3 core/ml_trainer.py

# 3. Smoke-test inference + ROI helpers
python3 core/ml_predictor.py

# 4. Quick dataset sanity check
sqlite3 manufacturing_data.db "SELECT month_year, COUNT(*), AVG(kwh_per_unit) FROM unified_view GROUP BY month_year;"
```

Run `streamlit run app.py` (or `bash scripts/bootstrap_py311_and_run.sh`) afterward to interact with the updated dashboards, ML recommendations, and maintenance action log.
- Subsequent page changes should be fast
- Clear cache with 'c' then 'Clear cache' in Streamlit menu

### Missing features
- Some features require complete data
- Check console for specific error messages

## 🔮 Future Enhancements (Stage 3 & 4)

- [ ] Energy consumption forecasting
- [ ] Anomaly detection algorithms
- [ ] Predictive maintenance alerts
- [ ] Real-time data integration
- [ ] API endpoints for external systems
- [ ] Cloud deployment

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review data format requirements
3. Ensure all dependencies are installed

## 🎯 Quick Start Example

```python
# After installation, simply run:
streamlit run app.py

# The app will:
# 1. Load and process June manufacturing data
# 2. Create machine mappings across systems
# 3. Generate hourly unified view
# 4. Display interactive analytics dashboard
```

---

**Note**: This application processes sensitive manufacturing data. Ensure proper access controls when deploying in production environments.
