from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_USERS_WRITE
from app.domains.rbac.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def list_Users(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_USERS_WRITE)),
) -> list[UserOut]:
	return rbac_service.list_Users(db)


@router.post("/", response_model=UserOut, status_code=201)
def create_User(
	db: DbSession,
	body: UserCreate,
	operator: CurrentUser = Depends(require_Permission(PERM_USERS_WRITE)),
) -> UserOut:
	out = rbac_service.create_User(db, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="user.create",
		resource_type="user",
		resource_id=str(out.id),
		payload={"username": out.username, "role_id": str(out.role_id)},
	)
	return out


@router.patch("/{user_id}", response_model=UserOut)
def update_User(
	db: DbSession,
	user_id: UUID,
	body: UserUpdate,
	operator: CurrentUser = Depends(require_Permission(PERM_USERS_WRITE)),
) -> UserOut:
	out = rbac_service.update_User(db, user_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="user.update",
		resource_type="user",
		resource_id=str(out.id),
		payload=body.model_dump(exclude_none=True, exclude={"password"}),
	)
	return out
