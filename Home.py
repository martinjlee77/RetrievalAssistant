"""
Multi-Standard Accounting Analysis Platform - Home Dashboard (Simplified & Standard)
"""
import streamlit as st

# Configure the page. initial_sidebar_state="expanded" is key here.
st.set_page_config(
    page_title="Controller.cpa | Technical Accounting AI Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded" # Keep the navigation visible by default
)

# Optional: A tiny bit of CSS for custom fonts, but no layout hacks.
def load_minimal_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Poppins:wght@600;700&display=swap');

            html, body, [class*="st-"], .st-emotion-cache-1gulkj5 {
                font-family: 'Lato', sans-serif;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: 'Poppins', sans-serif;
                color: #0A2B4C; /* Primary Color */
            }
            /* Hide Streamlit's default hamburger menu and footer for a cleaner look */
            [data-testid="stToolbar"] { display: none !important; }
            footer { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

load_minimal_css()

# --- Header Section ---
st.title("Controller.cpa Platform")
st.markdown("### Welcome to Your AI-Powered Technical Accounting Co-Pilot")
st.write(
    "Select an accounting standard from the navigation menu on the left to begin your analysis, "
    "or use the quick links below to jump directly into a tool."
)
st.markdown("---")


# --- Main Content: Call-to-Action Containers ---
st.subheader("Available Analysis Tools")

# We use standard columns and containers for a clean, card-like layout
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("#### 📈 ASC 606: Revenue from Contracts with Customers")
        st.write(
            "Analyze complex contracts for performance obligations, variable "
            "consideration, and proper recognition timing using the 5-step model."
        )
        # st.page_link is the standard, correct way to link to other pages
        st.page_link("pages/1_ASC_606_Revenue.py", label="Go to ASC 606 Analyzer", icon="➡️")

with col2:
    with st.container(border=True):
        st.markdown("#### 🏢 ASC 842: Leases")
        st.write(
            "Classify leases as operating or finance and generate amortization "
            "schedules and journal entries automatically."
        )
        st.page_link("pages/2_ASC_842_Leases.py", label="Go to ASC 842 Analyzer", icon="➡️")

# You can add more containers here for future standards
# st.markdown("...")


# --- Footer and Stats ---
st.markdown("---")
st.subheader("Platform at a Glance")

stat_cols = st.columns(4)
stat_cols[0].metric("Active Analyzers", "2")
stat_cols[1].metric("Knowledge Base", "1,510+", "Chunks")
stat_cols[2].metric("Avg. Analysis Time", "~30s")
stat_cols[3].metric("Platform Version", "2.0")

st.markdown("---")
st.markdown('<p style="text-align: center; color: #666;">&copy; 2024 Controller.cpa. All Rights Reserved.</p>', unsafe_allow_html=True)