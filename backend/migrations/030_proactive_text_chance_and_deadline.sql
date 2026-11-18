-- Configurable chance and hard maximum inactivity for proactive TEXT only.
ALTER TABLE proactive_contact_settings
    ADD COLUMN IF NOT EXISTS chance_percent INTEGER NOT NULL DEFAULT 50;
ALTER TABLE proactive_contact_settings
    ADD COLUMN IF NOT EXISTS max_idle_minutes INTEGER NOT NULL DEFAULT 60;
ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_chance_percent_check;
ALTER TABLE proactive_contact_settings
    ADD CONSTRAINT proactive_contact_settings_chance_percent_check
    CHECK (chance_percent BETWEEN 0 AND 100);
ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_max_idle_minutes_check;
ALTER TABLE proactive_contact_settings
    ADD CONSTRAINT proactive_contact_settings_max_idle_minutes_check
    CHECK (max_idle_minutes BETWEEN 1 AND 1440);
UPDATE proactive_contact_settings
SET chance_percent = 50, max_idle_minutes = 60, updated_at = now()
WHERE id = 1;
