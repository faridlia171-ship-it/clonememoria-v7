# Multi-Tenant Architecture Guide

**Version**: 1.0
**Date**: December 11, 2025
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [RLS Security Model](#rls-security-model)
5. [Backend Integration](#backend-integration)
6. [API Usage](#api-usage)
7. [Testing & Validation](#testing--validation)
8. [Migration Path](#migration-path)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

CloneMemoria implements **strict multi-tenant architecture** where:
- Every resource belongs to a **workspace** (called `spaces` in DB)
- **Zero cross-workspace data leakage**
- **Database-enforced isolation** via Row Level Security (RLS)
- **Role-based access** within workspaces (owner, admin, member)
- Support for **personal** and **shared** resources

### Key Features

✅ **Workspace Isolation** - Resources scoped to workspace
✅ **RLS Enforcement** - PostgreSQL-level security
✅ **Role Hierarchy** - owner > admin > member
✅ **Personal Mode** - Clones can be private (is_personal=true)
✅ **Auto Context Injection** - Middleware handles workspace context
✅ **Zero Trust** - All policies use auth.uid(), no session variables

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Request                          │
│            GET /api/clones/123?space_id=456                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  FastAPI Application        │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ WorkspaceContextMiddleware  │
         │ - Extract space_id          │
         │ - Set request.state         │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Route Handler              │
         │  - Validate access          │
         │  - Process request          │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Supabase PostgreSQL        │
         │  - RLS Policies Apply       │
         │  - user_has_workspace_      │
         │    access() called          │
         └─────────────┬───────────────┘
                       │
                       ▼
                 ┌─────────┐
                 │ Response│
                 └─────────┘
```

---

## Database Schema

### Core Tables

#### `spaces` (Workspaces)

```sql
CREATE TABLE spaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL REFERENCES users(id),
  name text NOT NULL,
  description text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  deleted_at timestamptz
);
```

**Columns**:
- `owner_user_id`: User who created the workspace (has full control)
- `name`: Workspace name
- `description`: Optional description

---

#### `space_members` (Workspace Membership)

```sql
CREATE TABLE space_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
  role_id uuid REFERENCES roles(id),
  created_at timestamptz DEFAULT now(),
  UNIQUE(space_id, user_id)
);
```

**Roles**:
- `owner`: Full control (implicit for creator, not stored in space_members)
- `admin`: Can manage members, delete resources
- `member`: Can create and edit content

---

### Resource Tables (with space_id)

All resource tables have `space_id` column:

| Table | space_id | Notes |
|-------|----------|-------|
| `clones` | ✅ | NULL for personal, UUID for shared |
| `memories` | ✅ | Inherits from clone |
| `conversations` | ✅ | Can be personal or workspace |
| `messages` | ✅ | Inherits from conversation |
| `clone_documents` | ✅ | Inherits from clone |
| `api_keys` | ✅ | Can be user-level or workspace-level |
| `webhooks` | ✅ | Can be user-level or workspace-level |
| `audit_log` | ✅ | Tracks workspace activities |
| `safety_events` | ✅ | Safety events scoped to workspace |
| `rate_limits` | ✅ | Rate limits per workspace |

**Personal vs Shared**:
- Personal: `space_id IS NULL` and `is_personal = true`
- Shared: `space_id IS NOT NULL` and `is_personal = false`

---

### Helper Functions

#### `user_has_workspace_access(p_space_id uuid, p_required_role text)`

Check if current user (auth.uid()) has access to workspace with minimum role.

```sql
SELECT user_has_workspace_access('workspace-uuid', 'member');
-- Returns: true/false
```

**Role Hierarchy**:
```
owner (3) >= admin (2) >= member (1)
```

If user has `admin`, they automatically have `member` access.

---

#### `get_user_workspace_role(p_space_id uuid)`

Get user's role in workspace.

```sql
SELECT get_user_workspace_role('workspace-uuid');
-- Returns: 'owner' | 'admin' | 'member' | NULL
```

---

#### `is_workspace_owner(p_space_id uuid)`

Check if user is workspace owner.

```sql
SELECT is_workspace_owner('workspace-uuid');
-- Returns: true/false
```

---

#### `get_user_workspaces()`

Get all workspaces user has access to.

```sql
SELECT * FROM get_user_workspaces();
-- Returns:
-- workspace_id | role
-- uuid1        | owner
-- uuid2        | admin
-- uuid3        | member
```

---

## RLS Security Model

### Principles

1. **Zero Trust**: All policies use `auth.uid()`, never `current_setting()`
2. **Workspace Scoped**: Every query checks workspace membership
3. **Role Enforced**: Actions require minimum role level
4. **No Cross-Workspace**: Resources invisible across workspaces

---

### Example Policies

#### Clones (Personal + Shared)

```sql
-- SELECT: View own personal OR workspace clones (member+)
CREATE POLICY "Users can view own clones"
  ON clones FOR SELECT
  TO authenticated
  USING (
    (is_personal = true AND user_id = auth.uid())
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'member'))
  );

-- INSERT: Create personal OR in workspace (member+)
CREATE POLICY "Users can create own clones"
  ON clones FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND (
      is_personal = true
      OR
      (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'member'))
    )
  );

