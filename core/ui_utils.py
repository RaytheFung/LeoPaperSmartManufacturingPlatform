"""UI utilities for the Smart Manufacturing Platform"""

import streamlit as st
import os

def load_custom_css():
    """Load custom CSS styles from the static folder"""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'styles.css')
    
    if os.path.exists(css_path):
        with open(css_path, 'r') as f:
            css_content = f.read()
            st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    else:
        # Fallback to minimal essential styles if CSS file not found
        st.markdown("""
            <style>
            [data-testid="metric-container"] {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 12px;
                border: 1px solid #e1e4e8;
            }
            </style>
        """, unsafe_allow_html=True)