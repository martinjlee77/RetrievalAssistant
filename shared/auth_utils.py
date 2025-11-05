"""
Authentication utilities for VeritasLogic Streamlit app
Handles user authentication, session management, and access control
"""

import streamlit as st
import requests
import json
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Backend API configuration - Use environment variables for cross-deployment support
import os
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
STREAMLIT_URL = os.getenv('STREAMLIT_URL', 'https://tas.veritaslogic.ai')

# Log the current configuration for debugging
logger.info(f"Auth Utils Configuration: WEBSITE_URL={WEBSITE_URL}")

class AuthManager:
    """Manages user authentication and session state"""
    
    def __init__(self):
        self.backend_url = WEBSITE_URL
        
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return (
            'auth_token' in st.session_state and 
            'user_data' in st.session_state and
            st.session_state.auth_token is not None
        )
    
    def get_user_data(self) -> Optional[Dict[str, Any]]:
        """Get current user data from session"""
        if self.is_authenticated():
            return st.session_state.user_data
        return None
    
    def get_auth_token(self) -> Optional[str]:
        """Get current auth token from session"""
        if self.is_authenticated():
            return st.session_state.auth_token
        return None
    
    def logout(self):
        """Clear user session and logout"""
        if 'auth_token' in st.session_state:
            del st.session_state.auth_token
        if 'user_data' in st.session_state:
            del st.session_state.user_data
        if 'credits_info' in st.session_state:
            del st.session_state.credits_info
        st.rerun()
    
    def check_credits(self, required_credits: float) -> Dict[str, Any]:
        """
        Check if user has sufficient word allowance for analysis
        Returns dict with can_proceed, subscription info, etc.
        """
        if not self.is_authenticated():
            return {'can_proceed': False, 'error': 'Not authenticated'}
        
        try:
            # Use WEBSITE_URL for API calls
            credits_url = f"{WEBSITE_URL}/api/user/check-credits"
            
            response = requests.post(
                credits_url,
                headers={'Authorization': f'Bearer {self.get_auth_token()}'},
                json={'required_credits': required_credits},
                timeout=10
            )
            
            if response.ok:
                return response.json()
            else:
                logger.error(f"Credits check failed: {response.status_code}")
                return {'can_proceed': False, 'error': 'Failed to check credits'}
                
        except Exception as e:
            logger.error(f"Credits check error: {e}")
            return {'can_proceed': False, 'error': 'Network error'}
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Get detailed user profile including recent analyses"""
        if not self.is_authenticated():
            return None
        
        try:
            # Use WEBSITE_URL for API calls
            profile_url = f"{WEBSITE_URL}/api/user/profile"
            
            response = requests.get(
                profile_url,
                headers={'Authorization': f'Bearer {self.get_auth_token()}'},
                timeout=10
            )
            
            if response.ok:
                return response.json()
            else:
                logger.error(f"Profile fetch failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Profile fetch error: {e}")
            return None

def require_authentication():
    """
    Decorator function to require authentication for a page.
    Call this at the start of any protected page.
    Returns True if authenticated, False if redirected to login.
    """
    auth_manager = AuthManager()
    
    # First try cross-domain authentication (from URL parameters, etc.)
    if not auth_manager.is_authenticated():
        if try_cross_domain_auth():
            auth_manager = AuthManager()  # Refresh after potential login
    
    if not auth_manager.is_authenticated():
        show_login_page()
        return False
    
    # Show user info in sidebar
    show_user_sidebar(auth_manager)
    return True

def show_login_page():
    """Show login page when user is not authenticated"""
    st.title("🔐 Authentication Required")
    
    with st.container(border=False):
        st.markdown("""  
        #### To access the ASC analysis tools, please sign in with your email address.
        """)
        
    # Direct login form (with email and password)
    with st.form("streamlit_login"):
        email = st.text_input("Email", placeholder="your.name@yourcompany.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.form_submit_button("Sign In", type="primary", use_container_width=True):
            if email and password:
                login_result = attempt_login(email, password)
                if login_result.get('success'):
                    st.success("Login successful! Refreshing page...")
                    st.rerun()
                else:
                    st.error(login_result.get('error', 'Login failed'))
            else:
                st.error("Please enter both email and password")
    
    st.markdown("---")
            
    # Links to full registration site
    st.markdown(
        f"""

        **[Reset your password]({WEBSITE_URL}/forgot-password.html)** - Forgot your password? Reset it here
        
        **[Create Account]({WEBSITE_URL}/signup.html)** - New users, sign up here
        

        
        **[Your Account]({WEBSITE_URL}/login.html)** - Log in to your account dashboard
        
        **[Need Help?]({WEBSITE_URL}/contact.html)** - Contact support
        """
    )

def attempt_login(email: str, password: str) -> Dict[str, Any]:
    """Attempt to login user with email and password via main website"""
    try:
        # Use WEBSITE_URL for API calls
        login_url = f"{WEBSITE_URL}/api/login"
        logger.info(f"SSO: Attempting login at {login_url}")
        
        response = requests.post(
            login_url,
            json={'email': email, 'password': password},
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            # Store auth data in session
            st.session_state.auth_token = data['token']
            st.session_state.user_data = data['user']
            return {'success': True}
        else:
            error_data = response.json()
            return {'success': False, 'error': error_data.get('error', 'Login failed')}
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {'success': False, 'error': 'Network error. Please try again.'}

def validate_existing_token(token: str) -> Dict[str, Any]:
    """Validate an existing token using the cross-subdomain validation endpoint"""
    try:
        # Use WEBSITE_URL for API calls
        validation_url = f"{WEBSITE_URL}/api/auth/validate-token"
        logger.info(f"SSO: Validating token at {validation_url}")
        
        response = requests.post(
            validation_url,
            json={'token': token},
            timeout=10
        )
        
        logger.info(f"SSO: Validation response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            if data.get('valid'):
                return {'valid': True, 'user': data['user']}
            else:
                return {'valid': False, 'error': data.get('error', 'Invalid token')}
        else:
            return {'valid': False, 'error': f'Token validation failed with status {response.status_code}'}
            
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return {'valid': False, 'error': f'Network error during validation: {str(e)}'}

def try_cross_domain_auth():
    """Try to authenticate using tokens from URL parameters or cross-domain cookies"""
    # Check for token in URL parameters (from redirects)
    query_params = st.query_params
    
    if 'auth_token' in query_params:
        token = query_params['auth_token']
        logger.info(f"SSO: Found auth_token in URL params, attempting validation")
        
        validation = validate_existing_token(token)
        logger.info(f"SSO: Token validation result: {validation.get('valid', False)}")
        
        if validation.get('valid'):
            st.session_state.auth_token = token
            st.session_state.user_data = validation['user']
            logger.info(f"SSO: Auto-login successful for user {validation['user'].get('email', 'unknown')}")
            
            # Clear only the auth_token from URL for security, preserve other params like analysis_id
            if 'auth_token' in st.query_params:
                del st.query_params['auth_token']
            
            return True
        else:
            logger.warning(f"SSO: Token validation failed: {validation.get('error', 'Unknown error')}")
            # Clear only the invalid auth_token from URL, preserve other params
            if 'auth_token' in st.query_params:
                del st.query_params['auth_token']
    
    return False

def show_user_sidebar(auth_manager: AuthManager):
    """Show user information and controls in sidebar"""
    user_data = auth_manager.get_user_data()
    if not user_data:
        return
    
    with st.sidebar:
     
        # User info
        st.markdown(f"Logged in as {user_data['first_name']} {user_data['last_name']}")
        st.markdown(f"{user_data['company_name']}")
        # st.text(user_data['email'])
              
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("My Account", f"{WEBSITE_URL}/dashboard.html", width="stretch")
        
        with col2:
            if st.button("Logout", width="stretch"):
                auth_manager.logout()

def show_credits_warning(required_credits: float, auth_manager: AuthManager):
    """Show warning if user doesn't have sufficient word allowance (DEPRECATED - use subscription checks)"""
    credits_info = auth_manager.check_credits(required_credits)
    
    if not credits_info.get('can_proceed', False):
        # Get subscription info from the response
        sub_info = credits_info.get('subscription', {})
        words_available = credits_info.get('words_available', 0)
        
        st.error(
            f"""
            **Insufficient Word Allowance for Analysis**
            
            This analysis requires **{required_credits:,.0f}** words.
            
            **Your current allowance:**
            - Plan: {sub_info.get('plan_name', 'No active subscription')}
            - Words available: {words_available:,.0f}
            
            **Next steps:**
            1. [Upgrade your subscription]({WEBSITE_URL}/dashboard.html)
            2. Contact support for assistance
            """
        )
        return False
    
    
    return True

# Initialize auth manager instance for global use
auth_manager = AuthManager()