-- UPDATE: Own personal OR workspace admin+
CREATE POLICY "Users can update own clones"
  ON clones FOR UPDATE
  TO authenticated
  USING (
    (is_personal = true AND user_id = auth.uid())
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  )
  WITH CHECK (
    (is_personal = true AND user_id = auth.uid())
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

-- DELETE: Own personal OR workspace admin+
CREATE POLICY "Users can delete own clones"
  ON clones FOR DELETE
  TO authenticated
  USING (
    (is_personal = true AND user_id = auth.uid())
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );
```

---

#### Memories (Inherit from Clone)

```sql
-- SELECT: Can view if can view parent clone
CREATE POLICY "Users can view memories"
  ON memories FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM clones
      WHERE clones.id = memories.clone_id
      AND (
        (clones.is_personal = true AND clones.user_id = auth.uid())
        OR
        (clones.space_id IS NOT NULL AND user_has_workspace_access(clones.space_id, 'member'))
      )
    )
  );
```

---

#### API Keys (User or Workspace Level)

```sql
-- SELECT: Own keys OR workspace admin
CREATE POLICY "Users can view own api keys"
  ON api_keys FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );
```

---

## Backend Integration

### Middleware

**WorkspaceContextMiddleware** extracts `space_id` from requests and validates access.

```python
# backend/api/workspace_middleware.py

class WorkspaceContextMiddleware(BaseHTTPMiddleware):
    """
    - Extracts space_id from query params or body
    - Sets request.state.space_id
    - Logs workspace context
    """
```

**Added to main.py**:
```python
app.add_middleware(WorkspaceContextMiddleware, enabled=True)
```

---

### Dependencies

#### `get_workspace_id(request)` - Optional

Returns workspace ID or None.

```python
from backend.api.workspace_middleware import get_workspace_id

@router.get("/clones")
async def list_clones(
    request: Request,
    space_id: Optional[UUID] = Depends(get_workspace_id)
):
    # space_id is None for personal, UUID for workspace
    pass
```

---

#### `require_workspace_id(request)` - Required

Raises 400 if workspace ID missing.

```python
from backend.api.workspace_middleware import require_workspace_id

@router.post("/clones")
async def create_clone(
    request: Request,
    space_id: UUID = Depends(require_workspace_id)
):
    # space_id is guaranteed to exist
    pass
```

---

#### `require_workspace_access(request, space_id, role)` - Async

Validates user has minimum role in workspace.

```python
from backend.api.workspace_middleware import require_workspace_access

@router.delete("/clones/{id}")
async def delete_clone(
    id: UUID,
    space_id: UUID,
    request: Request
):
    # Check admin access
    await require_workspace_access(request, space_id, 'admin')

    # Proceed with deletion
    pass
```

**Raises**:
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient role

---

### Workspace Routes

**New endpoint**: `/api/workspaces`

```python
# backend/api/routes/workspaces.py

@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(...)
    """List all workspaces user has access to."""

@router.post("", response_model=WorkspaceResponse)
async def create_workspace(...)
    """Create new workspace (user becomes owner)."""

@router.get("/{space_id}", response_model=WorkspaceResponse)
async def get_workspace(...)
    """Get workspace details (requires member)."""

@router.put("/{space_id}", response_model=WorkspaceResponse)
async def update_workspace(...)
    """Update workspace (requires owner)."""

@router.delete("/{space_id}")
async def delete_workspace(...)
    """Delete workspace (requires owner). Cascades."""

@router.get("/{space_id}/members")
async def list_workspace_members(...)
    """List members (requires member)."""

@router.post("/{space_id}/members")
async def add_workspace_member(...)
    """Add member (requires admin)."""

@router.delete("/{space_id}/members/{user_id}")
async def remove_workspace_member(...)
    """Remove member (requires admin)."""
```

---

## API Usage

### Creating a Workspace

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Team Workspace",
    "description": "Shared workspace for team"
  }'
```

**Response**:
```json
{
  "id": "workspace-uuid",
  "owner_user_id": "user-uuid",
  "name": "My Team Workspace",
  "description": "Shared workspace for team",
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:00:00Z"
}
```

---

### Creating a Workspace Clone

```bash
curl -X POST "http://localhost:8000/api/clones?space_id=workspace-uuid" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Clone",
    "description": "Shared clone for team",
    "is_personal": false
  }'
```

**Note**: `space_id` query parameter is REQUIRED for workspace resources.

