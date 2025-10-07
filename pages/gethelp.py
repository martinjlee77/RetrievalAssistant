"""
Get Help & Support Page

Redirects users to the unified professional contact form at contact.html
"""

import streamlit as st
import os

# Get website URL from environment
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
CONTACT_URL = f"{WEBSITE_URL}/contact.html"

st.title("🆘 Get Help & Support")

with st.container(border=True):
    st.markdown("""
    **Need assistance?** We're here to help with:
    
    - General questions about the platform
    - Technical issues or errors
    - Billing and payment inquiries
    - Memo rerun requests
    - Feature requests
    """)

st.markdown("---")

# Main call-to-action
st.markdown(f"""
### 📧 Contact Our Support Team

Visit our support center to submit your inquiry:

[**Contact Support**]({CONTACT_URL}){{:target="_blank"}}

Or email us directly at: **support@veritaslogic.ai**
""")

st.markdown("---")

# Helpful reminder about rerun policy
with st.container(border=True):
    st.info("""
    **💡 Rerun Policy Reminder**
    
    Each analysis includes **one complimentary re-run within 14 days** for:
    - Input corrections or clarifications
    - Extractable text issues
    - Contract data adjustments
    
    Use the contact form to request your rerun.
    """)
