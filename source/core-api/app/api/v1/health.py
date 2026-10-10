from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.config import get_Settings
from app.db.session import get_Engine
from app.texts import MSG_DB_FAIL, MSG_DB_OK, MSG_HEALTH_OK, MSG_REDIS_FAIL, MSG_REDIS_OK

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
	status: str
	debug: bool
	database: str
	redis: str


@router.get("/health", response_model=HealthOut)
def get_Health() -> HealthOut:
	settings = get_Settings()
	db_status = MSG_DB_FAIL
	redis_status = MSG_REDIS_FAIL

	try:
		with get_Engine().connect() as conn:
			conn.execute(text("SELECT 1"))
		db_status = MSG_DB_OK
	except Exception as exc:
		if settings.DEBUG:
			print(f"[DEBUG] db health check failed: {type(exc).__name__}: {exc}")

	try:
		import redis as redis_lib
		client = redis_lib.from_url(
			settings.REDIS_URL,
			socket_connect_timeout=1,
			socket_timeout=1,
		)
		if client.ping():
			redis_status = MSG_REDIS_OK
	except Exception as exc:
		if settings.DEBUG:
			print(f"[DEBUG] redis health check failed: {type(exc).__name__}: {exc}")

	return HealthOut(
		status=MSG_HEALTH_OK,
		debug=settings.DEBUG,
		database=db_status,
		redis=redis_status,
	)
