from fastapi import APIRouter

from app.deps import AgentTrap, DbSession
from app.domains.agent import service as agent_service
from app.domains.agent.schemas import (
	AgentConfigOut,
	AgentEventsBatchIn,
	AgentHeartbeatIn,
	AgentHeartbeatOut,
)

# Канонические пути; mimicry-алиасы - в collector.py
router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/heartbeat", response_model=AgentHeartbeatOut)
def post_AgentHeartbeat(
	db: DbSession, trap: AgentTrap, body: AgentHeartbeatIn
) -> AgentHeartbeatOut:
	return agent_service.post_Heartbeat(db, trap, body)


@router.get("/config", response_model=AgentConfigOut)
def get_AgentConfig(db: DbSession, trap: AgentTrap) -> AgentConfigOut:
	return agent_service.get_Config(db, trap)


@router.post("/events")
def post_AgentEvents(db: DbSession, trap: AgentTrap, body: AgentEventsBatchIn) -> dict:
	return agent_service.post_Events(db, trap, body)


@router.post("/commands/claim")
def claim_AgentCommand(db: DbSession, trap: AgentTrap) -> dict:
	return agent_service.claim_Command(db, trap)
