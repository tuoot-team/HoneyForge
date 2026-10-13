from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.domains.maintenance.schemas import WipeOut

# Сначала дочерние таблицы, потом те, на которые ссылаются.
RESET_TABLES = (
	"trap_commands",
	"pairing_sessions",
	"events",
	"traps",
	"profiles",
	"audit_log",
)
LOG_TABLES = (
	"events",
	"audit_log",
)


def clear_Logs(db: Session) -> WipeOut:
	return WipeOut(deleted=_wipe_Tables(db, LOG_TABLES))


def reset_Database(db: Session) -> WipeOut:
	return WipeOut(deleted=_wipe_Tables(db, RESET_TABLES))


def _wipe_Tables(db: Session, tables: tuple[str, ...]) -> dict[str, int]:
	deleted = {name: _count_Rows(db, name) for name in tables}
	settings = get_Settings()
	if settings.USE_SQLITE:
		for name in tables:
			db.execute(text(f"DELETE FROM {name}"))
		_reset_SqliteSequences(db, tables)
	else:
		joined = ", ".join(tables)
		db.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY"))
	db.commit()
	return deleted


def _count_Rows(db: Session, table: str) -> int:
	value = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
	return int(value or 0)


def _reset_SqliteSequences(db: Session, tables: tuple[str, ...]) -> None:
	exists = db.execute(
		text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'")
	).first()
	if exists is None:
		return
	for name in tables:
		db.execute(text("DELETE FROM sqlite_sequence WHERE name = :name"), {"name": name})
