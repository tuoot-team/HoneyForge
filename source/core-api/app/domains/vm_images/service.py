from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.domains.vm_images.schemas import VmImageListOut, VmImageOut
from app.texts import (
	MSG_VM_IMAGE_BAD_FORMAT,
	MSG_VM_IMAGE_BAD_NAME,
	MSG_VM_IMAGE_EMPTY,
	MSG_VM_IMAGE_NOT_FOUND,
	MSG_VM_IMAGE_TOO_LARGE,
	MSG_VM_IMAGE_UNKNOWN,
)

TOKEN_PREFIX = "vmi_"


def is_ImageToken(value: str) -> bool:
	return str(value or "").startswith(TOKEN_PREFIX)


def images_Dir() -> Path:
	settings = get_Settings()
	path = Path(settings.VM_IMAGES_DIR)
	path.mkdir(parents=True, exist_ok=True)
	return path


def image_FilePath(token: str) -> Path:
	return images_Dir() / token


def _new_Token() -> str:
	return TOKEN_PREFIX + secrets.token_hex(8)


def _detect_Format(filename: str) -> str:
	lower = (filename or "").lower()
	if lower.endswith(".ova"):
		return "ova"
	if lower.endswith(".vdi"):
		return "vdi"
	if lower.endswith(".vmdk"):
		return "vmdk"
	raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_VM_IMAGE_BAD_FORMAT)


def _image_ToOut(row: models.VmImage) -> VmImageOut:
	return VmImageOut(
		token=row.token,
		name=row.name,
		original_filename=row.original_filename or "",
		format=row.format,
		size_bytes=int(row.size_bytes or 0),
		sha256=row.sha256 or "",
		created_at=row.created_at,
	)


def list_VmImages(db: Session) -> VmImageListOut:
	rows = db.query(models.VmImage).order_by(models.VmImage.created_at.desc()).all()
	items = [_image_ToOut(row) for row in rows]
	return VmImageListOut(items=items, total=len(items))


def get_VmImage(db: Session, token: str) -> VmImageOut:
	return _image_ToOut(get_VmImageRow(db, token))


def get_VmImageRow(db: Session, token: str) -> models.VmImage:
	row = db.query(models.VmImage).filter(models.VmImage.token == token).one_or_none()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_VM_IMAGE_NOT_FOUND)
	return row


def image_FilePath_Or404(token: str) -> Path:
	path = image_FilePath(token)
	if not path.is_file():
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_VM_IMAGE_NOT_FOUND)
	return path


async def create_VmImage(
	db: Session,
	*,
	upload: UploadFile,
	name: str | None,
) -> VmImageOut:
	settings = get_Settings()
	filename = (upload.filename or "").strip() or "disk.ova"
	fmt = _detect_Format(filename)
	image_name = (name or "").strip() or Path(filename).stem or "vm-image"
	if not image_name:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_VM_IMAGE_BAD_NAME)

	token = _new_Token()
	for _ in range(5):
		exists = db.query(models.VmImage).filter(models.VmImage.token == token).one_or_none()
		if exists is None:
			break
		token = _new_Token()

	path = image_FilePath(token)
	hasher = hashlib.sha256()
	size = 0
	limit = int(settings.VM_IMAGES_MAX_BYTES)
	try:
		with path.open("wb") as out:
			while True:
				chunk = await upload.read(1024 * 1024)
				if not chunk:
					break
				size += len(chunk)
				if size > limit:
					out.close()
					path.unlink(missing_ok=True)
					limit_gib = max(1, limit // (1024 * 1024 * 1024))
					raise HTTPException(
						status_code=status.HTTP_400_BAD_REQUEST,
						detail=MSG_VM_IMAGE_TOO_LARGE.format(limit_gib=limit_gib),
					)
				hasher.update(chunk)
				out.write(chunk)
	except HTTPException:
		raise
	except Exception:
		path.unlink(missing_ok=True)
		raise

	if size == 0:
		path.unlink(missing_ok=True)
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_VM_IMAGE_EMPTY)

	row = models.VmImage(
		token=token,
		name=image_name,
		original_filename=filename,
		format=fmt,
		size_bytes=size,
		sha256=hasher.hexdigest(),
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return _image_ToOut(row)


def delete_VmImage(db: Session, token: str) -> None:
	row = get_VmImageRow(db, token)
	path = image_FilePath(token)
	db.delete(row)
	db.commit()
	if path.is_file():
		path.unlink()


def assert_VmImageExists(db: Session, blocks) -> None:
	emulation = getattr(blocks, "emulation", None)
	if emulation is None or not getattr(emulation, "enabled", False):
		return
	token = str(getattr(emulation, "image_token", "") or "").strip()
	if not token:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=MSG_VM_IMAGE_UNKNOWN.format(token="(empty)"),
		)
	if not is_ImageToken(token):
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=MSG_VM_IMAGE_UNKNOWN.format(token=token),
		)
	row = db.query(models.VmImage).filter(models.VmImage.token == token).one_or_none()
	if row is None:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail=MSG_VM_IMAGE_UNKNOWN.format(token=token),
		)
