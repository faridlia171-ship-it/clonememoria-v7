/*
  # CloneMemoria Phase 7 - Strict Multi-Tenant Architecture

  ## Overview
  Transforms the project into true multi-tenant with strict workspace isolation.
  Every resource is scoped to a workspace (space_id), with zero cross-workspace data leakage.

  ## Changes

  ### 1. Helper Functions
  - `user_has_workspace_access(p_space_id, p_required_role)` - Check access
  - `get_user_workspace_role(p_space_id)` - Get user's role
  - `is_workspace_owner(p_space_id)` - Check ownership
  - `get_user_workspaces()` - List user's workspaces

  ### 2. Strict RLS Policies
  Replace all policies to use auth.uid() instead of current_setting()
  Add workspace isolation for all resources

  ### 3. Performance Indexes
  Composite indexes for (space_id, user_id) lookups

  ## Security
  - Zero cross-workspace data access
  - auth.uid() enforcement on all policies
  - Workspace membership required for all operations
  - Owner/admin/member role hierarchy enforced
*/

-- ============================================================================
-- 1. COMPOSITE INDEXES FOR MULTI-TENANT QUERIES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_clones_space_user ON clones(space_id, user_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_space_clone ON memories(space_id, clone_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_space_clone ON conversations(space_id, clone_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_space_conversation ON messages(space_id, conversation_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_space_user ON api_keys(space_id, user_id) WHERE space_id IS NOT NULL;

-- ============================================================================
-- 2. HELPER FUNCTIONS FOR WORKSPACE ACCESS
-- ============================================================================

-- Function: Check if user has access to workspace with minimum role
CREATE OR REPLACE FUNCTION user_has_workspace_access(
  p_space_id uuid,
  p_required_role text DEFAULT 'member'
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_user_role text;
  v_role_hierarchy jsonb := '{"owner": 3, "admin": 2, "member": 1}';
  v_user_level int;
  v_required_level int;
BEGIN
  -- Get user's role in workspace
  SELECT role INTO v_user_role
  FROM space_members
  WHERE space_id = p_space_id
    AND user_id = auth.uid();

  -- If not a member, check if owner of workspace
  IF v_user_role IS NULL THEN
    SELECT 'owner' INTO v_user_role
    FROM spaces
    WHERE id = p_space_id
      AND owner_user_id = auth.uid();
  END IF;

  -- No role found
  IF v_user_role IS NULL THEN
    RETURN false;
  END IF;

  -- Check role hierarchy
  v_user_level := (v_role_hierarchy->>v_user_role)::int;
  v_required_level := (v_role_hierarchy->>p_required_role)::int;

  RETURN v_user_level >= v_required_level;
END;
$$;

-- Function: Get user's role in workspace
CREATE OR REPLACE FUNCTION get_user_workspace_role(p_space_id uuid)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_role text;
BEGIN
  -- Check if owner
  SELECT 'owner' INTO v_role
  FROM spaces
  WHERE id = p_space_id
    AND owner_user_id = auth.uid();

  IF v_role IS NOT NULL THEN
    RETURN v_role;
  END IF;

  -- Check membership
  SELECT role INTO v_role
  FROM space_members
  WHERE space_id = p_space_id
    AND user_id = auth.uid();

  RETURN v_role;
END;
$$;

-- Function: Check if user is workspace owner
CREATE OR REPLACE FUNCTION is_workspace_owner(p_space_id uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM spaces
    WHERE id = p_space_id
      AND owner_user_id = auth.uid()
  );
END;
$$;

-- Function: Get all workspace IDs user has access to
CREATE OR REPLACE FUNCTION get_user_workspaces()
RETURNS TABLE(space_id uuid, role text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  -- Owned workspaces
  SELECT s.id, 'owner'::text
  FROM spaces s
  WHERE s.owner_user_id = auth.uid()

  UNION

  -- Member workspaces
  SELECT sm.space_id, sm.role
  FROM space_members sm
  WHERE sm.user_id = auth.uid();
END;
$$;

-- ============================================================================
-- 3. STRICT RLS POLICIES - SPACES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view spaces they own or are members of" ON spaces;
CREATE POLICY "Users can view spaces they own or are members of"
  ON spaces FOR SELECT
  TO authenticated
  USING (
    owner_user_id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM space_members
      WHERE space_members.space_id = spaces.id
      AND space_members.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can create own spaces" ON spaces;
CREATE POLICY "Users can create own spaces"
  ON spaces FOR INSERT
  TO authenticated
  WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "Space owners can update their spaces" ON spaces;
CREATE POLICY "Space owners can update their spaces"
  ON spaces FOR UPDATE
  TO authenticated
  USING (owner_user_id = auth.uid())
  WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "Space owners can delete their spaces" ON spaces;
CREATE POLICY "Space owners can delete their spaces"
  ON spaces FOR DELETE
  TO authenticated
  USING (owner_user_id = auth.uid());

-- ============================================================================
-- 4. STRICT RLS POLICIES - SPACE MEMBERS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view members of their spaces" ON space_members;
CREATE POLICY "Users can view members of their spaces"
  ON space_members FOR SELECT
  TO authenticated
  USING (
    user_has_workspace_access(space_id, 'member')
  );

DROP POLICY IF EXISTS "Space admins can add members" ON space_members;
CREATE POLICY "Space admins can add members"
  ON space_members FOR INSERT
  TO authenticated
  WITH CHECK (
    user_has_workspace_access(space_id, 'admin')
  );

DROP POLICY IF EXISTS "Space admins can update members" ON space_members;
CREATE POLICY "Space admins can update members"
  ON space_members FOR UPDATE
  TO authenticated
  USING (user_has_workspace_access(space_id, 'admin'))
  WITH CHECK (user_has_workspace_access(space_id, 'admin'));

DROP POLICY IF EXISTS "Space admins can remove members" ON space_members;
CREATE POLICY "Space admins can remove members"
  ON space_members FOR DELETE
  TO authenticated
  USING (
    user_has_workspace_access(space_id, 'admin')
  );

-- ============================================================================
-- 5. STRICT RLS POLICIES - CLONES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own clones" ON clones;
DROP POLICY IF EXISTS "Users can view own personal clones" ON clones;
CREATE POLICY "Users can view own clones"
  ON clones FOR SELECT
  TO authenticated
  USING (
    (is_personal = true AND user_id = auth.uid())
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'member'))
  );

DROP POLICY IF EXISTS "Users can create own clones" ON clones;
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

DROP POLICY IF EXISTS "Users can update own clones" ON clones;
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

DROP POLICY IF EXISTS "Users can delete own clones" ON clones;
CREATE POLICY "Users can delete own clones"
  ON clones FOR DELETE
  TO authenticated
  USING (
    (is_personal = true AND user_id = auth.uid())
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

-- ============================================================================
-- 6. STRICT RLS POLICIES - MEMORIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view memories" ON memories;
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

DROP POLICY IF EXISTS "Users can create memories" ON memories;
CREATE POLICY "Users can create memories"
  ON memories FOR INSERT
  TO authenticated
  WITH CHECK (
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

DROP POLICY IF EXISTS "Users can update memories" ON memories;
CREATE POLICY "Users can update memories"
  ON memories FOR UPDATE
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
  )
  WITH CHECK (
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

DROP POLICY IF EXISTS "Users can delete memories" ON memories;
CREATE POLICY "Users can delete memories"
  ON memories FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM clones
      WHERE clones.id = memories.clone_id
      AND (
        (clones.is_personal = true AND clones.user_id = auth.uid())
        OR
        (clones.space_id IS NOT NULL AND user_has_workspace_access(clones.space_id, 'admin'))
      )
    )
  );

-- ============================================================================
-- 7. STRICT RLS POLICIES - CONVERSATIONS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view conversations" ON conversations;
CREATE POLICY "Users can view conversations"
  ON conversations FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'member'))
  );

DROP POLICY IF EXISTS "Users can create conversations" ON conversations;
CREATE POLICY "Users can create conversations"
  ON conversations FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND (
      space_id IS NULL
      OR
      user_has_workspace_access(space_id, 'member')
    )
  );

DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
CREATE POLICY "Users can update own conversations"
  ON conversations FOR UPDATE
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  )
  WITH CHECK (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

DROP POLICY IF EXISTS "Users can delete own conversations" ON conversations;
CREATE POLICY "Users can delete own conversations"
  ON conversations FOR DELETE
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

-- ============================================================================
-- 8. STRICT RLS POLICIES - MESSAGES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view messages" ON messages;
CREATE POLICY "Users can view messages"
  ON messages FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND (
        conversations.user_id = auth.uid()
        OR
        (conversations.space_id IS NOT NULL AND user_has_workspace_access(conversations.space_id, 'member'))
      )
    )
  );

