"""
Job-based Analysis Runner for ASC 718
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

logger = logging.getLogger(__name__)

def submit_and_monitor_asc718_job(
    pricing_result: Dict[str, Any],
    additional_context: str,
    user_token: str,
    cached_combined_text: str,
    uploaded_filenames: List[str],
    session_id: str
):
    """
    Submit ASC 718 analysis job to background queue and monitor progress
    
    Args:
        pricing_result: Pricing calculation result
        additional_context: User-provided context
        user_token: JWT authentication token
        cached_combined_text: De-identified contract text
        uploaded_filenames: List of uploaded file names
        session_id: Session ID for caching results
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
                'asc_standard': 'ASC 718',
                'words_count': pricing_result['total_words'],
                'tier_name': pricing_result['tier_info']['name'],
                'file_count': pricing_result['file_count']
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
                asc_standard='ASC 718',
                analysis_id=db_analysis_id,  # Pass database INTEGER id to worker
                user_id=user_id,
                user_token=service_token,  # Use service token instead of user token
                pricing_result=pricing_result,
                additional_context=additional_context,
                combined_text=cached_combined_text,
                uploaded_filenames=uploaded_filenames
            )
            
            logger.info(f"Job submitted: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit job: {str(e)}")
            st.error(f"❌ Failed to submit analysis job: {str(e)}")
            return
        
        # Poll for job completion
        st.markdown("### 🔄 Analysis Progress")
        st.info("""
        ✅ **Your analysis is running. Upon completion, the page will refresh with your memo.**
        """)
        
        # Create progress display components
        progress_bar = st.progress(0)
        status_container = st.empty()
        
        # Polling loop
        max_polls = 180  # 30 minutes max (10 second intervals)
        poll_count = 0
        
        while poll_count < max_polls:
            # Check job status
            status_info = job_manager.get_job_status(job_id)
            job_status = status_info['status']
            
            logger.info(f"Job {job_id} status: {job_status}")
            
            if job_status == 'finished':
                # Job completed successfully!
                progress_bar.progress(100)
                status_container.success("✅ Analysis complete!")
                
                # Fetch memo from database via backend API
                st.info("📥 Retrieving completed analysis...")
                
                try:
                    from shared.auth_utils import WEBSITE_URL
                    import requests
                    
                    status_response = requests.get(
                        f'{WEBSITE_URL}/api/analysis/status/{db_analysis_id}',  # Use database INTEGER id
                        headers={'Authorization': f'Bearer {user_token}'},
                        timeout=10
                    )
                    
                    if status_response.ok:
                        analysis_data = status_response.json()
                        logger.info(f"✓ Status API response: status={analysis_data.get('status')}, has_memo={bool(analysis_data.get('memo_content'))}")
                        
                        if analysis_data['status'] == 'completed' and analysis_data.get('memo_content'):
                            st.success("🎉 **Analysis completed successfully!**")
                            
                            # Store memo in session state for display
                            analysis_key = f'asc718_analysis_complete_{session_id}'
                            memo_key = f'asc718_memo_data_{session_id}'
                            
                            logger.info(f"✓ Storing memo in session state: session_id={session_id}, analysis_key={analysis_key}")
                            
                            st.session_state[analysis_key] = True
                            st.session_state[memo_key] = {
                                'memo_content': analysis_data['memo_content'],
                                'analysis_id': db_analysis_id,
                                'memo_uuid': analysis_data.get('memo_uuid'),
                                'completion_timestamp': analysis_data.get('completed_at')
                            }
                            
                            # Clear skip_auto_load flag now that new analysis is complete
                            if 'skip_auto_load' in st.session_state:
                                del st.session_state['skip_auto_load']
                            
                            logger.info(f"✓ Session state stored. Keys in session: {list(st.session_state.keys())}")
                            
                            st.info("📄 **Memo ready!** Refreshing page to display results...")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Analysis completed but memo not available.")
                            logger.error(f"Analysis status: {analysis_data.get('status')}, memo length: {len(analysis_data.get('memo_content', ''))}")
                    else:
                        st.error(f"❌ Failed to retrieve analysis: {status_response.text}")
                        logger.error(f"Status fetch failed: {status_response.status_code}")
                        
                except Exception as e:
                    st.error(f"❌ Error retrieving analysis: {str(e)}")
                    logger.error(f"Failed to fetch analysis status: {str(e)}")
                
                return
                
            elif job_status == 'failed':
                # Job failed
                progress_bar.empty()
                status_container.error("❌ Analysis failed")
                
                error_msg = status_info.get('error', 'Unknown error')
                st.error(f"❌ **Analysis Failed**: {error_msg}")
                
                logger.error(f"Job {job_id} failed: {error_msg}")
                return
                
            elif job_status == 'started':
                # Job is running - show progress with animated spinner
                progress = status_info.get('progress', {})
                current_step = progress.get('current_step', 1)
                total_steps = progress.get('total_steps', 5)
                step_name = progress.get('step_name', f'Step {current_step}')
                
                # Update progress bar (0-100%)
                progress_pct = int((current_step / total_steps) * 100)
                progress_bar.progress(progress_pct)
                
                # Show animated spinner with current step (replaces static status_text)
                with status_container:
                    with st.spinner(f"Processing: {step_name} ({current_step}/{total_steps})"):
                        time.sleep(10)  # Poll every 10 seconds
                        poll_count += 1
                        continue
                
            elif job_status == 'queued':
                # Job is queued, waiting to start with animated spinner
                with status_container:
                    with st.spinner("Waiting in queue..."):
                        time.sleep(10)  # Poll every 10 seconds
                        poll_count += 1
                        continue
                
            else:
                # Unknown status - show spinner while waiting
                with status_container:
                    with st.spinner(f"Status: {job_status}"):
                        time.sleep(10)  # Poll every 10 seconds
                        poll_count += 1
                        continue
        
        # If we exit the loop, job timed out
        st.error("⏱️ **Analysis timed out** - The job took longer than expected. Please contact support.")
        logger.error(f"Job {job_id} timed out after {max_polls * 10} seconds")
        
    except Exception as e:
        logger.error(f"Error in job submission/monitoring: {str(e)}")
        st.error(f"❌ **Error**: {str(e)}")
