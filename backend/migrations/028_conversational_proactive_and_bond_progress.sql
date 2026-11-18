-- Make proactive contact feel conversational rather than timer-gated.
-- Five minutes is the minimum spacing; there is no three-message cooldown.
-- Normalize existing rows first: migration 024 intentionally set these values to zero.
UPDATE proactive_contact_settings
SET messages_enabled = TRUE,
    min_idle_minutes = 5,
    min_interval_minutes = 5,
    proactive_cycle_count = 0,
    proactive_pause_until = NULL,
    updated_at = now()
WHERE id = 1;

ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_min_idle_minutes_check;
ALTER TABLE proactive_contact_settings
    ADD CONSTRAINT proactive_contact_settings_min_idle_minutes_check
    CHECK (min_idle_minutes BETWEEN 5 AND 1440);

ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_min_interval_minutes_check;
ALTER TABLE proactive_contact_settings
    ADD CONSTRAINT proactive_contact_settings_min_interval_minutes_check
    CHECK (min_interval_minutes BETWEEN 5 AND 10080);
