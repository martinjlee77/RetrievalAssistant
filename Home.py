"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
"""
import streamlit as st

# Define all pages
home_page = st.Page("pages/home_content.py", title="Home", icon=":material/home:")
asc606_page = st.Page("pages/asc606.py", title="ASC 606 Revenue", icon=":material/functions:")
asc842_page = st.Page("pages/asc842.py", title="ASC 842 Leases", icon=":material/real_estate_agent:")

# Create navigation
pg = st.navigation([home_page, asc606_page, asc842_page])

# Page configuration
st.set_page_config(
    page_title="Controller.cpa | Multi-Standard Accounting Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add logo to upper left corner of sidebar
st.logo("logo.png")

# Add branding to sidebar
with st.sidebar:
    st.title("Controller.cpa")
    st.divider()

# Run the selected page
pg.run()
