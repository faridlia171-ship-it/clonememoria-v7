from typing import Optional
from uuid import UUID
import logging
from supabase import Client

from backend.schemas.rbac import RBACPermissionResult

logger = logging.getLogger(__name__)


class RBACService:
    def __init__(self, db: Client):
        self.db = db

    def check_permission(
        self,
        user_id: UUID,
        space_id: Optional[UUID],
        required_role: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None
    ) -> RBACPermissionResult:
        try:
            if space_id is None:
                return RBACPermissionResult(
                    allowed=False,
                    reason="No workspace specified"
                )

            result = self.db.rpc(
                'has_workspace_role',
                {
                    'p_user_id': str(user_id),
                    'p_space_id': str(space_id),
                    'p_required_role': required_role
                }
            ).execute()

            allowed = result.data if result.data is not None else False

            user_role_data = self.db.table('space_members') \
                .select('role_id, roles(name, hierarchy_level)') \
                .eq('user_id', str(user_id)) \
                .eq('space_id', str(space_id)) \
                .maybeSingle() \
                .execute()

            user_role = None
            user_role_level = None
            if user_role_data.data and user_role_data.data.get('roles'):
                user_role = user_role_data.data['roles']['name']
                user_role_level = user_role_data.data['roles']['hierarchy_level']

            required_role_data = self.db.table('roles') \
                .select('hierarchy_level') \
                .eq('name', required_role) \
                .maybeSingle() \
                .execute()

            required_role_level = None
            if required_role_data.data:
                required_role_level = required_role_data.data['hierarchy_level']

            reason = None
            if not allowed:
                if user_role:
                    reason = f"User role '{user_role}' is insufficient for required role '{required_role}'"
                else:
                    reason = f"User is not a member of this workspace"

            return RBACPermissionResult(
                allowed=allowed,
                user_role=user_role,
                user_role_level=user_role_level,
                required_role_level=required_role_level,
                reason=reason
            )

        except Exception as e:
            logger.error(f"RBAC permission check failed: {str(e)}")
            return RBACPermissionResult(
                allowed=False,
                reason=f"Permission check error: {str(e)}"
            )

    def get_user_role_in_workspace(
        self,
        user_id: UUID,
        space_id: UUID
    ) -> Optional[str]:
        try:
            result = self.db.table('space_members') \
                .select('roles(name)') \
                .eq('user_id', str(user_id)) \
                .eq('space_id', str(space_id)) \
                .maybeSingle() \
                .execute()

            if result.data and result.data.get('roles'):
                return result.data['roles']['name']

            return None

        except Exception as e:
            logger.error(f"Failed to get user role: {str(e)}")
            return None

    def is_workspace_owner(self, user_id: UUID, space_id: UUID) -> bool:
        try:
            result = self.db.table('spaces') \
                .select('owner_user_id') \
                .eq('id', str(space_id)) \
                .maybeSingle() \
                .execute()

            if result.data:
                return str(result.data['owner_user_id']) == str(user_id)

            return False

        except Exception as e:
            logger.error(f"Failed to check workspace owner: {str(e)}")
            return False

    def is_platform_admin(self, user_id: UUID) -> bool:
        try:
            result = self.db.table('users') \
                .select('is_platform_admin') \
                .eq('id', str(user_id)) \
                .maybeSingle() \
                .execute()

            if result.data:
                return result.data.get('is_platform_admin', False)

            return False

        except Exception as e:
            logger.error(f"Failed to check platform admin: {str(e)}")
            return False

    def get_all_roles(self):
        try:
            result = self.db.table('roles') \
                .select('*') \
                .order('hierarchy_level', desc=True) \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get roles: {str(e)}")
            return []
