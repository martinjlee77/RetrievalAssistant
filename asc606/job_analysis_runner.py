"""
Job-based Analysis Runner for ASC 606
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

def submit_and_monitor_asc606_job(
    pricing_result: Dict[str, Any],
    additional_context: str,
    user_token: str,
    cached_combined_text: str,
    uploaded_filenames: List[str],
    session_id: str
):
    """
    Submit ASC 606 analysis job to background queue and monitor progress
    
    Args:
        pricing_result: Pricing calculation result
        additional_context: User-provided context
        user_token: JWT authentication token
        cached_combined_text: De-identified contract text
        uploaded_filenames: List of uploaded file names
        session_id: Session ID for caching results
    """
    try:
        # Generate unique analysis ID
        import uuid
        analysis_id = f"asc606_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Get user ID from session state (set during login)
        user_data = st.session_state.get('user_data', {})
        user_id = user_data.get('id')
        if not user_id:
            st.error("❌ User authentication failed. Please refresh and log in again.")
            return
        
        # CRITICAL: Create analysis record FIRST with status='processing'
        # This stores authoritative pricing info that backend will use for billing
        st.info("📝 Creating analysis record...")
        import requests
        
        backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
        create_response = requests.post(
            f'{backend_url}/api/analysis/create',
            headers={'Authorization': f'Bearer {user_token}'},
            json={
                'analysis_id': analysis_id,
                'asc_standard': 'ASC 606',
                'words_count': pricing_result['total_words'],
                'tier_name': pricing_result['tier_info']['name'],
                'file_count': pricing_result['file_count']
            },
            timeout=10
        )
        
        if not create_response.ok:
            st.error(f"❌ Failed to create analysis record: {create_response.text}")
            return
        
        # Extract database analysis_id (INTEGER) from response
        create_data = create_response.json()
        db_analysis_id = create_data.get('analysis_id')  # This is the database INTEGER
        
        logger.info(f"✓ Analysis record created with database ID: {db_analysis_id}")
        
        # Submit job to Redis queue
        st.info("📤 Submitting analysis to background queue...")
        
        try:
            job_id = job_manager.submit_analysis_job(
                asc_standard='ASC 606',
                analysis_id=db_analysis_id,  # Pass database INTEGER id to worker
                user_id=user_id,
                user_token=user_token,
                pricing_result=pricing_result,
                additional_context=additional_context,
                combined_text=cached_combined_text,
                uploaded_filenames=uploaded_filenames
            )
            
            st.success(f"✅ Job submitted successfully! Job ID: {job_id}")
            logger.info(f"Job submitted: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit job: {str(e)}")
            st.error(f"❌ Failed to submit analysis job: {str(e)}")
            return
        
        # Poll for job completion
        st.markdown("---")
        st.markdown("### 🔄 Analysis Progress")
        st.info("""
        ✅ **Your analysis is running in the background!**
        
        You can now:
        - Close this tab safely
        - Switch to other tabs
        - Lock your screen
        - Come back later
        
        **Your analysis will continue running** and results will be saved automatically.
        """)
        
        # Create progress display components
        progress_bar = st.progress(0)
        status_text = st.empty()
        step_details = st.empty()
        
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
                status_text.success("✅ Analysis complete!")
                
                # Fetch memo from database via backend API
                st.info("📥 Retrieving completed analysis...")
                
                try:
                    backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
                    import requests
                    
                    status_response = requests.get(
                        f'{backend_url}/api/analysis/status/{db_analysis_id}',  # Use database INTEGER id
                        headers={'Authorization': f'Bearer {user_token}'},
                        timeout=10
                    )
                    
                    if status_response.ok:
                        analysis_data = status_response.json()
                        
                        if analysis_data['status'] == 'completed' and analysis_data.get('memo_content'):
                            st.success("🎉 **Analysis completed successfully!**")
                            
                            # Store memo in session state for display
                            analysis_key = f'asc606_analysis_complete_{session_id}'
                            memo_key = f'asc606_memo_data_{session_id}'
                            
                            st.session_state[analysis_key] = True
                            st.session_state[memo_key] = {
                                'memo_content': analysis_data['memo_content'],
                                'analysis_id': db_analysis_id,
                                'memo_uuid': analysis_data.get('memo_uuid'),
                                'completion_timestamp': analysis_data.get('completed_at')
                            }
                            
                            st.info("📄 **Memo ready!** Refreshing page to display results...")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Analysis completed but memo not available.")
                            logger.error(f"Analysis status: {analysis_data}")
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
                status_text.error("❌ Analysis failed")
                
                error_msg = status_info.get('error', 'Unknown error')
                st.error(f"❌ **Analysis Failed**: {error_msg}")
                
                logger.error(f"Job {job_id} failed: {error_msg}")
                return
                
            elif job_status == 'started':
                # Job is running - show progress
                progress = status_info.get('progress', {})
                current_step = progress.get('current_step', 1)
                total_steps = progress.get('total_steps', 5)
                step_name = progress.get('step_name', f'Step {current_step}')
                
                # Update progress bar (0-100%)
                progress_pct = int((current_step / total_steps) * 100)
                progress_bar.progress(progress_pct)
                
                # Update status text
                status_text.info(f"🔄 Processing: {step_name} ({current_step}/{total_steps})")
                step_details.markdown(f"**Current Step:** {step_name}  \n**Progress:** {current_step} of {total_steps} steps")
                
            elif job_status == 'queued':
                # Job is queued, waiting to start
                status_text.info("⏳ Job queued - waiting for worker...")
                step_details.markdown("Your analysis is in the queue and will start shortly.")
                
            else:
                # Unknown status
                status_text.warning(f"⚠️ Unknown status: {job_status}")
            
            # Wait before next poll
            poll_count += 1
            time.sleep(10)  # Poll every 10 seconds
        
        # If we exit the loop, job timed out
        st.error("⏱️ **Analysis timed out** - The job took longer than expected. Please contact support.")
        logger.error(f"Job {job_id} timed out after {max_polls * 10} seconds")
        
    except Exception as e:
        logger.error(f"Error in job submission/monitoring: {str(e)}")
        st.error(f"❌ **Error**: {str(e)}")
