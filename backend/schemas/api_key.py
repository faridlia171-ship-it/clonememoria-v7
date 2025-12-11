import logging
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.info("API_KEY_SCHEMAS_LOADED", extra={"file": __file__})


class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    label: str = Field(..., min_length=1, max_length=100, description="Label for the API key")
    scopes: List[str] = Field(default=["read"], description="Scopes for the API key")
    rate_limit_requests: int = Field(default=100, ge=1, le=10000, description="Max requests per window")
    rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86400, description="Rate limit window in seconds")


class APIKeyResponse(BaseModel):
    """Schema for API key response."""
    id: str
    user_id: str
    label: str
    key_prefix: str
    scopes: List[str]
    rate_limit_requests: int
    rate_limit_window_seconds: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes raw key once)."""
    raw_key: str
    warning: str = "This is the only time the full API key will be shown. Store it securely."


class APIKeyRevoke(BaseModel):
    """Schema for revoking an API key."""
    pass
