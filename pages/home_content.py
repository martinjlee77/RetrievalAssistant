"""
Home page content for the Controller.cpa platform
"""
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Single Line Date/Time Header ---
# Get the current time, convert it to Eastern Time, and format it.
now_est = datetime.now(ZoneInfo("America/New_York"))

# Format string with Time first, then Date.
# %I:%M %p is 12-hour time, %Z is timezone, %A is Weekday, etc.
formatted_time = now_est.strftime("%I:%M %p %Z  |  %A, %B %d, %Y")

# Display it using st.markdown() to get the standard text color.
st.markdown(formatted_time)

# Streamlit version - DELETE THIS LINE IN PRODUCTION
st.write(f"Running Streamlit Version: {st.__version__}")

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