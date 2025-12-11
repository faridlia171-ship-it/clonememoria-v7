from fastapi import Depends, HTTPException, status
from typing import Optional
from uuid import UUID
import logging

from backend.db.client import get_db
from backend.services.rbac_service import RBACService
from backend.api.deps import get_current_user

logger = logging.getLogger(__name__)


class RBACDependency:
    def __init__(self, required_role: str, require_platform_admin: bool = False):
        self.required_role = required_role
        self.require_platform_admin = require_platform_admin

    async def __call__(
        self,
        space_id: Optional[UUID] = None,
        current_user: dict = Depends(get_current_user)
    ):
        try:
            user_id = UUID(current_user['id'])
            db = get_db()
            rbac_service = RBACService(db)

            if self.require_platform_admin:
                is_admin = rbac_service.is_platform_admin(user_id)
                if not is_admin:
                    logger.warning(
                        f"Platform admin access denied for user {user_id}",
                        extra={"user_id": str(user_id)}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Platform admin access required"
                    )
                return current_user

            if space_id is None:
                logger.warning(
                    f"Workspace access check without space_id for user {user_id}",
                    extra={"user_id": str(user_id), "required_role": self.required_role}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workspace ID required"
                )

            permission_result = rbac_service.check_permission(
                user_id=user_id,
                space_id=space_id,
                required_role=self.required_role
            )

            if not permission_result.allowed:
                logger.warning(
                    f"RBAC access denied for user {user_id}",
                    extra={
                        "user_id": str(user_id),
                        "space_id": str(space_id),
                        "required_role": self.required_role,
                        "user_role": permission_result.user_role,
                        "reason": permission_result.reason
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=permission_result.reason or f"Requires {self.required_role} role or higher"
                )

            logger.debug(
                f"RBAC access granted for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "space_id": str(space_id),
                    "user_role": permission_result.user_role,
                    "required_role": self.required_role
                }
            )

            return current_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"RBAC middleware error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )


require_viewer = RBACDependency(required_role="viewer")
require_editor = RBACDependency(required_role="editor")
require_admin = RBACDependency(required_role="admin")
require_owner = RBACDependency(required_role="owner")
require_platform_admin = RBACDependency(required_role="system", require_platform_admin=True)
