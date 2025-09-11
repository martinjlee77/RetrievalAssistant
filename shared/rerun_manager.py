"""
Rerun Manager for VeritasLogic Platform
Handles memo rerun requests and tracking
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from shared.postmark_client import PostmarkClient

logger = logging.getLogger(__name__)

class RerunManager:
    def __init__(self):
        self.postmark_client = PostmarkClient()
        
    def request_rerun(self, memo_id: str, requested_changes: str, 
                     user_email: Optional[str] = None, user_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a rerun request
        
        Args:
            memo_id: Original memo ID
            requested_changes: What the user wants changed
            user_email: User's email (from session if not provided)
            user_name: User's name (from session if not provided)
            
        Returns:
            Dict with success status and message
        """
        try:
            # Get user info from session if not provided
            if not user_email or not user_name:
                user_data = st.session_state.get('user_data', {})
                user_email = user_email or user_data.get('email', 'unknown@email.com')
                first_name = user_data.get('first_name', 'User') or 'User'
                last_name = user_data.get('last_name', '') or ''
                user_name = user_name or f"{first_name} {last_name}".strip()
            
            # Store rerun request in session state
            rerun_key = f'rerun_request_{memo_id}'
            rerun_data = {
                'memo_id': memo_id,
                'requested_changes': requested_changes,
                'user_email': user_email,
                'user_name': user_name,
                'request_timestamp': datetime.now().isoformat(),
                'status': 'submitted'
            }
            
            st.session_state[rerun_key] = rerun_data
            
            # Send notification emails
            admin_sent = self.postmark_client.send_rerun_notification(
                memo_id, user_email or 'unknown@email.com', user_name or 'User', requested_changes
            )
            
            user_sent = self.postmark_client.send_rerun_confirmation(
                user_email or 'unknown@email.com', memo_id
            )
            
            if admin_sent and user_sent:
                logger.info(f"Rerun request submitted successfully for memo {memo_id}")
                return {
                    'success': True,
                    'message': f'Rerun request submitted successfully! You\'ll receive email confirmation and updates for memo {memo_id}.'
                }
            elif admin_sent or user_sent:
                logger.warning(f"Partial email delivery for rerun request {memo_id}")
                return {
                    'success': True,
                    'message': f'Rerun request submitted! Some email notifications may be delayed for memo {memo_id}.'
                }
            else:
                logger.error(f"Failed to send emails for rerun request {memo_id}")
                return {
                    'success': True,  # Request still recorded, just no emails
                    'message': f'Rerun request recorded for memo {memo_id}. You\'ll be contacted within 1-2 business days.'
                }
                
        except Exception as e:
            logger.error(f"Error processing rerun request for memo {memo_id}: {e}")
            return {
                'success': False,
                'message': 'There was an error submitting your rerun request. Please try again or contact support.'
            }
    
    def show_rerun_request_form(self, memo_id: str) -> None:
        """
        Display the rerun request form in Streamlit
        
        Args:
            memo_id: The memo ID to request rerun for
        """
        # Check if rerun already requested
        rerun_key = f'rerun_request_{memo_id}'
        existing_request = st.session_state.get(rerun_key)
        
        if existing_request:
            st.info(f"✅ Rerun already requested for memo {memo_id} on {existing_request['request_timestamp'][:10]}")
            st.write("**Your requested changes:**")
            st.write(existing_request['requested_changes'])
            return
        
        st.markdown("### 🔄 Request Memo Rerun")
        st.write(f"**Memo ID:** {memo_id}")
        
        with st.form(f"rerun_form_{memo_id}"):
            st.write("**What adjustments would you like?**")
            st.caption("Describe specific changes, clarifications, or refinements you need.")
            
            requested_changes = st.text_area(
                "Requested Changes",
                placeholder="e.g., Please emphasize the performance obligation analysis in section 3, clarify the revenue recognition timing conclusion, adjust the tone to be more conservative...",
                height=100,
                label_visibility="collapsed"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                submit_rerun = st.form_submit_button("Submit Request", type="primary")
            with col2:
                st.caption("You'll receive email confirmation and the updated memo within 1-2 business days.")
            
            if submit_rerun:
                if not requested_changes.strip():
                    st.error("Please describe what changes you'd like.")
                    return
                
                result = self.request_rerun(memo_id, requested_changes.strip())
                
                if result['success']:
                    st.success(result['message'])
                    st.rerun()
                else:
                    st.error(result['message'])
    
    def add_rerun_button(self, memo_id: str) -> None:
        """
        Add rerun button to memo display
        
        Args:
            memo_id: The memo ID
        """
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔄 **Request Rerun**", key=f"rerun_btn_{memo_id}", type="secondary", use_container_width=True):
                st.session_state[f'show_rerun_form_{memo_id}'] = True
                st.rerun()
        
        with col2:
            if st.button("🔄 **Analyze Another Contract**", key=f"new_analysis_btn_{memo_id}", type="secondary", use_container_width=True):
                # Clear session state for new analysis
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 
                               any(term in k.lower() for term in ['analysis', 'memo', 'upload', 'file'])]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
        
        # Show rerun form if requested
        if st.session_state.get(f'show_rerun_form_{memo_id}', False):
            self.show_rerun_request_form(memo_id)