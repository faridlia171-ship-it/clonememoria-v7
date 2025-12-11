/*
  # CloneMemoria Database Schema

  ## Overview
  Complete database schema for CloneMemoria - an AI-powered personal clone application
  that allows users to create conversational clones of real people with memories.

  ## Tables Created
  
  1. **users** - Application users
     - id (uuid, primary key)
     - email (text, unique)
     - password_hash (text)
     - full_name (text, optional)
     - created_at (timestamptz)
     - updated_at (timestamptz)

  2. **clones** - AI clones created by users
     - id (uuid, primary key)
     - user_id (uuid, foreign key → users.id)
     - name (text) - Display name like "Papa", "Maman"
     - description (text) - Emotional description of the person
     - tone_config (jsonb) - Configuration for tone: warmth, humor, formality
     - avatar_url (text, optional)
     - created_at (timestamptz)
     - updated_at (timestamptz)

  3. **memories** - Text memories associated with clones
     - id (uuid, primary key)
     - user_id (uuid, foreign key → users.id)
     - clone_id (uuid, foreign key → clones.id)
     - title (text, optional)
     - content (text) - The actual memory text
     - source_type (text) - Type: "manual", "imported_whatsapp", etc.
     - created_at (timestamptz)
     - updated_at (timestamptz)

  4. **conversations** - Chat conversations between user and clone
     - id (uuid, primary key)
     - user_id (uuid, foreign key → users.id)
     - clone_id (uuid, foreign key → clones.id)
     - title (text, optional)
     - created_at (timestamptz)
     - updated_at (timestamptz)

  5. **messages** - Individual messages in conversations
     - id (uuid, primary key)
     - conversation_id (uuid, foreign key → conversations.id)
     - role (text) - "user", "clone", or "system"
     - content (text)
     - metadata (jsonb, optional) - For storing additional info
     - created_at (timestamptz)

  ## Security
  - Row Level Security (RLS) enabled on all tables
  - Policies ensure users can only access their own data
  - Cascade deletes configured for data integrity
  
  ## Indexes
  - Performance indexes on foreign keys and frequently queried columns
*/

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  full_name text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create clones table
CREATE TABLE IF NOT EXISTS clones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text DEFAULT '',
  tone_config jsonb DEFAULT '{"warmth": 0.7, "humor": 0.5, "formality": 0.3}'::jsonb,
  avatar_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  clone_id uuid NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
  title text,
  content text NOT NULL,
  source_type text DEFAULT 'manual',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  clone_id uuid NOT NULL REFERENCES clones(id) ON DELETE CASCADE,
  title text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'clone', 'system')),
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_clones_user_id ON clones(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_clone_id ON memories(clone_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_clone_id ON conversations(clone_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE clones ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  TO authenticated
  USING (id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (id = (current_setting('app.current_user_id'))::uuid);

-- RLS Policies for clones table
CREATE POLICY "Users can view own clones"
  ON clones FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can create own clones"
  ON clones FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can update own clones"
  ON clones FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can delete own clones"
  ON clones FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

-- RLS Policies for memories table
CREATE POLICY "Users can view own memories"
  ON memories FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can create own memories"
  ON memories FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can update own memories"
  ON memories FOR UPDATE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid)
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can delete own memories"
  ON memories FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

-- RLS Policies for conversations table
CREATE POLICY "Users can view own conversations"
  ON conversations FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can create own conversations"
  ON conversations FOR INSERT
  TO authenticated
  WITH CHECK (user_id = (current_setting('app.current_user_id'))::uuid);

CREATE POLICY "Users can delete own conversations"
  ON conversations FOR DELETE
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);

-- RLS Policies for messages table
CREATE POLICY "Users can view messages in own conversations"
  ON messages FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND conversations.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

CREATE POLICY "Users can create messages in own conversations"
  ON messages FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND conversations.user_id = (current_setting('app.current_user_id'))::uuid
    )
  );

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clones_updated_at
  BEFORE UPDATE ON clones
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at
  BEFORE UPDATE ON memories
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
  BEFORE UPDATE ON conversations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();