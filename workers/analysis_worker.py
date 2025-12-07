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
from asc842.step_analyzer import ASC842StepAnalyzer
from asc842.knowledge_search import ASC842KnowledgeSearch
from asc842.clean_memo_generator import CleanMemoGenerator as ASC842CleanMemoGenerator
from asc718.step_analyzer import ASC718StepAnalyzer
from asc718.knowledge_search import ASC718KnowledgeSearch
from asc718.clean_memo_generator import CleanMemoGenerator as ASC718CleanMemoGenerator
from asc805.step_analyzer import ASC805StepAnalyzer
from asc805.knowledge_search import ASC805KnowledgeSearch
from asc805.clean_memo_generator import CleanMemoGenerator as ASC805CleanMemoGenerator
from asc340.step_analyzer import ASC340StepAnalyzer
from asc340.knowledge_search import ASC340KnowledgeSearch
from asc340.clean_memo_generator import CleanMemoGenerator as ASC340CleanMemoGenerator
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
    allowance_result = job_data.get('allowance_result')  # New subscription-based data
    pricing_result = job_data.get('pricing_result')  # Legacy fallback
    additional_context = job_data['additional_context']
    combined_text = job_data['combined_text']
    uploaded_filenames = job_data['uploaded_filenames']
    org_id = job_data.get('org_id')  # For word deduction
    total_words = job_data.get('total_words')  # For word deduction
    
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
        # Worker sends analysis_id, memo_content, api_cost, success flag, and word deduction data
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,  # Database INTEGER id
                'memo_content': memo_content,
                'api_cost': api_cost,
                'success': True,
                'org_id': org_id,  # For word deduction
                'total_words': total_words  # For word deduction
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

def run_asc842_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ASC 842 analysis in background worker
    
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
    
    logger.info(f"🚀 Worker starting ASC 842 analysis: {analysis_id}")
    
    # Get current job for progress updates
    job = get_current_job()
    
    try:
        # Reset cost tracking for this analysis
        reset_cost_tracking()
        
        # Initialize analyzer and knowledge search
        analyzer = ASC842StepAnalyzer()
        knowledge_search = ASC842KnowledgeSearch()
        
        # Extract entity name for memo generation
        entity_name = "the Entity"  # Default value
        try:
            if "the Entity" in combined_text:
                entity_name = "the Entity"
        except:
            entity_name = "the Entity"  # Fallback on error
        
        # Initialize results storage
        analysis_results = {
            'steps': {},
            'entity_name': entity_name,
            'analysis_title': 'Lease Analysis',
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Run 5 ASC 842 steps with progress reporting
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
                
                # Analyze the step with retry logic
                step_result = analyzer._analyze_step_with_retry(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    entity_name=entity_name,
                    additional_context=additional_context
                )
                
                # Store under 'steps' key
                analysis_results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
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
        
        # Generate executive summary, background, and conclusion
        logger.info("→ Generating executive summary, background, and conclusion...")
        conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results['steps'])
        
        analysis_results['executive_summary'] = analyzer.generate_executive_summary(conclusions_text, entity_name)
        analysis_results['background'] = analyzer.generate_background_section(conclusions_text, entity_name)
        analysis_results['conclusion'] = analyzer.generate_final_conclusion(analysis_results['steps'])
        
        memo_generator = ASC842CleanMemoGenerator()
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
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
        
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,
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
        
        # CRITICAL: Always save failure to database
        try:
            api_cost = get_total_estimated_cost()
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            _save_analysis_with_retry(
                backend_url=backend_url,
                user_token=user_token,
                save_data={
                    'analysis_id': analysis_id,
                    'success': False,
                    'error_message': str(e)[:500],
                    'api_cost': api_cost
                },
                max_retries=5
            )
            
            logger.info(f"✓ Failure status saved to database")
            
        except Exception as save_error:
            logger.critical(f"🔥 CRITICAL: Failed to save failure status to database: {str(save_error)}")
            logger.critical(f"🔥 Original error: {str(e)}")
            logger.critical(f"🔥 Analysis {analysis_id} may be stuck in 'processing' status!")
        
        # Re-raise exception so RQ marks job as failed
        raise

