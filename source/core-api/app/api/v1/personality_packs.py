from fastapi import APIRouter, Depends

from app.deps import CurrentUser, require_Permission
from app.domains.personality_packs import service as personality_packs_service
from app.domains.personality_packs.schemas import PersonalityPackListOut
from app.domains.rbac.permissions import PERM_PROFILES_READ

router = APIRouter(prefix="/personality-packs", tags=["personality-packs"])


@router.get("/", response_model=PersonalityPackListOut)
def list_PersonalityPacks(
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> PersonalityPackListOut:
	"""Builtin JSON-пресеты с диска PERSONALITY_PACKS_DIR."""
	return personality_packs_service.list_PersonalityPacks()
