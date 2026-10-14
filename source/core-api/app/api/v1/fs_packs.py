from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.fs_packs import service as fs_packs_service
from app.domains.fs_packs.schemas import FsPackListOut, FsPackOut
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_FS_PACKS_WRITE, PERM_PROFILES_READ

router = APIRouter(prefix="/fs-packs", tags=["fs-packs"])


@router.get("/", response_model=FsPackListOut)
def list_FsPacks(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> FsPackListOut:
	return fs_packs_service.list_FsPacks(db)


@router.post("/", response_model=FsPackOut, status_code=201)
async def create_FsPack(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_FS_PACKS_WRITE)),
	file: UploadFile = File(...),
	name: str | None = Form(default=None),
) -> FsPackOut:
	out = await fs_packs_service.create_FsPack(db, upload=file, name=name)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="fs_pack.create",
		resource_type="fs_pack",
		resource_id=out.token,
		payload={"name": out.name},
	)
	return out


@router.get("/{token}", response_model=FsPackOut)
def get_FsPack(
	db: DbSession,
	token: str,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> FsPackOut:
	return fs_packs_service.get_FsPack(db, token)


@router.delete("/{token}", status_code=204)
def delete_FsPack(
	db: DbSession,
	token: str,
	operator: CurrentUser = Depends(require_Permission(PERM_FS_PACKS_WRITE)),
) -> None:
	fs_packs_service.delete_FsPack(db, token)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="fs_pack.delete",
		resource_type="fs_pack",
		resource_id=token,
	)
