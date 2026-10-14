from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.maintenance import service as maintenance_service
from app.domains.maintenance.schemas import WipeOut
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_MAINTENANCE_WRITE

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post("/clear-logs", response_model=WipeOut)
def clear_Logs(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_MAINTENANCE_WRITE)),
) -> WipeOut:
	out = maintenance_service.clear_Logs(db)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="maintenance.clear_logs",
		resource_type="db",
		payload=out.model_dump() if hasattr(out, "model_dump") else {},
	)
	return out


@router.post("/reset", response_model=WipeOut)
def reset_Database(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_MAINTENANCE_WRITE)),
) -> WipeOut:
	out = maintenance_service.reset_Database(db)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="maintenance.reset",
		resource_type="db",
		payload=out.model_dump() if hasattr(out, "model_dump") else {},
	)
	return out
