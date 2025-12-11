import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

# Import corrigé : Render exige des chemins absolus incluant "backend"
from backend.api.deps import get_current_user, get_db_client
from backend.schemas.api_key import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreateResponse
)
from backend.services.api_key_service import generate_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_client)
):
    """List all API keys for the current user."""
    try:
        result = await db.from_("api_keys").select("*").eq(
            "user_id", current_user["id"]
        ).order("created_at", desc=True).execute()

        logger.info(
            "API keys listed",
            extra={"user_id": current_user["id"], "count": len(result.data)}
        )

        return result.data

    except Exception as e:
        logger.error(
            "Error listing API keys",
            extra={"user_id": current_user["id"], "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_client)
):
    """Create a new API key for the current user."""
    try:
        full_key, key_hash, key_prefix = generate_api_key()

        new_key = {
            "user_id": current_user["id"],
            "label": api_key_data.label,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "scopes": api_key_data.scopes,
            "rate_limit_requests": api_key_data.rate_limit_requests,
            "rate_limit_window_seconds": api_key_data.rate_limit_window_seconds,
            "created_at": datetime.utcnow().isoformat()
        }

        result = await db.from_("api_keys").insert(new_key).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Failed to create API key")

        created_key = result.data[0]

        logger.info(
            "API key created",
            extra={
                "user_id": current_user["id"],
                "api_key_id": created_key["id"],
                "label": api_key_data.label
            }
        )

        return APIKeyCreateResponse(
            **created_key,
            raw_key=full_key
        )

    except Exception as e:
        logger.error(
            "Error creating API key",
            extra={"user_id": current_user["id"], "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to create API key")


@router.delete("/{api_key_id}", status_code=204)
async def revoke_api_key(
    api_key_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_client)
):
    """Revoke an API key (soft delete)."""
    try:
        existing = await db.from_("api_keys").select("id, user_id").eq(
            "id", api_key_id
        ).execute()

        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="API key not found")

        if existing.data[0]["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to revoke this API key"
            )

        await db.from_("api_keys").update({
            "revoked_at": datetime.utcnow().isoformat()
        }).eq("id", api_key_id).execute()

        logger.info(
            "API key revoked",
            extra={"user_id": current_user["id"], "api_key_id": api_key_id}
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error revoking API key",
            extra={"user_id": current_user["id"], "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to revoke API key")
