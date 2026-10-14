-- Пользователи и роли операторского API (фаза 4b).

CREATE TABLE IF NOT EXISTS roles (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	name            TEXT NOT NULL UNIQUE,
	is_system       BOOLEAN NOT NULL DEFAULT FALSE,
	permissions     JSONB NOT NULL DEFAULT '[]'::jsonb,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
	id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	username        TEXT NOT NULL UNIQUE,
	password_hash   TEXT NOT NULL,
	is_superadmin   BOOLEAN NOT NULL DEFAULT FALSE,
	disabled        BOOLEAN NOT NULL DEFAULT FALSE,
	role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
	created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_role_id ON users (role_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
