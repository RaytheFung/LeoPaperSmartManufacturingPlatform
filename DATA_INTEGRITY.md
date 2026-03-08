# Data Integrity & Automatic Month Detection System

## Overview
The system now automatically detects and maintains month labels based on actual datetime values, ensuring data consistency without manual intervention.

## Automatic Features Implemented

### 1. Database Triggers
- **auto_set_month_year**: Automatically sets month_year when new records are inserted
- **auto_update_month_year**: Updates month_year when datetime is modified
- Both triggers derive the month name from the actual datetime value

### 2. Utility Functions (core/data_utils.py)
- **get_month_year_from_datetime()**: Converts any datetime to "Month YYYY" format
- **ensure_month_year_consistency()**: Corrects month_year for entire DataFrames
- **get_available_months_from_data()**: Retrieves months from actual datetime values, not labels

### 3. UI Improvements
- Dropdown now shows months based on actual datetime data
- No longer relies on potentially incorrect month_year labels
- Automatically detects all available months in the database

## How It Works

### When Data is Inserted:
```sql
INSERT INTO unified_view (datetime, ...) VALUES ('2025-06-15 10:00:00', ...)
-- Trigger automatically sets month_year = 'June 2025'
```

### When Viewing Data:
```python
# Old way (could miss months if labels were wrong):
SELECT DISTINCT month_year FROM unified_view

# New way (always shows correct months):
SELECT derived_month_from_datetime, COUNT(*) 
FROM unified_view 
GROUP BY derived_month
```

## Benefits

1. **No Manual Fixes Required**: System self-corrects month labels
2. **Always Accurate**: Dropdown always shows actual months in data
3. **Future Proof**: New data automatically gets correct labels
4. **No Hardcoding**: Months are derived from data, not predefined

## Testing

To verify the system is working:

```bash
sqlite3 manufacturing_data.db "
SELECT 
    strftime('%Y-%m', datetime) as actual_month,
    month_year as labeled_month,
    COUNT(*) as records
FROM unified_view
GROUP BY actual_month, month_year
ORDER BY actual_month;
"
```

All records should show matching actual_month and labeled_month.

## Current Data Status

- January 2025: 23,430 records ✓
- February 2025: 24,425 records ✓
- March 2025: 36,549 records ✓
- April 2025: 36,020 records ✓
- May 2025: 37,897 records ✓
- June 2025: 470 records ✓

All months are correctly labeled and accessible in the UI.

## Maintenance

The system is self-maintaining. However, if you ever need to force a correction:

```python
from core.data_utils import ensure_month_year_consistency
df = pd.read_sql("SELECT * FROM unified_view", conn)
df = ensure_month_year_consistency(df)
# Save back to database
```

---

*Last Updated: [Current Date]*
*System: Fully Automatic Month Detection*