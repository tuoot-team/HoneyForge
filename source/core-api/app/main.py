from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router, collector_router
from app.config import get_Settings
from app.db.base import Base
from app.db.session import get_Engine
from app.texts import MSG_DEBUG_BOOT

from app.db import models


@asynccontextmanager
async def lifespan(_app: FastAPI):
	settings = get_Settings()
	if settings.DEBUG:
		print(f"[DEBUG] {MSG_DEBUG_BOOT}; debug={settings.DEBUG}; sqlite={settings.USE_SQLITE}")

	if settings.USE_SQLITE:
		Base.metadata.create_all(bind=get_Engine())
		if settings.DEBUG:
			print("[DEBUG] SQLite schema create_all done")

	yield


def ensure_SqliteSchema() -> None:
	settings = get_Settings()
	if settings.USE_SQLITE:
		Base.metadata.create_all(bind=get_Engine())


def create_App() -> FastAPI:
	settings = get_Settings()
	ensure_SqliteSchema()
	application = FastAPI(
		title="HoneyForge Control API",
		description="Конструктор профилей, traps, agent channel, events. Фаза 1.",
		version="0.1.0",
		lifespan=lifespan,
		debug=settings.DEBUG,
	)
	application.include_router(health_router)
	application.include_router(api_v1_router)
	application.include_router(collector_router)
	return application


app = create_App()
