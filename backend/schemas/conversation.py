import logging
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.info("CONVERSATION_SCHEMAS_LOADED", extra={"file": __file__})


class MessageBase(BaseModel):
    """Base message schema."""
    role: str = Field(..., pattern="^(user|clone|system)$")
    content: str = Field(..., min_length=1)


class MessageCreate(BaseModel):
    """Schema for message creation (from user)."""
    content: str = Field(..., min_length=1)


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    conversation_id: str
    created_at: datetime
    metadata: dict = {}

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """Base conversation schema."""
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    """Schema for conversation creation."""
    pass


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    id: str
    user_id: str
    clone_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Conversation response with messages."""
    messages: List[MessageResponse] = []


class ChatResponse(BaseModel):
    """Response for chat endpoint containing user message and clone reply."""
    user_message: MessageResponse
    clone_message: MessageResponse
