import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from supabase import Client
from pydantic import BaseModel

from backend.db.client import get_db
from backend.api.deps import get_current_user_id
from backend.api.workspace_middleware import (
    require_workspace_access,
    get_user_workspaces as get_workspaces_helper
)

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceResponse(BaseModel):
    id: str
    owner_user_id: str
    name: str
    description: str | None
    created_at: str
    updated_at: str


class WorkspaceMemberAdd(BaseModel):
    user_id: str
    role: str = 'member'


class WorkspaceMemberResponse(BaseModel):
    id: str
    space_id: str
    user_id: str
    role: str
    created_at: str


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """
    List all workspaces user has access to.
    Includes owned and member workspaces.
    """
    logger.info("LIST_WORKSPACES_REQUEST", extra={"user_id": user_id})

    try:
        workspaces = await get_workspaces_helper(user_id)

        workspace_ids = [w['space_id'] for w in workspaces]

        if not workspace_ids:
            return []

        result = db.table('spaces') \
            .select('*') \
            .in_('id', workspace_ids) \
            .order('created_at', desc=True) \
            .execute()

        logger.info("LIST_WORKSPACES_SUCCESS", extra={
            "user_id": user_id,
            "workspace_count": len(result.data)
        })

        return result.data

    except Exception as e:
        logger.error(f"LIST_WORKSPACES_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workspaces"
        )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """
    Create a new workspace.
    User becomes the owner automatically.
    """
    logger.info("CREATE_WORKSPACE_REQUEST", extra={
        "user_id": user_id,
        "workspace_name": workspace_data.name
    })

    try:
        workspace_insert = {
            "owner_user_id": user_id,
            "name": workspace_data.name,
            "description": workspace_data.description
        }

        result = db.table('spaces') \
            .insert(workspace_insert) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workspace"
            )

        workspace = result.data[0]

        db.rpc('log_auth_event', {
            'p_user_id': user_id,
            'p_event': 'workspace_created',
            'p_ip_address': None,
            'p_user_agent': None,
            'p_metadata': {
                'space_id': workspace['id'],
                'workspace_name': workspace['name']
            }
        }).execute()

        logger.info("CREATE_WORKSPACE_SUCCESS", extra={
            "user_id": user_id,
            "workspace_id": workspace['id']
        })

        return workspace

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CREATE_WORKSPACE_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )


@router.get("/{space_id}", response_model=WorkspaceResponse)
async def get_workspace(
    space_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Get workspace details (requires member access)."""
    await require_workspace_access(request, space_id, 'member')

    try:
        result = db.table('spaces') \
            .select('*') \
            .eq('id', str(space_id)) \
            .maybeSingle() \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET_WORKSPACE_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace"
        )


@router.put("/{space_id}", response_model=WorkspaceResponse)
async def update_workspace(
    space_id: UUID,
    workspace_data: WorkspaceUpdate,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Update workspace (requires owner)."""
    await require_workspace_access(request, space_id, 'owner')

    try:
        update_data = {}
        if workspace_data.name is not None:
            update_data['name'] = workspace_data.name
        if workspace_data.description is not None:
            update_data['description'] = workspace_data.description

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )

        result = db.table('spaces') \
            .update(update_data) \
            .eq('id', str(space_id)) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        db.rpc('log_auth_event', {
            'p_user_id': user_id,
            'p_event': 'workspace_updated',
            'p_ip_address': None,
            'p_user_agent': None,
            'p_metadata': {
                'space_id': str(space_id),
                'updates': update_data
            }
        }).execute()

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"UPDATE_WORKSPACE_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace"
        )


@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    space_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Delete workspace (requires owner). Cascades to all resources."""
    await require_workspace_access(request, space_id, 'owner')

    try:
        result = db.table('spaces') \
            .delete() \
            .eq('id', str(space_id)) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        db.rpc('log_auth_event', {
            'p_user_id': user_id,
            'p_event': 'workspace_deleted',
            'p_ip_address': None,
            'p_user_agent': None,
            'p_metadata': {'space_id': str(space_id)}
        }).execute()

        logger.info("DELETE_WORKSPACE_SUCCESS", extra={
            "user_id": user_id,
            "workspace_id": str(space_id)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE_WORKSPACE_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workspace"
        )


@router.get("/{space_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    space_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """List all members of workspace (requires member access)."""
    await require_workspace_access(request, space_id, 'member')

    try:
        result = db.table('space_members') \
            .select('*') \
            .eq('space_id', str(space_id)) \
            .order('created_at', desc=False) \
            .execute()

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LIST_WORKSPACE_MEMBERS_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workspace members"
        )


@router.post("/{space_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    space_id: UUID,
    member_data: WorkspaceMemberAdd,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Add member to workspace (requires admin access)."""
    await require_workspace_access(request, space_id, 'admin')

    try:
        member_insert = {
            "space_id": str(space_id),
            "user_id": member_data.user_id,
            "role": member_data.role
        }

        result = db.table('space_members') \
            .insert(member_insert) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add workspace member"
            )

        db.rpc('log_auth_event', {
            'p_user_id': user_id,
            'p_event': 'workspace_member_added',
            'p_ip_address': None,
            'p_user_agent': None,
            'p_metadata': {
                'space_id': str(space_id),
                'new_member_id': member_data.user_id,
                'role': member_data.role
            }
        }).execute()

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ADD_WORKSPACE_MEMBER_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add workspace member"
        )


@router.delete("/{space_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    space_id: UUID,
    member_user_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Remove member from workspace (requires admin access)."""
    await require_workspace_access(request, space_id, 'admin')

    try:
        result = db.table('space_members') \
            .delete() \
            .eq('space_id', str(space_id)) \
            .eq('user_id', str(member_user_id)) \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        db.rpc('log_auth_event', {
            'p_user_id': user_id,
            'p_event': 'workspace_member_removed',
            'p_ip_address': None,
            'p_user_agent': None,
            'p_metadata': {
                'space_id': str(space_id),
                'removed_member_id': str(member_user_id)
            }
        }).execute()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"REMOVE_WORKSPACE_MEMBER_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove workspace member"
        )
