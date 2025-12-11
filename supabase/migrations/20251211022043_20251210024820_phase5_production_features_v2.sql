/*
  # CloneMemoria Phase 5 - Production Features (v2)

  ## Overview
  Adds production-ready features for developer integrations, admin console,
  billing quotas, and avatar management. This version is compatible with Supabase
  and uses is_platform_admin instead of a custom role column.

  ## Schema Changes

  ### 1. API Keys System
  - New table `api_keys`: Developer API keys with scopes and rate limiting
  - New table `api_key_usage`: Rate limiting tracking per key
  - Space-aware API keys for workspace integrations

  ### 2. Admin Access
  - Uses `is_platform_admin` (from Phase 3) for platform administration
  - No custom role column to avoid conflicts with Supabase Auth

  ### 3. Billing Quotas
  - New table `billing_quotas`: Define limits per plan (free, pro, enterprise)
  - Helper functions for quota enforcement

  ### 4. Avatar Storage
  - Extend `clones` table with `avatar_image_url` for reference images

  ## Security
  - RLS enabled on all new tables
  - API keys use hashed storage (never store plain keys)
  - Admin-only policies for sensitive data using is_platform_admin
*/

-- ============================================================================
-- 1. CREATE API KEYS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  space_id uuid REFERENCES spaces(id) ON DELETE CASCADE,
  name text NOT NULL,
  key_hash text NOT NULL UNIQUE,
  key_prefix text NOT NULL,
  scopes text[] DEFAULT ARRAY[]::text[],
  created_at timestamptz DEFAULT now(),
  last_used_at timestamptz,
  expires_at timestamptz,
  revoked_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_space_id ON api_keys(space_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at);

-- ============================================================================
-- 2. CREATE API KEY USAGE TABLE (Rate Limiting)
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_key_usage (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_id uuid NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  window_start timestamptz NOT NULL,
  request_count integer DEFAULT 1,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(api_key_id, window_start)
);

CREATE INDEX IF NOT EXISTS idx_api_key_usage_api_key_id ON api_key_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_window_start ON api_key_usage(window_start);

-- ============================================================================
-- 3. CREATE BILLING QUOTAS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS billing_quotas (
  plan text PRIMARY KEY,
  max_clones integer NOT NULL,
  max_messages_per_month integer NOT NULL,
  max_documents_per_clone integer NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Insert default quota plans (idempotent)
INSERT INTO billing_quotas (plan, max_clones, max_messages_per_month, max_documents_per_clone)
VALUES
  ('free', 2, 100, 5),
  ('pro', 10, 1000, 20),
  ('enterprise', 50, 10000, 100)
ON CONFLICT (plan) DO UPDATE SET
  max_clones = EXCLUDED.max_clones,
  max_messages_per_month = EXCLUDED.max_messages_per_month,
  max_documents_per_clone = EXCLUDED.max_documents_per_clone;

-- ============================================================================
-- 4. EXTEND CLONES TABLE WITH AVATAR IMAGE URL
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'avatar_image_url'
  ) THEN
    ALTER TABLE clones ADD COLUMN avatar_image_url text;
  END IF;
END $$;

-- ============================================================================
-- 5. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_quotas ENABLE ROW LEVEL SECURITY;

-- API Keys policies
DROP POLICY IF EXISTS "Users can view own API keys" ON api_keys;
CREATE POLICY "Users can view own API keys"
  ON api_keys FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Users can create own API keys" ON api_keys;
CREATE POLICY "Users can create own API keys"
  ON api_keys FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Users can delete own API keys" ON api_keys;
CREATE POLICY "Users can delete own API keys"
  ON api_keys FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "Users can update own API keys" ON api_keys;
CREATE POLICY "Users can update own API keys"
  ON api_keys FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

-- API Key Usage policies
DROP POLICY IF EXISTS "Users can view own API key usage" ON api_key_usage;
CREATE POLICY "Users can view own API key usage"
  ON api_key_usage FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM api_keys
      WHERE api_keys.id = api_key_usage.api_key_id
      AND api_keys.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

