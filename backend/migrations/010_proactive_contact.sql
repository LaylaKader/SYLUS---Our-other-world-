CREATE TABLE IF NOT EXISTS proactive_contact_settings (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    messages_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    calls_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    quiet_start TIME NOT NULL DEFAULT '23:00',
    quiet_end TIME NOT NULL DEFAULT '08:00',
    min_idle_minutes INTEGER NOT NULL DEFAULT 90 CHECK (min_idle_minutes BETWEEN 15 AND 1440),
    min_interval_minutes INTEGER NOT NULL DEFAULT 240 CHECK (min_interval_minutes BETWEEN 60 AND 10080),
    timezone TEXT NOT NULL DEFAULT 'Asia/Dhaka',
    last_proactive_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO proactive_contact_settings (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;
