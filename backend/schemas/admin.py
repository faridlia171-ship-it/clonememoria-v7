import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.info("ADMIN_SCHEMAS_LOADED", extra={"file": __file__})


class AdminUserSummary(BaseModel):
    """Summary of a user for admin console."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    billing_plan: str
    created_at: datetime
    clone_count: int = 0
    message_count_this_month: int = 0

    class Config:
        from_attributes = True


class AdminCloneSummary(BaseModel):
    """Summary of a clone for admin console."""
    id: str
    name: str
    user_id: str
    user_email: str
    created_at: datetime
    memory_count: int = 0
    conversation_count: int = 0
    document_count: int = 0

    class Config:
        from_attributes = True


class PlatformStats(BaseModel):
    """Overall platform statistics."""
    total_users: int
    total_clones: int
    total_conversations: int
    total_messages: int
    total_documents: int
    active_users_this_month: int
    users_by_plan: dict


class BillingQuota(BaseModel):
    """Billing plan quota definition."""
    plan: str
    max_clones: int
    max_messages_per_month: int
    max_documents_per_clone: int

    class Config:
        from_attributes = True
