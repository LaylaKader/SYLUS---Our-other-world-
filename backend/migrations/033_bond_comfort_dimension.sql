-- A distinct comfort dimension, separate from trust and emotional safety.
ALTER TABLE bond_state
    ADD COLUMN IF NOT EXISTS comfort integer NOT NULL DEFAULT 10;
