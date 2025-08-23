"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st


# Function to load and inject custom CSS
def load_custom_css():
    css = """
        <style>
            /* Import fonts from website */
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap');
            
            /* --- Main App Background --- */
            .main .block-container {{
                background-color: #212F3C;
                color: #ffffff;
            }}
            
            /* --- Set body and main background --- */
            .stApp {{
                background-color: #212F3C;
                color: #ffffff;
            }}
            
            /* --- Main content area --- */
            section[data-testid="stAppViewContainer"] {{
                background-color: #212F3C;
            }}
            
            /* --- Typography matching website --- */
            .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {{
                font-family: 'Playfair Display', Georgia, 'Times New Roman', Times, serif !important;
                color: #ffffff !important;
                line-height: 1.2;
            }}
            
            .main p, .main div, .main span {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
                color: #ffffff !important;
            }}

            /* --- Sidebar Style matching website --- */
            [data-testid="stSidebar"] {{
                background: linear-gradient(135deg, #1A252F 0%, #212F3C 100%);
                border-right: 1px solid rgba(255,255,255,0.1);
                padding-top: 1rem;
            }}

            /* --- Sidebar Navigation Container --- */
            [data-testid="stSidebarNav"] {{
                padding: 0 1rem;
            }}

            /* --- Navigation Links General Style --- */
            [data-testid="stSidebarNav"] ul li a {{
                display: flex;
                align-items: center;
                padding: 0.75rem 1rem;
                margin: 0.25rem 0;
                transition: all 0.3s ease;
                text-decoration: none;
                border-radius: 8px;
                font-size: 0.95rem;
                font-weight: 500;
                color: rgba(255,255,255,0.8) !important;
                background-color: transparent;
                border: 1px solid transparent;
                font-family: 'Inter', sans-serif !important;
            }}

            /* --- Hover Effect --- */
            [data-testid="stSidebarNav"] ul li a:hover {{
                background-color: rgba(255,255,255,0.1);
                color: #ffffff !important;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }}

            /* --- Active Page Style --- */
            [data-testid="stSidebarNav"] ul li a[aria-current="page"] {{
                background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
                color: #212F3C !important;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(255,255,255,0.2);
            }}

            /* --- Home Link Special Styling --- */
            [data-testid="stSidebarNav"] ul li:first-child a {{
                border-bottom: 1px solid rgba(255,255,255,0.1);
                margin-bottom: 0.75rem;
                padding-bottom: 1rem;
            }}

            /* --- Logo Spacing --- */
            [data-testid="stSidebar"] [data-testid="stImage"] {{
                margin-bottom: 1.5rem;
                padding: 0 1rem;
                filter: brightness(0) invert(1);
            }}
            
            /* --- Container Cards matching website styling --- */
            .main [data-testid="stContainer"] {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
            }}
            
            .main [data-testid="stContainer"]:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 18px rgba(0,0,0,0.3);
            }}
            
            /* --- Buttons matching website style --- */
            .main button {{
                background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%) !important;
                color: #212F3C !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                font-family: 'Inter', sans-serif !important;
                box-shadow: 0 4px 12px rgba(255,255,255,0.2) !important;
                transition: all 0.3s ease !important;
            }}
            
            .main button:hover {{
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 18px rgba(255,255,255,0.3) !important;
            }}
            
            .main button:disabled {{
                background: rgba(255,255,255,0.1) !important;
                color: rgba(255,255,255,0.5) !important;
                transform: none !important;
            }}
            
            /* --- Metrics styling --- */
            [data-testid="metric-container"] {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 1rem;
            }}
            
            /* --- Dividers --- */
            .main hr {{
                border-color: rgba(255,255,255,0.1);
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
