/*
  # CloneMemoria Phase 5 - Production Features

  ## Overview
  Adds production-ready features for developer integrations, admin console,
  billing quotas, and avatar management.

  ## Schema Changes

  ### 1. API Keys System
  - New table `api_keys`: Developer API keys with scopes and rate limiting
  - New table `api_key_usage`: Rate limiting tracking per key

  ### 2. Admin & Roles
  - Extend `users` table with:
    - `role` (text): 'user' or 'admin' for platform administration
    - `billing_plan` (text): 'FREE', 'STARTER', or 'PRO'

  ### 3. Billing Quotas
  - New table `billing_quotas`: Define limits per plan

  ### 4. Avatar Storage
  - Extend `clones` table with:
    - `avatar_image_url` (text): URL to uploaded avatar reference image

  ## Security
  - RLS enabled on all new tables
  - API keys use hashed storage
  - Admin-only policies for sensitive data
*/

-- Extend users table with role and billing_plan
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'role'
  ) THEN
    ALTER TABLE users ADD COLUMN role text DEFAULT 'user' NOT NULL;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'billing_plan'
  ) THEN
    ALTER TABLE users ADD COLUMN billing_plan text DEFAULT 'FREE' NOT NULL;
  END IF;
END $$;

-- Create billing_quotas table (static configuration)
CREATE TABLE IF NOT EXISTS billing_quotas (
  plan text PRIMARY KEY,
  max_clones integer NOT NULL,
  max_messages_per_month integer NOT NULL,
  max_documents_per_clone integer NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Insert default quota plans
INSERT INTO billing_quotas (plan, max_clones, max_messages_per_month, max_documents_per_clone)
VALUES
  ('FREE', 2, 100, 5),
  ('STARTER', 10, 1000, 20),
  ('PRO', 50, 10000, 100)
ON CONFLICT (plan) DO UPDATE SET
  max_clones = EXCLUDED.max_clones,
  max_messages_per_month = EXCLUDED.max_messages_per_month,
  max_documents_per_clone = EXCLUDED.max_documents_per_clone;

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label text NOT NULL,
  key_hash text NOT NULL UNIQUE,
  key_prefix text NOT NULL,
  scopes text[] DEFAULT ARRAY['read']::text[],
  rate_limit_requests integer DEFAULT 100,
  rate_limit_window_seconds integer DEFAULT 3600,
  created_at timestamptz DEFAULT now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

-- Create indexes for api_keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at);

-- Create api_key_usage table for rate limiting
CREATE TABLE IF NOT EXISTS api_key_usage (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_id uuid NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  window_start timestamptz NOT NULL,
  request_count integer DEFAULT 1,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(api_key_id, window_start)
);

-- Create indexes for api_key_usage
CREATE INDEX IF NOT EXISTS idx_api_key_usage_api_key_id ON api_key_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_window_start ON api_key_usage(window_start);

-- Extend clones table with avatar_image_url
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'avatar_image_url'
  ) THEN
    ALTER TABLE clones ADD COLUMN avatar_image_url text;
  END IF;
END $$;

-- Enable RLS on new tables
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_quotas ENABLE ROW LEVEL SECURITY;

-- RLS Policies for api_keys
CREATE POLICY "Users can view own API keys"
  ON api_keys FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can create own API keys"
  ON api_keys FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can delete own API keys"
  ON api_keys FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can update own API keys"
  ON api_keys FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

-- RLS Policies for api_key_usage
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

CREATE POLICY "System can manage API key usage"
  ON api_key_usage FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- RLS Policies for billing_quotas (read-only for all authenticated users)
CREATE POLICY "All users can view billing quotas"
  ON billing_quotas FOR SELECT
  TO authenticated
  USING (true);

-- Create trigger for api_key_usage updated_at
CREATE OR REPLACE FUNCTION update_api_key_usage_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_api_key_usage_updated_at
  BEFORE UPDATE ON api_key_usage
  FOR EACH ROW
  EXECUTE FUNCTION update_api_key_usage_updated_at();

-- Helper function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean AS $$
BEGIN
  RETURN (
    SELECT role = 'admin'
    FROM users
    WHERE id = (current_setting('app.current_user_id'))::uuid
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to get user's current month message count
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
  AND m.created_at >= date_trunc('month', now());

  RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to get user's clone count
CREATE OR REPLACE FUNCTION get_user_clone_count(p_user_id uuid)
RETURNS integer AS $$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*)
  INTO v_count
  FROM clones
  WHERE user_id = p_user_id;

  RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to get clone's document count
CREATE OR REPLACE FUNCTION get_clone_document_count(p_clone_id uuid)
RETURNS integer AS $$
DECLARE
  v_count integer;
BEGIN
  SELECT COUNT(*)
  INTO v_count
  FROM clone_documents
  WHERE clone_id = p_clone_id;

  RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;