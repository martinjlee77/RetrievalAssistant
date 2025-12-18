"""
QuickBooks Online OAuth Callback Handler
This page handles the OAuth2 callback from Intuit and stores tokens for the Close Platform.
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'close_platform'))

try:
    import qbo_connector
except ImportError:
    qbo_connector = None

st.set_page_config(page_title="QuickBooks Connection", page_icon="🔗")

st.title("🔗 QuickBooks Online Connection")

query_params = st.query_params

if "code" in query_params and "realmId" in query_params:
    auth_code = query_params.get("code")
    realm_id = query_params.get("realmId")
    
    if qbo_connector:
        try:
            qbo_connector.handle_callback(auth_code, realm_id)
            st.success("✅ Successfully connected to QuickBooks Online!")
            st.info("You can now close this tab and return to the Close Platform to sync your data.")
            st.query_params.clear()
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
            st.info("Please try again from the Close Platform.")
    else:
        st.error("QBO connector module not available.")
elif "error" in query_params:
    error = query_params.get("error")
    st.error(f"❌ Authorization denied: {error}")
    st.info("Please try again from the Close Platform.")
else:
    st.info("This page handles QuickBooks Online OAuth callbacks.")
    st.write("To connect QuickBooks:")
    st.write("1. Go to the Close Platform")
    st.write("2. Click 'Login to Intuit' in the sidebar")
    st.write("3. Authorize the connection")
    st.write("4. You'll be redirected back here automatically")
    
    if qbo_connector and qbo_connector.is_connected():
        st.success("✅ QuickBooks is currently connected!")
    else:
        st.warning("⚠️ QuickBooks is not connected.")
