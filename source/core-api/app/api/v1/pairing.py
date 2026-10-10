from uuid import UUID

from fastapi import APIRouter, Query

from app.deps import DbSession, Operator
from app.domains.pairing import service as pairing_service
from app.domains.pairing.schemas import (
	PairingCompleteOut,
	PairingConfirmIn,
	PairingListOut,
	PairingStartOut,
)

router = APIRouter(prefix="/pairing", tags=["pairing"])


@router.get("/", response_model=PairingListOut)
def list_Pairings(
	db: DbSession,
	_operator: Operator,
	status: str | None = Query(
		default="pending",
		description="pending|confirmed|completed|expired|all",
	),
) -> PairingListOut:
	return pairing_service.list_Pairings(db, status_filter=status)


@router.post("/start", response_model=PairingStartOut)
def start_Pairing(db: DbSession) -> PairingStartOut:
	return pairing_service.start_Pairing(db)


@router.post("/confirm")
def confirm_Pairing(db: DbSession, _operator: Operator, body: PairingConfirmIn) -> dict:
	return pairing_service.confirm_Pairing(db, body)


@router.post("/{pairing_id}/complete", response_model=PairingCompleteOut)
def complete_Pairing(db: DbSession, pairing_id: UUID) -> PairingCompleteOut:
	return pairing_service.complete_Pairing(db, pairing_id)
