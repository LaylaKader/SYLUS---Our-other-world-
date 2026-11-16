-- Persistent artificial emotion and source-aware canon/update ingestion.
-- Apply after 001_initial.sql.

CREATE TABLE IF NOT EXISTS sylus_emotion_state (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    state JSONB NOT NULL DEFAULT
      '{"warmth":0.30,"amusement":0.10,"irritation":0.05,"anger":0.0,"pride":0.10,"concern":0.10,"curiosity":0.25,"affection":0.20,"confidence":0.85,"energy":0.45}'::jsonb,
    dominant_mood TEXT NOT NULL DEFAULT 'composed',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sylus_emotion_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    intensity DOUBLE PRECISION NOT NULL CHECK (intensity >= 0 AND intensity <= 1),
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    provenance TEXT NOT NULL DEFAULT 'application',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    state_after JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sylus_emotion_events_created
    ON sylus_emotion_events(created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    base_url TEXT NOT NULL UNIQUE,
    source_tier TEXT NOT NULL CHECK (
      source_tier IN ('official','secondary','community','private_shared_story')
    ),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    poll_interval_minutes INTEGER NOT NULL DEFAULT 360
      CHECK (poll_interval_minutes >= 15),
    last_checked_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_sync_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running'
      CHECK (status IN ('running','succeeded','failed','partial')),
    items_seen INTEGER NOT NULL DEFAULT 0,
    items_added INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_knowledge_sync_runs_source
    ON knowledge_sync_runs(source_id, started_at DESC);

-- Source metadata for character_knowledge is deliberately explicit.
ALTER TABLE character_knowledge
    ADD COLUMN IF NOT EXISTS source_tier TEXT NOT NULL DEFAULT 'secondary'
      CHECK (source_tier IN ('official','secondary','community','speculation','private_shared_story'));
ALTER TABLE character_knowledge
    ADD COLUMN IF NOT EXISTS retrieved_at TIMESTAMPTZ;
ALTER TABLE character_knowledge
    ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE character_knowledge
    ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION NOT NULL DEFAULT 0.7
      CHECK (confidence >= 0 AND confidence <= 1);
CREATE INDEX IF NOT EXISTS idx_character_knowledge_source_tier
    ON character_knowledge(source_tier);

-- Seed trusted starting points. Community sources remain lower-trust by design.
INSERT INTO knowledge_sources (name, base_url, source_tier, poll_interval_minutes)
VALUES
  ('Love and Deepspace official English news', 'https://loveanddeepspace.infoldgames.com/en-EN/news', 'official', 60),
  ('Love and Deepspace official YouTube', 'https://www.youtube.com/@LoveandDeepspace', 'official', 180),
  ('Love and Deepspace official X', 'https://x.com/Love_Deepspace', 'official', 60),
  ('Love and Deepspace wiki.gg', 'https://loveanddeepspace.wiki.gg/wiki/Love_and_Deepspace_Wiki', 'secondary', 720),
  ('Love and Deepspace Fandom wiki', 'https://loveanddeepspace.fandom.com/wiki/Love_and_Deepspace_Wiki', 'secondary', 720),
  ('Love and Deepspace Reddit', 'https://www.reddit.com/r/LoveAndDeepspace/', 'community', 180)
ON CONFLICT (base_url) DO NOTHING;
