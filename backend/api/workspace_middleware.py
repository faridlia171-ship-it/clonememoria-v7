import logging
from typing import Optional
from uuid import UUID
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from backend.db.client import get_db

logger = logging.getLogger(__name__)


class WorkspaceContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for multi-tenant workspace isolation.

    Extracts space_id from request and validates user access.
    Sets request.state.space_id for downstream route handlers.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        bypass_routes = [
            '/api/health',
            '/api/auth/',
            '/api/auth-v2/',
            '/docs',
            '/openapi.json',
            '/redoc'
        ]

        if any(request.url.path.startswith(route) for route in bypass_routes):
            return await call_next(request)

        space_id = self._extract_space_id(request)

        if space_id:
            request.state.space_id = str(space_id)
            logger.debug(f"Workspace context set: {space_id}")
        else:
            request.state.space_id = None

        response = await call_next(request)
        return response

    def _extract_space_id(self, request: Request) -> Optional[UUID]:
        """
        Extract space_id from query params or request body.
        Priority: query params > body
        """
        try:
            space_id_str = request.query_params.get('space_id')

            if space_id_str:
                return UUID(space_id_str)

            if request.method in ['POST', 'PUT', 'PATCH']:
                if hasattr(request.state, '_body'):
                    body = request.state._body
                    if isinstance(body, dict) and 'space_id' in body:
                        return UUID(body['space_id'])

            return None

        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid space_id format: {str(e)}")
            return None


def get_workspace_id(request: Request) -> Optional[UUID]:
    """
    Dependency to extract workspace ID from request state.
    Returns None if no workspace context.
    """
    space_id = getattr(request.state, 'space_id', None)
    if space_id:
        try:
            return UUID(space_id)
        except (ValueError, AttributeError):
            return None
    return None


def require_workspace_id(request: Request) -> UUID:
    """
    Dependency that REQUIRES workspace ID.
    Raises 400 if space_id is missing.
    """
    space_id = get_workspace_id(request)

    if not space_id:
        logger.warning(
            f"Missing space_id for {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "user_id": getattr(request.state, 'user_id', None)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "space_id is required for this operation",
                "hint": "Add ?space_id=<uuid> to the request URL"
            }
        )

    return space_id


async def require_workspace_access(
    request: Request,
    space_id: UUID,
    required_role: str = 'member'
) -> bool:
    """
    Check if current user has access to workspace with minimum role.

    Args:
        request: FastAPI request
        space_id: Workspace UUID
        required_role: Minimum required role (member, admin, owner)

    Returns:
        True if user has access

    Raises:
        HTTPException 403 if access denied
        HTTPException 401 if not authenticated
    """
    from backend.api.deps import get_current_user_id

    try:
        user_id = get_current_user_id(request)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    db = get_db()

    try:
        result = db.rpc(
            'user_has_workspace_access',
            {
                'p_space_id': str(space_id),
                'p_required_role': required_role
            }
        ).execute()

        has_access = result.data if result.data is not None else False

        if not has_access:
            user_role = db.rpc(
                'get_user_workspace_role',
                {'p_space_id': str(space_id)}
            ).execute()

            actual_role = user_role.data if user_role.data else 'none'

            logger.warning(
                f"Workspace access denied",
                extra={
                    "user_id": user_id,
                    "space_id": str(space_id),
                    "required_role": required_role,
                    "actual_role": actual_role
                }
            )

            db.rpc('log_auth_event', {
                'p_user_id': user_id,
                'p_event': 'workspace_access_denied',
                'p_ip_address': request.client.host if request.client else None,
                'p_user_agent': request.headers.get('user-agent'),
                'p_metadata': {
                    'space_id': str(space_id),
                    'required_role': required_role,
                    'actual_role': actual_role
                }
            }).execute()

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Access denied to this workspace",
                    "required_role": required_role,
                    "your_role": actual_role
                }
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check workspace access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify workspace access"
        )


async def get_user_workspaces(user_id: str) -> list:
    """
    Get all workspaces user has access to.

    Args:
        user_id: User UUID string

    Returns:
        List of dicts with space_id and role
    """
    db = get_db()

    try:
        result = db.rpc('get_user_workspaces', {}).execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Failed to get user workspaces: {str(e)}")
        return []


async def validate_workspace_resource(
    space_id: UUID,
    resource_type: str,
    resource_id: UUID,
    user_id: str
) -> bool:
    """
    Validate that a resource belongs to the specified workspace.
    Prevents cross-workspace data access.

    Args:
        space_id: Expected workspace UUID
        resource_type: Type of resource (clones, memories, etc.)
        resource_id: Resource UUID
        user_id: User UUID string

    Returns:
        True if resource belongs to workspace

    Raises:
        HTTPException 404 if resource not found or doesn't belong to workspace
    """
    db = get_db()

    table_map = {
        'clone': 'clones',
        'memory': 'memories',
        'conversation': 'conversations',
        'message': 'messages',
        'document': 'clone_documents'
    }

    table = table_map.get(resource_type)
    if not table:
        logger.error(f"Unknown resource type: {resource_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown resource type: {resource_type}"
        )

    try:
        result = db.table(table) \
            .select('id, space_id') \
            .eq('id', str(resource_id)) \
            .maybeSingle() \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_type.capitalize()} not found"
            )

        resource_space_id = result.data.get('space_id')

        if resource_space_id != str(space_id):
            logger.warning(
                f"Cross-workspace access attempt",
                extra={
                    "user_id": user_id,
                    "expected_space_id": str(space_id),
                    "actual_space_id": resource_space_id,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id)
                }
            )

            db.rpc('log_auth_event', {
                'p_user_id': user_id,
                'p_event': 'cross_workspace_access_attempt',
                'p_ip_address': None,
                'p_user_agent': None,
                'p_metadata': {
                    'expected_space_id': str(space_id),
                    'actual_space_id': resource_space_id,
                    'resource_type': resource_type,
                    'resource_id': str(resource_id)
                }
            }).execute()

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_type.capitalize()} not found"
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate workspace resource: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate resource"
        )
