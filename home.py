"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st
import requests
import hashlib

# 1. Set the page configuration
st.set_page_config(
    page_title="Welcome to VeritasLogic.ai",
    page_icon="assets/images/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded")

# 2. Add your logo to the sidebar.
try:
    st.logo("assets/images/nobkg.png", size = "large")
except:
    # If logo file doesn't exist, continue without it
    pass

# 5. Set up the navigation menu organized by sections.
pages = {
        
    
    "": [
        st.Page("pages/home_content.py", title="Home", icon=":material/home:", default=True)
    ],
    
    "TAS Platform": [
        st.Page("asc606/asc606_page.py", title="ASC 606: Revenue Recognition", icon=":material/expand_circle_right:"),
        st.Page("asc340/asc340_page.py", title="ASC 340-40: Cost to Obtain", icon=":material/expand_circle_right:"),
        st.Page("asc842/asc842_page.py", title="ASC 842: Leases (Lessee)", icon=":material/expand_circle_right:"),
        st.Page("asc718/asc718_page.py", title="ASC 718: Stock Compensation", icon=":material/expand_circle_right:"),
        st.Page("asc805/asc805_page.py", title="ASC 805: Business Combinations", icon=":material/expand_circle_right:"),
        ],
    "Tools": [
        st.Page("pages/research_assistant.py", title="ASC Research Assistant", icon=":material/search:"),
        ],
    "Get Help": [
        st.Page("pages/gethelp.py", title="Contact Support", icon=":material/contact_support:"),
    ],
}

pg = st.navigation(pages)

# 6. Auto-login check for SSO tokens before running the app
from shared.auth_utils import try_cross_domain_auth
# Check for SSO auto-login tokens in URL parameters
try_cross_domain_auth()

# 7. Run the app.
pg.run()