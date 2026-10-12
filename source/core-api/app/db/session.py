from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_Settings

_engine = None
_SessionLocal = None


def get_Engine():
	global _engine
	if _engine is not None:
		return _engine

	settings = get_Settings()
	connect_args: dict = {}
	if settings.USE_SQLITE:
		connect_args["check_same_thread"] = False
	else:
		connect_args["connect_timeout"] = 2

	_engine = create_engine(
		settings.database_url,
		pool_pre_ping=True,
		connect_args=connect_args,
	)

	if settings.USE_SQLITE:
		@event.listens_for(_engine, "connect")
		def _set_sqlite_fk(dbapi_connection, _connection_record):
			cursor = dbapi_connection.cursor()
			cursor.execute("PRAGMA foreign_keys=ON")
			cursor.close()

	return _engine


def get_SessionFactory():
	global _SessionLocal
	if _SessionLocal is None:
		_SessionLocal = sessionmaker(bind=get_Engine(), autoflush=False, autocommit=False)
	return _SessionLocal


def get_DbSession() -> Generator[Session, None, None]:
	session = get_SessionFactory()()
	try:
		yield session
	finally:
		session.close()


def reset_Engine_ForTests() -> None:
	global _engine, _SessionLocal
	if _engine is not None:
		_engine.dispose()
	_engine = None
	_SessionLocal = None
