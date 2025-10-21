#!/usr/bin/env python
"""
RQ Worker Script
Starts a Redis Queue worker to process background analysis jobs
Auto-detects environment: uses fakeredis locally, real Redis in production
"""

import os
import sys
import logging
from redis import Redis
from rq import Worker, Queue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_redis_connection():
    """
    Get Redis connection - automatically uses fakeredis for local dev
    Returns real Redis in production (Railway) or fakeredis locally (Replit)
    """
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        logger.info(f"Attempting to connect to Redis: {redis_url}")
        redis_conn = Redis.from_url(redis_url, socket_connect_timeout=2)
        redis_conn.ping()
        logger.info("✓ Connected to production Redis")
        return redis_conn
    except Exception as e:
        logger.warning(f"Production Redis unavailable ({e}), using fakeredis for local development")
        try:
            from fakeredis import FakeRedis
            fake_conn = FakeRedis(decode_responses=False)
            logger.info("✓ Using fakeredis (local development mode)")
            return fake_conn
        except ImportError:
            logger.error("fakeredis not installed. Run: pip install fakeredis")
            raise

def main():
    """Start the RQ worker"""
    redis_conn = get_redis_connection()
    
    worker = Worker(['analysis'], connection=redis_conn)
    logger.info("🚀 RQ Worker started. Waiting for jobs...")
    worker.work()

if __name__ == '__main__':
    main()
