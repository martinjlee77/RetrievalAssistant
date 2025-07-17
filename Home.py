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
    """Load custom CSS for the 'Invisible Button' card technique."""
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
            html, body, [class*="st-"], .st-emotion-cache-1gulkj5 { font-family: var(--body-font); }
            h1, h2, h3, h4, h5, h6 { font-family: var(--heading-font); color: var(--primary-color); }
            [data-testid="stToolbar"] { display: none !important; }
            footer { display: none !important; }

            /* --- Card Container (The Visual Border) --- */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #ffffff;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px;
                padding: 0 !important; /* Remove container padding to let the button control it */
                transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            }

            /* --- The Invisible Button (The Clickable Area) --- */
            .stButton > button {
                display: flex;
                flex-direction: column;
                align-items: stretch; /* Make content fill width */
                width: 100%;
                height: 350px;
                padding: 1.5rem !important; /* Add padding inside the button */

                /* Make the button itself transparent and borderless */
                background-color: transparent !important;
                border: none !important;
                color: var(--text-color) !important; /* Set default text color */
                text-align: left; /* Align text to the left */
            }

            /* --- THE HOVER EFFECT: Style the CONTAINER when the button INSIDE is hovered --- */
            [data-testid="stVerticalBlockBorderWrapper"]:has(button:hover) {
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }

            /* --- Card Content (The HTML inside the button label) --- */
            .card-content h3 { font-size: 1.5rem; margin-bottom: 0.25rem; color: var(--primary-color); }
            .card-content p { font-size: 1rem; color: #666; }
            .card-content .card-spacer { flex-grow: 1; }

            /* --- Inner "Launch Analyzer" Button Styling --- */
            .card-launch-button {
                text-align: center;
                padding: 0.75rem;
                border-radius: 5px;
                font-weight: 700;
                background-color: transparent;
                border: 2px solid var(--primary-color);
                color: var(--primary-color);
                transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out, border-color 0.2s ease-in-out;
            }

            /* Style the inner button when the main button is hovered */
            .stButton > button:hover .card-launch-button {
                background-color: var(--secondary-color);
                border-color: var(--secondary-color);
                color: white;
            }

            /* --- Disabled Card Styling --- */
            .stButton > button[disabled] {
                opacity: 0.7;
                background-color: #f8f9fa !important;
                border: 1px solid var(--border-color) !important;
            }
            .stButton > button[disabled] .card-launch-button {
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

# --- Invisible Button Card Layout ---
cols = st.columns(len(standards))

for i, (code, info) in enumerate(standards.items()):
    with cols[i]:
        # Use a container to create the border and hover shadow effect
        with st.container(border=True):

            # The label for the button will be the entire card's content, built with HTML
            card_content_html = f"""
            <div class="card-content">
                <h3>{info['icon']} {info['name']}</h3>
                <p style="font-size: 0.9rem; color: #888;">Standard: {code}</p>
                <p>{info['description']}</p>
                <div class="card-spacer"></div>
                <div class="card-launch-button">
                    {'🚀 Launch Analyzer' if info['status'] == 'available' else '⏳ Coming Soon'}
                </div>
            </div>
            """

            # Create a button that fills the container. When clicked, it navigates.
            if info['status'] == 'available':
                if st.button(card_content_html, key=f"nav_{code}", use_container_width=True):
                    st.switch_page(info['page'])
            else:
                # For disabled cards, the button is just disabled.
                st.button(card_content_html, key=f"nav_{code}", use_container_width=True, disabled=True)

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