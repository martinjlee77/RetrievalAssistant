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
    page_icon="assets/images/favicon.ico",
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
    
    "Analysis": [
        st.Page("asc606/asc606_page.py", title="ASC 606: Revenue Recognition", icon=":material/expand_circle_right:"),
        st.Page("asc340/asc340_page.py", title="ASC 340-40: Cost to Obtain", icon=":material/expand_circle_right:"),
        st.Page("asc842/asc842_page.py", title="ASC 842: Leases (Lessee)", icon=":material/expand_circle_right:"),
        st.Page("asc718/asc718_page.py", title="ASC 718: Stock Compensation", icon=":material/expand_circle_right:"),
        st.Page("asc805/asc805_page.py", title="ASC 805: Business Combinations", icon=":material/expand_circle_right:"),
        ],
    "Review": [
        st.Page("pages/memo_review.py", title="Memo Review (beta)", icon=":material/compare:"),
        ],
    "Tools": [
        st.Page("pages/research_assistant.py", title="ASC Research Assistant", icon=":material/search:"),
        ],
    "Get Help": [
        st.Page("pages/gethelp.py", title="Contact Support", icon=":material/contact_support:"),
    ],
    "Settings": [
        st.Page("pages/qbo_callback.py", title="QuickBooks Connection", icon=":material/link:"),
    ],
}

pg = st.navigation(pages)

# 6. Auto-login check for SSO tokens before running the app
from shared.auth_utils import try_cross_domain_auth
# Check for SSO auto-login tokens in URL parameters
try_cross_domain_auth()

# 6b. Handle QBO OAuth callback if present
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'close_platform'))
query_params = st.query_params
if "code" in query_params and "realmId" in query_params:
    try:
        import qbo_connector
        auth_code = query_params.get("code")
        realm_id = query_params.get("realmId")
        qbo_connector.handle_callback(auth_code, realm_id)
        st.toast("Successfully connected to QuickBooks!", icon="✅")
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"QBO Connection failed: {e}")

# 7. Run the app.
pg.run()