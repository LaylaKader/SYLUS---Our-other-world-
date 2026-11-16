-- Time-awareness and generated-image attachment support.
CREATE TABLE IF NOT EXISTS owner_runtime_context (
  id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  timezone TEXT NOT NULL DEFAULT 'Asia/Dhaka',
  locale TEXT NOT NULL DEFAULT 'en-BD',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO owner_runtime_context (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS last_user_message_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_assistant_message_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS messages_role_created_idx ON messages(role, created_at DESC);

CREATE TABLE IF NOT EXISTS media_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
  media_type TEXT NOT NULL CHECK (media_type IN ('image','audio','video','file')),
  storage_key TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  prompt TEXT,
  provider TEXT,
  generation_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  visibility TEXT NOT NULL DEFAULT 'private' CHECK (visibility = 'private'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS media_attachments_message_idx ON media_attachments(message_id, created_at);

-- A generated image is attached to an assistant message; private storage keys only.
-- Do not store binary image data or public bucket URLs in this database.
