"""
Central navigation module for the multi-standard accounting platform.
Uses modern st.navigation() for programmatic sidebar management.
"""

import streamlit as st

def build_sidebar():
    """
    Creates a sidebar with Controller.cpa branding.
    Navigation is handled by Streamlit's automatic page routing.
    """
    with st.sidebar:
        st.image("logo.png", width=150)
        st.title("Controller.cpa")
        st.divider()