import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from backend.db.client import get_db
from backend.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse
from backend.api.deps import get_current_user_id, verify_clone_ownership

logger = logging.getLogger(__name__)
logger.info("MEMORIES_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    clone_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Get all memories for a clone."""

    logger.info("LIST_MEMORIES_REQUEST", extra={
        "clone_id": clone_id,
        "user_id": user_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    result = db.table("memories").select("*").eq("clone_id", clone_id).order("created_at", desc=True).execute()

    logger.info("LIST_MEMORIES_SUCCESS", extra={
        "clone_id": clone_id,
        "memory_count": len(result.data)
    })

    return [MemoryResponse(**memory) for memory in result.data]


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    clone_id: str,
    memory_data: MemoryCreate,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Create a new memory for a clone."""

    logger.info("CREATE_MEMORY_REQUEST", extra={
        "clone_id": clone_id,
        "user_id": user_id,
        "memory_title": memory_data.title
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    memory_insert = {
        "user_id": user_id,
        "clone_id": clone_id,
        "title": memory_data.title,
        "content": memory_data.content,
        "source_type": memory_data.source_type
    }

    result = db.table("memories").insert(memory_insert).execute()

    if not result.data:
        logger.error("MEMORY_CREATION_FAILED", extra={
            "clone_id": clone_id,
            "user_id": user_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create memory"
        )

    memory = result.data[0]

    logger.info("MEMORY_CREATED_SUCCESS", extra={
        "memory_id": memory["id"],
        "clone_id": clone_id
    })

    return MemoryResponse(**memory)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    clone_id: str,
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Get a specific memory."""

    logger.info("GET_MEMORY_REQUEST", extra={
        "memory_id": memory_id,
        "clone_id": clone_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    result = db.table("memories").select("*").eq("id", memory_id).eq("clone_id", clone_id).maybe_single().execute()

    if not result.data:
        logger.warning("MEMORY_NOT_FOUND", extra={
            "memory_id": memory_id,
            "clone_id": clone_id
        })
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found"
        )

    return MemoryResponse(**result.data)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    clone_id: str,
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Delete a memory."""

    logger.info("DELETE_MEMORY_REQUEST", extra={
        "memory_id": memory_id,
        "clone_id": clone_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    db.table("memories").delete().eq("id", memory_id).eq("clone_id", clone_id).execute()

    logger.info("MEMORY_DELETED_SUCCESS", extra={
        "memory_id": memory_id,
        "clone_id": clone_id
    })

    return None
