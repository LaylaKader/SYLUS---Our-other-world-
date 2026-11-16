CREATE TABLE IF NOT EXISTS provider_acceptances (
  provider TEXT PRIMARY KEY,
  accepted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
