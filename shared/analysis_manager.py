"""
Analysis Manager for VeritasLogic Analysis Platform
Handles analysis concurrency, state tracking, and comprehensive logging
"""

import streamlit as st
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from shared.api_cost_tracker import reset_cost_tracking, get_total_estimated_cost

logger = logging.getLogger(__name__)

class AnalysisManager:
    """Manages analysis state, concurrency control, and logging"""
    
    def __init__(self):
        self.session_key_active = 'active_analysis'
        self.session_key_history = 'analysis_history'
    
    def is_analysis_active(self) -> bool:
        """
        Check if user currently has an active analysis
        
        Returns:
            True if analysis is currently running, False otherwise
        """
        if self.session_key_active not in st.session_state:
            return False
        
        active_analysis = st.session_state[self.session_key_active]
        if not active_analysis:
            return False
        
        # Check if analysis is still valid (not expired)
        start_time = active_analysis.get('start_time', 0)
        current_time = time.time()
        
        # Auto-expire analyses after 30 minutes (1800 seconds)
        if current_time - start_time > 1800:
            self.clear_active_analysis()
            logger.info("Auto-expired stale analysis session")
            return False
        
        return True
    
    def get_active_analysis_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about currently active analysis
        
        Returns:
            Dict with analysis info or None if no active analysis
        """
        if not self.is_analysis_active():
            return None
        
        return st.session_state[self.session_key_active]
    
    def start_analysis(self, analysis_details: Dict[str, Any]) -> str:
        """
        Start a new analysis and mark it as active
        
        Args:
            analysis_details: Details about the analysis being started
            
        Returns:
            Unique analysis ID
        """
        if self.is_analysis_active():
            raise ValueError("Cannot start analysis - another analysis is already active")
        
        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())[:8]
        
        # Reset API cost tracking for new analysis
        reset_cost_tracking()
        
        # Create analysis record
        analysis_record = {
            'analysis_id': analysis_id,
            'asc_standard': analysis_details.get('asc_standard', 'unknown'),
            'total_words': analysis_details.get('total_words', 0),
            'file_count': analysis_details.get('file_count', 0),
            'tier_info': analysis_details.get('tier_info', {}),
            'cost_charged': analysis_details.get('cost_charged', 0.0),
            'start_time': time.time(),
            'start_timestamp': datetime.now().isoformat(),
            'status': 'running',
            'user_id': st.session_state.get('user_data', {}).get('id', 'unknown')
        }
        
        # Set as active analysis
        st.session_state[self.session_key_active] = analysis_record
        
        # Log analysis start
        self._log_analysis_event('start', analysis_record)
        
        logger.info(f"Started analysis {analysis_id}: {analysis_details.get('asc_standard')} - {analysis_details.get('total_words')} words")
        
        return analysis_id
    
    def complete_analysis(self, analysis_id: str, success: bool = True, error_message: Optional[str] = None) -> bool:
        """
        Mark analysis as completed
        
        Args:
            analysis_id: ID of analysis to complete
            success: Whether analysis completed successfully
            error_message: Error message if analysis failed
            
        Returns:
            True if analysis was marked complete, False if not found or invalid
        """
        active_analysis = self.get_active_analysis_info()
        
        if not active_analysis or active_analysis['analysis_id'] != analysis_id:
            logger.warning(f"Attempted to complete non-active analysis {analysis_id}")
            return False
        
        # Calculate duration
        end_time = time.time()
        duration = end_time - active_analysis['start_time']
        
        # Update analysis record
        active_analysis['status'] = 'completed' if success else 'failed'
        active_analysis['end_time'] = end_time
        active_analysis['end_timestamp'] = datetime.now().isoformat()
        active_analysis['duration_seconds'] = duration
        active_analysis['success'] = success
        
        if error_message:
            active_analysis['error_message'] = error_message
        
        # Save to database for dashboard history  
        self._save_to_database(active_analysis)
        
        # Add to analysis history
        self._add_to_history(active_analysis)
        
        # Log completion
        self._log_analysis_event('complete', active_analysis)
        
        # Clear active analysis
        self.clear_active_analysis()
        
        logger.info(f"Completed analysis {analysis_id}: {'success' if success else 'failed'} - {duration:.1f}s")
        
        return True
    
    def clear_active_analysis(self):
        """Clear the currently active analysis"""
        if self.session_key_active in st.session_state:
            del st.session_state[self.session_key_active]
    
    def show_active_analysis_warning(self) -> bool:
        """
        Show warning message if user tries to start analysis while one is active
        
        Returns:
            True if warning was shown, False if no active analysis
        """
        active_analysis = self.get_active_analysis_info()
        
        if not active_analysis:
            return False
        
        # Calculate time elapsed
        elapsed = time.time() - active_analysis['start_time']
        elapsed_minutes = int(elapsed // 60)
        
        st.warning(f"""
        ⚠️ **Analysis Already in Progress**
        
        You have an active {active_analysis['asc_standard']} analysis running (started {elapsed_minutes} minutes ago).
        
        Please wait for the current analysis to complete before starting a new one.
        
        **Current Analysis Details:**
        - Memo ID: {active_analysis['analysis_id']}
        - Document Words: {active_analysis['total_words']:,}
        - Cost: \\${active_analysis['cost_charged']:.2f}
        """)
        
        # Provide option to force clear if analysis seems stuck
        if elapsed > 900:  # 15 minutes
            if st.button("🚨 Force Clear Stuck Analysis", key="force_clear_analysis"):
                self.complete_analysis(active_analysis['analysis_id'], success=False, error_message="Force cleared by user")
                st.success("Analysis cleared. You can now start a new analysis.")
                st.rerun()
        
        return True
    
    def _add_to_history(self, analysis_record: Dict[str, Any]):
        """Add completed analysis to user's history"""
        if self.session_key_history not in st.session_state:
            st.session_state[self.session_key_history] = []
        
        # Keep only last 10 analyses in session
        history = st.session_state[self.session_key_history]
        history.append(analysis_record)
        
        if len(history) > 10:
            history = history[-10:]
            st.session_state[self.session_key_history] = history
    
    def _save_to_database(self, analysis_record: Dict[str, Any]):
        """Save completed analysis to database using unified endpoint"""
        try:
            import requests
            from shared.auth_utils import auth_manager
            
            # STRATEGIC FIX: Attempt token refresh before database save to handle long-running analyses
            token = self._get_or_refresh_auth_token()
            if not token:
                logger.error("CRITICAL: No auth token available for database save - user not authenticated!")
                logger.error("Analysis will complete but won't be saved to database or charge credits")
                logger.error("Check authentication flow - user may need to re-login")
                return
            
            # Prepare analysis data for unified endpoint
            # Ensure we always have a valid started_at timestamp
            started_at = analysis_record.get('start_timestamp')
            if not started_at and 'start_time' in analysis_record:
                # Convert Unix timestamp to ISO format
                from datetime import datetime
                started_at = datetime.fromtimestamp(analysis_record['start_time']).isoformat()
            elif not started_at:
                # Fallback to current time if no start time available
                from datetime import datetime
                started_at = datetime.now().isoformat()
            
            analysis_data = {
                'asc_standard': analysis_record.get('asc_standard'),
                'words_count': analysis_record.get('total_words', 0),
                'api_cost': get_total_estimated_cost(),  # Get actual tracked API costs
                'file_count': analysis_record.get('file_count', 1),
                'tier_name': analysis_record.get('tier_info', {}).get('name', 'Unknown'),
                'is_free_analysis': analysis_record.get('cost_charged', 0) == 0,
                'idempotency_key': f"manager_{analysis_record.get('analysis_id', 'unknown')}_{int(analysis_record.get('start_time', 0)*1000)}",
                'started_at': started_at,
                'duration_seconds': analysis_record.get('duration_seconds', 0)
            }
            
            # Save to database via new unified API endpoint - use environment variable
            import os
            backend_url = os.getenv('BACKEND_URL', 'http://127.0.0.1:3000/api')
            website_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            # For production cross-service communication, use website URL
            api_base_url = website_url if not backend_url.startswith('http://127.0.0.1') and not backend_url.startswith('http://localhost') else backend_url.replace('/api', '')
            
            response = requests.post(
                f'{api_base_url}/api/analysis/complete',
                headers={'Authorization': f'Bearer {token}'},
                json=analysis_data,
                timeout=10
            )
            
            if response.ok:
                response_data = response.json()
                memo_uuid = response_data.get('memo_uuid')
                # Store memo_uuid in session state for access by calling code
                import streamlit as st
                st.session_state['analysis_manager_memo_uuid'] = memo_uuid
                logger.info(f"Analysis {analysis_record.get('analysis_id')} saved to database with memo UUID: {memo_uuid}")
            else:
                # Enhanced error logging to capture exact issue
                logger.error(f"Database save failed - Status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response body: {response.text}")
                logger.error(f"Request URL: {api_base_url}/api/analysis/complete")
                logger.error(f"Request payload: {analysis_data}")
                
                # Try to parse error details
                try:
                    error_data = response.json()
                    logger.error(f"Parsed error response: {error_data}")
                except:
                    logger.error("Could not parse error response as JSON")
                
        except Exception as e:
            logger.error(f"Database save error: {e}")
    
    def _get_or_refresh_auth_token(self) -> Optional[str]:
        """Get current auth token or refresh if expired"""
        try:
            from shared.auth_utils import auth_manager
            import requests
            import os
            
            # First try to get current token
            token = auth_manager.get_auth_token()
            if not token:
                logger.warning("No auth token in session")
                return None
            
            # Check if token is still valid by making a quick test call
            backend_url = os.getenv('BACKEND_URL', 'http://127.0.0.1:3000/api')
            website_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            api_base_url = website_url if not backend_url.startswith('http://127.0.0.1') and not backend_url.startswith('http://localhost') else backend_url.replace('/api', '')
            
            # Test current token (use GET method)
            test_response = requests.get(
                f'{api_base_url}/api/auth/validate-token',
                headers={'Authorization': f'Bearer {token}'},
                timeout=5
            )
            
            if test_response.ok:
                logger.info("Current auth token is valid")
                return token
            
            # Token is expired, try to refresh using session cookies  
            logger.info("Auth token expired, attempting refresh")
            import streamlit as st
            
            # STRATEGIC FIX: Use session to preserve cookies for cross-domain requests
            session = requests.Session()
            
            # If we're in Streamlit context, try to get refresh token from browser
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'refresh_token'):
                refresh_token = st.session_state.refresh_token
                session.cookies.set('refresh_token', refresh_token)
            
            refresh_response = session.post(
                f'{api_base_url}/api/auth/refresh-token',
                timeout=5
            )
            
            if refresh_response.ok:
                refresh_data = refresh_response.json()
                new_token = refresh_data.get('token')
                
                # Update session with new token
                import streamlit as st
                st.session_state.auth_token = new_token
                logger.info("Successfully refreshed auth token")
                return new_token
            else:
                logger.error(f"Token refresh failed: {refresh_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def _log_analysis_event(self, event_type: str, analysis_data: Dict[str, Any]):
        """Log analysis events for operational monitoring"""
        log_entry = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'analysis_id': analysis_data.get('analysis_id'),
            'asc_standard': analysis_data.get('asc_standard'),
            'total_words': analysis_data.get('total_words'),
            'file_count': analysis_data.get('file_count'),
            'tier': analysis_data.get('tier_info', {}).get('name'),
            'cost': analysis_data.get('cost_charged'),
            'user_id': analysis_data.get('user_id'),
            'status': analysis_data.get('status'),
            'success': analysis_data.get('success'),
            'duration': analysis_data.get('duration_seconds'),
            'error': analysis_data.get('error_message')
        }
        
        # Log comprehensive analysis data
        logger.info(f"ANALYSIS_EVENT: {json.dumps(log_entry, default=str)}")
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """
        Get user's recent analysis history
        
        Returns:
            List of recent analysis records
        """
        return st.session_state.get(self.session_key_history, [])

# Global instance for use across the application
analysis_manager = AnalysisManager()