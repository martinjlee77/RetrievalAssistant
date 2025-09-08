import streamlit as st
import requests
import json
import os
from urllib.parse import parse_qs, urlparse

# Configure page
st.set_page_config(
    page_title="VeritasLogic.ai",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
    color: white;
    margin: -1rem -1rem 2rem -1rem;
    border-radius: 0 0 10px 10px;
}
.auth-container {
    max-width: 400px;
    margin: 2rem auto;
    padding: 2rem;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}
.analysis-header {
    text-align: center;
    padding: 1rem 0;
    border-bottom: 2px solid #f0f0f0;
    margin-bottom: 2rem;
}
.standard-card {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid #007bff;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

def get_backend_url():
    """Get the backend URL - use localhost for now"""
    return "http://localhost:5001"  # We'll run Flask on 5001

def check_auth_status():
    """Check if user is authenticated"""
    if 'user_token' in st.session_state:
        try:
            response = requests.get(
                f"{get_backend_url()}/api/user/profile",
                headers={'Authorization': f"Bearer {st.session_state.user_token}"}
            )
            if response.status_code == 200:
                return True, response.json()
        except:
            pass
    return False, None

def login_form():
    """Display login form"""
    st.markdown('<div class="main-header"><h1>🎯 VeritasLogic.ai</h1><p>Multi-Standard Accounting Analysis Platform</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])
        
        with tab1:
            st.subheader("Welcome Back")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="Enter your business email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("Sign In", use_container_width=True)
                
                if submit:
                    try:
                        response = requests.post(f"{get_backend_url()}/api/auth/login", json={
                            "email": email,
                            "password": password
                        })
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.user_token = data['token']
                            st.rerun()
                        else:
                            st.error(response.json().get('error', 'Login failed'))
                    except:
                        st.error("Unable to connect to authentication service")
        
        with tab2:
            st.subheader("Join VeritasLogic")
            with st.form("signup_form"):
                company_name = st.text_input("Company Name", placeholder="Your company name")
                email = st.text_input("Business Email", placeholder="you@company.com")
                password = st.text_input("Password", type="password", placeholder="Choose a secure password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                submit = st.form_submit_button("Create Account", use_container_width=True)
                
                if submit:
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        try:
                            response = requests.post(f"{get_backend_url()}/api/auth/signup", json={
                                "email": email,
                                "password": password,
                                "company_name": company_name
                            })
                            if response.status_code == 201:
                                st.success("Account created! Please sign in.")
                            else:
                                st.error(response.json().get('error', 'Signup failed'))
                        except:
                            st.error("Unable to connect to authentication service")
        
        st.markdown('</div>', unsafe_allow_html=True)

def analysis_platform():
    """Display the analysis platform"""
    st.markdown('<div class="analysis-header"><h1>🎯 VeritasLogic Analysis Platform</h1><p>Multi-Standard Accounting Analysis with AI & Hybrid RAG</p></div>', unsafe_allow_html=True)
    
    # Quick logout in sidebar
    with st.sidebar:
        st.write("**Account**")
        if st.button("🚪 Sign Out"):
            del st.session_state.user_token
            st.rerun()
    
    # Main analysis interface
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="standard-card">
            <h3 style="color: #007bff;">ASC 606</h3>
            <p>Revenue Recognition</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch ASC 606 Analysis", key="asc606"):
            st.info("🚧 ASC 606 analysis tool loading...")
    
    with col2:
        st.markdown("""
        <div class="standard-card">
            <h3 style="color: #007bff;">ASC 842</h3>
            <p>Lease Accounting</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch ASC 842 Analysis", key="asc842"):
            st.info("🚧 ASC 842 analysis tool loading...")
    
    with col3:
        st.markdown("""
        <div class="standard-card">
            <h3 style="color: #007bff;">ASC 718</h3>
            <p>Stock Compensation</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch ASC 718 Analysis", key="asc718"):
            st.info("🚧 ASC 718 analysis tool loading...")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.markdown("""
        <div class="standard-card">
            <h3 style="color: #007bff;">ASC 805</h3>
            <p>Business Combinations</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch ASC 805 Analysis", key="asc805"):
            st.info("🚧 ASC 805 analysis tool loading...")
    
    with col5:
        st.markdown("""
        <div class="standard-card">
            <h3 style="color: #007bff;">ASC 340-40</h3>
            <p>Contract Costs</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch ASC 340-40 Analysis", key="asc34040"):
            st.info("🚧 ASC 340-40 analysis tool loading...")
    
    with col6:
        st.markdown("""
        <div class="standard-card">
            <h3 style="color: #007bff;">Research Assistant</h3>
            <p>RAG-powered guidance</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Research Assistant", key="research"):
            st.info("🚧 Research Assistant loading...")
    
    # Document Upload Section
    st.markdown("---")
    st.subheader("📄 Document Analysis")
    
    uploaded_file = st.file_uploader(
        "Upload contract or financial document", 
        type=['pdf', 'docx', 'txt'],
        help="Upload a document to analyze under multiple accounting standards"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.success(f"✅ Uploaded: {uploaded_file.name}")
        with col2:
            if st.button("🔍 Start Analysis"):
                st.info("🚧 Analysis engine starting - full integration coming soon!")

def main():
    """Main application logic"""
    # Check authentication
    is_auth, user_data = check_auth_status()
    
    if is_auth:
        # Show the analysis platform
        analysis_platform()
    else:
        # Show login/signup
        login_form()

if __name__ == "__main__":
    main()