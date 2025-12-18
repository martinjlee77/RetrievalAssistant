#!/usr/bin/env python
"""
RQ Worker Script
Starts a Redis Queue worker to process background analysis jobs
Auto-detects environment: uses fakeredis locally, real Redis in production
"""

import os
import sys
import logging
from rq import Worker, Queue

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.redis_connection import get_redis_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the RQ worker"""
    redis_conn = get_redis_connection()
    
    worker = Worker(['analysis', 'close'], connection=redis_conn)
    logger.info("🚀 RQ Worker started. Listening on 'analysis' and 'close' queues...")
    worker.work()

if __name__ == '__main__':
    main()
