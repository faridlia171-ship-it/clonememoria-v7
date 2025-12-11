/*
  # CloneMemoria Phase 3 - GDPR Compliance & Billing Infrastructure

  ## Overview
  Extends CloneMemoria with GDPR compliance features, billing infrastructure,
  usage tracking, and soft delete capabilities for production readiness.

  ## Schema Changes

  ### 1. GDPR Consent Management
  Extended `users` table with consent tracking:
  - `consent_data_processing` (boolean, default true) - Required for basic service use
  - `consent_voice_processing` (boolean, default false) - Required for text-to-speech features
  - `consent_video_processing` (boolean, default false) - Required for avatar generation
  - `consent_third_party_apis` (boolean, default false) - Required for external AI providers
  - `consent_whatsapp_ingestion` (boolean, default false) - Future WhatsApp integration
  - `last_data_export_at` (timestamptz) - Tracks when user last exported their data

  ### 2. Billing Infrastructure
  Extended `users` table with billing fields:
  - `billing_plan` (text, default 'free') - Current subscription plan
  - `billing_period_start` (timestamptz) - Billing cycle start date
  - `billing_period_end` (timestamptz) - Billing cycle end date
  - `billing_customer_id` (text) - External billing provider customer ID (e.g., Stripe)
  - `is_platform_admin` (boolean, default false) - Platform administrator flag

  ### 3. Usage Metrics Tracking
  New table `usage_metrics`:
  - Tracks daily usage statistics per user
  - Columns: messages_count, tokens_used, documents_uploaded, clones_created, tts_requests, avatar_requests
  - Unique constraint on (user_id, metric_date) for efficient daily aggregation
  - Enables billing enforcement and analytics

  ### 4. Soft Delete Support
  Added `deleted_at` (timestamptz) column to:
  - `users` - User account deletion
  - `clones` - Clone deletion (preserves history)
  - `memories` - Memory deletion
  - `conversations` - Conversation deletion
  - `messages` - Message deletion
  - `clone_documents` - Document deletion

  ### 5. Enhanced Documents
  Extended `clone_documents` table:
  - `language` (text, default 'en') - Document language for i18n
  - `metadata` (jsonb, default '{}') - Flexible metadata storage

  ## Security
  - RLS enabled on all new tables
  - Consent enforcement at application layer
  - Usage metrics isolated per user
  - Soft deletes preserve audit trail while hiding data
*/

-- ============================================================================
-- 1. EXTEND USERS TABLE - GDPR & BILLING
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'consent_data_processing'
  ) THEN
    ALTER TABLE users ADD COLUMN consent_data_processing boolean DEFAULT true;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'consent_voice_processing'
  ) THEN
    ALTER TABLE users ADD COLUMN consent_voice_processing boolean DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'consent_video_processing'
  ) THEN
    ALTER TABLE users ADD COLUMN consent_video_processing boolean DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'consent_third_party_apis'
  ) THEN
    ALTER TABLE users ADD COLUMN consent_third_party_apis boolean DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'consent_whatsapp_ingestion'
  ) THEN
    ALTER TABLE users ADD COLUMN consent_whatsapp_ingestion boolean DEFAULT false;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'last_data_export_at'
  ) THEN
    ALTER TABLE users ADD COLUMN last_data_export_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'billing_plan'
  ) THEN
    ALTER TABLE users ADD COLUMN billing_plan text DEFAULT 'free';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'billing_period_start'
  ) THEN
    ALTER TABLE users ADD COLUMN billing_period_start timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'billing_period_end'
  ) THEN
    ALTER TABLE users ADD COLUMN billing_period_end timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'billing_customer_id'
  ) THEN
    ALTER TABLE users ADD COLUMN billing_customer_id text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'is_platform_admin'
  ) THEN
    ALTER TABLE users ADD COLUMN is_platform_admin boolean DEFAULT false;
  END IF;
END $$;