DROP POLICY IF EXISTS "System can manage API key usage" ON api_key_usage;
CREATE POLICY "System can manage API key usage"
  ON api_key_usage FOR INSERT
  TO authenticated
  WITH CHECK (true);

DROP POLICY IF EXISTS "System can update API key usage" ON api_key_usage;
CREATE POLICY "System can update API key usage"
  ON api_key_usage FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Billing Quotas policies (read-only for authenticated users)
DROP POLICY IF EXISTS "All users can view billing quotas" ON billing_quotas;
CREATE POLICY "All users can view billing quotas"
  ON billing_quotas FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "Admins can manage billing quotas" ON billing_quotas;
CREATE POLICY "Admins can manage billing quotas"
  ON billing_quotas FOR ALL
  TO authenticated
  USING (is_platform_admin())
  WITH CHECK (is_platform_admin());

-- ============================================================================
-- 6. TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_api_key_usage_updated_at ON api_key_usage;
CREATE TRIGGER update_api_key_usage_updated_at
  BEFORE UPDATE ON api_key_usage
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 7. HELPER FUNCTIONS FOR QUOTA MANAGEMENT
-- ============================================================================

-- Get user's current month message count
CREATE OR REPLACE FUNCTION get_user_message_count_this_month(p_user_id uuid)
RETURNS integer AS $$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*)
  INTO v_count
  FROM messages m
  JOIN conversations c ON c.id = m.conversation_id
  WHERE c.user_id = p_user_id
  AND m.created_at >= date_trunc('month', now())
  AND m.deleted_at IS NULL;

  RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get user's clone count
CREATE OR REPLACE FUNCTION get_user_clone_count(p_user_id uuid)
RETURNS integer AS $$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*)
  INTO v_count
  FROM clones
  WHERE user_id = p_user_id
  AND deleted_at IS NULL;

  RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get clone's document count
CREATE OR REPLACE FUNCTION get_clone_document_count(p_clone_id uuid)
RETURNS integer AS $$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*)
  INTO v_count
  FROM clone_documents
  WHERE clone_id = p_clone_id
  AND deleted_at IS NULL;

  RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if user can create more clones
CREATE OR REPLACE FUNCTION can_create_clone(p_user_id uuid)
RETURNS boolean AS $$
DECLARE
  v_current_plan text;
  v_max_clones integer;
  v_current_count integer;
BEGIN
  SELECT billing_plan INTO v_current_plan FROM users WHERE id = p_user_id;
  SELECT max_clones INTO v_max_clones FROM billing_quotas WHERE plan = COALESCE(v_current_plan, 'free');
  SELECT get_user_clone_count(p_user_id) INTO v_current_count;

  RETURN v_current_count < v_max_clones;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if user can send more messages this month
CREATE OR REPLACE FUNCTION can_send_message(p_user_id uuid)
RETURNS boolean AS $$
DECLARE
  v_current_plan text;
  v_max_messages integer;
  v_current_count integer;
BEGIN
  SELECT billing_plan INTO v_current_plan FROM users WHERE id = p_user_id;
  SELECT max_messages_per_month INTO v_max_messages FROM billing_quotas WHERE plan = COALESCE(v_current_plan, 'free');
  SELECT get_user_message_count_this_month(p_user_id) INTO v_current_count;

  RETURN v_current_count < v_max_messages;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if clone can have more documents
CREATE OR REPLACE FUNCTION can_add_document(p_clone_id uuid)
RETURNS boolean AS $$
DECLARE
  v_user_id uuid;
  v_current_plan text;
  v_max_documents integer;
  v_current_count integer;
BEGIN
  SELECT user_id INTO v_user_id FROM clones WHERE id = p_clone_id;
  SELECT billing_plan INTO v_current_plan FROM users WHERE id = v_user_id;
  SELECT max_documents_per_clone INTO v_max_documents FROM billing_quotas WHERE plan = COALESCE(v_current_plan, 'free');
  SELECT get_clone_document_count(p_clone_id) INTO v_current_count;

  RETURN v_current_count < v_max_documents;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
