ALTER TABLE proactive_contact_settings
    ADD COLUMN IF NOT EXISTS no_call_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS no_call_reason TEXT;
