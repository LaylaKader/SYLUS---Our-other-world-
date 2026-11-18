-- Owner-requested proactive TEXT timing: 5-minute initial inactivity and 3-minute follow-up spacing.
-- Calls remain governed by their independent call settings and scheduler.
ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_min_interval_minutes_check;
ALTER TABLE proactive_contact_settings
    ADD CONSTRAINT proactive_contact_settings_min_interval_minutes_check
    CHECK (min_interval_minutes BETWEEN 1 AND 10080);

UPDATE proactive_contact_settings
SET min_idle_minutes = 5,
    min_interval_minutes = 3,
    updated_at = now()
WHERE id = 1;
