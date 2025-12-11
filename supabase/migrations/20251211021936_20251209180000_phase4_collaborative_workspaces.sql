/*
  # CloneMemoria Phase 4 - Collaborative Workspaces & Enterprise Features

  ## Overview
  Introduces collaborative workspace functionality, allowing teams to share clones,
  conversations, and knowledge bases. Includes audit logging, webhooks, and safety features.

  ## Schema Changes

  ### 1. Spaces System (Collaborative Workspaces)
  
  New table `spaces`:
  - Multi-tenant workspace for teams
  - Each space has an owner and can have multiple members
  - Clones, conversations, and documents can belong to a space
  - Personal clones remain private (is_personal flag)

  New table `space_members`:
  - Links users to spaces with roles (owner, admin, member)
  - Controls access permissions within workspace

  New table `space_invitations`:
  - Manages pending invitations to join spaces
  - Token-based invitation system with expiration
  - Tracks invitation status (pending, accepted, expired, cancelled)

  ### 2. Space Integration
  Extended existing tables with `space_id` column:
  - `clones` - Clones can be shared within a space
  - `memories` - Memories can be shared
  - `conversations` - Conversations can be collaborative
  - `messages` - Messages inherit space context
  - `clone_documents` - Documents can be shared
  - `api_keys` - API keys can be scoped to a space
  - Column `is_personal` added to clones to distinguish personal vs shared

  ### 3. Audit Logging
  New table `audit_log`:
  - Comprehensive activity tracking for compliance
  - Records all significant actions (create, update, delete)
  - Includes user info, IP address, user agent
  - Space-aware for multi-tenant audit trails

  ### 4. Webhook System
  New table `webhooks`:
  - Event-driven integrations for external systems
  - Per-user or per-space webhook configurations
  - Event filtering and secret-based authentication
  - Status tracking and monitoring

  New table `webhook_logs`:
  - Records webhook delivery attempts
  - Captures HTTP status codes and errors
  - Enables debugging and monitoring

  ### 5. Safety & Moderation
  New table `safety_events`:
  - Content moderation event logging
  - Tracks blocked or flagged content
  - Supports compliance and safety monitoring
  - Types: input_blocked, output_blocked, warning, flagged

  ## Security
  - RLS enabled on all new tables
  - Space-based access control
  - Owner/admin/member role hierarchy
  - Audit trail for all sensitive operations
*/

-- ============================================================================
-- 1. CREATE SPACES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS spaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  deleted_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_spaces_owner_user_id ON spaces(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_spaces_deleted_at ON spaces(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- 2. CREATE SPACE MEMBERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS space_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('owner', 'admin', 'member')),
  created_at timestamptz DEFAULT now(),
  UNIQUE(space_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_space_members_space_id ON space_members(space_id);
CREATE INDEX IF NOT EXISTS idx_space_members_user_id ON space_members(user_id);

-- ============================================================================
-- 3. CREATE SPACE INVITATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS space_invitations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  space_id uuid NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
  invited_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email text NOT NULL,
  token text NOT NULL UNIQUE,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
  expires_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'cancelled')),
  created_at timestamptz DEFAULT now(),
  accepted_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_space_invitations_space_id ON space_invitations(space_id);
CREATE INDEX IF NOT EXISTS idx_space_invitations_email ON space_invitations(email);
CREATE INDEX IF NOT EXISTS idx_space_invitations_token ON space_invitations(token) WHERE status = 'pending';

