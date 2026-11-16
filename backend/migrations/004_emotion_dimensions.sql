-- Extend the original emotion JSON with dimensions used by the current persona model.
UPDATE emotion_states
SET dimensions = dimensions || '{"happiness": 0.18, "disappointment": 0.0}'::jsonb,
    updated_at = now()
WHERE id = 1;
