import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client

from backend.core.security import decode_access_token
from backend.db.client import get_db

logger = logging.getLogger(__name__)
logger.info("API_DEPS_MODULE_LOADED", extra={"file": __file__})

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db)
) -> str:
    """
    Dependency to get current authenticated user ID from JWT token.

    Args:
        credentials: HTTP bearer token
        db: Database client

    Returns:
        User ID string

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    logger.debug("VALIDATING_USER_TOKEN")

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")

        if not user_id:
            logger.warning("TOKEN_MISSING_USER_ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        logger.debug("USER_AUTHENTICATED", extra={"user_id": user_id})
        return user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error("AUTHENTICATION_ERROR", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def verify_clone_ownership(
    clone_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
) -> dict:
    """
    Verify that the clone belongs to the current user.

    Args:
        clone_id: Clone ID to verify
        user_id: Current user ID
        db: Database client

    Returns:
        Clone data if user owns it

    Raises:
        HTTPException: If clone not found or user doesn't own it
    """
    logger.debug("VERIFYING_CLONE_OWNERSHIP", extra={
        "clone_id": clone_id,
        "user_id": user_id
    })

    try:
        response = db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    result = db.table("clones").select("*").eq("id", clone_id).eq("user_id", user_id).maybe_single().execute()

    if not result.data:
        logger.warning("CLONE_NOT_FOUND_OR_UNAUTHORIZED", extra={
            "clone_id": clone_id,
            "user_id": user_id
        })
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clone not found"
        )

    logger.debug("CLONE_OWNERSHIP_VERIFIED", extra={"clone_id": clone_id})
    return result.data


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
) -> dict:
    """
    Dependency to get full current user data.

    Returns:
        User data dict including is_platform_admin and billing_plan
    """
    result = db.table("users").select("*").eq("id", user_id).maybe_single().execute()

    if not result.data:
        logger.error("CURRENT_USER_NOT_FOUND", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return result.data


async def get_current_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to verify current user is a platform admin.

    Returns:
        User data if user is admin

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.get("is_platform_admin", False):
        logger.warning(
            "NON_ADMIN_ACCESS_ATTEMPT",
            extra={"user_id": current_user["id"]}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    logger.debug("ADMIN_ACCESS_GRANTED", extra={"user_id": current_user["id"]})
    return current_user


def get_db_client():
    """Alias for get_db for consistency."""
    return get_db()
