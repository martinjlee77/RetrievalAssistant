"""
ASC 842 Lease Analysis Page - Coming Soon
"""

import streamlit as st
from core.ui_helpers import load_custom_css

# Page configuration
st.set_page_config(
    page_title="ASC 842 Lease Analysis | Controller.cpa",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Material Icons font is now loaded in load_custom_css()

# Load custom styling
load_custom_css()

# Add sidebar navigation
with st.sidebar:
    st.markdown("## Navigation")
    
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")
    
    st.markdown("---")
    
    if st.button("📈 ASC 606 Rev Rec", use_container_width=True):
        st.switch_page("pages/1_ASC_606_Revenue.py")
    
    if st.button("🏢 ASC 842 Leases", use_container_width=True, disabled=True):
        pass  # Already on this page

# Header
st.markdown("""
<div style="text-align: center; padding: 2rem 0 1rem 0;">
    <h1 style="font-size: 2.2rem; color: #0A2B4C; margin-bottom: 0.5rem; font-family: 'Poppins', sans-serif;">ASC 842 Lease Analysis</h1>
    <p style="font-size: 1rem; color: #666; margin-bottom: 1rem; font-weight: 400;">AI-powered lease classification and measurement analysis</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Coming soon message
st.info("🚧 ASC 842 Lease Analysis is coming soon! This feature will provide comprehensive lease classification and measurement analysis.")

st.markdown("### What's Coming:")
st.markdown("""
- **Lease Classification**: Determine if leases are operating or finance leases
- **Initial Measurement**: Calculate lease liabilities and right-of-use assets
- **Subsequent Measurement**: Generate amortization schedules and journal entries
- **Disclosure Requirements**: Prepare required lease disclosures
- **Transition Guidance**: Support for ASC 842 implementation
""")