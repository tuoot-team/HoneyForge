from fastapi import APIRouter

from app.api.v1 import (
	agent,
	auth,
	collector,
	deploy,
	events,
	fs_packs,
	health,
	maintenance,
	pairing,
	profiles,
	roles,
	traps,
	users,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(roles.router)
api_v1_router.include_router(profiles.router)
api_v1_router.include_router(traps.router)
api_v1_router.include_router(pairing.router)
api_v1_router.include_router(agent.router)
api_v1_router.include_router(events.router)
api_v1_router.include_router(maintenance.router)
api_v1_router.include_router(deploy.router)
api_v1_router.include_router(fs_packs.router)

# mimicry коллектора на корне приложения монтируется отдельно в main
collector_router = collector.router
