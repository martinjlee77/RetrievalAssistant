import streamlit as st


def build_sidebar():
    """
    Creates a sidebar with Controller.cpa branding.
    Navigation is handled by Streamlit's automatic page routing.
    """
    with st.sidebar:
        # Add Controller.cpa branding at the top
        st.image("logo.png", width=150)
        st.title("Controller.cpa")
        st.divider()
