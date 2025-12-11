import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.info("DOCUMENT_SCHEMAS_LOADED", extra={"file": __file__})


class DocumentBase(BaseModel):
    """Base document schema."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    source_type: str = Field(default="manual")


class DocumentCreate(DocumentBase):
    """Schema for document creation."""
    pass


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: str
    clone_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentWithStats(DocumentResponse):
    """Document response with additional statistics."""
    chunk_count: int = 0
