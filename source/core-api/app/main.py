from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router, collector_router
from app.config import get_Settings
from app.db.base import Base
from app.db.session import get_Engine
from app.texts import MSG_DEBUG_BOOT

from app.db import models


def ensure_Schema() -> None:
	"""Создаёт отсутствующие таблицы (SQLite и уже живой Postgres без 002)."""
	Base.metadata.create_all(bind=get_Engine())


@asynccontextmanager
async def lifespan(_app: FastAPI):
	settings = get_Settings()
	if settings.DEBUG:
		print(f"[DEBUG] {MSG_DEBUG_BOOT}; debug={settings.DEBUG}; sqlite={settings.USE_SQLITE}")

	ensure_Schema()
	if settings.DEBUG:
		print("[DEBUG] schema create_all done")

	yield


def create_App() -> FastAPI:
	settings = get_Settings()
	ensure_Schema()
	application = FastAPI(
		title="HoneyForge Control API",
		description=(
			"Конструктор профилей, traps, agent channel, events. Фаза 1.\n\n"
			"**Auth в /docs:**\n"
			"1. `POST /api/v1/auth/login` с паролем из `.env` (`OPERATOR_PASSWORD`)\n"
			"2. Скопировать `access_token`\n"
			"3. Кнопка **Authorize** → вставить токен **без** слова Bearer "
			"(Swagger сам добавит `Authorization: Bearer ...`)\n"
			"4. Вызывать защищённые методы (profiles, traps, events, pairing confirm/list)\n\n"
			"Агент использует заголовок `X-Agent-Token`, не Bearer."
		),
		version="0.1.0",
		lifespan=lifespan,
		debug=settings.DEBUG,
	)
	application.include_router(health_router)
	application.include_router(api_v1_router)
	application.include_router(collector_router)
	# Тот же каталог, что nginx отдаёт как /downloads/. Нужен и для uvicorn без прокси.
	downloads_dir = Path(__file__).resolve().parents[1] / "downloads"
	downloads_dir.mkdir(parents=True, exist_ok=True)
	application.mount(
		"/downloads",
		StaticFiles(directory=str(downloads_dir)),
		name="downloads",
	)
	return application


app = create_App()
