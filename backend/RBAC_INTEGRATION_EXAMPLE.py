"""
Example: How to integrate RBAC middleware into existing routes

This file demonstrates how to add RBAC protection to your endpoints.
DO NOT USE THIS FILE DIRECTLY - it's for reference only.
"""

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from backend.api.rbac_middleware import (
    require_viewer,
    require_editor,
    require_admin,
    require_owner,
    require_platform_admin
)
from backend.api.deps import get_current_user

router = APIRouter()


@router.get("/clones/{clone_id}")
async def get_clone(
    clone_id: UUID,
    space_id: UUID,
    current_user: dict = Depends(require_viewer)
):
    """
    GET /clones/{clone_id}?space_id={space_id}

    Requires: viewer role or higher
    Protected by RBAC middleware
    """
    pass


@router.post("/clones")
async def create_clone(
    space_id: UUID,
    current_user: dict = Depends(require_editor)
):
    """
    POST /clones?space_id={space_id}

    Requires: editor role or higher
    Protected by RBAC middleware
    """
    pass


@router.put("/clones/{clone_id}")
async def update_clone(
    clone_id: UUID,
    space_id: UUID,
    current_user: dict = Depends(require_editor)
):
    """
    PUT /clones/{clone_id}?space_id={space_id}

    Requires: editor role or higher
    Protected by RBAC middleware
    """
    pass


@router.delete("/clones/{clone_id}")
async def delete_clone(
    clone_id: UUID,
    space_id: UUID,
    current_user: dict = Depends(require_admin)
):
    """
    DELETE /clones/{clone_id}?space_id={space_id}

    Requires: admin role or higher
    Protected by RBAC middleware
    """
    pass


@router.delete("/spaces/{space_id}")
async def delete_workspace(
    space_id: UUID,
    current_user: dict = Depends(require_owner)
):
    """
    DELETE /spaces/{space_id}

    Requires: owner role
    Protected by RBAC middleware
    """
    pass


@router.get("/admin/users")
async def list_all_users(
    current_user: dict = Depends(require_platform_admin)
):
    """
    GET /admin/users

    Requires: platform admin (system role)
    Protected by RBAC middleware
    """
    pass


@router.get("/public/clones/{clone_id}")
async def get_public_clone(
    clone_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    GET /public/clones/{clone_id}

    No RBAC required - uses standard auth only
    Any authenticated user can access
    """
    pass


"""
RBAC ROLE HIERARCHY:
- system (100): Platform admin, access to everything
- owner (90): Workspace owner, full control of workspace
- admin (80): Workspace admin, can manage users and resources
- editor (70): Can create and modify content
- viewer (60): Read-only access

Higher level roles automatically have lower level permissions.
Example: admin can do everything editor and viewer can do.

USAGE IN ROUTES:
1. Import the appropriate require_* function
2. Add it to Depends()
3. ALWAYS include space_id as query parameter (except for platform admin)
4. The middleware will check permissions automatically

QUERY PARAMETERS:
- space_id: Required for workspace-scoped operations
- Example: GET /api/clones/{id}?space_id={uuid}

ERROR RESPONSES:
- 400: Bad Request (missing space_id)
- 403: Forbidden (insufficient role)
- 500: Internal Server Error (permission check failed)

AUDIT LOGGING:
All RBAC checks are automatically logged to audit_log table with:
- user_id
- space_id
- required_role
- actual_role
- allowed/denied
- timestamp
"""
