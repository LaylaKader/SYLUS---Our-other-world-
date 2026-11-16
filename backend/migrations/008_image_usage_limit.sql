ALTER TABLE media_assets
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'upload'
  CHECK (source IN ('upload','generated'));

CREATE INDEX IF NOT EXISTS media_assets_generated_created_idx
  ON media_assets(created_at DESC) WHERE source = 'generated';
