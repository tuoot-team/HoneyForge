-- HoneyForge schema - фаза 0/1
-- Профили хранят блоки конструктора в JSONB.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS audit_log (
	id              BIGSERIAL PRIMARY KEY,
	actor           TEXT,
	action          TEXT NOT NULL,
	resource_type   TEXT,
	resource_id     TEXT,
	payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profiles (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	name            TEXT NOT NULL,
	description     TEXT NOT NULL DEFAULT '',
	interaction_level TEXT NOT NULL,
	blocks          JSONB NOT NULL DEFAULT '{}'::jsonb,
	config_version  INTEGER NOT NULL DEFAULT 1,
	config_hash     TEXT NOT NULL DEFAULT '',
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT profiles_level_check CHECK (interaction_level IN ('low', 'medium', 'high'))
);

CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles (name);

CREATE TABLE IF NOT EXISTS traps (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	name            TEXT NOT NULL,
	profile_id      UUID REFERENCES profiles (id) ON DELETE SET NULL,
	status          TEXT NOT NULL DEFAULT 'pending',
	agent_token_hash TEXT,
	last_seen_at    TIMESTAMPTZ,
	meta            JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT traps_status_check CHECK (status IN ('pending', 'online', 'offline'))
);

CREATE INDEX IF NOT EXISTS idx_traps_profile_id ON traps (profile_id);
CREATE INDEX IF NOT EXISTS idx_traps_status ON traps (status);

CREATE TABLE IF NOT EXISTS pairing_sessions (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	device_code      TEXT NOT NULL UNIQUE,
	trap_id         UUID REFERENCES traps (id) ON DELETE CASCADE,
	status          TEXT NOT NULL DEFAULT 'pending',
	registration_token_hash TEXT,
	pending_agent_token TEXT,
	expires_at      TIMESTAMPTZ NOT NULL,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	completed_at    TIMESTAMPTZ,
	CONSTRAINT pairing_status_check CHECK (status IN ('pending', 'confirmed', 'completed', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_pairing_device_code ON pairing_sessions (device_code);
CREATE INDEX IF NOT EXISTS idx_pairing_status ON pairing_sessions (status);

CREATE TABLE IF NOT EXISTS events (
	id              BIGSERIAL PRIMARY KEY,
	trap_id         UUID REFERENCES traps (id) ON DELETE SET NULL,
	event_type      TEXT NOT NULL,
	source_ip       TEXT,
	source_port     INTEGER,
	occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_trap_id ON events (trap_id);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_source_ip ON events (source_ip);

CREATE TABLE IF NOT EXISTS trap_commands (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	trap_id         UUID NOT NULL REFERENCES traps (id) ON DELETE CASCADE,
	command_type    TEXT NOT NULL,
	payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
	status          TEXT NOT NULL DEFAULT 'pending',
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	claimed_at      TIMESTAMPTZ,
	CONSTRAINT trap_commands_status_check CHECK (status IN ('pending', 'claimed', 'done'))
);

CREATE INDEX IF NOT EXISTS idx_trap_commands_trap_pending
	ON trap_commands (trap_id, status, created_at);
