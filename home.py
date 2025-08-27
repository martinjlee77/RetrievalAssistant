"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st



# 1. Set the page configuration
st.set_page_config(
    page_title="VeritasLogic.ai | Multi-Standard Accounting Platform",
    layout="wide",
    initial_sidebar_state="expanded")


# 3. Add your logo to the sidebar.
st.logo("assets/images/nobkg.png", size = "large")

# 4. Define all pages in your app.
pg = st.navigation([
    st.Page("pages/home_content.py", title="Home"),
    st.Page("pages/research_assistant.py", title="🔍 ASC Research Assistant"),
    st.Page("asc606/asc606_page.py", title="ASC 606 Revenue Recognition"),
    st.Page("asc340/asc340_page.py", title="ASC 340-40 Sales Commissions"),
    st.Page("pages/asc842.py", title="ASC 842 Leases"),
])

# 5. Run the app.
pg.run()
