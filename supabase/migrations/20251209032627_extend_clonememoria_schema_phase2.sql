/*
  # CloneMemoria Phase 2 - Schema Extensions

  ## Overview
  Extends the CloneMemoria database schema to support:
  - Per-clone AI configuration (LLM, embeddings, TTS providers)
  - Document-based knowledge management with RAG
  - Vector embeddings for semantic search

  ## Schema Changes

  ### 1. Extend `clones` table with AI configuration columns:
     - `llm_provider` (text) - LLM provider selection
     - `llm_model` (text) - Model name override
     - `embedding_provider` (text) - Embeddings provider selection
     - `tts_provider` (text) - TTS provider selection
     - `tts_voice_id` (text) - Voice identifier for TTS
     - `temperature` (numeric) - Generation temperature
     - `max_tokens` (integer) - Maximum tokens to generate

  ### 2. New table `clone_documents`:
     - Stores documents/knowledge base entries for each clone
     - Supports various source types (manual, upload, url, etc.)
     - Full RLS for user isolation

  ### 3. New table `clone_document_chunks`:
     - Stores chunked text segments from documents
     - Includes embedding vectors for semantic search
     - Linked to both clone and parent document
     - RLS enabled for security

  ## Security
  - Row Level Security enabled on all new tables
  - Policies ensure only clone owners can access their data
  - Cascade deletes maintain referential integrity
*/

-- Extend clones table with AI configuration columns
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'llm_provider'
  ) THEN
    ALTER TABLE clones ADD COLUMN llm_provider text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'llm_model'
  ) THEN
    ALTER TABLE clones ADD COLUMN llm_model text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'embedding_provider'
  ) THEN
    ALTER TABLE clones ADD COLUMN embedding_provider text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'tts_provider'
  ) THEN
    ALTER TABLE clones ADD COLUMN tts_provider text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'tts_voice_id'
  ) THEN
    ALTER TABLE clones ADD COLUMN tts_voice_id text;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'temperature'
  ) THEN
    ALTER TABLE clones ADD COLUMN temperature numeric DEFAULT 0.7;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clones' AND column_name = 'max_tokens'
  ) THEN
    ALTER TABLE clones ADD COLUMN max_tokens integer;
  END IF;
END $$;

-- Create clone_documents table
CREATE TABLE IF NOT EXISTS clone_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clone_id uuid NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title text NOT NULL,
  content text NOT NULL,
  source_type text DEFAULT 'manual',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create indexes for clone_documents
CREATE INDEX IF NOT EXISTS idx_clone_documents_clone_id ON clone_documents(clone_id);
CREATE INDEX IF NOT EXISTS idx_clone_documents_user_id ON clone_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_clone_documents_created_at ON clone_documents(created_at);

-- Create clone_document_chunks table
CREATE TABLE IF NOT EXISTS clone_document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clone_id uuid NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES clone_documents(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  content text NOT NULL,
  embedding double precision[],
  created_at timestamptz DEFAULT now()
);

-- Create indexes for clone_document_chunks
CREATE INDEX IF NOT EXISTS idx_clone_document_chunks_clone_id ON clone_document_chunks(clone_id);
CREATE INDEX IF NOT EXISTS idx_clone_document_chunks_document_id ON clone_document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_clone_document_chunks_chunk_index ON clone_document_chunks(document_id, chunk_index);

-- Enable Row Level Security on new tables
ALTER TABLE clone_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE clone_document_chunks ENABLE ROW LEVEL SECURITY;

-- RLS Policies for clone_documents
CREATE POLICY "Users can view own clone documents"
  ON clone_documents FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can create own clone documents"
  ON clone_documents FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can update own clone documents"
  ON clone_documents FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can delete own clone documents"
  ON clone_documents FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

-- RLS Policies for clone_document_chunks
CREATE POLICY "Users can view own clone document chunks"
  ON clone_document_chunks FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM clone_documents
      WHERE clone_documents.id = clone_document_chunks.document_id
      AND clone_documents.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

CREATE POLICY "Users can create own clone document chunks"
  ON clone_document_chunks FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM clone_documents
      WHERE clone_documents.id = clone_document_chunks.document_id
      AND clone_documents.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

CREATE POLICY "Users can delete own clone document chunks"
  ON clone_document_chunks FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM clone_documents
      WHERE clone_documents.id = clone_document_chunks.document_id
      AND clone_documents.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

-- Create trigger for clone_documents updated_at
CREATE TRIGGER update_clone_documents_updated_at
  BEFORE UPDATE ON clone_documents
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();