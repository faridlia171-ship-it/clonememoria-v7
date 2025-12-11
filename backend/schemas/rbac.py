from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class RoleBase(BaseModel):
    name: str = Field(..., pattern="^(system|owner|admin|editor|viewer)$")
    description: str
    permissions: Dict[str, Any] = Field(default_factory=dict)
    hierarchy_level: int


class RoleCreate(RoleBase):
    pass


class Role(RoleBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceMemberRole(BaseModel):
    user_id: UUID
    space_id: UUID
    role: Role
    created_at: datetime

    class Config:
        from_attributes = True


class RBACPermissionCheck(BaseModel):
    user_id: UUID
    space_id: Optional[UUID] = None
    required_role: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None


class RBACPermissionResult(BaseModel):
    allowed: bool
    user_role: Optional[str] = None
    user_role_level: Optional[int] = None
    required_role_level: Optional[int] = None
    reason: Optional[str] = None
