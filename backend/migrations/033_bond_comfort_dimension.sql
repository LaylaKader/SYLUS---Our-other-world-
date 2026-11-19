-- A distinct comfort dimension, separate from trust and emotional safety.
ALTER TABLE bond_state
    ADD COLUMN IF NOT EXISTS comfort integer NOT NULL DEFAULT 10;

-- Preserve the existing relationship history when introducing the new meter.
UPDATE bond_state
SET comfort = LEAST(100, 10 + 8 * (
    SELECT count(*) FROM bond_events WHERE event_key LIKE '%:comfort'
))
WHERE id = 1;
