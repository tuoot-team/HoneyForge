from fastapi import APIRouter

from app.deps import DbSession, Operator
from app.domains.maintenance import service as maintenance_service
from app.domains.maintenance.schemas import WipeOut

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post("/clear-logs", response_model=WipeOut)
def clear_Logs(db: DbSession, _operator: Operator) -> WipeOut:
	return maintenance_service.clear_Logs(db)


@router.post("/reset", response_model=WipeOut)
def reset_Database(db: DbSession, _operator: Operator) -> WipeOut:
	return maintenance_service.reset_Database(db)
