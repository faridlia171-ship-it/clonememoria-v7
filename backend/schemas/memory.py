import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.info("MEMORY_SCHEMAS_LOADED", extra={"file": __file__})


class MemoryBase(BaseModel):
    """Base memory schema."""
    title: Optional[str] = Field(None, max_length=200)
    content: str = Field(..., min_length=1)
    source_type: str = Field(default="manual")


class MemoryCreate(MemoryBase):
    """Schema for memory creation."""
    pass


class MemoryUpdate(BaseModel):
    """Schema for memory update."""
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    source_type: Optional[str] = None


class MemoryResponse(MemoryBase):
    """Schema for memory response."""
    id: str
    user_id: str
    clone_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
