"""
Background Worker for ASC Analysis Processing
This worker runs in a separate process and handles long-running analyses
"""

import logging
import sys
import os
import time
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path to import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.knowledge_search import ASC606KnowledgeSearch
from asc606.clean_memo_generator import CleanMemoGenerator
from shared.api_cost_tracker import reset_cost_tracking, get_total_estimated_cost
from rq import get_current_job
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _save_analysis_with_retry(backend_url: str, user_token: str, save_data: Dict[str, Any], max_retries: int = 5) -> Dict[str, Any]:
    """
    Save analysis to database with exponential backoff retry logic
    
    Retries up to max_retries times with exponential backoff (1s, 2s, 4s, 8s, 16s)
    Handles 401 (auth) specially as non-retryable
    
    Returns:
        Response JSON from successful save
        
    Raises:
        Exception with descriptive error message on failure
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Saving analysis (attempt {attempt + 1}/{max_retries})...")
            
            response = requests.post(
                f'{backend_url}/api/analysis/save',
                headers={'Authorization': f'Bearer {user_token}'},
                json=save_data,
                timeout=30
            )
            
            if response.ok:
                logger.info(f"✓ Analysis saved successfully on attempt {attempt + 1}")
                return response.json()
            elif response.status_code == 401:
                # Auth failure - don't retry
                logger.error(f"Authentication failed (401) - token expired")
                raise Exception("Session expired - please log in again and retry your analysis")
            elif response.status_code == 403:
                # Forbidden (e.g., email not verified) - don't retry
                logger.error(f"Access forbidden (403): {response.text}")
                raise Exception(f"Access denied: {response.text}")
            else:
                # Retryable error
                logger.warning(f"Save failed with status {response.status_code}: {response.text}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Database save failed after {max_retries} attempts: {response.status_code} - {response.text}")
                    
        except requests.exceptions.Timeout:
            logger.warning(f"Save request timed out (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Database save timed out after {max_retries} attempts")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error on save (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Network error after {max_retries} attempts: {str(e)}")
    
    # Should never reach here, but just in case
    raise Exception(f"Save failed after {max_retries} attempts")

def run_asc606_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ASC 606 analysis in background worker
    
    Args:
        job_data: Dictionary containing all necessary analysis parameters
        
    Returns:
        Dictionary with analysis results including memo content
    """
    analysis_id = job_data['analysis_id']  # This is now the database INTEGER
    user_id = job_data['user_id']
    user_token = job_data['user_token']
    pricing_result = job_data['pricing_result']
    additional_context = job_data['additional_context']
    combined_text = job_data['combined_text']
    uploaded_filenames = job_data['uploaded_filenames']
    
    logger.info(f"🚀 Worker starting ASC 606 analysis: {analysis_id}")
    
    # Get current job for progress updates
    job = get_current_job()
    
    try:
        # Reset cost tracking for this analysis
        reset_cost_tracking()
        
        # Initialize analyzer and knowledge search
        analyzer = ASC606StepAnalyzer()
        knowledge_search = ASC606KnowledgeSearch()
        
        # Extract customer name for memo generation
        customer_name = "the Customer"  # Default value
        try:
            if "the Customer" in combined_text:
                customer_name = "the Customer"
        except:
            customer_name = "the Customer"  # Fallback on error
        
        # Initialize results storage with proper structure matching analyze_contract
        analysis_results = {
            'steps': {},  # Store steps under 'steps' key like original flow
            'customer_name': customer_name,
            'analysis_title': 'Contract Analysis',
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Run 5 ASC 606 steps with progress reporting
        step_failures = []
        for step_num in range(1, 6):
            # Update job progress
            if job:
                job.meta['progress'] = {
                    'current_step': step_num,
                    'total_steps': 5,
                    'step_name': f'Step {step_num}',
                    'updated_at': datetime.now().isoformat()
                }
                job.save_meta()
            
            logger.info(f"📊 Processing Step {step_num}/5")
            
            try:
                # Get relevant knowledge for this step
                authoritative_context = knowledge_search.search_for_step(step_num, combined_text)
                
                # Analyze the step with retry logic (matches original flow)
                step_result = analyzer._analyze_step_with_retry(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name,
                    additional_context=additional_context
                )
                
                # Store under 'steps' key to match original flow structure
                analysis_results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
                step_failures.append(f"Step {step_num}: {str(e)}")
                # CRITICAL: If step fails, raise exception to prevent billing
                raise Exception(f"Step {step_num} failed: {str(e)}")
        
        # Generate final memo
        logger.info("📝 Generating final memo...")
        if job:
            job.meta['progress'] = {
                'current_step': 5,
                'total_steps': 5,
                'step_name': 'Generating Memo',
                'updated_at': datetime.now().isoformat()
            }
            job.save_meta()
        
        # Generate executive summary, background, and conclusion using analyzer's method
        logger.info("→ Generating executive summary, background, and conclusion...")
        conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results['steps'])
        
        analysis_results['executive_summary'] = analyzer.generate_executive_summary(conclusions_text, customer_name)
        analysis_results['background'] = analyzer.generate_background_section(conclusions_text, customer_name)
        analysis_results['conclusion'] = analyzer.generate_final_conclusion(analysis_results['steps'])
        
        memo_generator = CleanMemoGenerator()
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
        
        # Prepare analysis results with metadata (customer_name already set during init)
        analysis_results['filename'] = filename
        
        memo_content = memo_generator.combine_clean_steps(
            analysis_results,
            analysis_id=analysis_id
        )
        
        # Get actual API costs
        api_cost = get_total_estimated_cost()
        
        # Save analysis to database WITH RETRY LOGIC
        logger.info("💾 Saving analysis to database...")
        backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
        
        # NOTE: Server will look up analysis by analysis_id (database INTEGER)
        # Worker only sends analysis_id, memo_content, api_cost, and success flag
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,  # Database INTEGER id
                'memo_content': memo_content,
                'api_cost': api_cost,
                'success': True
            },
            max_retries=5
        )
        
        memo_uuid = save_result.get('memo_uuid')
        logger.info(f"✓ Analysis saved successfully: {memo_uuid}")
        
        # Return results
        return {
            'success': True,
            'analysis_id': analysis_id,
            'memo_uuid': memo_uuid,
            'memo_content': memo_content,
            'api_cost': api_cost,
            'message': 'Analysis completed successfully'
        }
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {str(e)}", exc_info=True)
        
        # CRITICAL: Always save failure to database with retry logic
        # This prevents analyses from getting stuck in 'processing' status
        try:
            # Get API cost even on failure for tracking
            api_cost = get_total_estimated_cost()
            
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            # Use retry helper to ensure failure is persisted
            # NOTE: Server will look up analysis by analysis_id (database INTEGER)
            _save_analysis_with_retry(
                backend_url=backend_url,
                user_token=user_token,
                save_data={
                    'analysis_id': analysis_id,  # Database INTEGER id
                    'success': False,
                    'error_message': str(e)[:500],  # Truncate to 500 chars
                    'api_cost': api_cost
                },
                max_retries=5
            )
            
            logger.info(f"✓ Failure status saved to database")
            
        except Exception as save_error:
            # If we can't save failure, log it prominently
            logger.critical(f"🔥 CRITICAL: Failed to save failure status to database: {str(save_error)}")
            logger.critical(f"🔥 Original error: {str(e)}")
            logger.critical(f"🔥 Analysis {analysis_id} may be stuck in 'processing' status!")
        
        # Re-raise exception so RQ marks job as failed
        raise
