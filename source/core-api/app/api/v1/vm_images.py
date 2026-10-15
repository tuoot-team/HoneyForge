from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_PROFILES_READ, PERM_VM_IMAGES_WRITE
from app.domains.vm_images import service as vm_images_service
from app.domains.vm_images.schemas import VmImageListOut, VmImageOut

router = APIRouter(prefix="/vm-images", tags=["vm-images"])


@router.get("/", response_model=VmImageListOut)
def list_VmImages(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> VmImageListOut:
	return vm_images_service.list_VmImages(db)


@router.post("/", response_model=VmImageOut, status_code=201)
async def create_VmImage(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_VM_IMAGES_WRITE)),
	file: UploadFile = File(...),
	name: str | None = Form(default=None),
) -> VmImageOut:
	out = await vm_images_service.create_VmImage(db, upload=file, name=name)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="vm_image.create",
		resource_type="vm_image",
		resource_id=out.token,
		payload={"name": out.name, "format": out.format},
	)
	return out


@router.get("/{token}", response_model=VmImageOut)
def get_VmImage(
	db: DbSession,
	token: str,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> VmImageOut:
	return vm_images_service.get_VmImage(db, token)


@router.delete("/{token}", status_code=204)
def delete_VmImage(
	db: DbSession,
	token: str,
	operator: CurrentUser = Depends(require_Permission(PERM_VM_IMAGES_WRITE)),
) -> None:
	vm_images_service.delete_VmImage(db, token)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="vm_image.delete",
		resource_type="vm_image",
		resource_id=token,
		payload={},
	)


@router.get("/{token}/download")
def download_VmImage(
	db: DbSession,
	token: str,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> FileResponse:
	row = vm_images_service.get_VmImageRow(db, token)
	path = vm_images_service.image_FilePath_Or404(token)
	return FileResponse(
		path,
		filename=row.original_filename or f"{token}.{row.format}",
		media_type="application/octet-stream",
	)