-- ============================================================================
-- 4. EXTEND EXISTING TABLES WITH SPACE_ID
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'space_id'
  ) THEN
    ALTER TABLE clones ADD COLUMN space_id uuid REFERENCES spaces(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'is_personal'
  ) THEN
    ALTER TABLE clones ADD COLUMN is_personal boolean DEFAULT true;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'memories' AND column_name = 'space_id'
  ) THEN
    ALTER TABLE memories ADD COLUMN space_id uuid REFERENCES spaces(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'conversations' AND column_name = 'space_id'
  ) THEN
    ALTER TABLE conversations ADD COLUMN space_id uuid REFERENCES spaces(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'messages' AND column_name = 'space_id'
  ) THEN
    ALTER TABLE messages ADD COLUMN space_id uuid REFERENCES spaces(id) ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clone_documents' AND column_name = 'space_id'
  ) THEN
    ALTER TABLE clone_documents ADD COLUMN space_id uuid REFERENCES spaces(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_clones_space_id ON clones(space_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_space_id ON memories(space_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_space_id ON conversations(space_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_space_id ON messages(space_id) WHERE space_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_clone_documents_space_id ON clone_documents(space_id) WHERE space_id IS NOT NULL;

-- ============================================================================
-- 5. CREATE AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  space_id uuid REFERENCES spaces(id) ON DELETE CASCADE,
  event text NOT NULL,
  resource_type text,
  resource_id uuid,
  metadata jsonb DEFAULT '{}'::jsonb,
  ip_address text,
  user_agent text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_space_id ON audit_log(space_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_event ON audit_log(event);

-- ============================================================================
-- 6. CREATE WEBHOOKS SYSTEM
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhooks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  space_id uuid REFERENCES spaces(id) ON DELETE CASCADE,
  url text NOT NULL,
  secret text NOT NULL,
  events text[] DEFAULT ARRAY[]::text[],
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  last_called_at timestamptz,
  last_status text
);

CREATE INDEX IF NOT EXISTS idx_webhooks_user_id ON webhooks(user_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_space_id ON webhooks(space_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_is_active ON webhooks(is_active) WHERE is_active = true;

CREATE TABLE IF NOT EXISTS webhook_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id uuid NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
  event text NOT NULL,
  payload jsonb NOT NULL,
  status_code integer,
  error_message text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at);

-- ============================================================================
-- 7. CREATE SAFETY EVENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS safety_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  clone_id uuid REFERENCES clones(id) ON DELETE SET NULL,
  space_id uuid REFERENCES spaces(id) ON DELETE CASCADE,
  type text NOT NULL CHECK (type IN ('input_blocked', 'output_blocked', 'warning', 'flagged')),
  reason text NOT NULL,
  content_snippet text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_safety_events_user_id ON safety_events(user_id);
CREATE INDEX IF NOT EXISTS idx_safety_events_clone_id ON safety_events(clone_id);
CREATE INDEX IF NOT EXISTS idx_safety_events_space_id ON safety_events(space_id);
CREATE INDEX IF NOT EXISTS idx_safety_events_type ON safety_events(type);
CREATE INDEX IF NOT EXISTS idx_safety_events_created_at ON safety_events(created_at);

-- ============================================================================
-- 8. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE space_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE space_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety_events ENABLE ROW LEVEL SECURITY;

-- Spaces policies
DROP POLICY IF EXISTS "Users can view spaces they own or are members of" ON spaces;
CREATE POLICY "Users can view spaces they own or are members of"
  ON spaces FOR SELECT
  TO authenticated
  USING (
    owner_user_id = (current_setting('app.current_user_id'))::uuid
    OR EXISTS (
      SELECT 1 FROM space_members
      WHERE space_members.space_id = spaces.id
      AND space_members.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

DROP POLICY IF EXISTS "Users can create own spaces" ON spaces;
CREATE POLICY "Users can create own spaces"
  ON spaces FOR INSERT
  TO authenticated
  WITH CHECK (owner_user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Space owners can update their spaces" ON spaces;
CREATE POLICY "Space owners can update their spaces"
  ON spaces FOR UPDATE
  TO authenticated
  USING (owner_user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (owner_user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Space owners can delete their spaces" ON spaces;
CREATE POLICY "Space owners can delete their spaces"
  ON spaces FOR DELETE
  TO authenticated
  USING (owner_user_id = (current_setting('app.current_user_id'))::uuid);

-- Space members policies
DROP POLICY IF EXISTS "Users can view members of their spaces" ON space_members;
CREATE POLICY "Users can view members of their spaces"
  ON space_members FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM spaces
      WHERE spaces.id = space_members.space_id
      AND (spaces.owner_user_id = (current_setting('app.current_user_id'))::uuid
        OR EXISTS (
          SELECT 1 FROM space_members sm
          WHERE sm.space_id = spaces.id
          AND sm.user_id = (current_setting('app.current_user_id'))::uuid
        ))
    )
  );

DROP POLICY IF EXISTS "Space admins can add members" ON space_members;
CREATE POLICY "Space admins can add members"
  ON space_members FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM space_members sm
      WHERE sm.space_id = space_members.space_id
      AND sm.user_id = (current_setting('app.current_user_id'))::uuid
      AND sm.role IN ('owner', 'admin')
    )
  );

DROP POLICY IF EXISTS "Space admins can remove members" ON space_members;
CREATE POLICY "Space admins can remove members"
  ON space_members FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM space_members sm
      WHERE sm.space_id = space_members.space_id
      AND sm.user_id = (current_setting('app.current_user_id'))::uuid
      AND sm.role IN ('owner', 'admin')
    )
  );

-- Space invitations policies
DROP POLICY IF EXISTS "Users can view invitations for their spaces" ON space_invitations;
CREATE POLICY "Users can view invitations for their spaces"
  ON space_invitations FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM space_members
      WHERE space_members.space_id = space_invitations.space_id
      AND space_members.user_id = (current_setting('app.current_user_id'))::uuid
      AND space_members.role IN ('owner', 'admin')
    )
  );

DROP POLICY IF EXISTS "Space admins can create invitations" ON space_invitations;
CREATE POLICY "Space admins can create invitations"
  ON space_invitations FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM space_members
      WHERE space_members.space_id = space_invitations.space_id
      AND space_members.user_id = (current_setting('app.current_user_id'))::uuid
      AND space_members.role IN ('owner', 'admin')
    )
  );