def run_asc718_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ASC 718 analysis in background worker
    
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
    
    logger.info(f"🚀 Worker starting ASC 718 analysis: {analysis_id}")
    
    # Get current job for progress updates
    job = get_current_job()
    
    try:
        # Reset cost tracking for this analysis
        reset_cost_tracking()
        
        # Initialize analyzer and knowledge search
        analyzer = ASC718StepAnalyzer()
        knowledge_search = ASC718KnowledgeSearch()
        
        # Extract entity name for memo generation
        entity_name = "the Entity"  # Default value
        try:
            if "the Entity" in combined_text:
                entity_name = "the Entity"
        except:
            entity_name = "the Entity"  # Fallback on error
        
        # Initialize results storage
        analysis_results = {
            'steps': {},
            'entity_name': entity_name,
            'analysis_title': 'Stock Compensation Analysis',
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Run 5 ASC 718 steps with progress reporting
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
                
                # Analyze the step with retry logic
                step_result = analyzer._analyze_step_with_retry(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    entity_name=entity_name,
                    additional_context=additional_context
                )
                
                # Store under 'steps' key
                analysis_results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
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
        
        # Generate executive summary, background, and conclusion
        logger.info("→ Generating executive summary, background, and conclusion...")
        conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results['steps'])
        
        analysis_results['executive_summary'] = analyzer.generate_executive_summary(conclusions_text, entity_name)
        analysis_results['background'] = analyzer.generate_background_section(conclusions_text, entity_name)
        analysis_results['conclusion'] = analyzer.generate_final_conclusion(analysis_results['steps'])
        
        memo_generator = ASC718CleanMemoGenerator()
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
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
        
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,
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
        
        # CRITICAL: Always save failure to database
        try:
            api_cost = get_total_estimated_cost()
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            _save_analysis_with_retry(
                backend_url=backend_url,
                user_token=user_token,
                save_data={
                    'analysis_id': analysis_id,
                    'success': False,
                    'error_message': str(e)[:500],
                    'api_cost': api_cost
                },
                max_retries=5
            )
            
            logger.info(f"✓ Failure status saved to database")
            
        except Exception as save_error:
            logger.critical(f"🔥 CRITICAL: Failed to save failure status to database: {str(save_error)}")
            logger.critical(f"🔥 Original error: {str(e)}")
            logger.critical(f"🔥 Analysis {analysis_id} may be stuck in 'processing' status!")
        
        # Re-raise exception so RQ marks job as failed
        raise

def run_asc805_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ASC 805 analysis in background worker
    
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
    
    logger.info(f"🚀 Worker starting ASC 805 analysis: {analysis_id}")
    
    # Get current job for progress updates
    job = get_current_job()
    
    try:
        # Reset cost tracking for this analysis
        reset_cost_tracking()
        
        # Initialize analyzer and knowledge search
        analyzer = ASC805StepAnalyzer()
        knowledge_search = ASC805KnowledgeSearch()
        
        # Extract target company name for memo generation
        target_company = "the Target Company"  # Default value
        try:
            if "the Target Company" in combined_text:
                target_company = "the Target Company"
        except:
            target_company = "the Target Company"  # Fallback on error
        
        # Initialize results storage
        analysis_results = {
            'steps': {},
            'target_company': target_company,
            'analysis_title': 'Business Combination Analysis',
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Run 5 ASC 805 steps with progress reporting
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
                
                # Analyze the step with retry logic
                step_result = analyzer._analyze_step_with_retry(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    customer_name=target_company,
                    additional_context=additional_context
                )
                
                # Store under 'steps' key
                analysis_results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
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
        
        # Generate executive summary, background, and conclusion
        logger.info("→ Generating executive summary, background, and conclusion...")
        conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results['steps'])
        
        analysis_results['executive_summary'] = analyzer.generate_executive_summary(conclusions_text, target_company)
        analysis_results['background'] = analyzer.generate_background_section(conclusions_text, target_company)
        analysis_results['conclusion'] = analyzer.generate_final_conclusion(analysis_results['steps'])
        
        memo_generator = ASC805CleanMemoGenerator()
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
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
        
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,
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
        
        # CRITICAL: Always save failure to database
        try:
            api_cost = get_total_estimated_cost()
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            _save_analysis_with_retry(
                backend_url=backend_url,
                user_token=user_token,
                save_data={
                    'analysis_id': analysis_id,
                    'success': False,
                    'error_message': str(e)[:500],
                    'api_cost': api_cost
                },
                max_retries=5
            )
            
            logger.info(f"✓ Failure status saved to database")
            
        except Exception as save_error:
            logger.critical(f"🔥 CRITICAL: Failed to save failure status to database: {str(save_error)}")
            logger.critical(f"🔥 Original error: {str(e)}")
            logger.critical(f"🔥 Analysis {analysis_id} may be stuck in 'processing' status!")
        
        # Re-raise exception so RQ marks job as failed
        raise

