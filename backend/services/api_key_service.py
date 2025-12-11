import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
    """
    random_part = secrets.token_urlsafe(32)
    full_key = f"cmk_{random_part}"

    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    key_prefix = full_key[:12] + "..."

    logger.info("API key generated", extra={"key_prefix": key_prefix})

    return full_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def check_rate_limit(
    db_client,
    api_key_id: UUID,
    rate_limit_requests: int,
    rate_limit_window_seconds: int
) -> Tuple[bool, Optional[str]]:
    """
    Check if an API key has exceeded its rate limit.

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        window_start = datetime.utcnow().replace(second=0, microsecond=0)

        window_start_minus = window_start - timedelta(seconds=rate_limit_window_seconds)

        result = await db_client.from_("api_key_usage").select("*").eq(
            "api_key_id", str(api_key_id)
        ).eq("window_start", window_start.isoformat()).execute()

        if result.data and len(result.data) > 0:
            current_count = result.data[0]["request_count"]

            if current_count >= rate_limit_requests:
                error_msg = f"Rate limit exceeded. Max {rate_limit_requests} requests per {rate_limit_window_seconds}s window."
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "api_key_id": str(api_key_id),
                        "current_count": current_count,
                        "limit": rate_limit_requests
                    }
                )
                return False, error_msg

            await db_client.from_("api_key_usage").update({
                "request_count": current_count + 1,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", result.data[0]["id"]).execute()
        else:
            await db_client.from_("api_key_usage").insert({
                "api_key_id": str(api_key_id),
                "window_start": window_start.isoformat(),
                "request_count": 1
            }).execute()

        return True, None

    except Exception as e:
        logger.error(
            "Error checking rate limit",
            extra={"api_key_id": str(api_key_id), "error": str(e)}
        )
        return True, None


async def validate_api_key(db_client, api_key: str) -> Optional[dict]:
    """
    Validate an API key and return associated user info.

    Returns:
        Dict with user_id, api_key_id, scopes, rate_limit info, or None if invalid
    """
    try:
        key_hash = hash_api_key(api_key)

        result = await db_client.from_("api_keys").select(
            "id, user_id, scopes, rate_limit_requests, rate_limit_window_seconds, revoked_at"
        ).eq("key_hash", key_hash).execute()

        if not result.data or len(result.data) == 0:
            logger.warning("Invalid API key attempted")
            return None

        key_data = result.data[0]

        if key_data.get("revoked_at"):
            logger.warning(
                "Revoked API key attempted",
                extra={"api_key_id": key_data["id"]}
            )
            return None

        is_allowed, error_msg = await check_rate_limit(
            db_client,
            UUID(key_data["id"]),
            key_data["rate_limit_requests"],
            key_data["rate_limit_window_seconds"]
        )

        if not is_allowed:
            return None

        await db_client.from_("api_keys").update({
            "last_used_at": datetime.utcnow().isoformat()
        }).eq("id", key_data["id"]).execute()

        logger.info(
            "API key validated",
            extra={
                "api_key_id": key_data["id"],
                "user_id": key_data["user_id"]
            }
        )

        return {
            "user_id": key_data["user_id"],
            "api_key_id": key_data["id"],
            "scopes": key_data.get("scopes", ["read"]),
            "rate_limit_requests": key_data["rate_limit_requests"],
            "rate_limit_window_seconds": key_data["rate_limit_window_seconds"]
        }

    except Exception as e:
        logger.error("Error validating API key", extra={"error": str(e)})
        return None