DROP POLICY IF EXISTS "Users can create messages" ON messages;
CREATE POLICY "Users can create messages"
  ON messages FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND (
        conversations.user_id = auth.uid()
        OR
        (conversations.space_id IS NOT NULL AND user_has_workspace_access(conversations.space_id, 'member'))
      )
    )
  );

-- ============================================================================
-- 9. STRICT RLS POLICIES - API KEYS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own api keys" ON api_keys;
CREATE POLICY "Users can view own api keys"
  ON api_keys FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

DROP POLICY IF EXISTS "Users can create own api keys" ON api_keys;
CREATE POLICY "Users can create own api keys"
  ON api_keys FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND (
      space_id IS NULL
      OR
      user_has_workspace_access(space_id, 'admin')
    )
  );

DROP POLICY IF EXISTS "Users can update own api keys" ON api_keys;
CREATE POLICY "Users can update own api keys"
  ON api_keys FOR UPDATE
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  )
  WITH CHECK (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

DROP POLICY IF EXISTS "Users can delete own api keys" ON api_keys;
CREATE POLICY "Users can delete own api keys"
  ON api_keys FOR DELETE
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

-- ============================================================================
-- 10. STRICT RLS POLICIES - AUDIT LOG
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own audit logs" ON audit_log;
CREATE POLICY "Users can view own audit logs"
  ON audit_log FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

DROP POLICY IF EXISTS "System can create audit logs" ON audit_log;
CREATE POLICY "System can create audit logs"
  ON audit_log FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- ============================================================================
-- 11. STRICT RLS POLICIES - WEBHOOKS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own webhooks" ON webhooks;
CREATE POLICY "Users can view own webhooks"
  ON webhooks FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

DROP POLICY IF EXISTS "Users can create own webhooks" ON webhooks;
CREATE POLICY "Users can create own webhooks"
  ON webhooks FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND (
      space_id IS NULL
      OR
      user_has_workspace_access(space_id, 'admin')
    )
  );

