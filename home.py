"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st


# Function to load and inject custom CSS
def load_custom_css():

    # Brand colors
    primary_color = "#0A2B4C"  # Deep Sapphire Blue (for text)
    secondary_color = "#C5A565"  # Muted Gold (for active background)
    bg_color = "#E9ECEF"  # Very Light Gray (for sidebar background)
    # F8F9FA, F0F2F5, E9ECEF, DEE2E6

    
    css = f"""
        <style>
            /* --- Main Sidebar Style --- */
            [data-testid="stSidebar"] {{
                background-color: {bg_color};
                border-right: 1px solid #e0e0e0;
                padding-top: 1rem;
            }}

            /* --- Sidebar Navigation Container --- */
            [data-testid="stSidebarNav"] {{
                padding: 0 1rem;
            }}

            /* --- Navigation List --- */
            [data-testid="stSidebarNav"] ul {{
                list-style: none;
                padding: 0;
                margin: 0;
                gap: 0.5rem;
                display: flex;
                flex-direction: column;
            }}

            /* --- Navigation List Items --- */
            [data-testid="stSidebarNav"] ul li {{
                margin: 0;
                padding: 0;
            }}

            /* --- Navigation Links General Style --- */
            [data-testid="stSidebarNav"] ul li a {{
                display: flex;
                align-items: center;
                padding: 0.75rem 1rem;
                margin: 0.25rem 0;
                transition: all 0.2s ease-in-out;
                text-decoration: none;
                border-radius: 8px;
                font-size: 0.95rem;
                font-weight: 500;
                color: {primary_color};
                background-color: transparent;
                border: 1px solid transparent;
            }}



            /* --- Hover Effect --- */
            [data-testid="stSidebarNav"] ul li a:hover {{
                background-color: #F8F9FA;
                border-color: #DEE2E6;
                transform: translateX(2px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}

            /* --- Active Page Style --- */
            [data-testid="stSidebarNav"] ul li a[aria-current="page"] {{
                background-color: {secondary_color};
                color: white;
                font-weight: 600;
                border-color: {secondary_color};
                box-shadow: 0 2px 8px rgba(197, 165, 101, 0.3);
            }}



            /* --- Home Link Special Styling --- */
            [data-testid="stSidebarNav"] ul li:first-child a {{
                border-bottom: 1px solid #DEE2E6;
                margin-bottom: 0.75rem;
                padding-bottom: 1rem;
            }}

            /* --- Coming Soon Indicator for Future Modules --- */
            [data-testid="stSidebarNav"] ul li:last-child a {{
                opacity: 0.6;
                cursor: not-allowed;
            }}

            /* --- Logo Spacing --- */
            [data-testid="stSidebar"] [data-testid="stImage"] {{
                margin-bottom: 1.5rem;
                padding: 0 1rem;
            }}
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# 1. Set the page configuration
st.set_page_config(
    page_title="VeritasLogic.ai | Multi-Standard Accounting Platform",
    page_icon="assets/images/VL_black_nobk.png",
    layout="wide",
    initial_sidebar_state="expanded")

# 2. Inject our custom CSS
load_custom_css()

# 3. Add your logo to the sidebar.
st.logo("assets/images/VL_black_nobk.png")

# 4. Define all pages in your app.
pg = st.navigation([
    st.Page("pages/home_content.py", title="Home"),
    st.Page("asc606/asc606_page.py", title="ASC 606 Revenue Recognition"),
    st.Page("pages/asc340.py", title="ASC 340-40 Contract Costs"),
    st.Page("pages/asc842.py", title="ASC 842 Leases"),
])

# 5. Run the app.
pg.run()
