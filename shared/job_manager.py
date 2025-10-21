"""
Job Manager for Background Analysis Processing
Handles job submission, status checking, and result retrieval using Redis Queue (RQ)
Auto-detects environment: uses fakeredis locally, real Redis in production
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from rq import Queue
from rq.job import Job
from shared.redis_connection import get_redis_connection

logger = logging.getLogger(__name__)

class JobManager:
    """Manages background job processing for ASC analyses"""
    
    def __init__(self):
        """Initialize Redis connection and job queue"""
        try:
            self.redis_conn = get_redis_connection()
            self.queue = Queue('analysis', connection=self.redis_conn)
            logger.info("Job manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize job manager: {e}")
            raise
    
    def submit_analysis_job(self, 
                           asc_standard: str,
                           analysis_id: int,
                           user_id: int,
                           user_token: str,
                           pricing_result: Dict[str, Any],
                           additional_context: str,
                           combined_text: str,
                           uploaded_filenames: list) -> str:
        """
        Submit an analysis job to the background queue
        
        Args:
            asc_standard: ASC standard (e.g., "ASC 606")
            analysis_id: Database INTEGER analysis ID
            user_id: User ID for authentication
            user_token: JWT token for API calls
            pricing_result: Pricing calculation result
            additional_context: User-provided context
            combined_text: De-identified contract text
            uploaded_filenames: List of uploaded file names
            
        Returns:
            Job ID for tracking (string representation of analysis_id)
        """
        try:
            from workers.analysis_worker import run_asc606_analysis
            
            job_data = {
                'analysis_id': analysis_id,
                'user_id': user_id,
                'user_token': user_token,
                'pricing_result': pricing_result,
                'additional_context': additional_context,
                'combined_text': combined_text,
                'uploaded_filenames': uploaded_filenames
            }
            
            job = self.queue.enqueue(
                run_asc606_analysis,
                job_data,
                job_timeout='30m',
                result_ttl=86400,
                failure_ttl=86400,
                job_id=str(analysis_id)
            )
            
            logger.info(f"✓ Job submitted: {job.id} for analysis {analysis_id}")
            return job.id
            
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current status of a job
        
        Returns:
            Dictionary with status, progress, and result if complete
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            meta = job.meta or {}
            
            status_info = {
                'job_id': job_id,
                'status': job.get_status(),
                'progress': meta.get('progress', {}),
                'error': None,
                'result': None
            }
            
            if job.is_finished:
                status_info['result'] = job.result
                
            if job.is_failed:
                status_info['error'] = str(job.exc_info) if job.exc_info else "Unknown error"
                
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return {
                'job_id': job_id,
                'status': 'unknown',
                'error': str(e),
                'progress': {},
                'result': None
            }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job"""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            logger.info(f"✓ Job cancelled: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    def update_job_progress(self, job_id: str, step_num: int, step_name: str):
        """
        Update job progress (called from within worker)
        
        This is meant to be called by the worker itself to report progress
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.meta['progress'] = {
                'current_step': step_num,
                'total_steps': 5,
                'step_name': step_name,
                'updated_at': str(datetime.now())
            }
            job.save_meta()
        except Exception as e:
            logger.error(f"Failed to update progress for job {job_id}: {e}")


job_manager = JobManager()