-- ============================================================================
-- 2. CREATE USAGE METRICS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS usage_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  metric_date date NOT NULL DEFAULT CURRENT_DATE,
  messages_count integer DEFAULT 0,
  tokens_used integer DEFAULT 0,
  documents_uploaded integer DEFAULT 0,
  clones_created integer DEFAULT 0,
  tts_requests integer DEFAULT 0,
  avatar_requests integer DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_usage_metrics_user_id ON usage_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_date ON usage_metrics(metric_date);

-- ============================================================================
-- 3. ADD SOFT DELETE COLUMNS
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'deleted_at'
  ) THEN
    ALTER TABLE users ADD COLUMN deleted_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'deleted_at'
  ) THEN
    ALTER TABLE clones ADD COLUMN deleted_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'memories' AND column_name = 'deleted_at'
  ) THEN
    ALTER TABLE memories ADD COLUMN deleted_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'conversations' AND column_name = 'deleted_at'
  ) THEN
    ALTER TABLE conversations ADD COLUMN deleted_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'messages' AND column_name = 'deleted_at'
  ) THEN
    ALTER TABLE messages ADD COLUMN deleted_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clone_documents' AND column_name = 'deleted_at'
  ) THEN
    ALTER TABLE clone_documents ADD COLUMN deleted_at timestamptz;
  END IF;
END $$;

-- ============================================================================
-- 4. ENHANCE CLONE DOCUMENTS TABLE
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clone_documents' AND column_name = 'language'
  ) THEN
    ALTER TABLE clone_documents ADD COLUMN language text DEFAULT 'en';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clone_documents' AND column_name = 'metadata'
  ) THEN
    ALTER TABLE clone_documents ADD COLUMN metadata jsonb DEFAULT '{}'::jsonb;
  END IF;
END $$;

-- ============================================================================
-- 5. ROW LEVEL SECURITY FOR USAGE METRICS
-- ============================================================================

ALTER TABLE usage_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own usage metrics" ON usage_metrics;
CREATE POLICY "Users can view own usage metrics"
  ON usage_metrics FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "System can manage usage metrics" ON usage_metrics;
CREATE POLICY "System can manage usage metrics"
  ON usage_metrics FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

DROP POLICY IF EXISTS "System can update usage metrics" ON usage_metrics;
CREATE POLICY "System can update usage metrics"
  ON usage_metrics FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

-- ============================================================================
-- 6. HELPER FUNCTIONS
-- ============================================================================

DROP TRIGGER IF EXISTS update_usage_metrics_updated_at ON usage_metrics;
CREATE TRIGGER update_usage_metrics_updated_at
  BEFORE UPDATE ON usage_metrics
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION is_platform_admin()
RETURNS boolean AS $$
BEGIN
  RETURN (
    SELECT COALESCE(is_platform_admin, false)
    FROM users
    WHERE id = (current_setting('app.current_user_id'))::uuid
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION has_consent(p_user_id uuid, p_consent_type text)
RETURNS boolean AS $$
DECLARE
  v_has_consent boolean;
BEGIN
  CASE p_consent_type
    WHEN 'data_processing' THEN
      SELECT consent_data_processing INTO v_has_consent FROM users WHERE id = p_user_id;
    WHEN 'voice_processing' THEN
      SELECT consent_voice_processing INTO v_has_consent FROM users WHERE id = p_user_id;
    WHEN 'video_processing' THEN
      SELECT consent_video_processing INTO v_has_consent FROM users WHERE id = p_user_id;
    WHEN 'third_party_apis' THEN
      SELECT consent_third_party_apis INTO v_has_consent FROM users WHERE id = p_user_id;
    WHEN 'whatsapp_ingestion' THEN
      SELECT consent_whatsapp_ingestion INTO v_has_consent FROM users WHERE id = p_user_id;
    ELSE
      RETURN false;
  END CASE;

  RETURN COALESCE(v_has_consent, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
