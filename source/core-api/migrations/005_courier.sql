-- Курьер: сборщик логов + задания визитов + SSH ловушки.

ALTER TABLE traps
	ADD COLUMN IF NOT EXISTS courier_ssh JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS couriers (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	name            TEXT NOT NULL,
	status          TEXT NOT NULL DEFAULT 'pending',
	agent_token_hash TEXT,
	owner_user_id   UUID REFERENCES users (id) ON DELETE SET NULL,
	last_seen_at    TIMESTAMPTZ,
	meta            JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT couriers_status_check CHECK (status IN ('pending', 'online', 'offline'))
);

CREATE INDEX IF NOT EXISTS idx_couriers_owner_user_id ON couriers (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_couriers_status ON couriers (status);

CREATE TABLE IF NOT EXISTS courier_pairing_sessions (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	device_code      TEXT NOT NULL UNIQUE,
	courier_id      UUID REFERENCES couriers (id) ON DELETE CASCADE,
	status          TEXT NOT NULL DEFAULT 'pending',
	pending_agent_token TEXT,
	expires_at      TIMESTAMPTZ NOT NULL,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	completed_at    TIMESTAMPTZ,
	CONSTRAINT courier_pairing_status_check CHECK (
		status IN ('pending', 'confirmed', 'completed', 'expired')
	)
);

CREATE INDEX IF NOT EXISTS idx_courier_pairing_device_code ON courier_pairing_sessions (device_code);
CREATE INDEX IF NOT EXISTS idx_courier_pairing_status ON courier_pairing_sessions (status);

CREATE TABLE IF NOT EXISTS courier_visits (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	courier_id      UUID REFERENCES couriers (id) ON DELETE SET NULL,
	trap_id         UUID NOT NULL REFERENCES traps (id) ON DELETE CASCADE,
	status          TEXT NOT NULL DEFAULT 'pending',
	scheduled_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	claimed_at      TIMESTAMPTZ,
	finished_at     TIMESTAMPTZ,
	error           TEXT,
	payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT courier_visits_status_check CHECK (
		status IN ('pending', 'claimed', 'succeeded', 'failed')
	)
);

CREATE INDEX IF NOT EXISTS idx_courier_visits_status ON courier_visits (status);
CREATE INDEX IF NOT EXISTS idx_courier_visits_trap_id ON courier_visits (trap_id);
CREATE INDEX IF NOT EXISTS idx_courier_visits_scheduled_at ON courier_visits (scheduled_at);
