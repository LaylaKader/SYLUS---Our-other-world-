-- Restore spontaneous calling by default after the owner requested no call constraints.
-- Future temporary pauses remain available only through explicit Admin instructions.
UPDATE proactive_contact_settings
SET calls_enabled = TRUE,
    no_call_until = NULL,
    no_call_reason = NULL,
    last_call_invite_at = NULL,
    updated_at = now()
WHERE id = 1;
