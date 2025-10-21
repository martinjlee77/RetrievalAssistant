"""
Shared Redis Connection for Development and Production
Auto-detects environment and provides consistent Redis access across all processes
"""

import os
import logging
from redis import Redis

logger = logging.getLogger(__name__)

def get_redis_connection():
    """
    Get Redis connection - automatically uses fakeredis for local dev
    Returns real Redis in production (Railway) or fakeredis locally (Replit)
    
    Note: In local dev, we use separate FakeRedis instances per process.
    This is a limitation of fakeredis - it's in-memory per process.
    For full testing, use production (Railway) with real Redis.
    """
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Try real Redis first (production)
    try:
        logger.info(f"Attempting to connect to Redis: {redis_url}")
        redis_conn = Redis.from_url(redis_url, socket_connect_timeout=2, decode_responses=False)
        redis_conn.ping()
        logger.info("✓ Connected to production Redis")
        return redis_conn
    except Exception as e:
        logger.warning(f"Production Redis unavailable: {e}")
    
    # Fallback: Use fakeredis (local dev only - limited functionality)
    try:
        from fakeredis import FakeStrictRedis
        fake_conn = FakeStrictRedis(decode_responses=False)
        logger.warning("⚠️  Using fakeredis (local dev) - Background jobs will NOT work across processes")
        logger.warning("⚠️  For full testing, deploy to Railway where real Redis is available")
        return fake_conn
    except ImportError:
        logger.error("fakeredis not installed. Run: pip install fakeredis")
        raise
