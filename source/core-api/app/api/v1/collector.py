"""Mimicry-пути коллектора. Снаружи их закрывает nginx, если нет X-Agent-Token."""

from fastapi import APIRouter

from app.deps import AgentTrap, DbSession
from app.domains.agent import service as agent_service
from app.domains.agent.schemas import AgentEventsBatchIn, AgentHeartbeatIn, AgentHeartbeatOut

router = APIRouter(tags=["collector-mimicry"])


def _noise_Envelope(data: dict) -> dict:
	# шумовые поля, чтобы ответ не выглядел как голый C2
	return {
		"status": "ok",
		"server": "edge-cache",
		"region": "eu-central",
		"trace_id": "0",
		"result": data,
	}


@router.post("/v1/metrics")
def collector_Metrics(db: DbSession, trap: AgentTrap, body: AgentHeartbeatIn) -> dict:
	"""Mimicry heartbeat."""
	out: AgentHeartbeatOut = agent_service.post_Heartbeat(db, trap, body)
	return _noise_Envelope(out.model_dump())


@router.post("/cdn/edge-check")
def collector_EdgeCheck(db: DbSession, trap: AgentTrap, body: AgentHeartbeatIn) -> dict:
	out = agent_service.post_Heartbeat(db, trap, body)
	return _noise_Envelope(out.model_dump())


@router.post("/api/telemetry/batch")
def collector_TelemetryBatch(db: DbSession, trap: AgentTrap, body: AgentEventsBatchIn) -> dict:
	"""Mimicry batch events."""
	out = agent_service.post_Events(db, trap, body)
	return _noise_Envelope(out)
