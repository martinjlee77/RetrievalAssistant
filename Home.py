"""
Multi-Standard Accounting Analysis Platform - Home Dashboard
"""
import streamlit as st

st.set_page_config(
    page_title="Controller.cpa | Technical Accounting AI Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Simplified and Robust CSS ---
def load_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Poppins:wght@600;700&display=swap');

            :root {
                --primary-color: #0A2B4C;
                --secondary-color: #C5A565;
                --text-color: #212529;
                --heading-font: 'Poppins', sans-serif;
                --body-font: 'Lato', sans-serif;
            }

            html, body, [class*="st-"], .st-emotion-cache-1gulkj5 {
                font-family: var(--body-font);
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: var(--heading-font);
                color: var(--primary-color);
            }

            /* Hide Streamlit's default hamburger menu and footer for a custom feel */
            [data-testid="stToolbar"] { display: none !important; }
            footer { display: none !important; }

            /* Enhance Streamlit's native bordered container to create our card */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #ffffff;
                transition: box-shadow 0.3s ease-in-out, border-color 0.3s ease-in-out;
                border-width: 1px !important;
            }
            [data-testid="stVerticalBlockBorderWrapper"]:hover {
                border-color: var(--secondary-color) !important;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }

            /* Style st.page_link to look like a call-to-action button */
            a[data-testid="stPageLink"] {
                display: block;
                background-color: var(--primary-color);
                color: white;
                text-align: center;
                padding: 0.75rem;
                border-radius: 5px;
                text-decoration: none;
                font-weight: 700;
                transition: background-color 0.3s ease-in-out;
                margin-top: auto; /* Push button to bottom */
            }
            a[data-testid="stPageLink"]:hover {
                background-color: var(--secondary-color);
                color: white;
            }

            /* Style for disabled-looking buttons */
            .stButton>button[disabled] {
                background-color: #e9ecef !important;
                color: #6c757d !important;
                border: 1px solid #ced4da !important;
            }

        </style>
    """, unsafe_allow_html=True)

load_css()

# --- Header Section ---
st.markdown("""
<div style="text-align: center; padding: 1rem 0 2rem 0;">
    <h1 style="font-size: 2.8rem; margin-bottom: 0.5rem;">Controller.cpa</h1>
    <p style="font-size: 1.2rem; color: #666;">AI-Powered Technical Accounting Analysis Platform</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- Standards Definition ---
standards = {
    'ASC 606': { 'name': 'Revenue', 'description': 'Analyze contracts for performance obligations, variable consideration, and proper recognition timing.', 'status': 'available', 'page': 'pages/1_ASC_606_Revenue.py', 'icon': '📈'},
    'ASC 842': { 'name': 'Leases', 'description': 'Classify leases as operating or finance and generate amortization schedules automatically.', 'status': 'available', 'page': 'pages/2_ASC_842_Leases.py', 'icon': '🏢'},
    'ASC 815': { 'name': 'Derivatives', 'description': 'Analyze instruments for derivative characteristics and apply appropriate accounting.', 'status': 'coming_soon', 'page': 'pages/3_ASC_815_Derivatives.py', 'icon': '⚖️'},
    'ASC 326': { 'name': 'Credit Losses', 'description': 'Implement the Current Expected Credit Loss (CECL) model for financial assets.', 'status': 'coming_soon', 'page': 'pages/4_ASC_326_Credit_Losses.py', 'icon': '📉'}
}

# --- Rebuilt Card Layout ---
cols = st.columns(len(standards))

for i, (code, info) in enumerate(standards.items()):
    with cols[i]:
        # Use st.container with border=True to create the native card element
        with st.container(border=True, height=350):
            st.markdown(f"### {info['icon']} {info['name']}")
            st.caption(f"Standard: {code}")
            st.write(info['description'])

            # Spacer to push the button to the bottom
            st.markdown('<div style="flex-grow: 1;"></div>', unsafe_allow_html=True)

            if info['status'] == 'available':
                st.page_link(info['page'], label="Launch Analyzer", use_container_width=True)
            else:
                st.button("⏳ Coming Soon", disabled=True, use_container_width=True, key=f"coming_soon_{code}")

# --- Footer and Stats ---
st.markdown("---")
st.markdown("### Platform at a Glance")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Analyzers", "2")
col2.metric("Knowledge Base", "1,510+", "Chunks")
col3.metric("Avg. Analysis Time", "~30s")
col4.metric("Platform Version", "2.0")

st.markdown("---")
st.markdown('<p style="text-align: center; color: #666;">&copy; 2024 Controller.cpa. All Rights Reserved.</p>', unsafe_allow_html=True)