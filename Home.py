"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
"""
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

# Define all pages
home_page = st.Page("pages/home_content.py", title="Home", icon=":material/home:")
asc606_page = st.Page("pages/1_ASC_606_Revenue.py", title="ASC 606 Revenue", icon=":material/functions:")
asc842_page = st.Page("pages/2_ASC_842_Leases.py", title="ASC 842 Leases", icon=":material/real_estate_agent:")

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

# --- Header Section ---
st.title("Controller.cpa Platform")
st.subheader("Welcome back. Please select an analysis tool below to begin.")

# --- Main Content: Call-to-Action Containers ---
st.divider()
st.subheader("Available Analysis Tools")

# We use standard columns and containers for a clean, card-like layout
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("##### 📄 ASC 606 - Revenue from Contracts with Customers")
        st.write(
            "Generate audit-ready memos by analyzing contracts with our Hybrid RAG system, leveraging both authoritative FASB and industry interpretative guidance."
        )
        st.page_link(
            "pages/1_ASC_606_Revenue.py",
            label="Go to ASC 606 Analyzer",
            icon="➡️"
        )

with col2:
    with st.container(border=True):
        st.markdown("##### 🏢 ASC 842 - Leases")
        st.write(
            "Automatically classify leases as operating or finance, and generate amortization schedules for right-of-use assets and lease liabilities with full support."
        )
        st.page_link(
            "pages/2_ASC_842_Leases.py",
            label="Go to ASC 842 Analyzer",
            icon="➡️"
        )

# --- Footer and Stats ---
st.divider()
st.subheader("Platform at a Glance")

stat_cols = st.columns(4)
stat_cols[0].metric("Available Modules", "2", "ASC 606 & 842")
stat_cols[1].metric("Knowledge Base", "1,510+", "Chunks")
stat_cols[2].metric("Knowledge Sources", "FASB/ Industry", "Hybrid RAG")
stat_cols[3].metric("Avg. Analysis Time", "~30s")

st.divider()
st.caption("© 2024 Controller.cpa. All Rights Reserved.")
