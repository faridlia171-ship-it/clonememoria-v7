from fastapi import APIRouter, Depends
from backend.api.deps import get_current_user
from backend.schemas.chat import ChatMessage
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{clone_id}")
async def chat(clone_id: str, payload: ChatMessage, user=Depends(get_current_user)):
    return ChatService.generate_reply(user.id, clone_id, payload.message)
