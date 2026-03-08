"""Data utility functions for the Smart Manufacturing Platform"""

from datetime import datetime
import pandas as pd

def get_month_year_from_datetime(dt):
    """
    Automatically derive month_year string from a datetime object
    
    Args:
        dt: datetime object or string
    
    Returns:
        str: Month year in format "Month YYYY" (e.g., "June 2025")
    """
    if isinstance(dt, str):
        dt = pd.to_datetime(dt)
    elif isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    
    month_names = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April',
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    
    return f"{month_names[dt.month]} {dt.year}"


def ensure_month_year_consistency(df):
    """
    Ensure month_year column is consistent with datetime column
    
    Args:
        df: DataFrame with datetime column
    
    Returns:
        DataFrame with corrected month_year column
    """
    if 'datetime' in df.columns:
        df['month_year'] = df['datetime'].apply(get_month_year_from_datetime)
    return df


def get_available_months_from_data(conn):
    """
    Get available months from actual datetime data, not from month_year column
    This ensures we always show the correct months based on actual data
    
    Args:
        conn: SQLite connection
    
    Returns:
        DataFrame with month_year and record counts
    """
    import sqlite3
    
    query = """
    SELECT 
        CASE 
            WHEN strftime('%m', datetime) = '01' THEN 'January ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '02' THEN 'February ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '03' THEN 'March ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '04' THEN 'April ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '05' THEN 'May ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '06' THEN 'June ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '07' THEN 'July ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '08' THEN 'August ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '09' THEN 'September ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '10' THEN 'October ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '11' THEN 'November ' || strftime('%Y', datetime)
            WHEN strftime('%m', datetime) = '12' THEN 'December ' || strftime('%Y', datetime)
        END as month_year,
        COUNT(*) as record_count
    FROM unified_view
    WHERE datetime IS NOT NULL
    GROUP BY month_year
    ORDER BY MIN(datetime)
    """
    
    return pd.read_sql_query(query, conn)