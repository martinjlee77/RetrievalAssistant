"""
Shared Redis Connection for Development and Production
Auto-detects environment and provides consistent Redis access across all processes
"""

import os
import logging
from redis import Redis

logger = logging.getLogger(__name__)

# Global shared fakeredis server for local development
_fake_server = None

def get_redis_connection():
    """
    Get Redis connection - automatically uses fakeredis for local dev
    Returns real Redis in production (Railway) or shared fakeredis locally (Replit)
    
    Important: Uses a shared fakeredis server in dev so all processes
    (Streamlit, Worker, Flask) connect to the same in-memory queue
    """
    global _fake_server
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        logger.info(f"Attempting to connect to Redis: {redis_url}")
        redis_conn = Redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=False)
        redis_conn.ping()
        logger.info("✓ Connected to production Redis")
        return redis_conn
    except Exception as e:
        logger.warning(f"Production Redis unavailable ({e}), using fakeredis for local development")
        try:
            from fakeredis import FakeServer, FakeStrictRedis
            
            # Create or reuse shared fakeredis server
            # This ensures all processes connect to the same in-memory queue
            if _fake_server is None:
                _fake_server = FakeServer()
                logger.info("✓ Created shared fakeredis server (local development mode)")
            
            fake_conn = FakeStrictRedis(server=_fake_server, decode_responses=False)
            logger.info("✓ Connected to shared fakeredis server")
            return fake_conn
        except ImportError:
            logger.error("fakeredis not installed. Run: pip install fakeredis")
            raise
