"""
Job-based Analysis Runner for Memo Review
Submits analysis to background queue and polls for completion
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

def submit_and_monitor_memo_review_job(
    allowance_result: Dict[str, Any],
    asc_standard: str,
    user_token: str,
    contract_text: str,
    source_memo_text: str,
    source_memo_filename: str,
    contract_filenames: List[str],
    session_id: str,
    org_id: int,
    total_words: int
):
    """
    Submit Memo Review analysis job to background queue and monitor progress
    
    Args:
        allowance_result: Subscription allowance check result
        asc_standard: ASC standard to use for analysis (e.g., 'ASC 606')
        user_token: JWT authentication token
        contract_text: Extracted contract text
        source_memo_text: Extracted text from user's uploaded memo
        source_memo_filename: Name of user's uploaded memo file
        contract_filenames: List of uploaded contract file names
        session_id: Session ID for caching results
        org_id: Organization ID for word deduction
        total_words: Total words used for this analysis
    """
    try:
        user_data = st.session_state.get('user_data', {})
        user_id = user_data.get('id')
        if not user_id:
            st.error("User authentication failed. Please refresh and log in again.")
            return
        
        import requests
        from shared.auth_utils import WEBSITE_URL
        
        create_response = requests.post(
            f'{WEBSITE_URL}/api/analysis/create',
            headers={'Authorization': f'Bearer {user_token}'},
            json={
                'asc_standard': asc_standard,
                'words_count': total_words,
                'file_count': len(contract_filenames),
                'org_id': org_id,
                'analysis_type': 'review',
                'source_memo_filename': source_memo_filename
            },
            timeout=10
        )
        
        if not create_response.ok:
            st.error(f"Failed to create analysis record: {create_response.text}")
            return
        
        create_data = create_response.json()
        db_analysis_id = create_data.get('analysis_id')
        service_token = create_data.get('service_token')
        
        if not service_token:
            st.error("Failed to generate service token for background worker")
            return
        
        logger.info(f"Memo Review analysis record created with database ID: {db_analysis_id}")
        
        try:
            job_id = job_manager.submit_analysis_job(
                asc_standard='MEMO_REVIEW',
                analysis_id=db_analysis_id,
                user_id=user_id,
                user_token=service_token,
                allowance_result=allowance_result,
                additional_context='',
                combined_text=contract_text,
                uploaded_filenames=contract_filenames,
                org_id=org_id,
                total_words=total_words
            )
            
            job_manager.queue.connection.hset(
                f'rq:job:{db_analysis_id}',
                'asc_standard',
                asc_standard
            )
            job_manager.queue.connection.hset(
                f'rq:job:{db_analysis_id}',
                'source_memo_text',
                source_memo_text
            )
            
            logger.info(f"Memo Review job submitted: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit Memo Review job: {str(e)}")
            st.error(f"Failed to submit analysis job: {str(e)}")
            return
        
        ui_analysis_id = analysis_manager.start_analysis({
            'asc_standard': asc_standard,
            'analysis_type': 'review',
            'total_words': total_words,
            'file_count': len(contract_filenames),
            'cost_charged': 0.0,
            'job_id': job_id,
            'db_analysis_id': db_analysis_id,
            'service_token': service_token,
            'source_memo_filename': source_memo_filename
        })
        
        st.session_state['current_ui_analysis_id'] = ui_analysis_id
        st.session_state['current_db_analysis_id'] = db_analysis_id
        st.session_state['memo_review_source_memo'] = source_memo_text
        
        logger.info(f"Started Memo Review analysis tracking: UI ID={ui_analysis_id}, DB ID={db_analysis_id}, Job ID={job_id}")
        
        monitor_job_progress(
            asc_standard=asc_standard,
            job_id=job_id,
            db_analysis_id=db_analysis_id,
            session_id=session_id,
            user_token=user_token,
            service_token=service_token
        )
        
    except Exception as e:
        logger.error(f"Error in Memo Review job submission: {str(e)}")
        st.error(f"Error: {str(e)}")