DROP POLICY IF EXISTS "Users can update own webhooks" ON webhooks;
CREATE POLICY "Users can update own webhooks"
  ON webhooks FOR UPDATE
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  )
  WITH CHECK (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

DROP POLICY IF EXISTS "Users can delete own webhooks" ON webhooks;
CREATE POLICY "Users can delete own webhooks"
  ON webhooks FOR DELETE
  TO authenticated
  USING (
    user_id = auth.uid()
    OR
    (space_id IS NOT NULL AND user_has_workspace_access(space_id, 'admin'))
  );

-- ============================================================================
-- 12. GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION user_has_workspace_access(uuid, text) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_workspace_role(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION is_workspace_owner(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_workspaces() TO authenticated;

-- ============================================================================
-- 13. COMMENTS
-- ============================================================================

COMMENT ON FUNCTION user_has_workspace_access IS 'Check if current user has access to workspace with minimum role';
COMMENT ON FUNCTION get_user_workspace_role IS 'Get current user role in workspace (owner, admin, member)';
COMMENT ON FUNCTION is_workspace_owner IS 'Check if current user is workspace owner';
COMMENT ON FUNCTION get_user_workspaces IS 'Get all workspaces current user has access to';

COMMENT ON TABLE spaces IS 'Multi-tenant workspaces for team collaboration';
COMMENT ON TABLE space_members IS 'Workspace membership with role-based access';
COMMENT ON COLUMN clones.space_id IS 'Workspace ID for shared clones, NULL for personal';
COMMENT ON COLUMN clones.is_personal IS 'TRUE for personal clones, FALSE for workspace clones';
