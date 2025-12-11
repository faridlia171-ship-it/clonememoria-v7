from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import logging
import redis

from backend.core.redis_client import get_redis_client
from backend.db.client import get_db

logger = logging.getLogger(__name__)


class RedisRateLimitService:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.db = get_db()
        self.enabled = self.redis_client is not None

    def _get_key(self, user_id: UUID, endpoint: str, window: str = "minute") -> str:
        return f"ratelimit:{window}:{user_id}:{endpoint}"

    def _get_plan_limits(self, user_id: UUID, endpoint: str) -> Dict[str, int]:
        try:
            user_result = self.db.table('users') \
                .select('billing_plan') \
                .eq('id', str(user_id)) \
                .maybeSingle() \
                .execute()

            plan = user_result.data.get('billing_plan', 'free') if user_result.data else 'free'

            config_result = self.db.table('rate_limit_configs') \
                .select('*') \
                .eq('plan', plan) \
                .is_('role', 'null') \
                .execute()

            if config_result.data:
                for config in config_result.data:
                    pattern = config['endpoint_pattern']
                    if self._matches_pattern(endpoint, pattern):
                        return {
                            "per_minute": config['requests_per_minute'],
                            "per_hour": config['requests_per_hour'],
                            "per_day": config['requests_per_day']
                        }

            return {
                "per_minute": 10,
                "per_hour": 100,
                "per_day": 1000
            }

        except Exception as e:
            logger.error(f"Failed to get plan limits: {str(e)}")
            return {
                "per_minute": 10,
                "per_hour": 100,
                "per_day": 1000
            }

    def _matches_pattern(self, endpoint: str, pattern: str) -> bool:
        if pattern.endswith('/*'):
            prefix = pattern[:-2]
            return endpoint.startswith(prefix)
        return endpoint == pattern

    def check_rate_limit(
        self,
        user_id: UUID,
        endpoint: str,
        space_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "allowed": True,
                "current_count": 0,
                "limit_per_minute": 999999,
                "reason": "rate_limiting_disabled"
            }

        try:
            limits = self._get_plan_limits(user_id, endpoint)

            key_minute = self._get_key(user_id, endpoint, "minute")
            key_hour = self._get_key(user_id, endpoint, "hour")
            key_day = self._get_key(user_id, endpoint, "day")

            count_minute = int(self.redis_client.get(key_minute) or 0)
            count_hour = int(self.redis_client.get(key_hour) or 0)
            count_day = int(self.redis_client.get(key_day) or 0)

            if count_minute >= limits["per_minute"]:
                ttl = self.redis_client.ttl(key_minute)
                return {
                    "allowed": False,
                    "current_count": count_minute,
                    "limit_per_minute": limits["per_minute"],
                    "limit_per_hour": limits["per_hour"],
                    "limit_per_day": limits["per_day"],
                    "reset_at": (datetime.utcnow() + timedelta(seconds=max(ttl, 0))).isoformat(),
                    "window": "minute"
                }

            if count_hour >= limits["per_hour"]:
                ttl = self.redis_client.ttl(key_hour)
                return {
                    "allowed": False,
                    "current_count": count_hour,
                    "limit_per_minute": limits["per_minute"],
                    "limit_per_hour": limits["per_hour"],
                    "limit_per_day": limits["per_day"],
                    "reset_at": (datetime.utcnow() + timedelta(seconds=max(ttl, 0))).isoformat(),
                    "window": "hour"
                }

            if count_day >= limits["per_day"]:
                ttl = self.redis_client.ttl(key_day)
                return {
                    "allowed": False,
                    "current_count": count_day,
                    "limit_per_minute": limits["per_minute"],
                    "limit_per_hour": limits["per_hour"],
                    "limit_per_day": limits["per_day"],
                    "reset_at": (datetime.utcnow() + timedelta(seconds=max(ttl, 0))).isoformat(),
                    "window": "day"
                }

            return {
                "allowed": True,
                "current_count": count_minute,
                "limit_per_minute": limits["per_minute"],
                "limit_per_hour": limits["per_hour"],
                "limit_per_day": limits["per_day"],
                "reset_at": (datetime.utcnow() + timedelta(minutes=1)).isoformat()
            }

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limit check: {str(e)}")
            return {"allowed": True, "current_count": 0, "reason": "redis_error"}
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return {"allowed": True, "current_count": 0, "reason": "check_error"}

    def increment_rate_limit(
        self,
        user_id: UUID,
        endpoint: str,
        space_id: Optional[UUID] = None
    ) -> bool:
        if not self.enabled:
            return True

        try:
            key_minute = self._get_key(user_id, endpoint, "minute")
            key_hour = self._get_key(user_id, endpoint, "hour")
            key_day = self._get_key(user_id, endpoint, "day")

            pipe = self.redis_client.pipeline()

            pipe.incr(key_minute)
            pipe.expire(key_minute, 60)

            pipe.incr(key_hour)
            pipe.expire(key_hour, 3600)

            pipe.incr(key_day)
            pipe.expire(key_day, 86400)

            pipe.execute()

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limit increment: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to increment rate limit: {str(e)}")
            return False

    def reset_user_rate_limits(self, user_id: UUID) -> int:
        if not self.enabled:
            return 0

        try:
            pattern = f"ratelimit:*:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Reset {deleted} rate limit keys for user {user_id}")
                return deleted
            return 0

        except redis.RedisError as e:
            logger.error(f"Redis error in reset: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {str(e)}")
            return 0

    def get_user_rate_limit_status(
        self,
        user_id: UUID,
        endpoint_pattern: str = '/api/*'
    ) -> Dict[str, Any]:
        try:
            limits = self._get_plan_limits(user_id, endpoint_pattern)

            if not self.enabled:
                return {
                    "limits": limits,
                    "current": {"minute": 0, "hour": 0, "day": 0},
                    "enabled": False
                }

            key_minute = self._get_key(user_id, endpoint_pattern, "minute")
            key_hour = self._get_key(user_id, endpoint_pattern, "hour")
            key_day = self._get_key(user_id, endpoint_pattern, "day")

            current = {
                "minute": int(self.redis_client.get(key_minute) or 0),
                "hour": int(self.redis_client.get(key_hour) or 0),
                "day": int(self.redis_client.get(key_day) or 0)
            }

            return {
                "limits": limits,
                "current": current,
                "enabled": True
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {str(e)}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        try:
            if not self.redis_client:
                return {"status": "disabled", "message": "Redis client not initialized"}

            self.redis_client.ping()
            info = self.redis_client.info('stats')

            return {
                "status": "healthy",
                "connected_clients": info.get('connected_clients', 0),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "instantaneous_ops_per_sec": info.get('instantaneous_ops_per_sec', 0)
            }
        except redis.RedisError as e:
            return {"status": "unhealthy", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
