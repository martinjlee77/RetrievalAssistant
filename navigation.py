"""
Central navigation module for the multi-standard accounting platform.
Creates consistent sidebar branding across all pages.
"""

import streamlit as st

def build_sidebar():
    """
    Creates a sidebar with Controller.cpa branding at the top.
    This provides consistent branding across all pages while allowing 
    Streamlit's automatic navigation to handle page routing.
    """
    with st.sidebar:
        # Add Controller.cpa branding at the top
        st.image("logo.png", width=150)
        st.title("Controller.cpa")
        st.divider()