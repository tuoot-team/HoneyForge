from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_TRAPS_READ, PERM_TRAPS_WRITE
from app.domains.traps import service as trap_service
from app.domains.traps.schemas import TrapBindProfile, TrapOut

router = APIRouter(prefix="/traps", tags=["traps"])


@router.get("/", response_model=list[TrapOut])
def list_Traps(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_READ)),
) -> list[TrapOut]:
	return trap_service.list_Traps(db)


@router.get("/{trap_id}", response_model=TrapOut)
def get_Trap(
	db: DbSession,
	trap_id: UUID,
	_operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_READ)),
) -> TrapOut:
	return trap_service.get_Trap(db, trap_id)


@router.post("/{trap_id}/bind-profile", response_model=TrapOut)
def bind_TrapProfile(
	db: DbSession,
	trap_id: UUID,
	body: TrapBindProfile,
	operator: CurrentUser = Depends(require_Permission(PERM_TRAPS_WRITE)),
) -> TrapOut:
	out = trap_service.bind_TrapProfile(db, trap_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="trap.bind_profile",
		resource_type="trap",
		resource_id=str(trap_id),
		payload={"profile_id": str(body.profile_id)},
	)
	return out
