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

# Backend API configuration
BACKEND_URL = "https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:3001/api"

class AuthManager:
    """Manages user authentication and session state"""
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        
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
        Check if user has sufficient credits for analysis
        Returns dict with can_proceed, credits_balance, etc.
        """
        if not self.is_authenticated():
            return {'can_proceed': False, 'error': 'Not authenticated'}
        
        try:
            response = requests.post(
                f"{self.backend_url}/user/check-credits",
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
            response = requests.get(
                f"{self.backend_url}/user/profile",
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
        #### To access the ASC analysis tools, please sign in with your registered email address.
        """)
        
    # Direct login form (simplified)
    with st.form("streamlit_login"):
        email = st.text_input("Email", placeholder="your.name@yourcompany.com")
        
        if st.form_submit_button("Sign In", type="primary", use_container_width=True):
            if email:
                login_result = attempt_login(email)
                if login_result.get('success'):
                    st.success("Login successful! Refreshing page...")
                    st.rerun()
                else:
                    st.error(login_result.get('error', 'Login failed'))
            else:
                st.error("Please enter your email address")
    
    st.markdown("---")
            
    # Links to full registration site
    st.markdown("#### New User?")
    st.markdown(
        """
        **[Create Account](https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:3001/signup.html)** - Sign up here
        
        **[Your Account](https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:3001/login.html)** - Log in to your account dashboard
        
        **[Need Help?](https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:3001/contact.html)** - Contact support
        """
    )

def attempt_login(email: str) -> Dict[str, Any]:
    """Attempt to login user with email"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/login",
            json={'email': email},
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

def show_user_sidebar(auth_manager: AuthManager):
    """Show user information and controls in sidebar"""
    user_data = auth_manager.get_user_data()
    if not user_data:
        return
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 Account")
        
        # User info
        st.markdown(f"**{user_data['first_name']} {user_data['last_name']}**")
        st.markdown(f"*{user_data['company_name']}*")
        st.markdown(f"📧 {user_data['email']}")
        
        # Credits info
        st.markdown("### 💳 Credits")
        if user_data.get('free_analyses_remaining', 0) > 0:
            st.success(f"🎁 {user_data['free_analyses_remaining']} free analyses remaining")
        
        credits_balance = user_data.get('credits_balance', 0)
        if credits_balance > 0:
            st.info(f"💰 ${credits_balance:.2f} in credits")
        else:
            st.warning("💰 $0.00 in credits")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Dashboard", use_container_width=True):
                st.link_button("Go to Dashboard", "https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:8000/dashboard.html")
        
        with col2:
            if st.button("Logout", use_container_width=True):
                auth_manager.logout()

def show_credits_warning(required_credits: float, auth_manager: AuthManager):
    """Show warning if user doesn't have sufficient credits"""
    credits_info = auth_manager.check_credits(required_credits)
    
    if not credits_info.get('can_proceed', False):
        st.error(
            f"""
            **Insufficient Credits for Analysis**
            
            This analysis requires **${required_credits:.2f}** in credits.
            
            **Your current balance:**
            - Free analyses: {credits_info.get('free_analyses_remaining', 0)}
            - Paid credits: ${credits_info.get('credits_balance', 0):.2f}
            
            **Next steps:**
            1. [Add credits to your account](https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:8000/dashboard.html)
            2. Contact support for assistance
            """
        )
        return False
    
    # Show cost estimate
    if credits_info.get('is_free_analysis', False):
        st.success("🎁 This analysis will use one of your free analyses!")
    else:
        st.info(f"💰 This analysis will cost **${required_credits:.2f}** from your credit balance.")
    
    return True

# Initialize auth manager instance for global use
auth_manager = AuthManager()