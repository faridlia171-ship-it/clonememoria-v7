import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)
logger.info("USER_SCHEMAS_LOADED", extra={"file": __file__})


class UserConsent(BaseModel):
    """GDPR / privacy consent schema."""
    marketing: bool = False
    analytics: bool = False
    ai_training: bool = False


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None
    consent: Optional[UserConsent] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user info."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    consent: Optional[UserConsent] = None


class UserResponse(UserBase):
    """Schema for user returned to clients."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
