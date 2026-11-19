-- Track Sylus's side of the relationship independently from Umi's.
ALTER TABLE bond_state
    ADD COLUMN IF NOT EXISTS sylus_affection integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sylus_trust integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS sylus_comfort integer NOT NULL DEFAULT 0;
