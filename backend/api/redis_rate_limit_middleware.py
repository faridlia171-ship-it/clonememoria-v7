from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from uuid import UUID
import logging

from backend.services.redis_rate_limit_service import RedisRateLimitService

logger = logging.getLogger(__name__)

# Champs autorisés pour éviter les collisions avec le système de logs
SAFE_LOG_FIELDS = {
    "user_id",
    "endpoint",
    "current_count",
    "limit",
    "window",
    "limit_per_minute",
    "limit_per_hour",
    "limit_per_day"
}

def safe_log(extra: dict):
    """Filtre les champs extra pour éviter d'utiliser une clé réservée."""
    return {k: v for k, v in extra.items() if k in SAFE_LOG_FIELDS}


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.rate_limit_service = RedisRateLimitService()

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or not self.rate_limit_service.enabled:
            return await call_next(request)

        # API uniquement
        if not request.url.path.startswith('/api/'):
            return await call_next(request)

        # Routes ignorées
        bypass_routes = ['/api/health', '/api/auth/login', '/api/auth/register']
        if request.url.path in bypass_routes:
            return await call_next(request)

        # Extraction user
        user_id = self._get_user_id_from_request(request)
        if not user_id:
            return await call_next(request)

        try:
            endpoint = self._normalize_endpoint(request.url.path)

            rate_limit_result = self.rate_limit_service.check_rate_limit(
                user_id=user_id,
                endpoint=endpoint
            )

            # Limite atteinte
            if not rate_limit_result.get('allowed', True):

                logger.warning(
                    f"Rate limit exceeded for user {user_id} on endpoint {endpoint}",
                    extra=safe_log({
                        "user_id": str(user_id),
                        "endpoint": endpoint,
                        "current_count": rate_limit_result.get('current_count'),
                        "limit": rate_limit_result.get('limit_per_minute'),
                        "window": rate_limit_result.get('window')
                    })
                )

                # Log BD Supabase
                from backend.db.client import get_db
                db = get_db()
                try:
                    db.rpc("log_quota_violation", {
                        "p_user_id": str(user_id),
                        "p_resource_type": "rate_limit",
                        "p_metadata": {
                            "endpoint": endpoint,
                            "window": rate_limit_result.get("window"),
                            "current_count": rate_limit_result.get("current_count"),
                            "limit": rate_limit_result.get(
                                f"limit_per_{rate_limit_result.get('window')}"
                            ),
                        },
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to log quota violation: {str(e)}")

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Rate limit exceeded",
                        "window": rate_limit_result.get("window"),
                        "current_count": rate_limit_result.get("current_count"),
                        "limit_per_minute": rate_limit_result.get("limit_per_minute"),
                        "limit_per_hour": rate_limit_result.get("limit_per_hour"),
                        "limit_per_day": rate_limit_result.get("limit_per_day"),
                        "reset_at": rate_limit_result.get("reset_at"),
                    },
                )

            # Incrémentation
            self.rate_limit_service.increment_rate_limit(
                user_id=user_id,
                endpoint=endpoint
            )

            # Réponse normale
            response = await call_next(request)

            # Headers de quota
            response.headers["X-RateLimit-Limit-Minute"] = str(rate_limit_result.get("limit_per_minute", 0))
            response.headers["X-RateLimit-Limit-Hour"] = str(rate_limit_result.get("limit_per_hour", 0))
            response.headers["X-RateLimit-Limit-Day"] = str(rate_limit_result.get("limit_per_day", 0))
            response.headers["X-RateLimit-Remaining"] = str(
                rate_limit_result.get("limit_per_minute", 0) - rate_limit_result.get("current_count", 0)
            )
            response.headers["X-RateLimit-Reset"] = rate_limit_result.get("reset_at", "")

            return response

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}")
            return await call_next(request)

    # -----------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------

    def _get_user_id_from_request(self, request: Request) -> Optional[UUID]:
        try:
            if hasattr(request.state, "user_id"):
                return UUID(request.state.user_id)

            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            from backend.core.security import decode_access_token
            token = auth_header.split(" ")[1]
            payload = decode_access_token(token)
            user_id = payload.get("sub")

            return UUID(user_id) if user_id else None

        except Exception:
            return None

    def _normalize_endpoint(self, path: str) -> str:
        parts = path.split("/")
        normalized = []

        for part in parts:
            if part and not self._is_uuid(part) and not part.isdigit():
                normalized.append(part)
            elif part:
                normalized.append("*")

        return "/" + "/".join(normalized) + "/*" if normalized else path

    def _is_uuid(self, value: str) -> bool:
        try:
            UUID(value)
            return True
        except Exception:
            return False
