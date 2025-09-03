"""
Multi-Standard Accounting Analysis Platform - Main Entry Point
This file acts as the master "router" for the application.
"""
import streamlit as st



# 1. Set the page configuration
st.set_page_config(
    page_title="Welcome to VeritasLogic.ai",
    layout="wide",
    initial_sidebar_state="expanded")


# 3. Add your logo to the sidebar.
st.logo("assets/images/nobkg.png", size = "large")

# 4. Define all pages in your app.
pg = st.navigation([
    st.Page("pages/home_content.py", title="Home"),

    st.Page("asc606/asc606_page.py", title="ASC 606: 5 Steps", icon="➡️"),
    st.Page("asc842/asc842_page.py", title="ASC 842: Lessee Accounting", icon="➡️"),
    st.Page("asc718/asc718_page.py", title="ASC 718: Stock Compensation", icon="➡️"),
    st.Page("asc805/asc805_page.py", title="ASC 805: Business Combinations", icon="➡️"),
    st.Page("asc340/asc340_page.py", title="ASC 340-40: Cost to Obtain", icon="➡️"),
    st.Page("pages/research_assistant.py", title="🔍 ASC Research Assistant"),
    st.Page("pages/faq.py", title="FAQ"),
    st.Page("pages/gethelp.py", title="Get help")
])

# 5. Run the app.
pg.run()
