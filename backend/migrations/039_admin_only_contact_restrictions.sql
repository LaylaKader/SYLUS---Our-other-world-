ALTER TABLE proactive_contact_settings
    ADD COLUMN IF NOT EXISTS no_message_until timestamptz,
    ADD COLUMN IF NOT EXISTS no_message_reason text;
