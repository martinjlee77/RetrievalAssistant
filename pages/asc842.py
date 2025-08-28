"""
ASC 842 Lease Accounting Analysis Page
Integration with the main Streamlit navigation system.
"""

import streamlit as st
from asc842.asc842_page import render_asc842_page

# Set page config for better display
st.set_page_config(
    page_title="ASC 842 Lease Analyzer", 
    page_icon="🏢",
    layout="wide"
)

# Render the ASC 842 page
render_asc842_page()