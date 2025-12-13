from fastapi import APIRouter, Depends
from backend.schemas.user import UserResponse
from backend.models.user_consent import UserConsent
from backend.api.deps import get_current_user
from backend.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/consent")
async def update_consent(
    payload: UserConsent,
    current_user: UserResponse = Depends(get_current_user),
):
    updated = UserService.update_consent(current_user.id, payload.dict())
    return {"success": True, "consent": updated}
