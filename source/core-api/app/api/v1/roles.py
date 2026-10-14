from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import ALL_PERMISSIONS, PERM_ROLES_WRITE
from app.domains.rbac.schemas import (
	PermissionsCatalogOut,
	RoleCreate,
	RoleOut,
	RoleUpdate,
)

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/permissions", response_model=PermissionsCatalogOut)
def list_Permission_Catalog(
	_operator: CurrentUser = Depends(require_Permission(PERM_ROLES_WRITE)),
) -> PermissionsCatalogOut:
	return PermissionsCatalogOut(permissions=list(ALL_PERMISSIONS))


@router.get("/", response_model=list[RoleOut])
def list_Roles(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_ROLES_WRITE)),
) -> list[RoleOut]:
	return rbac_service.list_Roles(db)


@router.post("/", response_model=RoleOut, status_code=201)
def create_Role(
	db: DbSession,
	body: RoleCreate,
	operator: CurrentUser = Depends(require_Permission(PERM_ROLES_WRITE)),
) -> RoleOut:
	out = rbac_service.create_Role(db, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="role.create",
		resource_type="role",
		resource_id=str(out.id),
		payload={"name": out.name, "permissions": out.permissions},
	)
	return out


@router.patch("/{role_id}", response_model=RoleOut)
def update_Role(
	db: DbSession,
	role_id: UUID,
	body: RoleUpdate,
	operator: CurrentUser = Depends(require_Permission(PERM_ROLES_WRITE)),
) -> RoleOut:
	out = rbac_service.update_Role(db, role_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="role.update",
		resource_type="role",
		resource_id=str(out.id),
		payload=body.model_dump(exclude_none=True),
	)
	return out


@router.delete("/{role_id}", status_code=204)
def delete_Role(
	db: DbSession,
	role_id: UUID,
	operator: CurrentUser = Depends(require_Permission(PERM_ROLES_WRITE)),
) -> None:
	rbac_service.delete_Role(db, role_id)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="role.delete",
		resource_type="role",
		resource_id=str(role_id),
	)
