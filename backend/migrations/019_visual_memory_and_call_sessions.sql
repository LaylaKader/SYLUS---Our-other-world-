-- Persistent visual reference library and private voice-call records.
CREATE TABLE IF NOT EXISTS visual_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('sylus','owner','other')),
  status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed','pending')),
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO visual_identities (display_name, category, status)
SELECT 'Sylus', 'sylus', 'confirmed'
WHERE NOT EXISTS (SELECT 1 FROM visual_identities WHERE category='sylus');
INSERT INTO visual_identities (display_name, category, status)
SELECT 'Umi / MC', 'owner', 'confirmed'
WHERE NOT EXISTS (SELECT 1 FROM visual_identities WHERE category='owner');

CREATE TABLE IF NOT EXISTS visual_reference_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  identity_id UUID NOT NULL REFERENCES visual_identities(id) ON DELETE CASCADE,
  content_type TEXT NOT NULL CHECK (content_type IN ('image/jpeg','image/png','image/webp')),
  filename TEXT NOT NULL,
  data BYTEA NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','auto')),
  analysis_notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS visual_reference_images_identity_idx
  ON visual_reference_images(identity_id, created_at DESC);

CREATE TABLE IF NOT EXISTS call_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
  transcript JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS call_sessions_started_idx ON call_sessions(started_at DESC);
