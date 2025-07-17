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
    """Load custom CSS for clickable cards and refined styling."""
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Poppins:wght@600;700&display=swap');

            :root {
                --primary-color: #0A2B4C;
                --secondary-color: #C5A565;
                --text-color: #212529;
                --heading-font: 'Poppins', sans-serif;
                --body-font: 'Lato', sans-serif;
                --border-color: #e0e0e0;
            }

            /* --- Global & Basic Styling --- */
            html, body, [class*="st-"], .st-emotion-cache-1gulkj5 {
                font-family: var(--body-font);
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: var(--heading-font);
                color: var(--primary-color);
            }
            [data-testid="stToolbar"] { display: none !important; }
            footer { display: none !important; }

            /* --- Card Container Styling --- */
            .clickable-card-container {
                /* Layout & Sizing */
                display: flex;
                flex-direction: column;
                height: 280px;
                margin-bottom: 1rem;

                /* Appearance */
                background-color: #ffffff;
                border: 1px solid var(--border-color);
                border-radius: 8px;

                /* Interaction */
                transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            }
            .clickable-card-container:hover {
                transform: translateY(-5px); /* Lift effect on hover */
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }

            /* --- Card Content --- */
            .clickable-card-content {
                padding: 1.5rem;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
            }
            .clickable-card-content h3 {
                font-size: 1.5rem; margin-bottom: 0.25rem;
            }
            .clickable-card-content p {
                font-size: 1rem; color: #666;
            }
            .clickable-card-content .card-spacer {
                flex-grow: 1; /* Pushes the button to the bottom */
            }

            /* --- Enhanced Page Link Styling --- */
            a[data-testid="stPageLink"] {
                display: block;
                background-color: transparent !important;
                border: 2px solid var(--primary-color) !important;
                color: var(--primary-color) !important;
                text-align: center;
                padding: 0.75rem;
                border-radius: 5px;
                text-decoration: none;
                font-weight: 700;
                transition: all 0.2s ease-in-out;
                margin-top: 0 !important;
            }
            a[data-testid="stPageLink"]:hover {
                background-color: var(--secondary-color) !important;
                border-color: var(--secondary-color) !important;
                color: white !important;
            }

            /* --- Disabled Card Styling --- */
            .disabled-card {
                display: flex;
                flex-direction: column;
                height: 350px;
                padding: 1.5rem;
                background-color: #f8f9fa;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                opacity: 0.7;
            }
            .disabled-card .card-button {
                text-align: center;
                padding: 0.75rem;
                border-radius: 5px;
                font-weight: 700;
                background-color: #e9ecef;
                color: #6c757d;
                border: 2px solid #ced4da;
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

# --- Enhanced Clickable Card Layout ---
cols = st.columns(len(standards))

for i, (code, info) in enumerate(standards.items()):
    with cols[i]:
        if info['status'] == 'available':
            # Create clickable card with st.page_link embedded inside
            card_html = f"""
            <div class="clickable-card-container">
                <div class="clickable-card-content">
                    <h3>{info['icon']} {info['name']}</h3>
                    <p style="font-size: 0.9rem; color: #888;">Standard: {code}</p>
                    <p>{info['description']}</p>
                    <div class="card-spacer"></div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            # Use st.page_link for proper navigation
            st.page_link(
                info['page'], 
                label="🚀 Launch Analyzer",
                use_container_width=True
            )

        else:
            # For "Coming Soon", we use a <div> instead of an <a> tag so it's not clickable
            disabled_card_html = f"""
            <div class="disabled-card">
                <h3>{info['icon']} {info['name']}</h3>
                <p style="font-size: 0.9rem; color: #aaa;">Standard: {code}</p>
                <p>{info['description']}</p>
                <div class="card-spacer"></div>
                <div class="card-button">⏳ Coming Soon</div>
            </div>
            """
            st.markdown(disabled_card_html, unsafe_allow_html=True)

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