---

### Creating a Personal Clone

```bash
curl -X POST "http://localhost:8000/api/clones" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Personal Clone",
    "description": "Private clone",
    "is_personal": true
  }'
```

**Note**: No `space_id` for personal resources.

---

### Adding a Workspace Member

```bash
curl -X POST "http://localhost:8000/api/workspaces/workspace-uuid/members" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "new-user-uuid",
    "role": "member"
  }'
```

**Roles**: `admin`, `member` (owner is implicit)

---

### Listing User's Workspaces

```bash
curl -X GET http://localhost:8000/api/workspaces \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
[
  {
    "id": "workspace-1",
    "name": "Personal Workspace",
    "owner_user_id": "user-uuid",
    ...
  },
  {
    "id": "workspace-2",
    "name": "Team Workspace",
    "owner_user_id": "other-user-uuid",
    ...
  }
]
```

---

## Testing & Validation

### Test Workspace Isolation

```sql
-- As User A (owner of Workspace 1)
SET LOCAL jwt.claims.sub = 'user-a-uuid';

-- Should see Workspace 1 resources
SELECT * FROM clones WHERE space_id = 'workspace-1';
-- Returns: clones in Workspace 1

-- Should NOT see Workspace 2 resources
SELECT * FROM clones WHERE space_id = 'workspace-2';
-- Returns: empty (RLS blocks)
```

---

### Test Role Hierarchy

```sql
-- As User B (member of Workspace 1)
SET LOCAL jwt.claims.sub = 'user-b-uuid';

-- Can view (member+)
SELECT * FROM clones WHERE space_id = 'workspace-1';
-- Returns: clones in Workspace 1

-- Cannot delete (requires admin+)
DELETE FROM clones WHERE id = 'clone-in-workspace-1';
-- ERROR: RLS policy violation
```

---

### Test Cross-Workspace Prevention

```bash
# Create clone in Workspace 1
CLONE_ID=$(curl -X POST "http://localhost:8000/api/clones?space_id=workspace-1" \
  -H "Authorization: Bearer $TOKEN_USER_A" \
  -H "Content-Type: application/json" \
  -d '{"name":"Clone 1"}' | jq -r '.id')

# Try to access from Workspace 2 (should fail)
curl -X GET "http://localhost:8000/api/clones/$CLONE_ID?space_id=workspace-2" \
  -H "Authorization: Bearer $TOKEN_USER_A"

# Response: 404 Not Found (RLS blocks)
```

---

## Migration Path

### Existing Personal Resources

Existing personal clones automatically have:
- `is_personal = true`
- `space_id = NULL`

No migration needed - they remain private.

---

### Migrating to Workspace

1. **Create Workspace**:
```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"My Workspace"}'
```

2. **Move Personal Clone to Workspace**:
```sql
UPDATE clones
SET space_id = 'workspace-uuid',
    is_personal = false
WHERE id = 'personal-clone-uuid'
  AND user_id = auth.uid();
```

3. **Update Related Resources**:
```sql
-- Memories
UPDATE memories
SET space_id = 'workspace-uuid'
WHERE clone_id = 'personal-clone-uuid';

-- Conversations
UPDATE conversations
SET space_id = 'workspace-uuid'
WHERE clone_id = 'personal-clone-uuid';
```

---

## Best Practices

### 1. Always Provide space_id

```python
# ✅ Good
@router.get("/clones/{id}")
async def get_clone(
    id: UUID,
    space_id: UUID,  # Required query param
    request: Request
):
    await require_workspace_access(request, space_id, 'member')
    # ...

# ❌ Bad
@router.get("/clones/{id}")
async def get_clone(
    id: UUID,
    request: Request
):
    # No workspace context - ambiguous
```

---

### 2. Validate Resource Belongs to Workspace

```python
from backend.api.workspace_middleware import validate_workspace_resource

@router.get("/clones/{id}")
async def get_clone(
    id: UUID,
    space_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    # Check user has workspace access
    await require_workspace_access(request, space_id, 'member')

    # Check clone belongs to workspace (prevents cross-workspace access)
    await validate_workspace_resource(space_id, 'clone', id, user_id)

    # Proceed
```

---

### 3. Support Both Personal and Workspace

```python
@router.get("/clones")
async def list_clones(
    request: Request,
    space_id: Optional[UUID] = None,  # Optional
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    if space_id:
        # Workspace clones
        await require_workspace_access(request, space_id, 'member')
        query = db.table('clones').select('*').eq('space_id', str(space_id))
    else:
        # Personal clones
        query = db.table('clones').select('*').eq('user_id', user_id).eq('is_personal', True)

    result = query.execute()
    return result.data
```

---

### 4. Audit Workspace Operations

