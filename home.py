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
            }}

            /* --- Sidebar Navigation Links General Style --- */
            [data-testid="stSidebarNav"] ul li a {{
            
                padding: 0.5rem 0.75rem;
                transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out;
                text-decoration: none;
                border-radius: 8px;
            }}

            /* --- Hover effect for navigation links --- */
            [data-testid="stSidebarNav"] ul li a:hover {{
                background-color: #F8F9FA;
            }}

            /* --- Active Page Link Style --- */
            [data-testid="stSidebarNav"] ul li a[aria-current="page"] {{
                background-color: {secondary_color};
                font-weight: 800;
            }}

            /* --- Login/Register links separator --- */
            [data-testid="stSidebarNav"] ul li:nth-last-child(1) a,
            [data-testid="stSidebarNav"] ul li:nth-last-child(2) a {{
                border-top: 1px solid #ddd;
                margin-top: 20px;
                padding-top: 20px;
            }}
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# 1. Set the page configuration
st.set_page_config(
    page_title="Controller.cpa | Multi-Standard Accounting Platform",
    page_icon="assets/images/logo.png",
    layout="wide",
    initial_sidebar_state="expanded")

# 2. Inject our custom CSS
load_custom_css()

# 3. Add your logo to the sidebar.
st.logo("assets/images/logo.png")

# 4. Define all pages in your app.
pg = st.navigation([
    st.Page("pages/home_content.py", title="Home", icon=":material/home:"),
    st.Page("pages/asc606.py",
            title="ASC 606 Analyzer",
            icon=":material/arrow_forward:"),
    st.Page("pages/asc842.py",
            title="ASC 842 Analyzer",
            icon=":material/arrow_forward:"),
    st.Page("pages/login.py", title="Login", icon=":material/login:"),
    st.Page("pages/register.py",
            title="Register",
            icon=":material/person_add:"),
])

# 5. Run the app.
pg.run()
