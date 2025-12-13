from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.schemas.clone import CloneCreate
from backend.services.clone_service import CloneService

router = APIRouter(prefix="/clones", tags=["clones"])


@router.post("")
async def create_clone(data: CloneCreate, user=Depends(get_current_user)):
    return CloneService.create_clone(user.id, data)


@router.get("")
async def list_clones(user=Depends(get_current_user)):
    return CloneService.list_clones(user.id)