-- Audit log policies
DROP POLICY IF EXISTS "Users can view own audit logs" ON audit_log;
CREATE POLICY "Users can view own audit logs"
  ON audit_log FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "System can create audit logs" ON audit_log;
CREATE POLICY "System can create audit logs"
  ON audit_log FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Webhooks policies
DROP POLICY IF EXISTS "Users can view own webhooks" ON webhooks;
CREATE POLICY "Users can view own webhooks"
  ON webhooks FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Users can create own webhooks" ON webhooks;
CREATE POLICY "Users can create own webhooks"
  ON webhooks FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Users can update own webhooks" ON webhooks;
CREATE POLICY "Users can update own webhooks"
  ON webhooks FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Users can delete own webhooks" ON webhooks;
CREATE POLICY "Users can delete own webhooks"
  ON webhooks FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

-- Webhook logs policies
DROP POLICY IF EXISTS "Users can view own webhook logs" ON webhook_logs;
CREATE POLICY "Users can view own webhook logs"
  ON webhook_logs FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM webhooks
      WHERE webhooks.id = webhook_logs.webhook_id
      AND webhooks.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

DROP POLICY IF EXISTS "System can create webhook logs" ON webhook_logs;
CREATE POLICY "System can create webhook logs"
  ON webhook_logs FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Safety events policies
DROP POLICY IF EXISTS "Users can view own safety events" ON safety_events;
CREATE POLICY "Users can view own safety events"
  ON safety_events FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Admins can view all safety events" ON safety_events;
CREATE POLICY "Admins can view all safety events"
  ON safety_events FOR SELECT
  TO authenticated
  USING (is_platform_admin());

DROP POLICY IF EXISTS "System can create safety events" ON safety_events;
CREATE POLICY "System can create safety events"
  ON safety_events FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- ============================================================================
-- 9. TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_spaces_updated_at ON spaces;
CREATE TRIGGER update_spaces_updated_at
  BEFORE UPDATE ON spaces
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_webhooks_updated_at ON webhooks;
CREATE TRIGGER update_webhooks_updated_at
  BEFORE UPDATE ON webhooks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