def run_asc340_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ASC 340-40 analysis in background worker
    
    NOTE: ASC 340-40 has only 2 steps (not 5)
    
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
    
    logger.info(f"🚀 Worker starting ASC 340-40 analysis: {analysis_id}")
    
    # Get current job for progress updates
    job = get_current_job()
    
    try:
        # Reset cost tracking for this analysis
        reset_cost_tracking()
        
        # Initialize analyzer and knowledge search
        analyzer = ASC340StepAnalyzer()
        knowledge_search = ASC340KnowledgeSearch()
        
        # Extract company name for memo generation
        company_name = "the Company"  # Default value
        try:
            if "the Company" in combined_text:
                company_name = "the Company"
        except:
            company_name = "the Company"  # Fallback on error
        
        # Initialize results storage
        analysis_results = {
            'steps': {},
            'company_name': company_name,
            'analysis_title': 'Contract Cost Analysis',
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Run 2 ASC 340-40 steps with progress reporting (NOT 5!)
        for step_num in range(1, 3):  # Steps 1-2 only
            # Update job progress
            if job:
                job.meta['progress'] = {
                    'current_step': step_num,
                    'total_steps': 2,  # Only 2 steps for ASC 340-40
                    'step_name': f'Step {step_num}',
                    'updated_at': datetime.now().isoformat()
                }
                job.save_meta()
            
            logger.info(f"📊 Processing Step {step_num}/2")
            
            try:
                # Get relevant knowledge for this step
                authoritative_context = knowledge_search.search_for_step(step_num, combined_text)
                
                # Analyze the step with retry logic
                step_result = analyzer._analyze_step_with_retry(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    customer_name=company_name,
                    additional_context=additional_context
                )
                
                # Store under 'steps' key
                analysis_results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
                raise Exception(f"Step {step_num} failed: {str(e)}")
        
        # Generate final memo
        logger.info("📝 Generating final memo...")
        if job:
            job.meta['progress'] = {
                'current_step': 2,
                'total_steps': 2,
                'step_name': 'Generating Memo',
                'updated_at': datetime.now().isoformat()
            }
            job.save_meta()
        
        # Generate executive summary, background, and conclusion
        logger.info("→ Generating executive summary, background, and conclusion...")
        conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results['steps'])
        
        analysis_results['executive_summary'] = analyzer.generate_executive_summary(conclusions_text, company_name)
        analysis_results['background'] = analyzer.generate_background_section(conclusions_text, company_name)
        analysis_results['conclusion'] = analyzer.generate_final_conclusion(analysis_results['steps'])
        
        memo_generator = ASC340CleanMemoGenerator()
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
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
        
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,
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
        
        # CRITICAL: Always save failure to database
        try:
            api_cost = get_total_estimated_cost()
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            _save_analysis_with_retry(
                backend_url=backend_url,
                user_token=user_token,
                save_data={
                    'analysis_id': analysis_id,
                    'success': False,
                    'error_message': str(e)[:500],
                    'api_cost': api_cost
                },
                max_retries=5
            )
            
            logger.info(f"✓ Failure status saved to database")
            
        except Exception as save_error:
            logger.critical(f"🔥 CRITICAL: Failed to save failure status to database: {str(save_error)}")
            logger.critical(f"🔥 Original error: {str(e)}")
            logger.critical(f"🔥 Analysis {analysis_id} may be stuck in 'processing' status!")
        
        # Re-raise exception so RQ marks job as failed
        raise


