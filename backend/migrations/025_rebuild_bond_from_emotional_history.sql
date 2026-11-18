-- Rebuild relationship metrics using the refined emotional interaction model.
-- Conversation history, call transcripts, saved memories, and character knowledge remain untouched.
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
    summary = 'A beginning. The connection grows through the moments you choose to share.',
    milestones = '[]'::jsonb,
    total_user_messages = 0,
    total_shared_turns = 0,
    progression_started_at = COALESCE(
      (SELECT MIN(created_at) FROM messages WHERE role = 'user' AND archived_at IS NULL),
      now()
    ),
    updated_at = now()
WHERE id = 1;
