# Smart Manufacturing App - Design Language & Implementation Guidelines

## Overview
This document establishes the design patterns, coding conventions, and implementation guidelines developed during the ETL module phase. These standards should be followed for all subsequent modules to ensure consistency and maintainability.

## UI/UX Design Principles

### 1. Page Structure Pattern
```
┌─────────────────────────────────────┐
│         Module Title                │
│         Description                 │
├─────────────────────────────────────┤
│      File Upload Section            │
│   [Upload Box] [Upload Box] [...]   │
├─────────────────────────────────────┤
│      Control Section                │
│   [Select Month ▼] [Select Year ▼]  │
│   [Process Button]                  │
├─────────────────────────────────────┤
│      Results Display                │
│   ┌─────────┬─────────┬─────────┐  │
│   │ Metric  │ Metric  │ Metric  │  │
│   └─────────┴─────────┴─────────┘  │
│      Detailed Results               │
│   [Download Excel] [Download JSON]  │
├─────────────────────────────────────┤
│      Historical Data (Expandable)   │
└─────────────────────────────────────┘
```

### 2. Interactive Elements

#### File Upload
```python
uploaded_file = st.file_uploader(
    "Upload Energy Usage Files",
    type=['xlsx', 'xls'],
    accept_multiple_files=True,
    help="Select one or more Excel files"
)
```

#### Selection Controls
```python
col1, col2 = st.columns(2)
with col1:
    selected_month = st.selectbox("Select Month", months)
with col2:
    selected_year = st.selectbox("Select Year", years)
```

#### Action Buttons
```python
if st.button("Process Data", type="primary", use_container_width=True):
    # Processing logic
```

### 3. Feedback Patterns

#### Success Messages
```python
st.success("✅ Processing completed successfully!")
```

#### Error Messages
```python
st.error("❌ Error: Unable to process file. Please check the format.")
```

#### Information Messages
```python
st.info("ℹ️ Tip: You can select multiple files for batch processing")
```

#### Progress Indication
```python
with st.spinner("Processing data..."):
    # Long running operation
progress_bar = st.progress(0)
for i in range(100):
    progress_bar.progress(i + 1)
```

### 4. Data Display Patterns

#### Metrics Display
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Machines", "1,459", "+12")
with col2:
    st.metric("Three-Way Matches", "60", "-1")
with col3:
    st.metric("Match Rate", "14.5%", "+0.5%")
```

#### Tabular Data
```python
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "machine_id": "Machine ID",
        "status": st.column_config.Column(
            "Status",
            help="Current machine status"
        )
    }
)
```

#### Charts (using Altair)
```python
chart = alt.Chart(df).mark_line().encode(
    x=alt.X('date:T', title='Date'),
    y=alt.Y('value:Q', title='Value'),
    tooltip=['date', 'value']
).properties(
    width='container',
    height=400
)
st.altair_chart(chart, use_container_width=True)
```

## Code Architecture Patterns

### 1. Module Structure
```python
# module_name.py
import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

class ModuleNameModule:
    def __init__(self):
        self.db_path = "manufacturing_data.db"
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize module-specific session state"""
        if 'module_data' not in st.session_state:
            st.session_state.module_data = None
    
    def render(self):
        """Main rendering method for the module"""
        st.title("Module Name")
        st.write("Module description")
        
        # Module implementation
```

### 2. Database Operations Pattern
```python
def save_to_database(self, data):
    """Save data with proper error handling"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Use parameterized queries
            cursor.execute("""
                INSERT INTO table_name (col1, col2) 
                VALUES (?, ?)
            """, (val1, val2))
            
            conn.commit()
            return True
            
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return False
```

### 3. Session State Management
```python
# Store results after processing
st.session_state.results = {
    'data': processed_data,
    'timestamp': datetime.now(),
    'parameters': {'month': month, 'year': year}
}

# Check for existing results
if 'results' in st.session_state:
    self._display_results(st.session_state.results)
else:
    self._show_upload_interface()
```

### 4. File Processing Pattern
```python
def process_file(self, file):
    """Standard file processing with validation"""
    try:
        # Read file
        df = pd.read_excel(file)
        
        # Validate required columns
        required_cols = ['machine_id', 'value']
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing columns: {missing_cols}")
        
        # Normalize data
        df['machine_id'] = df['machine_id'].str.upper().str.strip()
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['machine_id'])
        
        return df
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None
```

## Visual Design Standards

### 1. Color Usage
- **Success**: Green (✅, 🟢) - For successful operations
- **Error**: Red (❌, 🔴) - For errors and failures  
- **Warning**: Orange (⚠️, 🟠) - For warnings
- **Info**: Blue (ℹ️, 🔵) - For information
- **Neutral**: Gray - For disabled states

### 2. Icons and Emojis
- 📊 - Data/Charts
- 📈 - Trends/Growth
- 📉 - Decline
- 🔄 - Process/Refresh
- ⬇️ - Download
- ⬆️ - Upload
- 🗑️ - Delete
- ✏️ - Edit
- 🔍 - Search/Analysis
- 💾 - Save
- 📁 - Folder/Files
- ⚡ - Energy
- 🏭 - Manufacturing/Factory
- 🤖 - Automation/ML

### 3. Spacing and Layout
- Use consistent spacing with Streamlit's column system
- Group related controls together
- Provide clear visual separation between sections
- Use expanders for optional/detailed information

## Data Handling Standards

### 1. Data Normalization
```python
# Always normalize machine IDs
df['machine_id'] = df['machine_id'].str.upper().str.strip()

# Standardize date formats
df['date'] = pd.to_datetime(df['date'])

# Handle missing values explicitly
df['value'].fillna(0, inplace=True)
```

### 2. Error Messages
- Be specific about what went wrong
- Provide actionable guidance
- Never expose system paths or sensitive information
- Log technical details separately

### 3. Performance Guidelines
- Use `st.cache_data` for expensive computations
- Implement pagination for large datasets
- Show progress for operations > 2 seconds
- Batch database operations

## Integration Guidelines

### 1. Module Integration
- Each module should be self-contained
- Use consistent database schema
- Share common utilities via utils.py
- Maintain module independence

### 2. Data Flow
```
User Upload → Validation → Processing → Database → Display
                              ↓
                         Session State
```

### 3. State Preservation
- Always preserve user selections
- Maintain results after actions
- Allow users to modify and reprocess
- Provide clear reset options

## Testing Checklist
- [ ] File upload works with drag-and-drop
- [ ] Empty file handling
- [ ] Missing column handling  
- [ ] Large file performance
- [ ] Session state persistence
- [ ] Download functionality
- [ ] Database integrity
- [ ] Error message clarity
- [ ] UI responsiveness
- [ ] Cross-browser compatibility

## Example Implementation

```python
def render_analysis_module():
    """Example module following all guidelines"""
    st.title("📊 Data Analysis Module")
    st.write("Analyze your manufacturing data with advanced insights")
    
    # Check for existing results
    if 'analysis_results' in st.session_state:
        _display_results()
        
        if st.button("🔄 New Analysis"):
            del st.session_state.analysis_results
            st.rerun()
    else:
        # File upload section
        uploaded_file = st.file_uploader(
            "Upload Data File",
            type=['xlsx', 'csv']
        )
        
        if uploaded_file:
            # Process with feedback
            with st.spinner("Analyzing data..."):
                results = process_analysis(uploaded_file)
                
            if results:
                st.session_state.analysis_results = results
                st.rerun()
```

## Conclusion
Following these guidelines ensures a consistent, professional, and user-friendly experience across all modules of the Smart Manufacturing Application. Each new module should reference this document and the completed ETL module as examples of proper implementation.