"""
Test script to verify UI fixes in ML module
"""

import streamlit as st
import sys
import os

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

# Test import
try:
    from ml_module import render_ml_module
    print("✅ ML module imported successfully")
except Exception as e:
    print(f"❌ Error importing ML module: {e}")
    exit(1)

# Test render without errors
try:
    # Set page config first
    st.set_page_config(
        page_title="UI Test - ML Module",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 UI Fix Test")
    st.success("Testing ML Module UI Improvements...")
    
    # Render the module
    render_ml_module()
    
    print("✅ ML module rendered without errors")
    
except Exception as e:
    print(f"❌ Error rendering ML module: {e}")
    st.error(f"Error: {e}")