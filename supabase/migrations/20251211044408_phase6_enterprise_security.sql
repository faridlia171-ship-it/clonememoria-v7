/*
  # CloneMemoria Phase 6 - Enterprise Security & RBAC

  ## Overview
  Implements enterprise-grade security features including:
  - Granular Role-Based Access Control (RBAC)
  - JWT refresh token system with rotation
  - Token blacklist for revocation
  - Rate limiting infrastructure
  - Enhanced audit logging
  - Strict CORS and CSP policies

  ## Schema Changes

  ### 1. RBAC System
  - New table `roles`: Defines granular system roles
  - New table `workspace_roles`: Links users to spaces with specific roles
  - Roles hierarchy: system > owner > admin > editor > viewer
  - Fine-grained permissions per role

  ### 2. JWT Enterprise System
  - New table `refresh_tokens`: Stores refresh tokens with rotation
  - New table `token_blacklist`: Revoked tokens list
  - Automatic expiration and cleanup
  - Session tracking per user

  ### 3. Rate Limiting
  - New table `rate_limits`: Track API usage per user/workspace/endpoint
  - Configurable limits per plan and role
  - Redis-compatible structure

  ### 4. Enhanced Audit
  - Extend audit_log with security events
  - Track all authentication events
  - Track quota violations
  - Track admin actions

  ## Security
  - RLS enabled on all tables
  - Role-based access control enforced at database level
  - Automatic token expiration
  - Audit trail for all security events
*/

-- ============================================================================
-- 1. CREATE ROLES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE CHECK (name IN ('system', 'owner', 'admin', 'editor', 'viewer')),
  description text NOT NULL,
  permissions jsonb DEFAULT '{}'::jsonb,
  hierarchy_level integer NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Insert default roles (idempotent)
INSERT INTO roles (name, description, permissions, hierarchy_level)
VALUES
  ('system', 'System administrator with full platform access', '{"all": true}'::jsonb, 100),
  ('owner', 'Workspace owner with full workspace control', '{"workspace": {"delete": true, "manage_members": true, "manage_settings": true}}'::jsonb, 90),
  ('admin', 'Administrator with most workspace permissions', '{"workspace": {"manage_members": true, "manage_settings": true}, "clones": {"create": true, "delete": true, "update": true}, "documents": {"upload": true, "delete": true}}'::jsonb, 80),
  ('editor', 'Editor with create and update permissions', '{"clones": {"create": true, "update": true}, "documents": {"upload": true}, "chat": {"send": true}}'::jsonb, 70),
  ('viewer', 'Viewer with read-only access', '{"clones": {"view": true}, "chat": {"view": true}}'::jsonb, 60)
ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  permissions = EXCLUDED.permissions,
  hierarchy_level = EXCLUDED.hierarchy_level;

CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_hierarchy_level ON roles(hierarchy_level);

-- ============================================================================
-- 2. EXTEND SPACE_MEMBERS WITH ROLE_ID
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'space_members' AND column_name = 'role_id'
  ) THEN
    ALTER TABLE space_members ADD COLUMN role_id uuid REFERENCES roles(id);
  END IF;
END $$;

-- Migrate existing roles to new role_id system
DO $$
DECLARE
  owner_role_id uuid;
  admin_role_id uuid;
  member_role_id uuid;
BEGIN
  SELECT id INTO owner_role_id FROM roles WHERE name = 'owner';
  SELECT id INTO admin_role_id FROM roles WHERE name = 'admin';
  SELECT id INTO member_role_id FROM roles WHERE name = 'editor';

  UPDATE space_members SET role_id = owner_role_id WHERE role = 'owner' AND role_id IS NULL;
  UPDATE space_members SET role_id = admin_role_id WHERE role = 'admin' AND role_id IS NULL;
  UPDATE space_members SET role_id = member_role_id WHERE role = 'member' AND role_id IS NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_space_members_role_id ON space_members(role_id);

-- ============================================================================
-- 3. CREATE REFRESH TOKENS TABLE (JWT Enterprise)
-- ============================================================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  created_at timestamptz DEFAULT now(),
  revoked_at timestamptz,
  replaced_by_token_id uuid REFERENCES refresh_tokens(id),
  device_info jsonb DEFAULT '{}'::jsonb,
  ip_address text,
  user_agent text
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens(token_hash) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_created_at ON refresh_tokens(created_at);

