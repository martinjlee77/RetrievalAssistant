"""
Background Worker for ASC Analysis Processing
This worker runs in a separate process and handles long-running analyses
"""

import logging
import sys
import os
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

def run_asc606_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ASC 606 analysis in background worker
    
    Args:
        job_data: Dictionary containing all necessary analysis parameters
        
    Returns:
        Dictionary with analysis results including memo content
    """
    analysis_id = job_data['analysis_id']
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
        customer_name = None
        try:
            if "the Customer" in combined_text:
                customer_name = "the Customer"
        except:
            pass
        
        # Initialize results storage
        analysis_results = {}
        
        # Run 5 ASC 606 steps with progress reporting
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
                
                # Analyze the step
                step_result = analyzer._analyze_step(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name,
                    additional_context=additional_context
                )
                
                analysis_results[f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
                # Continue with other steps
                analysis_results[f'step_{step_num}'] = {
                    'markdown_content': f"Error in Step {step_num}: {str(e)}",
                    'title': f"Step {step_num}: Error",
                    'step_num': str(step_num)
                }
        
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
        
        memo_generator = CleanMemoGenerator()
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
        
        memo_content = memo_generator.generate_clean_memo(
            analysis_results,
            filename=filename,
            customer_name=customer_name,
            analysis_id=analysis_id
        )
        
        # Get actual API costs
        api_cost = get_total_estimated_cost()
        
        # Save analysis to database
        logger.info("💾 Saving analysis to database...")
        backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
        
        save_response = requests.post(
            f'{backend_url}/api/analysis/save',
            headers={'Authorization': f'Bearer {user_token}'},
            json={
                'analysis_id': analysis_id,
                'memo_content': memo_content,
                'api_cost': api_cost,
                'success': True,
                'asc_standard': 'ASC 606',
                'words_count': pricing_result['total_words'],
                'tier_name': pricing_result['tier_info']['name'],
                'file_count': pricing_result['file_count'],
                'cost_charged': pricing_result['tier_info']['price']
            },
            timeout=30
        )
        
        if not save_response.ok:
            logger.error(f"Failed to save analysis to database: {save_response.text}")
            raise Exception(f"Database save failed: {save_response.status_code}")
        
        memo_uuid = save_response.json().get('memo_uuid')
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
        
        # Save failed analysis to database
        try:
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            requests.post(
                f'{backend_url}/api/analysis/save',
                headers={'Authorization': f'Bearer {user_token}'},
                json={
                    'analysis_id': analysis_id,
                    'success': False,
                    'error_message': str(e),
                    'asc_standard': 'ASC 606',
                    'words_count': pricing_result['total_words'],
                    'tier_name': pricing_result['tier_info']['name'],
                    'file_count': pricing_result['file_count'],
                    'cost_charged': 0  # Don't charge for failed analysis
                },
                timeout=30
            )
        except:
            logger.error("Failed to save error to database")
        
        # Re-raise exception so RQ marks job as failed
        raise
