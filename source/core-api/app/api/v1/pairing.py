from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.pairing import service as pairing_service
from app.domains.pairing.schemas import (
	PairingCompleteOut,
	PairingConfirmIn,
	PairingListOut,
	PairingStartOut,
)
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_PAIRING_WRITE, PERM_TRAPS_READ
from app.domains.traps import access as trap_access

router = APIRouter(prefix="/pairing", tags=["pairing"])


@router.get("/", response_model=PairingListOut)
def list_Pairings(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_READ)),
	status: str | None = Query(
		default="pending",
		description="pending|confirmed|completed|expired|all",
	),
) -> PairingListOut:
	visible = trap_access.visible_Trap_Ids(db, operator)
	return pairing_service.list_Pairings(
		db, status_filter=status, visible_trap_ids=visible
	)


@router.post("/start", response_model=PairingStartOut)
def start_Pairing(db: DbSession) -> PairingStartOut:
	return pairing_service.start_Pairing(db)


@router.post("/confirm")
def confirm_Pairing(
	db: DbSession,
	body: PairingConfirmIn,
	operator: CurrentUser = Depends(require_Permission(PERM_PAIRING_WRITE)),
) -> dict:
	out = pairing_service.confirm_Pairing(db, body, owner_user_id=operator.id)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="pairing.confirm",
		resource_type="pairing",
		resource_id=str(body.device_code),
		payload={"trap_name": body.trap_name, "owner_user_id": str(operator.id)},
	)
	return out


@router.post("/{pairing_id}/complete", response_model=PairingCompleteOut)
def complete_Pairing(db: DbSession, pairing_id: UUID) -> PairingCompleteOut:
	return pairing_service.complete_Pairing(db, pairing_id)
