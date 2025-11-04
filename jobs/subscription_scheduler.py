#!/usr/bin/env python3
"""
RQ Scheduler for Subscription Maintenance Jobs
Sets up recurring jobs for subscription management.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rq_scheduler import Scheduler
from rq import Queue
from shared.redis_connection import get_redis
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_subscription_scheduler():
    """
    Set up recurring jobs for subscription management.
    Should be run once to schedule jobs, then RQ Scheduler daemon keeps them running.
    """
    redis_conn = get_redis()
    scheduler = Scheduler(connection=redis_conn, queue_name='maintenance')
    
    logger.info("Setting up subscription maintenance scheduler")
    
    # Cancel any existing scheduled jobs to avoid duplicates
    for job in scheduler.get_jobs():
        if 'monthly_subscription_reset' in job.description:
            scheduler.cancel(job)
            logger.info(f"Cancelled existing job: {job.id}")
    
    # Schedule monthly reset for 1st of each month at 2 AM UTC
    from jobs.monthly_subscription_reset import reset_monthly_allowances
    
    # Calculate next occurrence (1st of next month at 2 AM UTC)
    now = datetime.now(timezone.utc)
    next_month = now.month + 1 if now.month < 12 else 1
    next_year = now.year if now.month < 12 else now.year + 1
    
    next_run = datetime(next_year, next_month, 1, 2, 0, 0, tzinfo=timezone.utc)
    
    job = scheduler.cron(
        '0 2 1 * *',  # Cron expression: minute hour day month day_of_week
        func=reset_monthly_allowances,
        queue_name='maintenance',
        timeout='30m',
        description='Monthly subscription allowance reset (runs 1st of month at 2 AM UTC)'
    )
    
    logger.info(f"✅ Scheduled monthly reset: {job.id}")
    logger.info(f"   Next run: {next_run.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"   Cron: 0 2 1 * * (1st of month at 2 AM UTC)")
    
    return {
        'job_id': job.id,
        'next_run': next_run.isoformat(),
        'cron': '0 2 1 * *'
    }


def list_scheduled_jobs():
    """List all scheduled subscription jobs"""
    redis_conn = get_redis()
    scheduler = Scheduler(connection=redis_conn, queue_name='maintenance')
    
    jobs = scheduler.get_jobs()
    
    if not jobs:
        logger.info("No scheduled jobs found")
        return []
    
    logger.info(f"Found {len(jobs)} scheduled jobs:")
    
    job_list = []
    for job in jobs:
        logger.info(f"  - {job.id}: {job.description}")
        logger.info(f"    Next run: {job.meta.get('scheduled_for', 'Unknown')}")
        
        job_list.append({
            'id': job.id,
            'description': job.description,
            'next_run': str(job.meta.get('scheduled_for'))
        })
    
    return job_list


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Subscription job scheduler')
    parser.add_argument('--setup', action='store_true', help='Set up scheduled jobs')
    parser.add_argument('--list', action='store_true', help='List all scheduled jobs')
    
    args = parser.parse_args()
    
    if args.setup:
        print("Setting up subscription scheduler...")
        result = setup_subscription_scheduler()
        print(f"✅ Scheduler configured successfully")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Next run: {result['next_run']}")
        print()
        print("To start the RQ Scheduler daemon, run:")
        print("   rqscheduler --host localhost --port 6379 --db 0 --interval 60")
        print()
        print("Or add to your workflow with supervisord/systemd")
    
    elif args.list:
        jobs = list_scheduled_jobs()
        if not jobs:
            print("No scheduled jobs found")
        else:
            print(f"\n{len(jobs)} scheduled jobs:")
            for job in jobs:
                print(f"  - {job['description']}")
                print(f"    ID: {job['id']}")
                print(f"    Next: {job['next_run']}")
                print()
    
    else:
        parser.print_help()
