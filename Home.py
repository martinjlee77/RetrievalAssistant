"""
Multi-Standard Accounting Analysis Platform - Home Dashboard
"""
import streamlit as st

st.write(f"Running Streamlit Version: {st.__version__}")

# Configure the page. initial_sidebar_state="expanded" is key here.
st.set_page_config(
    page_title="Controller.cpa | Technical Accounting AI Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"  # Keep the navigation visible by default
)

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
        # The button is colored using your theme's primaryColor.
        if st.button("➡️ Go to ASC 606 Analyzer",
                     type="primary",
                     key="asc606_button"):
            st.switch_page("pages/1_ASC_606_Revenue.py")

with col2:
    with st.container(border=True):
        st.markdown("##### 🏢 ASC 842 - Leases")
        st.write(
            "Automatically classify leases as operating or finance, and generate amortization schedules for right-of-use assets and lease liabilities with full support."
        )
        if st.button("➡️ Go to ASC 842 Analyzer",
                     type="primary",
                     key="asc842_button"):
            st.switch_page("pages/2_ASC_842_Leases.py")


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
