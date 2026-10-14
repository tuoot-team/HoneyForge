"""Идемпотентные патчи схемы для уже живых БД (create_all не делает ALTER)."""

from __future__ import annotations

from sqlalchemy import text

from app.config import get_Settings
from app.db.session import get_Engine


def apply_Schema_Patches() -> None:
	settings = get_Settings()
	engine = get_Engine()
	with engine.begin() as conn:
		if settings.USE_SQLITE:
			_patch_Sqlite(conn)
		else:
			_patch_Postgres(conn)


def _column_Exists_Sqlite(conn, table: str, column: str) -> bool:
	rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
	return any(row[1] == column for row in rows)


def _patch_Sqlite(conn) -> None:
	if not _column_Exists_Sqlite(conn, "traps", "courier_ssh"):
		conn.execute(text("ALTER TABLE traps ADD COLUMN courier_ssh JSON NOT NULL DEFAULT '{}'"))
	if not _column_Exists_Sqlite(conn, "traps", "owner_user_id"):
		conn.execute(text("ALTER TABLE traps ADD COLUMN owner_user_id CHAR(36)"))
	# Таблицы курьера создаст create_all.


def _patch_Postgres(conn) -> None:
	conn.execute(
		text(
			"""
			ALTER TABLE traps
				ADD COLUMN IF NOT EXISTS courier_ssh JSONB NOT NULL DEFAULT '{}'::jsonb
			"""
		)
	)
	conn.execute(
		text(
			"""
			ALTER TABLE traps
				ADD COLUMN IF NOT EXISTS owner_user_id UUID
					REFERENCES users(id) ON DELETE SET NULL
			"""
		)
	)
	conn.execute(
		text("CREATE INDEX IF NOT EXISTS idx_traps_owner_user_id ON traps (owner_user_id)")
	)
	# Таблицы couriers / visits / pairing - create_all; на всякий случай дублируем IF NOT EXISTS.
	conn.execute(
		text(
			"""
			CREATE TABLE IF NOT EXISTS couriers (
				id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
				name TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'pending',
				agent_token_hash TEXT,
				owner_user_id UUID REFERENCES users (id) ON DELETE SET NULL,
				last_seen_at TIMESTAMPTZ,
				meta JSONB NOT NULL DEFAULT '{}'::jsonb,
				created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
				updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
			)
			"""
		)
	)
	conn.execute(
		text(
			"""
			CREATE TABLE IF NOT EXISTS courier_pairing_sessions (
				id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
				device_code TEXT NOT NULL UNIQUE,
				courier_id UUID REFERENCES couriers (id) ON DELETE CASCADE,
				status TEXT NOT NULL DEFAULT 'pending',
				pending_agent_token TEXT,
				expires_at TIMESTAMPTZ NOT NULL,
				created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
				completed_at TIMESTAMPTZ
			)
			"""
		)
	)
	conn.execute(
		text(
			"""
			CREATE TABLE IF NOT EXISTS courier_visits (
				id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
				courier_id UUID REFERENCES couriers (id) ON DELETE SET NULL,
				trap_id UUID NOT NULL REFERENCES traps (id) ON DELETE CASCADE,
				status TEXT NOT NULL DEFAULT 'pending',
				scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
				claimed_at TIMESTAMPTZ,
				finished_at TIMESTAMPTZ,
				error TEXT,
				payload JSONB NOT NULL DEFAULT '{}'::jsonb,
				created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
			)
			"""
		)
	)
	conn.execute(text("CREATE INDEX IF NOT EXISTS idx_couriers_owner_user_id ON couriers (owner_user_id)"))
	conn.execute(text("CREATE INDEX IF NOT EXISTS idx_couriers_status ON couriers (status)"))
	conn.execute(
		text(
			"CREATE INDEX IF NOT EXISTS idx_courier_pairing_device_code "
			"ON courier_pairing_sessions (device_code)"
		)
	)
	conn.execute(
		text(
			"CREATE INDEX IF NOT EXISTS idx_courier_pairing_status "
			"ON courier_pairing_sessions (status)"
		)
	)
	conn.execute(text("CREATE INDEX IF NOT EXISTS idx_courier_visits_status ON courier_visits (status)"))
	conn.execute(text("CREATE INDEX IF NOT EXISTS idx_courier_visits_trap_id ON courier_visits (trap_id)"))
	conn.execute(
		text(
			"CREATE INDEX IF NOT EXISTS idx_courier_visits_scheduled_at "
			"ON courier_visits (scheduled_at)"
		)
	)
