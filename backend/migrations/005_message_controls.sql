ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS archive_reason TEXT,
  ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS messages_active_created_idx
  ON messages(created_at) WHERE archived_at IS NULL;

CREATE TABLE IF NOT EXISTS message_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  previous_body TEXT NOT NULL,
  reason TEXT NOT NULL CHECK (reason IN ('edited')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS message_revisions_message_idx
  ON message_revisions(message_id, created_at DESC);
