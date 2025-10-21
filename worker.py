#!/usr/bin/env python
"""
RQ Worker Script
Starts a Redis Queue worker to process background analysis jobs
"""

import os
import sys
import logging
from redis import Redis
from rq import Worker, Queue

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the RQ worker"""
    # Get Redis connection from environment
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    logger.info(f"Connecting to Redis: {redis_url}")
    
    # Connect to Redis
    redis_conn = Redis.from_url(redis_url)
    
    # Create worker with the 'analysis' queue
    worker = Worker(['analysis'], connection=redis_conn)
    logger.info("🚀 RQ Worker started. Waiting for jobs...")
    worker.work()

if __name__ == '__main__':
    main()
