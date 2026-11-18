-- Owner-approved proactive contact policy: no quiet hours, one-hour message threshold,
-- a few spaced follow-ups per hour, and call invitations at any time.
ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_min_interval_minutes_check;

ALTER TABLE proactive_contact_settings
    ADD CONSTRAINT proactive_contact_settings_min_interval_minutes_check
    CHECK (min_interval_minutes BETWEEN 15 AND 10080);

UPDATE proactive_contact_settings
SET messages_enabled = TRUE,
    calls_enabled = TRUE,
    min_idle_minutes = 60,
    min_interval_minutes = 15,
    quiet_start = '00:00',
    quiet_end = '00:00',
    updated_at = now()
WHERE id = 1;