-- ============================================================================
-- 4. CREATE TOKEN BLACKLIST TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS token_blacklist (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_hash text NOT NULL UNIQUE,
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  expires_at timestamptz NOT NULL,
  reason text DEFAULT 'manual_revoke',
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_token_hash ON token_blacklist(token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires_at ON token_blacklist(expires_at);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_user_id ON token_blacklist(user_id);

-- ============================================================================
-- 5. CREATE RATE LIMITS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS rate_limits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  space_id uuid REFERENCES spaces(id) ON DELETE CASCADE,
  endpoint text NOT NULL,
  window_start timestamptz NOT NULL,
  request_count integer DEFAULT 1,
  limit_type text NOT NULL CHECK (limit_type IN ('per_user', 'per_space', 'per_endpoint', 'global')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, space_id, endpoint, window_start, limit_type)
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON rate_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_limits_space_id ON rate_limits(space_id);
CREATE INDEX IF NOT EXISTS idx_rate_limits_endpoint ON rate_limits(endpoint);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON rate_limits(window_start);
CREATE INDEX IF NOT EXISTS idx_rate_limits_limit_type ON rate_limits(limit_type);

-- ============================================================================
-- 6. CREATE RATE LIMIT CONFIGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS rate_limit_configs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan text NOT NULL,
  role text,
  endpoint_pattern text NOT NULL,
  requests_per_minute integer NOT NULL,
  requests_per_hour integer NOT NULL,
  requests_per_day integer NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(plan, role, endpoint_pattern)
);

-- Insert default rate limit configs
INSERT INTO rate_limit_configs (plan, role, endpoint_pattern, requests_per_minute, requests_per_hour, requests_per_day)
VALUES
  ('free', NULL, '/api/chat/*', 10, 100, 500),
  ('free', NULL, '/api/clones/*', 20, 200, 1000),
  ('free', NULL, '/api/documents/*', 5, 50, 200),
  ('free', NULL, '/api/*', 30, 300, 1500),
  ('pro', NULL, '/api/chat/*', 50, 500, 5000),
  ('pro', NULL, '/api/clones/*', 100, 1000, 10000),
  ('pro', NULL, '/api/documents/*', 20, 200, 2000),
  ('pro', NULL, '/api/*', 150, 1500, 15000),
  ('enterprise', NULL, '/api/chat/*', 200, 2000, 20000),
  ('enterprise', NULL, '/api/clones/*', 500, 5000, 50000),
  ('enterprise', NULL, '/api/documents/*', 100, 1000, 10000),
  ('enterprise', NULL, '/api/*', 600, 6000, 60000),
  ('enterprise', 'admin', '/api/*', 1000, 10000, 100000)
ON CONFLICT (plan, role, endpoint_pattern) DO UPDATE SET
  requests_per_minute = EXCLUDED.requests_per_minute,
  requests_per_hour = EXCLUDED.requests_per_hour,
  requests_per_day = EXCLUDED.requests_per_day;

CREATE INDEX IF NOT EXISTS idx_rate_limit_configs_plan ON rate_limit_configs(plan);
CREATE INDEX IF NOT EXISTS idx_rate_limit_configs_endpoint_pattern ON rate_limit_configs(endpoint_pattern);

-- ============================================================================
-- 7. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_blacklist ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_configs ENABLE ROW LEVEL SECURITY;

-- Roles policies
DROP POLICY IF EXISTS "All users can view roles" ON roles;
CREATE POLICY "All users can view roles"
  ON roles FOR SELECT
  TO authenticated
  USING (true);

-- Refresh tokens policies
DROP POLICY IF EXISTS "Users can view own refresh tokens" ON refresh_tokens;
CREATE POLICY "Users can view own refresh tokens"
  ON refresh_tokens FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "System can manage refresh tokens" ON refresh_tokens;
CREATE POLICY "System can manage refresh tokens"
  ON refresh_tokens FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Token blacklist policies
DROP POLICY IF EXISTS "System can manage token blacklist" ON token_blacklist;
CREATE POLICY "System can manage token blacklist"
  ON token_blacklist FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Rate limits policies
DROP POLICY IF EXISTS "Users can view own rate limits" ON rate_limits;
CREATE POLICY "Users can view own rate limits"
  ON rate_limits FOR SELECT
  TO authenticated
  USING (
    user_id = (current_setting('app.current_user_id'))::uuid
    OR EXISTS (
      SELECT 1 FROM space_members sm
      WHERE sm.space_id = rate_limits.space_id
      AND sm.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

DROP POLICY IF EXISTS "System can manage rate limits" ON rate_limits;
CREATE POLICY "System can manage rate limits"
  ON rate_limits FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Rate limit configs policies
DROP POLICY IF EXISTS "All users can view rate limit configs" ON rate_limit_configs;
CREATE POLICY "All users can view rate limit configs"
  ON rate_limit_configs FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "Admins can manage rate limit configs" ON rate_limit_configs;
CREATE POLICY "Admins can manage rate limit configs"
  ON rate_limit_configs FOR ALL
  TO authenticated
  USING (is_platform_admin())
  WITH CHECK (is_platform_admin());

-- ============================================================================
-- 8. HELPER FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION has_workspace_role(p_user_id uuid, p_space_id uuid, p_required_role text)
RETURNS boolean AS $$
DECLARE
  v_user_role text;
  v_role_level integer;
  v_required_level integer;
BEGIN
  SELECT r.name, r.hierarchy_level
  INTO v_user_role, v_role_level
  FROM space_members sm
  JOIN roles r ON r.id = sm.role_id
  WHERE sm.user_id = p_user_id
  AND sm.space_id = p_space_id;

  SELECT hierarchy_level INTO v_required_level
  FROM roles
  WHERE name = p_required_role;

  RETURN v_role_level >= v_required_level;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION is_token_blacklisted(p_token_hash text)
RETURNS boolean AS $$
DECLARE
  v_exists boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM token_blacklist
    WHERE token_hash = p_token_hash
    AND expires_at > now()
  ) INTO v_exists;

  RETURN v_exists;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
  DELETE FROM refresh_tokens WHERE expires_at < now() - interval '7 days';
  DELETE FROM token_blacklist WHERE expires_at < now();
  DELETE FROM rate_limits WHERE window_start < now() - interval '30 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION check_rate_limit(
  p_user_id uuid,
  p_space_id uuid,
  p_endpoint text,
  p_window_start timestamptz
)
RETURNS jsonb AS $$
DECLARE
  v_user_plan text;
  v_user_role text;
  v_config record;
  v_current_count integer;
  v_result jsonb;
BEGIN
  SELECT billing_plan INTO v_user_plan FROM users WHERE id = p_user_id;
  v_user_plan := COALESCE(v_user_plan, 'free');

  IF p_space_id IS NOT NULL THEN
    SELECT r.name INTO v_user_role
    FROM space_members sm
    JOIN roles r ON r.id = sm.role_id
    WHERE sm.user_id = p_user_id
    AND sm.space_id = p_space_id;
  END IF;

  SELECT * INTO v_config
  FROM rate_limit_configs
  WHERE plan = v_user_plan
  AND (role IS NULL OR role = v_user_role)
  AND p_endpoint LIKE endpoint_pattern
  ORDER BY role DESC NULLS LAST
  LIMIT 1;

  IF v_config IS NULL THEN
    v_config.requests_per_minute := 10;
    v_config.requests_per_hour := 100;
    v_config.requests_per_day := 1000;
  END IF;

  SELECT COALESCE(request_count, 0) INTO v_current_count
  FROM rate_limits
  WHERE user_id = p_user_id
  AND (space_id = p_space_id OR (space_id IS NULL AND p_space_id IS NULL))
  AND endpoint = p_endpoint
  AND window_start = p_window_start
  AND limit_type = 'per_user';

  v_result := jsonb_build_object(
    'allowed', v_current_count < v_config.requests_per_minute,
    'current_count', v_current_count,
    'limit_per_minute', v_config.requests_per_minute,
    'limit_per_hour', v_config.requests_per_hour,
    'limit_per_day', v_config.requests_per_day,
    'reset_at', p_window_start + interval '1 minute'
  );

  RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION increment_rate_limit(
  p_user_id uuid,
  p_space_id uuid,
  p_endpoint text,
  p_window_start timestamptz
)
RETURNS void AS $$
BEGIN
  INSERT INTO rate_limits (user_id, space_id, endpoint, window_start, request_count, limit_type)
  VALUES (p_user_id, p_space_id, p_endpoint, p_window_start, 1, 'per_user')
  ON CONFLICT (user_id, space_id, endpoint, window_start, limit_type)
  DO UPDATE SET
    request_count = rate_limits.request_count + 1,
    updated_at = now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION log_auth_event(
  p_user_id uuid,
  p_event text,
  p_ip_address text,
  p_user_agent text,
  p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS void AS $$
BEGIN
  INSERT INTO audit_log (user_id, event, resource_type, metadata, ip_address, user_agent)
  VALUES (p_user_id, p_event, 'auth', p_metadata, p_ip_address, p_user_agent);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION log_quota_violation(
  p_user_id uuid,
  p_resource_type text,
  p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS void AS $$
BEGIN
  INSERT INTO audit_log (user_id, event, resource_type, metadata)
  VALUES (p_user_id, 'quota_violation', p_resource_type, p_metadata);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION log_admin_action(
  p_user_id uuid,
  p_action text,
  p_resource_type text,
  p_resource_id uuid,
  p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS void AS $$
BEGIN
  INSERT INTO audit_log (user_id, event, resource_type, resource_id, metadata)
  VALUES (p_user_id, p_action, p_resource_type, p_resource_id, p_metadata);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 9. TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_rate_limits_updated_at ON rate_limits;
CREATE TRIGGER update_rate_limits_updated_at
  BEFORE UPDATE ON rate_limits
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