```python
# Log workspace events
db.rpc('log_auth_event', {
    'p_user_id': user_id,
    'p_event': 'workspace_clone_created',
    'p_ip_address': request.client.host,
    'p_user_agent': request.headers.get('user-agent'),
    'p_metadata': {
        'space_id': str(space_id),
        'clone_id': str(clone_id)
    }
}).execute()
```

---

### 5. Handle Workspace Deletion

Workspace deletion cascades to all resources:
- `ON DELETE CASCADE` on `space_id` foreign keys
- Automatically removes all clones, memories, conversations, etc.
- Irreversible - warn users

```python
@router.delete("/{space_id}")
async def delete_workspace(
    space_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    # Only owner can delete
    await require_workspace_access(request, space_id, 'owner')

    # Count resources before deletion
    clones_result = db.table('clones').select('id', count='exact').eq('space_id', str(space_id)).execute()
    clone_count = clones_result.count or 0

    # Warn if workspace has resources
    if clone_count > 0:
        logger.warning(f"Deleting workspace {space_id} with {clone_count} clones")

    # Delete (cascades)
    db.table('spaces').delete().eq('id', str(space_id)).execute()
```

---

## Troubleshooting

### Issue: "space_id is required"

**Cause**: Missing `space_id` query parameter on workspace endpoint.

**Solution**: Add `?space_id={uuid}` to URL.

```bash
# ❌ Bad
GET /api/clones/123

# ✅ Good
GET /api/clones/123?space_id=workspace-uuid
```

---

### Issue: 403 Forbidden

**Cause**: User doesn't have required role in workspace.

**Check**:
```sql
-- Check user's role
SELECT get_user_workspace_role('workspace-uuid');

-- Check membership
SELECT * FROM space_members
WHERE space_id = 'workspace-uuid'
  AND user_id = 'user-uuid';
```

**Solution**: Add user to workspace or upgrade role.

---

### Issue: 404 Not Found (but resource exists)

**Cause**: Resource belongs to different workspace (RLS blocks).

**Check**:
```sql
-- Check resource's workspace
SELECT id, space_id FROM clones WHERE id = 'clone-uuid';

-- Check if user has access
SELECT user_has_workspace_access('workspace-uuid', 'member');
```

**Solution**: Use correct `space_id` or grant user access.

---

### Issue: Can't see personal clones

**Cause**: Querying with `space_id` when clones are personal.

**Check**:
```sql
SELECT id, is_personal, space_id FROM clones WHERE user_id = 'user-uuid';
```

**Solution**: Query without `space_id` for personal clones.

```bash
# Personal clones
GET /api/clones

# Workspace clones
GET /api/clones?space_id=workspace-uuid
```

---

## Security Checklist

- [x] All tables have RLS enabled
- [x] All policies use `auth.uid()` (not session variables)
- [x] Workspace membership checked on every access
- [x] Role hierarchy enforced
- [x] Cross-workspace access blocked
- [x] Cascade deletion on workspace removal
- [x] Audit logging for workspace operations
- [x] Middleware validates workspace context
- [x] Helper functions use SECURITY DEFINER
- [x] No SQL injection vectors

---

## Performance Optimization

### Indexes

Composite indexes for workspace queries:

```sql
CREATE INDEX idx_clones_space_user ON clones(space_id, user_id) WHERE space_id IS NOT NULL;
CREATE INDEX idx_memories_space_clone ON memories(space_id, clone_id) WHERE space_id IS NOT NULL;
CREATE INDEX idx_conversations_space_clone ON conversations(space_id, clone_id) WHERE space_id IS NOT NULL;
CREATE INDEX idx_messages_space_conversation ON messages(space_id, conversation_id) WHERE space_id IS NOT NULL;
CREATE INDEX idx_api_keys_space_user ON api_keys(space_id, user_id) WHERE space_id IS NOT NULL;
```

### Query Patterns

```sql
-- ✅ Good: Uses composite index
SELECT * FROM clones WHERE space_id = 'uuid' AND user_id = 'uuid';

-- ✅ Good: Uses partial index
SELECT * FROM clones WHERE space_id = 'uuid' AND is_personal = false;

-- ❌ Avoid: Full table scan
SELECT * FROM clones WHERE is_personal = false;
```

---

## Summary

CloneMemoria's multi-tenant architecture provides:

✅ **Strict Isolation**: Zero cross-workspace leakage
✅ **Database Enforced**: RLS at PostgreSQL level
✅ **Role-Based**: owner > admin > member hierarchy
✅ **Flexible**: Personal + shared resources
✅ **Auditable**: Complete operation logging
✅ **Performant**: Optimized indexes
✅ **Secure**: Zero-trust security model

**Status**: ✅ Production Ready

---

**Last Updated**: December 11, 2025
**Migration**: Phase 7 - Strict Multi-Tenant
**Database**: Supabase PostgreSQL
