import logging
from typing import Optional
from fastapi import Header, HTTPException, Depends
from db.client import get_db_client
from services.api_key_service import validate_api_key

logger = logging.getLogger(__name__)


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None),
    db=Depends(get_db_client)
) -> dict:
    """
    Dependency to get current user from API key.

    Used for external API endpoints that accept X-API-Key header.
    """
    if not x_api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header."
        )

    key_data = await validate_api_key(db, x_api_key)

    if not key_data:
        logger.warning("Invalid or rate-limited API key")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key or rate limit exceeded"
        )

    logger.info(
        "User authenticated via API key",
        extra={
            "user_id": key_data["user_id"],
            "api_key_id": key_data["api_key_id"]
        }
    )

    return key_data
