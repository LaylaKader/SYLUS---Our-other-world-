-- Track a short sequence of proactive messages, then pause before trying again.
ALTER TABLE proactive_contact_settings
    ADD COLUMN IF NOT EXISTS proactive_cycle_count INTEGER NOT NULL DEFAULT 0
        CHECK (proactive_cycle_count BETWEEN 0 AND 3),
    ADD COLUMN IF NOT EXISTS proactive_pause_until TIMESTAMPTZ;
