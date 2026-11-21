CREATE TABLE IF NOT EXISTS journal_entries (
    entry_date DATE PRIMARY KEY,
    goals JSONB NOT NULL DEFAULT '[]'::jsonb,
    highlights TEXT NOT NULL DEFAULT '',
    sylus_thoughts TEXT NOT NULL,
    audio_mp3 BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS journal_entries_updated_idx ON journal_entries (entry_date DESC);