"""
Login Page - Placeholder Implementation
"""
import streamlit as st

st.title("Welcome Back")
st.markdown("Sign in to your Controller.cpa account")

with st.form("login_form"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        email = st.text_input("Email Address", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col_a, col_b = st.columns(2)
        with col_a:
            remember_me = st.checkbox("Remember me")
        with col_b:
            st.markdown("[Forgot password?](#)", unsafe_allow_html=True)
        
        submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
    
    with col2:
        st.markdown("---")
        st.markdown("**New to Controller.cpa?**")
        if st.form_submit_button("Create Account", use_container_width=True):
            st.switch_page("pages/register.py")

if submit:
    if email and password:
        # Placeholder authentication logic
        st.success("Login functionality will be implemented here!")
        st.info(f"Attempting to log in: {email}")
        # TODO: Implement actual authentication
    else:
        st.error("Please enter both email and password")

st.divider()

# Social login placeholders
st.markdown("**Or continue with:**")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔗 SSO", use_container_width=True):
        st.info("Single Sign-On coming soon!")

with col2:
    if st.button("🏢 Microsoft", use_container_width=True):
        st.info("Microsoft OAuth coming soon!")

with col3:
    if st.button("🔒 Google", use_container_width=True):
        st.info("Google OAuth coming soon!")