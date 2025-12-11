import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.info("CLONE_SCHEMAS_LOADED", extra={"file": __file__})


class ToneConfig(BaseModel):
    """Configuration for clone's tone and personality."""
    warmth: float = Field(default=0.7, ge=0.0, le=1.0, description="How warm and affectionate")
    humor: float = Field(default=0.5, ge=0.0, le=1.0, description="How humorous")
    formality: float = Field(default=0.3, ge=0.0, le=1.0, description="How formal")


class CloneBase(BaseModel):
    """Base clone schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    tone_config: Optional[ToneConfig] = None
    avatar_url: Optional[str] = None


class CloneCreate(CloneBase):
    """Schema for clone creation."""
    pass


class CloneUpdate(BaseModel):
    """Schema for clone update."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    tone_config: Optional[ToneConfig] = None
    avatar_url: Optional[str] = None


class CloneResponse(CloneBase):
    """Schema for clone response."""
    id: str
    user_id: str
    tone_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CloneWithStats(CloneResponse):
    """Clone response with additional statistics."""
    memory_count: int = 0
    conversation_count: int = 0
