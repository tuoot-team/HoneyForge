from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.deps import CourierAgent, CurrentUser, DbSession, require_Permission
from app.domains.couriers import service as courier_service
from app.domains.couriers.schemas import (
	CourierConfirmIn,
	CourierConfigOut,
	CourierOut,
	CourierPairingCompleteOut,
	CourierPairingListOut,
	CourierPairingStartOut,
	CourierVisitClaimOut,
	CourierVisitCompleteIn,
	DeployCourierIn,
	DeployCourierOut,
)
from app.domains.deploy import service as deploy_service
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import (
	PERM_COURIERS_READ,
	PERM_COURIERS_WRITE,
	PERM_DEPLOY_WRITE,
	PERM_PAIRING_WRITE,
)

router = APIRouter(tags=["couriers"])


@router.get("/couriers/", response_model=list[CourierOut])
def list_Couriers(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_COURIERS_READ)),
) -> list[CourierOut]:
	return courier_service.list_Couriers(db, operator)


@router.get("/couriers/{courier_id}", response_model=CourierOut)
def get_Courier(
	db: DbSession,
	courier_id: UUID,
	operator: CurrentUser = Depends(require_Permission(PERM_COURIERS_READ)),
) -> CourierOut:
	return courier_service.get_Courier(db, operator, courier_id)


@router.get("/courier-pairing/", response_model=CourierPairingListOut)
def list_Courier_Pairings(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_COURIERS_READ)),
	status: str | None = Query(default="pending"),
) -> CourierPairingListOut:
	return courier_service.list_Courier_Pairings(db, status_filter=status)


@router.post("/courier-pairing/start", response_model=CourierPairingStartOut)
def start_Courier_Pairing(db: DbSession) -> CourierPairingStartOut:
	return courier_service.start_Courier_Pairing(db)


@router.post("/courier-pairing/confirm")
def confirm_Courier_Pairing(
	db: DbSession,
	body: CourierConfirmIn,
	operator: CurrentUser = Depends(require_Permission(PERM_PAIRING_WRITE)),
) -> dict:
	out = courier_service.confirm_Courier_Pairing(
		db, body, owner_user_id=operator.id
	)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="courier.pairing.confirm",
		resource_type="courier",
		resource_id=str(out.get("courier_id")),
		payload={"device_code": body.device_code, "name": body.name},
	)
	return out


@router.post(
	"/courier-pairing/{pairing_id}/complete",
	response_model=CourierPairingCompleteOut,
)
def complete_Courier_Pairing(
	db: DbSession, pairing_id: UUID
) -> CourierPairingCompleteOut:
	return courier_service.complete_Courier_Pairing(db, pairing_id)


@router.post("/deploy/courier", response_model=DeployCourierOut)
def deploy_Courier(
	db: DbSession,
	body: DeployCourierIn,
	operator: CurrentUser = Depends(require_Permission(PERM_DEPLOY_WRITE)),
) -> DeployCourierOut:
	out = deploy_service.install_CourierOverSsh(body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="courier.deploy",
		resource_type="courier",
		resource_id=body.host,
		payload={"user": body.user, "port": body.port},
	)
	return out


@router.get("/courier/config", response_model=CourierConfigOut)
def courier_Config(db: DbSession, courier: CourierAgent) -> CourierConfigOut:
	return courier_service.courier_Config(db, courier)


@router.post("/courier/visits/claim", response_model=CourierVisitClaimOut)
def claim_Visit(db: DbSession, courier: CourierAgent) -> CourierVisitClaimOut:
	return courier_service.claim_Visit(db, courier)


@router.post("/courier/visits/{visit_id}/complete")
def complete_Visit(
	db: DbSession,
	visit_id: UUID,
	body: CourierVisitCompleteIn,
	courier: CourierAgent,
) -> dict:
	return courier_service.complete_Visit(db, courier, visit_id, body)
