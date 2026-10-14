from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router, collector_router
from app.config import get_Settings
from app.db.base import Base
from app.db.session import get_Engine, get_SessionFactory
from app.domains.rbac.bootstrap import ensure_Rbac_Bootstrap
from app.texts import MSG_DEBUG_BOOT

from app.db import models  # noqa: F401 - регистрация таблиц


def ensure_Schema() -> None:
	"""Создаёт отсутствующие таблицы (SQLite и уже живой Postgres без миграций)."""
	Base.metadata.create_all(bind=get_Engine())


def bootstrap_Rbac() -> None:
	settings = get_Settings()
	db = get_SessionFactory()()
	try:
		ensure_Rbac_Bootstrap(db, settings)
	finally:
		db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
	settings = get_Settings()
	if settings.DEBUG:
		print(f"[DEBUG] {MSG_DEBUG_BOOT}; debug={settings.DEBUG}; sqlite={settings.USE_SQLITE}")

	ensure_Schema()
	bootstrap_Rbac()
	if settings.DEBUG:
		print("[DEBUG] schema create_all + rbac bootstrap done")

	yield


def create_App() -> FastAPI:
	settings = get_Settings()
	ensure_Schema()
	bootstrap_Rbac()
	application = FastAPI(
		title="HoneyForge Control API",
		description=(
			"Конструктор профилей, traps, agent channel, events.\n\n"
			"**Auth в /docs:**\n"
			"1. `POST /api/v1/auth/login` с `username` + `password` "
			"(bootstrap: `OPERATOR_USERNAME` / `OPERATOR_PASSWORD` из `.env`)\n"
			"2. Скопировать `access_token`\n"
			"3. Кнопка **Authorize** → вставить токен **без** слова Bearer "
			"(Swagger сам добавит `Authorization: Bearer ...`)\n"
			"4. Вызывать защищённые методы; права зависят от роли пользователя\n\n"
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
