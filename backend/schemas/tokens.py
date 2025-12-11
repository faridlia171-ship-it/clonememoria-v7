from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenCreate(BaseModel):
    user_id: UUID
    token_hash: str
    expires_at: datetime
    device_info: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    id: UUID
    user_id: UUID
    expires_at: datetime
    created_at: datetime
    revoked_at: Optional[datetime] = None
    device_info: Dict[str, Any] = {}
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class TokenBlacklistEntry(BaseModel):
    token_hash: str
    user_id: Optional[UUID] = None
    expires_at: datetime
    reason: str = "manual_revoke"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
