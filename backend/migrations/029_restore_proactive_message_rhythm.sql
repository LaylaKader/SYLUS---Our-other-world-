-- Restore the owner-approved first-message and follow-up rhythm.
-- The previous stochastic implementation ignored these columns and made
-- proactive messages much less predictable than the settings screen promised.
UPDATE proactive_contact_settings
SET messages_enabled = TRUE,
    min_idle_minutes = 60,
    min_interval_minutes = 15,
    quiet_start = '00:00',
    quiet_end = '00:00',
    last_proactive_at = NULL,
    proactive_cycle_count = 0,
    proactive_pause_until = NULL,
    updated_at = now()
WHERE id = 1;
