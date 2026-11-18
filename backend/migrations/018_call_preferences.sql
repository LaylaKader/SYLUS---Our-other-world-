ALTER TABLE proactive_contact_settings
    ADD COLUMN IF NOT EXISTS no_call_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS no_call_reason TEXT,
    ADD COLUMN IF NOT EXISTS last_call_invite_at TIMESTAMPTZ;

-- The owner previously requested spontaneous calls as an enabled-by-default feature.
UPDATE proactive_contact_settings SET calls_enabled = TRUE WHERE id = 1;
