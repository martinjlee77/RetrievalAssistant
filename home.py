"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st

# 1. Set the page configuration as the very first Streamlit command.
#    This is the master blueprint for the entire app.
st.set_page_config(
    page_title="Controller.cpa | Multi-Standard Accounting Platform",
    page_icon="assets/images/logo.png",  # Use your logo as the browser tab icon!
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Add your logo to the sidebar.
#    This command is designed to be called once in your main script.
st.logo("assets/images/logo.png")  # Logo in sidebar (no internal linking supported by Streamlit)

# 3. Define all pages in your app.
#    This is the single source of truth for your navigation.
#    Using Material Icons for a consistent, professional look.
pg = st.navigation(
    [
        st.Page("pages/home_content.py", title="Home", icon=":material/home:"),
        st.Page("pages/asc606.py", title="ASC 606 Analyzer", icon=":material/functions:"),
        st.Page("pages/asc842.py", title="ASC 842 Analyzer", icon=":material/real_estate_agent:"),
        st.Page("pages/login.py", title="Login", icon=":material/login:"),
        st.Page("pages/register.py", title="Register", icon=":material/person_add:"),
    ]
)

# 4. Run the app.
#    This command executes the script for the currently selected page.
pg.run()
