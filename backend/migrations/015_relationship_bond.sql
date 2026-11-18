-- Persistent relationship progression, separate from chat history and artificial mood.
CREATE TABLE IF NOT EXISTS bond_state (
  id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  affection INTEGER NOT NULL DEFAULT 0 CHECK (affection BETWEEN 0 AND 100),
  trust INTEGER NOT NULL DEFAULT 0 CHECK (trust BETWEEN 0 AND 100),
  familiarity INTEGER NOT NULL DEFAULT 0 CHECK (familiarity BETWEEN 0 AND 100),
  shared_experiences INTEGER NOT NULL DEFAULT 0 CHECK (shared_experiences BETWEEN 0 AND 100),
  stage TEXT NOT NULL DEFAULT 'A First Connection',
  summary TEXT NOT NULL DEFAULT 'A connection beginning to take shape.',
  milestones JSONB NOT NULL DEFAULT '[]'::jsonb,
  total_user_messages INTEGER NOT NULL DEFAULT 0,
  total_shared_turns INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO bond_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
CREATE TABLE IF NOT EXISTS bond_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bond_events_created_idx ON bond_events(created_at ASC);
