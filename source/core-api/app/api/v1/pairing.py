from uuid import UUID

from fastapi import APIRouter

from app.deps import DbSession, Operator
from app.domains.pairing import service as pairing_service
from app.domains.pairing.schemas import PairingCompleteOut, PairingConfirmIn, PairingStartOut

router = APIRouter(prefix="/pairing", tags=["pairing"])


@router.post("/start", response_model=PairingStartOut)
def start_Pairing(db: DbSession) -> PairingStartOut:
	"""Агент запрашивает device_code."""
	return pairing_service.start_Pairing(db)


@router.post("/confirm")
def confirm_Pairing(db: DbSession, _operator: Operator, body: PairingConfirmIn) -> dict:
	"""Оператор подтверждает код в CLI/UI."""
	return pairing_service.confirm_Pairing(db, body)


@router.post("/{pairing_id}/complete", response_model=PairingCompleteOut)
def complete_Pairing(db: DbSession, pairing_id: UUID) -> PairingCompleteOut:
	"""Агент поллит до выдачи agent_token."""
	return pairing_service.complete_Pairing(db, pairing_id)
