-- Recalibrate the relationship without deleting any conversation or saved memory.
-- The old backfill awarded milestones for ordinary banter, lore mentions, and saved-memory rows.
DELETE FROM bond_events;

UPDATE bond_state
SET affection = 0,
    trust = 0,
    familiarity = 0,
    shared_experiences = 0,
    commitment = 0,
    vulnerability = 0,
    emotional_safety = 0,
    consistency = 0,
    bond_points = 0,
    level = 1,
    stage = 'A First Encounter',
    summary = 'A beginning. Neither of you knows yet what this connection may become.',
    milestones = '[]'::jsonb,
    total_user_messages = 0,
    total_shared_turns = 0,
    progression_started_at = COALESCE(
      (SELECT MIN(created_at) FROM messages WHERE role = 'user' AND archived_at IS NULL),
      now()
    ),
    updated_at = now()
WHERE id = 1;

-- The relationship engine now uses probabilistic impulses instead of interval gates.
ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_min_idle_minutes_check;
ALTER TABLE proactive_contact_settings
    DROP CONSTRAINT IF EXISTS proactive_contact_settings_min_interval_minutes_check;

UPDATE proactive_contact_settings
SET min_idle_minutes = 0,
    min_interval_minutes = 0,
    quiet_start = '00:00',
    quiet_end = '00:00',
    proactive_cycle_count = 0,
    proactive_pause_until = NULL,
    last_proactive_at = now(),
    last_call_invite_at = now(),
    updated_at = now()
WHERE id = 1;
