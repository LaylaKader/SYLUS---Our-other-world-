-- Start a cleaner, evidence-based relationship progression from this deployment.
ALTER TABLE bond_state
  ADD COLUMN IF NOT EXISTS progression_started_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Old rules inferred familiarity and shared history from greetings, lore mentions,
-- and message volume. Rebase only these two misleading dimensions.
UPDATE bond_state
SET familiarity = 8,
    shared_experiences = 0,
    updated_at = now()
WHERE id = 1;

-- Remove milestones that were awarded by the overly broad old rules.
DELETE FROM bond_events
WHERE event_key LIKE 'day:%:shared_world'
   OR event_key LIKE 'day:%:shared_media'
   OR event_key LIKE 'day:%:daily_life';
