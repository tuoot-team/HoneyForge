from fastapi import APIRouter

from app.api.v1 import agent, auth, collector, events, health, pairing, profiles, traps

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(profiles.router)
api_v1_router.include_router(traps.router)
api_v1_router.include_router(pairing.router)
api_v1_router.include_router(agent.router)
api_v1_router.include_router(events.router)

# mimicry коллектора на корне приложения монтируется отдельно в main
collector_router = collector.router
