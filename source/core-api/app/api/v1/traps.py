from uuid import UUID

from fastapi import APIRouter

from app.deps import DbSession, Operator
from app.domains.traps import service as trap_service
from app.domains.traps.schemas import TrapBindProfile, TrapOut

router = APIRouter(prefix="/traps", tags=["traps"])


@router.get("/", response_model=list[TrapOut])
def list_Traps(db: DbSession, _operator: Operator) -> list[TrapOut]:
	return trap_service.list_Traps(db)


@router.get("/{trap_id}", response_model=TrapOut)
def get_Trap(db: DbSession, _operator: Operator, trap_id: UUID) -> TrapOut:
	return trap_service.get_Trap(db, trap_id)


@router.post("/{trap_id}/bind-profile", response_model=TrapOut)
def bind_TrapProfile(
	db: DbSession, _operator: Operator, trap_id: UUID, body: TrapBindProfile
) -> TrapOut:
	return trap_service.bind_TrapProfile(db, trap_id, body)
