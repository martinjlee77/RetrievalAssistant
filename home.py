"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st


# Function to load and inject custom CSS
def load_custom_css():
    css = """
        <style>
            /* --- Sidebar Style matching website colors --- */
            [data-testid="stSidebar"] {{
                background-color: #2C3E50;
                border-right: 1px solid #34495E;
            }}

            /* --- Navigation Links --- */
            [data-testid="stSidebarNav"] ul li a {{
                color: #ECF0F1;
                border-radius: 6px;
                margin: 2px 0;
                padding: 8px 12px;
                transition: all 0.2s ease;
            }}

            /* --- Active/Hover states --- */
            [data-testid="stSidebarNav"] ul li a:hover {{
                background-color: #34495E;
                transform: translateX(2px);
            }}

            [data-testid="stSidebarNav"] ul li a[aria-current="page"] {{
                background-color: #ffffff;
                color: #2C3E50;
                font-weight: 600;
            }}

            /* --- Logo adjustment --- */
            [data-testid="stSidebar"] [data-testid="stImage"] {{
                filter: brightness(0) invert(1);
                padding: 0 1rem;
                margin-bottom: 1rem;
            }}
            
            /* --- Card styling --- */
            .main [data-testid="stContainer"] {{
                border-radius: 8px;
                border: 1px solid #E5E5E5;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                transition: transform 0.2s ease;
            }}
            
            .main [data-testid="stContainer"]:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.12);
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
