-- SYLUS: simulated emotion, proactive delivery, and source-aware knowledge.
-- Additive migration: preserves the initial schema and existing records.

CREATE TABLE IF NOT EXISTS emotion_states (
  id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  dimensions JSONB NOT NULL DEFAULT '{"calm":0.5,"amusement":0,"happiness":0,"affection":0,"pride":0,"curiosity":0,"concern":0,"irritation":0,"anger":0,"disappointment":0}'::jsonb,
  dominant_mood TEXT NOT NULL DEFAULT 'calm',
  rationale TEXT,
  confidence NUMERIC(3,2) NOT NULL DEFAULT 0.50 CHECK (confidence BETWEEN 0 AND 1),
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO emotion_states (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS emotion_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  previous_state JSONB NOT NULL,
  next_state JSONB NOT NULL,
  trigger_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  trigger_type TEXT NOT NULL,
  rationale TEXT,
  confidence NUMERIC(3,2) NOT NULL DEFAULT 0.50 CHECK (confidence BETWEEN 0 AND 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS emotion_events_created_idx ON emotion_events(created_at DESC);

CREATE TABLE IF NOT EXISTS contact_restrictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel TEXT NOT NULL CHECK (channel IN ('message','call','both')),
  original_wording TEXT NOT NULL,
  starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ends_at TIMESTAMPTZ NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'Asia/Dhaka',
  parse_confidence NUMERIC(3,2) NOT NULL DEFAULT 0.80 CHECK (parse_confidence BETWEEN 0 AND 1),
  lifted_at TIMESTAMPTZ,
  lift_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (ends_at > starts_at)
);
CREATE INDEX IF NOT EXISTS contact_restrictions_active_idx
  ON contact_restrictions(channel, ends_at) WHERE lifted_at IS NULL;

CREATE TABLE IF NOT EXISTS outbound_sequences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trigger_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','sending','sent','cancelled','failed')),
  scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ,
  idempotency_key TEXT NOT NULL UNIQUE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS outbound_sequences_due_idx
  ON outbound_sequences(scheduled_at) WHERE status = 'queued';

CREATE TABLE IF NOT EXISTS outbound_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sequence_id UUID NOT NULL REFERENCES outbound_sequences(id) ON DELETE CASCADE,
  bubble_index SMALLINT NOT NULL CHECK (bubble_index BETWEEN 1 AND 3),
  body TEXT NOT NULL,
  delivery_status TEXT NOT NULL DEFAULT 'queued' CHECK (delivery_status IN ('queued','sent','delivered','failed','cancelled')),
  provider_message_id TEXT,
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(sequence_id, bubble_index)
);
CREATE INDEX IF NOT EXISTS outbound_messages_sequence_idx
  ON outbound_messages(sequence_id, bubble_index);

CREATE TABLE IF NOT EXISTS knowledge_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name TEXT NOT NULL,
  source_class TEXT NOT NULL CHECK (source_class IN ('official','secondary','community','private')),
  base_url TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT true,
  check_interval_minutes INTEGER NOT NULL DEFAULT 1440 CHECK (check_interval_minutes >= 60),
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(base_url)
);

CREATE TABLE IF NOT EXISTS character_knowledge_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  namespace TEXT NOT NULL CHECK (namespace IN ('official','secondary','community','speculation','private')),
  topic TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_id UUID REFERENCES knowledge_sources(id) ON DELETE SET NULL,
  source_title TEXT,
  source_url TEXT NOT NULL,
  publication_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_verified_at TIMESTAMPTZ,
  canon_status TEXT NOT NULL CHECK (canon_status IN ('official','secondary','community','speculation','private','unverified')),
  confidence NUMERIC(3,2) NOT NULL DEFAULT 0.50 CHECK (confidence BETWEEN 0 AND 1),
  language TEXT,
  game_version TEXT,
  event_key TEXT,
  content_hash TEXT,
  supersedes_id UUID REFERENCES character_knowledge_records(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS character_knowledge_records_topic_idx
  ON character_knowledge_records(topic, namespace, fetched_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS character_knowledge_records_source_hash_idx
  ON character_knowledge_records(source_url, content_hash) WHERE content_hash IS NOT NULL;

-- Preserve the original restriction wording and parser metadata on the single-owner preferences row.
ALTER TABLE contact_preferences
  ADD COLUMN IF NOT EXISTS last_restriction_wording TEXT,
  ADD COLUMN IF NOT EXISTS restriction_parse_confidence NUMERIC(3,2)
    CHECK (restriction_parse_confidence IS NULL OR restriction_parse_confidence BETWEEN 0 AND 1);
