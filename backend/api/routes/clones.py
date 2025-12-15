import logging
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from supabase import Client

from backend.db.client import get_db
from backend.schemas.clone import CloneCreate, CloneUpdate, CloneResponse, CloneWithStats
from backend.schemas.ai_config import AIConfigUpdate
from backend.schemas.avatar import AvatarUploadResponse
from backend.api.deps import get_current_user_id, verify_clone_ownership, get_current_user
from backend.services.quota_service import check_clone_creation_quota

logger = logging.getLogger(__name__)
logger.info("CLONES_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.get("", response_model=List[CloneWithStats])
async def list_clones(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Get all clones for the current user."""

    logger.info("LIST_CLONES_REQUEST", extra={"user_id": user_id})

    result = (
        db.table("clones")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    clones_with_stats = []

    for clone in result.data:
        memory_count_result = (
            db.table("memories")
            .select("id", count="exact")
            .eq("clone_id", clone["id"])
            .execute()
        )
        memory_count = memory_count_result.count or 0

        conversation_count_result = (
            db.table("conversations")
            .select("id", count="exact")
            .eq("clone_id", clone["id"])
            .execute()
        )
        conversation_count = conversation_count_result.count or 0

        clones_with_stats.append(
            CloneWithStats(
                **clone,
                memory_count=memory_count,
                conversation_count=conversation_count
            )
        )

    logger.info(
        "LIST_CLONES_SUCCESS",
        extra={"user_id": user_id, "clone_count": len(clones_with_stats)}
    )

    return clones_with_stats


@router.post("", response_model=CloneResponse, status_code=status.HTTP_201_CREATED)
async def create_clone(
    clone_data: CloneCreate,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """Create a new clone."""

    user_id = current_user["id"]
    billing_plan = current_user.get("billing_plan", "FREE")

    logger.info(
        "CREATE_CLONE_REQUEST",
        extra={"user_id": user_id, "clone_name": clone_data.name, "billing_plan": billing_plan}
    )

    is_allowed, error_message = await check_clone_creation_quota(
        db, user_id, billing_plan
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=error_message
        )

    tone_config = (
        clone_data.tone_config.model_dump()
        if clone_data.tone_config
        else {"warmth": 0.7, "humor": 0.5, "formality": 0.3}
    )

    clone_insert = {
        "user_id": user_id,
        "name": clone_data.name,
        "description": clone_data.description,
        "tone_config": tone_config,
        "avatar_url": clone_data.avatar_url
    }

    result = db.table("clones").insert(clone_insert).execute()

    if not result.data:
        logger.error("CLONE_CREATION_FAILED", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create clone"
        )

    clone = result.data[0]

    logger.info(
        "CLONE_CREATED_SUCCESS",
        extra={"clone_id": clone["id"], "clone_name": clone["name"]}
    )

    return CloneResponse(**clone)


@router.get("/{clone_id}", response_model=CloneResponse)
async def get_clone(
    clone: dict = Depends(verify_clone_ownership)
):
    """Get a specific clone."""

    logger.info("GET_CLONE_REQUEST", extra={"clone_id": clone["id"]})
    return CloneResponse(**clone)


@router.put("/{clone_id}", response_model=CloneResponse)
async def update_clone(
    clone_id: str,
    clone_data: CloneUpdate,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Update a clone."""

    logger.info(
        "UPDATE_CLONE_REQUEST",
        extra={"clone_id": clone_id, "user_id": user_id}
    )

    update_data = {}

    if clone_data.name is not None:
        update_data["name"] = clone_data.name
    if clone_data.description is not None:
        update_data["description"] = clone_data.description
    if clone_data.tone_config is not None:
        update_data["tone_config"] = clone_data.tone_config.model_dump()
    if clone_data.avatar_url is not None:
        update_data["avatar_url"] = clone_data.avatar_url

    if not update_data:
        logger.warning("UPDATE_CLONE_NO_CHANGES", extra={"clone_id": clone_id})
        return CloneResponse(**clone)

    result = (
        db.table("clones")
        .update(update_data)
        .eq("id", clone_id)
        .execute()
    )

    if not result.data:
        logger.error("CLONE_UPDATE_FAILED", extra={"clone_id": clone_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update clone"
        )

    updated_clone = result.data[0]

    logger.info("CLONE_UPDATED_SUCCESS", extra={"clone_id": clone_id})
    return CloneResponse(**updated_clone)


@router.delete("/{clone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clone(
    clone_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Delete a clone."""

    logger.info(
        "DELETE_CLONE_REQUEST",
        extra={"clone_id": clone_id, "user_id": user_id}
    )

    db.table("clones").delete().eq("id", clone_id).execute()

    logger.info("CLONE_DELETED_SUCCESS", extra={"clone_id": clone_id})
    return None


@router.patch("/{clone_id}/settings", response_model=CloneResponse)
async def update_clone_ai_settings(
    clone_id: str,
    config_data: AIConfigUpdate,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Update clone AI configuration settings."""

    logger.info(
        "UPDATE_CLONE_AI_SETTINGS_REQUEST",
        extra={"clone_id": clone_id, "user_id": user_id}
    )

    update_data = {}

    if config_data.llm_provider is not None:
        update_data["llm_provider"] = config_data.llm_provider
    if config_data.llm_model is not None:
        update_data["llm_model"] = config_data.llm_model
    if config_data.embedding_provider is not None:
        update_data["embedding_provider"] = config_data.embedding_provider
    if config_data.tts_provider is not None:
        update_data["tts_provider"] = config_data.tts_provider
    if config_data.tts_voice_id is not None:
        update_data["tts_voice_id"] = config_data.tts_voice_id
    if config_data.temperature is not None:
        update_data["temperature"] = config_data.temperature
    if config_data.max_tokens is not None:
        update_data["max_tokens"] = config_data.max_tokens

    if not update_data:
        logger.warning("UPDATE_CLONE_AI_SETTINGS_NO_CHANGES", extra={"clone_id": clone_id})
        return CloneResponse(**clone)

    result = (
        db.table("clones")
        .update(update_data)
        .eq("id", clone_id)
        .execute()
    )

    if not result.data:
        logger.error("CLONE_AI_SETTINGS_UPDATE_FAILED", extra={"clone_id": clone_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update clone AI settings"
        )

    updated_clone = result.data[0]

    logger.info("CLONE_AI_SETTINGS_UPDATED_SUCCESS", extra={"clone_id": clone_id})
    return CloneResponse(**updated_clone)


@router.get("/{clone_id}/settings")
async def get_clone_ai_settings(
    clone_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership)
):
    """Get clone AI configuration settings."""

    logger.info(
        "GET_CLONE_AI_SETTINGS_REQUEST",
        extra={"clone_id": clone_id, "user_id": user_id}
    )

    return {
        "llm_provider": clone.get("llm_provider", "dummy"),
        "llm_model": clone.get("llm_model"),
        "embedding_provider": clone.get("embedding_provider", "dummy"),
        "tts_provider": clone.get("tts_provider", "dummy"),
        "tts_voice_id": clone.get("tts_voice_id"),
        "temperature": clone.get("temperature", 0.7),
        "max_tokens": clone.get("max_tokens")
    }


@router.post("/{clone_id}/avatar", response_model=AvatarUploadResponse)
async def upload_clone_avatar(
    clone_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Upload an avatar image for a clone."""

    logger.info(
        "UPLOAD_CLONE_AVATAR_REQUEST",
        extra={
            "clone_id": clone_id,
            "user_id": user_id,
            "filename": file.filename,
            "content_type": file.content_type
        }
    )

    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
        )

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 5MB limit"
        )

    media_dir = os.path.join(os.getcwd(), "media", "avatars")
    os.makedirs(media_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{clone_id}{ext}"
    path = os.path.join(media_dir, filename)

    with open(path, "wb") as f:
        f.write(contents)

    avatar_url = f"/media/avatars/{filename}"

    result = (
        db.table("clones")
        .update({"avatar_image_url": avatar_url})
        .eq("id", clone_id)
        .execute()
    )

    if not result.data:
        logger.error("AVATAR_UPDATE_FAILED", extra={"clone_id": clone_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update clone with avatar URL"
        )

    logger.info(
        "CLONE_AVATAR_UPLOADED_SUCCESS",
        extra={"clone_id": clone_id, "avatar_url": avatar_url}
    )

    return AvatarUploadResponse(avatar_image_url=avatar_url)
