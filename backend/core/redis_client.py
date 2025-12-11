import logging
from typing import Optional
import redis
from redis.connection import ConnectionPool

from backend.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


def get_redis_pool() -> ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        _redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        logger.info(f"Redis connection pool created: {redis_url}")
    return _redis_pool


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        pool = get_redis_pool()
        _redis_client = redis.Redis(connection_pool=pool)
        try:
            _redis_client.ping()
            logger.info("Redis client connected successfully")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {str(e)}")
            logger.warning("Rate limiting will be disabled")
            _redis_client = None
    return _redis_client


def close_redis():
    global _redis_client, _redis_pool
    if _redis_client:
        _redis_client.close()
        _redis_client = None
    if _redis_pool:
        _redis_pool.disconnect()
        _redis_pool = None
    logger.info("Redis connection closed")
