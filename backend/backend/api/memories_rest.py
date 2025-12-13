from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.schemas.memory import MemoryCreate
from backend.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("")
async def create_memory(payload: MemoryCreate, user=Depends(get_current_user)):
    return MemoryService.create_memory(user.id, payload)
