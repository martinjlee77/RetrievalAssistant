"""
Registration Page - Placeholder Implementation
"""
import streamlit as st

st.title("Join Controller.cpa")
st.markdown("Create your account to access AI-powered technical accounting tools")

with st.form("registration_form"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Basic information
        first_name = st.text_input("First Name", placeholder="John")
        last_name = st.text_input("Last Name", placeholder="Smith")
        email = st.text_input("Email Address", placeholder="your.email@company.com")
        
        # Company information
        company = st.text_input("Company Name", placeholder="ABC Corporation")
        title = st.text_input("Job Title", placeholder="Senior Accountant")
        
        # Password
        password = st.text_input("Password", type="password", placeholder="Create a secure password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        # Terms and conditions
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        marketing = st.checkbox("I'd like to receive product updates and accounting insights")
        
        submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")
    
    with col2:
        st.markdown("---")
        st.markdown("**Already have an account?**")
        if st.form_submit_button("Sign In", use_container_width=True):
            st.switch_page("pages/login.py")
        
        st.markdown("---")
        st.markdown("**What you get:**")
        st.markdown("• AI-powered contract analysis")
        st.markdown("• Professional accounting memos")
        st.markdown("• Expert review options")
        st.markdown("• Pay-per-use pricing")

if submit:
    # Basic validation
    errors = []
    
    if not first_name:
        errors.append("First name is required")
    if not last_name:
        errors.append("Last name is required")
    if not email or "@" not in email:
        errors.append("Valid email address is required")
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if password != confirm_password:
        errors.append("Passwords do not match")
    if not terms:
        errors.append("You must agree to the Terms of Service")
    
    if errors:
        for error in errors:
            st.error(error)
    else:
        # Placeholder registration logic
        st.success("Registration functionality will be implemented here!")
        st.info(f"Creating account for: {first_name} {last_name} ({email})")
        # TODO: Implement actual registration
        # TODO: Send welcome email
        # TODO: Create user profile