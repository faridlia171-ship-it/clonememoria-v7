from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import logging
from supabase import Client

logger = logging.getLogger(__name__)


class RateLimitService:
    def __init__(self, db: Client):
        self.db = db

    def check_rate_limit(
        self,
        user_id: UUID,
        endpoint: str,
        space_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        try:
            window_start = datetime.utcnow().replace(second=0, microsecond=0)

            result = self.db.rpc('check_rate_limit', {
                'p_user_id': str(user_id),
                'p_space_id': str(space_id) if space_id else None,
                'p_endpoint': endpoint,
                'p_window_start': window_start.isoformat()
            }).execute()

            if result.data:
                return result.data

            return {
                "allowed": True,
                "current_count": 0,
                "limit_per_minute": 10,
                "limit_per_hour": 100,
                "limit_per_day": 1000,
                "reset_at": (window_start + timedelta(minutes=1)).isoformat()
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return {"allowed": True, "current_count": 0}

    def increment_rate_limit(
        self,
        user_id: UUID,
        endpoint: str,
        space_id: Optional[UUID] = None
    ) -> bool:
        try:
            window_start = datetime.utcnow().replace(second=0, microsecond=0)

            self.db.rpc('increment_rate_limit', {
                'p_user_id': str(user_id),
                'p_space_id': str(space_id) if space_id else None,
                'p_endpoint': endpoint,
                'p_window_start': window_start.isoformat()
            }).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to increment rate limit: {str(e)}")
            return False

    def get_user_rate_limit_status(
        self,
        user_id: UUID,
        endpoint_pattern: str = '/api/*'
    ) -> Dict[str, Any]:
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
                .eq('endpoint_pattern', endpoint_pattern) \
                .is_('role', 'null') \
                .maybeSingle() \
                .execute()

            if config_result.data:
                return {
                    "plan": plan,
                    "endpoint_pattern": endpoint_pattern,
                    "limits": {
                        "per_minute": config_result.data['requests_per_minute'],
                        "per_hour": config_result.data['requests_per_hour'],
                        "per_day": config_result.data['requests_per_day']
                    }
                }

            return {
                "plan": plan,
                "endpoint_pattern": endpoint_pattern,
                "limits": {
                    "per_minute": 10,
                    "per_hour": 100,
                    "per_day": 1000
                }
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {str(e)}")
            return {"error": str(e)}

    def reset_user_rate_limits(self, user_id: UUID) -> int:
        try:
            result = self.db.table('rate_limits') \
                .delete() \
                .eq('user_id', str(user_id)) \
                .execute()

            count = len(result.data) if result.data else 0
            logger.info(f"Reset {count} rate limit entries for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Failed to reset rate limits: {str(e)}")
            return 0

    def get_rate_limit_configs(self, plan: str = 'free') -> list:
        try:
            result = self.db.table('rate_limit_configs') \
                .select('*') \
                .eq('plan', plan) \
                .order('endpoint_pattern') \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get rate limit configs: {str(e)}")
            return []
