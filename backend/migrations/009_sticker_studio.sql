CREATE TABLE IF NOT EXISTS sticker_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  label TEXT NOT NULL DEFAULT 'New sticker',
  content_type TEXT NOT NULL DEFAULT 'image/png',
  filename TEXT NOT NULL,
  data BYTEA NOT NULL,
  is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sticker_assets_created_idx ON sticker_assets (created_at DESC);
