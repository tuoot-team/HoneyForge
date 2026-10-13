from fastapi import APIRouter, File, Form, UploadFile

from app.deps import DbSession, Operator
from app.domains.fs_packs import service as fs_packs_service
from app.domains.fs_packs.schemas import FsPackListOut, FsPackOut

router = APIRouter(prefix="/fs-packs", tags=["fs-packs"])


@router.get("/", response_model=FsPackListOut)
def list_FsPacks(db: DbSession, _operator: Operator) -> FsPackListOut:
	return fs_packs_service.list_FsPacks(db)


@router.post("/", response_model=FsPackOut, status_code=201)
async def create_FsPack(
	db: DbSession,
	_operator: Operator,
	file: UploadFile = File(...),
	name: str | None = Form(default=None),
) -> FsPackOut:
	return await fs_packs_service.create_FsPack(db, upload=file, name=name)


@router.get("/{token}", response_model=FsPackOut)
def get_FsPack(db: DbSession, _operator: Operator, token: str) -> FsPackOut:
	return fs_packs_service.get_FsPack(db, token)


@router.delete("/{token}", status_code=204)
def delete_FsPack(db: DbSession, _operator: Operator, token: str) -> None:
	fs_packs_service.delete_FsPack(db, token)
