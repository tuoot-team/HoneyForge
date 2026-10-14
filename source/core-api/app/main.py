import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router, collector_router
from app.config import get_Settings
from app.db.base import Base
from app.db.schema_patches import apply_Schema_Patches
from app.db.session import get_Engine, get_SessionFactory
from app.domains.couriers import service as courier_service
from app.domains.rbac.bootstrap import ensure_Rbac_Bootstrap
from app.texts import MSG_DEBUG_BOOT

from app.db import models  # noqa: F401 - регистрация таблиц

_COURIER_SCHEDULER_SEC = 30


async def _courier_Scheduler_Loop() -> None:
	"""Фон: создаёт visit-задания для ловушек в режиме courier."""
	while True:
		try:
			db = get_SessionFactory()()
			try:
				created = courier_service.schedule_Courier_Visits(db)
				settings = get_Settings()
				if settings.DEBUG and created:
					print(f"[DEBUG] courier visits scheduled: {created}")
			finally:
				db.close()
		except Exception as exc:
			settings = get_Settings()
			if settings.DEBUG:
				print(f"[DEBUG] courier scheduler: {exc}")
		await asyncio.sleep(_COURIER_SCHEDULER_SEC)


def ensure_Schema() -> None:
	"""Создаёт отсутствующие таблицы и накатывает ALTER для живых volume."""
	Base.metadata.create_all(bind=get_Engine())
	apply_Schema_Patches()


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

	scheduler_task = asyncio.create_task(_courier_Scheduler_Loop())
	try:
		yield
	finally:
		scheduler_task.cancel()
		try:
			await scheduler_task
		except asyncio.CancelledError:
			pass


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
