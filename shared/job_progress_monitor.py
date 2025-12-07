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

def check_and_resume_polling(asc_standard: str, session_id: str, analysis_type: str = 'standard'):
    """
    Check if there's an active analysis for this ASC standard and resume polling if needed
    
    Args:
        asc_standard: ASC standard name (e.g., 'ASC 606')
        session_id: Session ID for caching results
        analysis_type: Type of analysis ('standard' or 'review') - prevents cross-contamination
    """
    try:
        # Get active analysis from analysis_manager
        active_analysis = analysis_manager.get_active_analysis_info()
        
        if not active_analysis:
            return  # No active analysis to resume
        
        # Check if the active analysis is for this ASC standard
        if active_analysis.get('asc_standard') != asc_standard:
            return  # Different ASC standard, don't resume here
        
        # Check if the analysis type matches - prevent review jobs from resuming on Analysis page
        active_type = active_analysis.get('analysis_type', 'standard')
        if active_type != analysis_type:
            logger.info(f"Skipping resume: analysis_type mismatch (active={active_type}, requested={analysis_type})")
            return  # Different analysis type, don't resume here
        
        # Extract stored polling information
        job_id = active_analysis.get('job_id')
        db_analysis_id = active_analysis.get('db_analysis_id')
        service_token = active_analysis.get('service_token')
        
        if not job_id or not db_analysis_id:
            logger.warning(f"Active analysis missing job_id or db_analysis_id: {active_analysis}")
            return
        
        logger.info(f"📌 Resume polling: ASC={asc_standard}, type={analysis_type}, job_id={job_id}, db_analysis_id={db_analysis_id}")
        
        # Get user token from session (fallback to service_token if user not logged in)
        user_token = st.session_state.get('user_data', {}).get('auth_token', service_token)
        
        # Resume polling by calling monitor_job_progress
        monitor_job_progress(
            asc_standard=asc_standard,
            job_id=job_id,
            db_analysis_id=db_analysis_id,
            session_id=session_id,
            user_token=user_token,
            service_token=service_token,
            analysis_type=analysis_type
        )
        
    except Exception as e:
        logger.error(f"Error in check_and_resume_polling: {str(e)}")
        # Don't show error to user - just log it and continue page rendering


def monitor_job_progress(
    asc_standard: str,
    job_id: str,
    db_analysis_id: int,
    session_id: str,
    user_token: str,
    service_token: Optional[str] = None,
    analysis_type: str = 'standard'
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
        analysis_type: Type of analysis ('standard' or 'review')
    """
    try:
        # Determine which token to use for API calls
        auth_token = service_token if service_token else user_token
        
        # Determine session key prefix based on ASC standard and analysis type
        # Map to exact prefixes used by page files
        prefix_map = {
            'ASC 606': 'asc606',
            'ASC 340-40': 'asc340',  # NOT asc34040 - matches page file
            'ASC 718': 'asc718',
            'ASC 805': 'asc805',
            'ASC 842': 'asc842'
        }
        base_prefix = prefix_map.get(asc_standard, asc_standard.lower().replace(' ', '').replace('-', ''))
        # Use different prefix for review vs standard analysis to prevent cross-contamination
        asc_prefix = f'review_{base_prefix}' if analysis_type == 'review' else base_prefix
        
        # Poll for job completion
        st.markdown("### 🔄 Analysis Progress")
        if analysis_type == 'review':
            st.info("""
            ✅ **Your review is running. Upon completion, the page will refresh with your analysis and review comments.**
            """)
        else:
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
                                'completion_timestamp': analysis_data.get('completed_at'),
                                'source_memo_filename': analysis_data.get('source_memo_filename'),
                                'analysis_type': analysis_type
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
