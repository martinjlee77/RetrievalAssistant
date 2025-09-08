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
    layout="wide",
    initial_sidebar_state="expanded")

# 2. Authentication check
def check_authentication():
    """Simple authentication for the platform"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("# 🎯 VeritasLogic.ai")
        st.markdown("### Multi-Standard Accounting Analysis Platform")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Please sign in to access the analysis platform")
            
            tab1, tab2 = st.tabs(["Sign In", "Create Account"])
            
            with tab1:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    login_btn = st.form_submit_button("Sign In", use_container_width=True)
                    
                    if login_btn:
                        # Simple authentication - you can replace this with your backend API
                        if email and password:
                            st.session_state.authenticated = True
                            st.session_state.user_email = email
                            st.rerun()
                        else:
                            st.error("Please enter both email and password")
            
            with tab2:
                with st.form("signup_form"):
                    company = st.text_input("Company Name")
                    email = st.text_input("Business Email")
                    password = st.text_input("Password", type="password")
                    signup_btn = st.form_submit_button("Create Account", use_container_width=True)
                    
                    if signup_btn:
                        if company and email and password:
                            st.success("Account created! Please sign in.")
                        else:
                            st.error("Please fill in all fields")
        
        st.stop()  # Stop execution here if not authenticated

# Check authentication first
check_authentication()

# 3. Add your logo to the sidebar (only shown after authentication)
try:
    st.logo("assets/images/nobkg.png", size = "large")
except:
    # If logo file doesn't exist, continue without it
    pass

# 4. Add logout option in sidebar
with st.sidebar:
    if st.session_state.get('authenticated', False):
        st.markdown(f"**Welcome:** {st.session_state.get('user_email', 'User')}")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()

# 5. Set up the navigation menu organized by sections.
pages = {
        
    
    "": [
        st.Page("pages/home_content.py", title="Home", icon=":material/home:", default=True)
    ],
    
    "TAS Platform": [
        st.Page("asc606/asc606_page.py", title="ASC 606: Rev Rec", icon=":material/expand_circle_right:"),
        st.Page("asc340/asc340_page.py", title="ASC 340-40: Cost to Obtain", icon=":material/expand_circle_right:"),
        st.Page("asc842/asc842_page.py", title="ASC 842: Leases (Lessee)", icon=":material/expand_circle_right:"),
        st.Page("asc718/asc718_page.py", title="ASC 718: Stock Comp", icon=":material/expand_circle_right:"),
        st.Page("asc805/asc805_page.py", title="ASC 805: Bus Com", icon=":material/expand_circle_right:"),
        ],
    "Tools": [
        st.Page("pages/research_assistant.py", title="ASC Research Assistant", icon=":material/search:"),
        ],
    "Get Help": [
        st.Page("pages/faq.py", title="FAQ", icon=":material/quick_reference:"),
        st.Page("pages/gethelp.py", title="Contact Support", icon=":material/contact_support:"),
    ],
}

pg = st.navigation(pages)

# 6. Run the app.
pg.run()