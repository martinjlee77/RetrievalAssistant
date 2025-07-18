"""
ASC 842 Lease Analysis Page - Coming Soon
"""

import streamlit as st
from navigation import build_sidebar

# Page configuration
st.set_page_config(
    page_title="ASC 842 Lease Analysis | Controller.cpa",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Build centralized sidebar navigation
build_sidebar()

# Standard header
st.title("ASC 842 Lease Analysis")
st.write("AI-powered lease classification and measurement analysis")

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