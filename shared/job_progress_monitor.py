"""
Shared Job Progress Monitor for VeritasLogic Analysis Platform
Provides reusable polling logic for all ASC standards
"""

import streamlit as st
import logging
import time
from typing import Optional

from shared.job_manager import job_manager
from shared.analysis_manager import analysis_manager

logger = logging.getLogger(__name__)

def monitor_job_progress(
    asc_standard: str,
    job_id: str,
    db_analysis_id: int,
    session_id: str,
    user_token: str,
    service_token: Optional[str] = None
):
    """
    Monitor analysis job progress and handle completion
    
    Args:
        asc_standard: ASC standard name (e.g., 'ASC 606')
        job_id: Redis job ID for polling
        db_analysis_id: Database analysis ID
        session_id: Session ID for caching results
        user_token: User authentication token (or service token)
        service_token: Optional service token (if different from user_token)
    """
    try:
        # Determine which token to use for API calls
        auth_token = service_token if service_token else user_token
        
        # Determine session key prefix based on ASC standard
        asc_prefix = asc_standard.lower().replace(' ', '').replace('-', '')  # e.g., 'asc606'
        
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
                        f'{WEBSITE_URL}/api/analysis/status/{db_analysis_id}',
                        headers={'Authorization': f'Bearer {auth_token}'},
                        timeout=10
                    )
                    
                    if status_response.ok:
                        analysis_data = status_response.json()
                        logger.info(f"✓ Status API response: status={analysis_data.get('status')}, has_memo={bool(analysis_data.get('memo_content'))}")
                        
                        if analysis_data['status'] == 'completed' and analysis_data.get('memo_content'):
                            st.success("🎉 **Analysis completed successfully!**")
                            
                            # Store memo in session state for display
                            analysis_key = f'{asc_prefix}_analysis_complete_{session_id}'
                            memo_key = f'{asc_prefix}_memo_data_{session_id}'
                            
                            logger.info(f"✓ Storing memo in session state: session_id={session_id}, analysis_key={analysis_key}")
                            
                            st.session_state[analysis_key] = True
                            st.session_state[memo_key] = {
                                'memo_content': analysis_data['memo_content'],
                                'analysis_id': db_analysis_id,
                                'memo_uuid': analysis_data.get('memo_uuid'),
                                'completion_timestamp': analysis_data.get('completed_at')
                            }
                            
                            logger.info(f"✓ Session state stored. Keys in session: {list(st.session_state.keys())}")
                            
                            # Mark analysis as complete before rerun
                            ui_analysis_id = st.session_state.get('current_ui_analysis_id')
                            if ui_analysis_id:
                                analysis_manager.complete_analysis(ui_analysis_id, success=True)
                                logger.info(f"✓ Marked analysis {ui_analysis_id} as complete")
                            
                            st.info("📄 **Memo ready!** Refreshing page to display results...")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Analysis completed but memo not available.")
                            logger.error(f"Analysis status: {analysis_data.get('status')}, memo length: {len(analysis_data.get('memo_content', ''))}")
                            # Mark analysis as failed (memo not available)
                            ui_analysis_id = st.session_state.get('current_ui_analysis_id')
                            if ui_analysis_id:
                                analysis_manager.complete_analysis(ui_analysis_id, success=False, error_message="Memo not available after completion")
                    else:
                        st.error(f"❌ Failed to retrieve analysis: {status_response.text}")
                        logger.error(f"Status fetch failed: {status_response.status_code}")
                        # Mark analysis as failed (status fetch failed)
                        ui_analysis_id = st.session_state.get('current_ui_analysis_id')
                        if ui_analysis_id:
                            analysis_manager.complete_analysis(ui_analysis_id, success=False, error_message=f"Status fetch failed: {status_response.status_code}")
                        
                except Exception as e:
                    st.error(f"❌ Error retrieving analysis: {str(e)}")
                    logger.error(f"Failed to fetch analysis status: {str(e)}")
                    # Mark analysis as failed (exception during status fetch)
                    ui_analysis_id = st.session_state.get('current_ui_analysis_id')
                    if ui_analysis_id:
                        analysis_manager.complete_analysis(ui_analysis_id, success=False, error_message=str(e))
                
                return
                
            elif job_status == 'failed':
                # Job failed
                progress_bar.empty()
                status_container.error("❌ Analysis failed")
                
                error_msg = status_info.get('error', 'Unknown error')
                st.error(f"❌ **Analysis Failed**: {error_msg}")
                
                logger.error(f"Job {job_id} failed: {error_msg}")
                
                # Mark analysis as failed
                ui_analysis_id = st.session_state.get('current_ui_analysis_id')
                if ui_analysis_id:
                    analysis_manager.complete_analysis(ui_analysis_id, success=False, error_message=error_msg)
                
                return
                
            elif job_status == 'started':
                # Job is running - show progress with animated spinner
                progress = status_info.get('progress', {})
                current_step = progress.get('current_step', 1)
                total_steps = progress.get('total_steps', 5)
                step_name = progress.get('step_name', f'Step {current_step}')
                
                # Update progress bar (0-100%)
                progress_pct = int(((current_step - 0.5) / total_steps) * 100)
                progress_bar.progress(progress_pct)
                
                # Show animated spinner with current step
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
        
        # Mark analysis as failed due to timeout
        ui_analysis_id = st.session_state.get('current_ui_analysis_id')
        if ui_analysis_id:
            analysis_manager.complete_analysis(ui_analysis_id, success=False, error_message="Analysis timed out after 30 minutes")
        
    except Exception as e:
        logger.error(f"Error in job monitoring: {str(e)}")
        st.error(f"❌ **Error**: {str(e)}")
        
        # Clear analysis tracking on exception
        ui_analysis_id = st.session_state.get('current_ui_analysis_id')
        if ui_analysis_id:
            analysis_manager.complete_analysis(ui_analysis_id, success=False, error_message=str(e))
