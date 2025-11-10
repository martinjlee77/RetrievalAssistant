"""
Job-based Analysis Runner for ASC 340-40
Submits analysis to background queue and polls for completion

NOTE: ASC 340-40 has only 2 steps (not 5)
"""

import streamlit as st
import logging
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from shared.job_manager import job_manager
from shared.analysis_manager import analysis_manager
from shared.job_progress_monitor import monitor_job_progress

logger = logging.getLogger(__name__)

def submit_and_monitor_asc340_job(
    allowance_result: Dict[str, Any],
    additional_context: str,
    user_token: str,
    cached_combined_text: str,
    uploaded_filenames: List[str],
    session_id: str,
    org_id: int,
    total_words: int
):
    """
    Submit ASC 340-40 analysis job to background queue and monitor progress
    
    NOTE: ASC 340-40 has only 2 steps, not 5
    
    Args:
        allowance_result: Subscription allowance check result
        additional_context: User-provided context
        user_token: JWT authentication token
        cached_combined_text: De-identified contract text
        uploaded_filenames: List of uploaded file names
        session_id: Session ID for caching results
        org_id: Organization ID for word deduction
        total_words: Total words used for this analysis
    """
    try:
        # Get user ID from session state (set during login)
        user_data = st.session_state.get('user_data', {})
        user_id = user_data.get('id')
        if not user_id:
            st.error("❌ User authentication failed. Please refresh and log in again.")
            return
        
        # CRITICAL: Create analysis record FIRST with status='processing'
        # This stores authoritative pricing info that backend will use for billing
        # Backend will generate the database INTEGER analysis_id
        import requests
        from shared.auth_utils import WEBSITE_URL
        
        create_response = requests.post(
            f'{WEBSITE_URL}/api/analysis/create',
            headers={'Authorization': f'Bearer {user_token}'},
            json={
                'asc_standard': 'ASC 340-40',
                'words_count': total_words,
                'file_count': allowance_result['file_count'],
                'org_id': org_id  # For word deduction tracking
            },
            timeout=10
        )
        
        if not create_response.ok:
            st.error(f"❌ Failed to create analysis record: {create_response.text}")
            return
        
        # Extract database analysis_id (INTEGER) and service token from response
        create_data = create_response.json()
        db_analysis_id = create_data.get('analysis_id')  # This is the database INTEGER
        service_token = create_data.get('service_token')  # Long-lived token for worker
        
        if not service_token:
            st.error("❌ Failed to generate service token for background worker")
            return
        
        logger.info(f"✓ Analysis record created with database ID: {db_analysis_id}")
        
        # Submit job to Redis queue with service token (not user token)
        # Service token is long-lived (24h) to prevent expiration during analysis
        try:
            job_id = job_manager.submit_analysis_job(
                asc_standard='ASC 340-40',
                analysis_id=db_analysis_id,  # Pass database INTEGER id to worker
                user_id=user_id,
                user_token=service_token,  # Use service token instead of user token
                allowance_result=allowance_result,
                additional_context=additional_context,
                combined_text=cached_combined_text,
                uploaded_filenames=uploaded_filenames,
                org_id=org_id,  # For word deduction
                total_words=total_words  # For word deduction
            )
            
            logger.info(f"Job submitted: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit job: {str(e)}")
            st.error(f"❌ Failed to submit analysis job: {str(e)}")
            return
        
        # Start analysis tracking in session state (for UI blocking and resume polling)
        # This must happen AFTER job submission so we have job_id
        ui_analysis_id = analysis_manager.start_analysis({
            'asc_standard': 'ASC 340-40',
            'total_words': total_words,
            'file_count': allowance_result['file_count'],
            'tier_info': allowance_result.get('tier_info', {}),
            'cost_charged': allowance_result.get('cost_charged', 0.0),
            'job_id': job_id,  # Store for resume polling
            'db_analysis_id': db_analysis_id,  # Store database ID
            'service_token': service_token  # Store long-lived token for resume polling
        })
        
        # Store analysis IDs in session state for tracking across navigation
        st.session_state['current_ui_analysis_id'] = ui_analysis_id
        st.session_state['current_db_analysis_id'] = db_analysis_id
        
        logger.info(f"✓ Started analysis tracking: UI ID={ui_analysis_id}, DB ID={db_analysis_id}, Job ID={job_id}")
        
        # Delegate to shared monitor for polling
        monitor_job_progress(
            asc_standard='ASC 340-40',
            job_id=job_id,
            db_analysis_id=db_analysis_id,
            session_id=session_id,
            user_token=user_token,
            service_token=service_token
        )
        
    except Exception as e:
        logger.error(f"Error in job submission: {str(e)}")
        st.error(f"❌ **Error**: {str(e)}")
