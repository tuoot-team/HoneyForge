from fastapi import APIRouter
from fastapi.responses import Response

from app.deps import AgentTrap, DbSession
from app.domains.agent import service as agent_service
from app.domains.agent.schemas import (
	AgentConfigOut,
	AgentEventsBatchIn,
	AgentHeartbeatIn,
	AgentHeartbeatOut,
)
from app.domains.fs_packs import service as fs_packs_service
from app.domains.vm_images import service as vm_images_service

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


@router.get("/fs-packs/{token}")
def get_AgentFsPack(db: DbSession, trap: AgentTrap, token: str) -> Response:
	# Агент качает архив целиком; trap нужен только для auth заголовка
	_ = trap
	fs_packs_service.get_FsPackRow(db, token)
	raw = fs_packs_service.read_PackBytes(token)
	return Response(content=raw, media_type="application/octet-stream")


@router.get("/vm-images/{token}")
def get_AgentVmImage(db: DbSession, trap: AgentTrap, token: str):
	from fastapi.responses import FileResponse

	_ = trap
	row = vm_images_service.get_VmImageRow(db, token)
	path = vm_images_service.image_FilePath_Or404(token)
	return FileResponse(
		path,
		filename=row.original_filename or f"{token}.{row.format}",
		media_type="application/octet-stream",
	)


@router.post("/events")
def post_AgentEvents(db: DbSession, trap: AgentTrap, body: AgentEventsBatchIn) -> dict:
	return agent_service.post_Events(db, trap, body)


@router.post("/commands/claim")
def claim_AgentCommand(db: DbSession, trap: AgentTrap) -> dict:
	return agent_service.claim_Command(db, trap)


@router.post("/commands/{command_id}/ack")
def ack_AgentCommand(db: DbSession, trap: AgentTrap, command_id: str, body: dict) -> dict:
	return agent_service.ack_Command(db, trap, command_id, body or {})