def run_memo_review_analysis(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Memo Review analysis in background worker
    
    This generates a vLogic memo from the uploaded contract using the selected
    ASC standard analyzer, for comparison against the user's uploaded memo.
    
    Args:
        job_data: Dictionary containing analysis parameters including:
            - asc_standard: The ASC standard to use for analysis (e.g., 'ASC 606')
            - combined_text: The contract text to analyze
            - source_memo_text: The user's uploaded memo for comparison (Phase 2)
            - source_memo_filename: Name of the user's uploaded memo file
        
    Returns:
        Dictionary with analysis results including generated memo content
    """
    analysis_id = job_data['analysis_id']
    user_id = job_data['user_id']
    user_token = job_data['user_token']
    asc_standard = job_data.get('asc_standard', 'ASC 606')
    combined_text = job_data['combined_text']
    source_memo_text = job_data.get('source_memo_text', '')
    source_memo_filename = job_data.get('source_memo_filename', '')
    uploaded_filenames = job_data['uploaded_filenames']
    additional_context = job_data.get('additional_context', '')
    org_id = job_data.get('org_id')
    total_words = job_data.get('total_words')
    
    job = get_current_job()
    
    try:
        reset_cost_tracking()
        logger.info(f"🔍 Starting Memo Review Analysis (ID: {analysis_id})")
        logger.info(f"   ASC Standard: {asc_standard}")
        logger.info(f"   Contract words: {len(combined_text.split())}")
        logger.info(f"   Source memo words: {len(source_memo_text.split())}")
        
        # Update progress - Step 1: Initialize
        if job:
            job.meta['progress'] = {
                'current_step': 1,
                'total_steps': 3,
                'step_name': 'Initializing analysis',
                'updated_at': datetime.now().isoformat()
            }
            job.save_meta()
        
        # Select the appropriate analyzer and components based on ASC standard
        if asc_standard == 'ASC 606':
            analyzer = ASC606StepAnalyzer()
            knowledge_search = ASC606KnowledgeSearch()
            memo_generator = CleanMemoGenerator()
            step_count = 5
        elif asc_standard == 'ASC 842':
            analyzer = ASC842StepAnalyzer()
            knowledge_search = ASC842KnowledgeSearch()
            memo_generator = ASC842CleanMemoGenerator()
            step_count = 2
        elif asc_standard == 'ASC 718':
            analyzer = ASC718StepAnalyzer()
            knowledge_search = ASC718KnowledgeSearch()
            memo_generator = ASC718CleanMemoGenerator()
            step_count = 2
        elif asc_standard == 'ASC 805':
            analyzer = ASC805StepAnalyzer()
            knowledge_search = ASC805KnowledgeSearch()
            memo_generator = ASC805CleanMemoGenerator()
            step_count = 2
        elif asc_standard == 'ASC 340-40':
            analyzer = ASC340StepAnalyzer()
            knowledge_search = ASC340KnowledgeSearch()
            memo_generator = ASC340CleanMemoGenerator()
            step_count = 2
        else:
            raise ValueError(f"Unsupported ASC standard for memo review: {asc_standard}")
        
        # De-identify contract text for privacy protection
        logger.info("🔒 Applying privacy protection (de-identification)...")
        parties = analyzer.extract_contract_parties(combined_text)
        vendor_name = parties.get('vendor')
        customer_name = parties.get('customer')
        
        if vendor_name or customer_name:
            deidentify_result = analyzer.deidentify_contract_text(combined_text, vendor_name, customer_name)
            if deidentify_result.get('success'):
                combined_text = deidentify_result['text']
                logger.info(f"   ✓ De-identified: vendor '{vendor_name}' → 'the Company', customer '{customer_name}' → 'the Customer'")
            else:
                logger.warning(f"   ⚠️ De-identification failed: {deidentify_result.get('error', 'Unknown error')}")
        else:
            logger.warning("   ⚠️ Could not identify contract parties for de-identification")
        
        # Extract company name from de-identified text
        company_name = analyzer._extract_company_name(combined_text)
        logger.info(f"   Company identified: {company_name}")
        
        # Update progress - Step 2: Running Analysis
        if job:
            job.meta['progress'] = {
                'current_step': 2,
                'total_steps': 3,
                'step_name': f'Analyzing contract for {asc_standard}',
                'updated_at': datetime.now().isoformat()
            }
            job.save_meta()
        
        # Run the analysis steps
        analysis_results = {
            'steps': {},
            'asc_standard': asc_standard
        }
        
        for step_num in range(1, step_count + 1):
            logger.info(f"📋 Analyzing Step {step_num}/{step_count}...")
            
            try:
                authoritative_context = knowledge_search.search_for_step(step_num, combined_text)
                
                step_result = analyzer._analyze_step_with_retry(
                    step_num=step_num,
                    contract_text=combined_text,
                    authoritative_context=authoritative_context,
                    customer_name=company_name,
                    additional_context=additional_context
                )
                
                analysis_results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"✓ Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
                raise Exception(f"Step {step_num} failed: {str(e)}")
        
        # Update progress - Step 3: Generating Memo
        if job:
            job.meta['progress'] = {
                'current_step': 3,
                'total_steps': 3,
                'step_name': 'Generating memo',
                'updated_at': datetime.now().isoformat()
            }
            job.save_meta()
        
        logger.info("📝 Generating memo sections...")
        conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results['steps'])
        
        analysis_results['executive_summary'] = analyzer.generate_executive_summary(conclusions_text, company_name)
        analysis_results['background'] = analyzer.generate_background_section(conclusions_text, company_name)
        analysis_results['conclusion'] = analyzer.generate_final_conclusion(analysis_results['steps'])
        
        filename = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
        analysis_results['filename'] = filename
        
        memo_content = memo_generator.combine_clean_steps(
            analysis_results,
            analysis_id=analysis_id
        )
        
        api_cost = get_total_estimated_cost()
        
        # Save analysis to database
        logger.info("💾 Saving memo review analysis to database...")
        backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
        
        save_result = _save_analysis_with_retry(
            backend_url=backend_url,
            user_token=user_token,
            save_data={
                'analysis_id': analysis_id,
                'memo_content': memo_content,
                'api_cost': api_cost,
                'success': True,
                'org_id': org_id,
                'total_words': total_words
            },
            max_retries=5
        )
        
        memo_uuid = save_result.get('memo_uuid')
        logger.info(f"✓ Memo Review analysis saved successfully: {memo_uuid}")
        
        return {
            'success': True,
            'analysis_id': analysis_id,
            'memo_uuid': memo_uuid,
            'memo_content': memo_content,
            'api_cost': api_cost,
            'asc_standard': asc_standard,
            'message': 'Memo Review analysis completed successfully'
        }
        
    except Exception as e:
        logger.error(f"❌ Memo Review analysis failed: {str(e)}", exc_info=True)
        
        try:
            api_cost = get_total_estimated_cost()
            backend_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
            
            _save_analysis_with_retry(
                backend_url=backend_url,
                user_token=user_token,
                save_data={
                    'analysis_id': analysis_id,
                    'success': False,
                    'error_message': str(e)[:500],
                    'api_cost': api_cost
                },
                max_retries=5
            )
            
            logger.info(f"✓ Failure status saved to database")
            
        except Exception as save_error:
            logger.critical(f"🔥 CRITICAL: Failed to save failure status: {str(save_error)}")
            logger.critical(f"🔥 Original error: {str(e)}")
            logger.critical(f"🔥 Analysis {analysis_id} may be stuck in 'processing' status!")
        
        raise
