from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_TRAPS_READ, PERM_TRAPS_WRITE
from app.domains.traps import service as trap_service
from app.domains.couriers import service as courier_service
from app.domains.couriers.schemas import TrapCourierSshIn
from app.domains.traps.schemas import TrapBindProfile, TrapOut, TrapSetOwner

router = APIRouter(prefix="/traps", tags=["traps"])


@router.get("/", response_model=list[TrapOut])
def list_Traps(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_READ)),
) -> list[TrapOut]:
	return trap_service.list_Traps(db, operator)


@router.get("/{trap_id}", response_model=TrapOut)
def get_Trap(
	db: DbSession,
	trap_id: UUID,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_READ)),
) -> TrapOut:
	return trap_service.get_Trap(db, operator, trap_id)


@router.post("/{trap_id}/bind-profile", response_model=TrapOut)
def bind_TrapProfile(
	db: DbSession,
	trap_id: UUID,
	body: TrapBindProfile,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_WRITE)),
) -> TrapOut:
	out = trap_service.bind_TrapProfile(db, operator, trap_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="trap.bind_profile",
		resource_type="trap",
		resource_id=str(trap_id),
		payload={"profile_id": str(body.profile_id)},
	)
	return out


@router.patch("/{trap_id}/owner", response_model=TrapOut)
def set_Trap_Owner(
	db: DbSession,
	trap_id: UUID,
	body: TrapSetOwner,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_WRITE)),
) -> TrapOut:
	out = trap_service.set_Trap_Owner(db, operator, trap_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="trap.set_owner",
		resource_type="trap",
		resource_id=str(trap_id),
		payload={"user_id": str(body.user_id)},
	)
	return out


@router.post("/{trap_id}/vm/{action}", response_model=TrapOut)
def trap_Vm_Action(
	db: DbSession,
	trap_id: UUID,
	action: str,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_WRITE)),
) -> TrapOut:
	"""action: ensure|start|stop|revert|status → команда vm_* в очередь агента."""
	command_type = f"vm_{action}" if not action.startswith("vm_") else action
	out = trap_service.enqueue_Trap_Vm_Command(db, operator, trap_id, command_type)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="trap.vm_command",
		resource_type="trap",
		resource_id=str(trap_id),
		payload={"command_type": command_type},
	)
	return out


@router.patch("/{trap_id}/courier-ssh")
def set_Trap_Courier_Ssh(
	db: DbSession,
	trap_id: UUID,
	body: TrapCourierSshIn,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_WRITE)),
) -> dict:
	out = courier_service.set_Trap_Courier_Ssh(db, operator, trap_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="trap.set_courier_ssh",
		resource_type="trap",
		resource_id=str(trap_id),
		payload={"host": body.host, "user": body.user, "port": body.port},
	)
	return out
