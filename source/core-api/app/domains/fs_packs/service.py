from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.domains.fs_packs.schemas import FsPackListOut, FsPackOut
from app.texts import (
	MSG_FS_PACK_BAD_FORMAT,
	MSG_FS_PACK_BAD_NAME,
	MSG_FS_PACK_EMPTY,
	MSG_FS_PACK_NOT_FOUND,
	MSG_FS_PACK_TOO_LARGE,
	MSG_FS_PACK_UNKNOWN,
)

BUILTIN_FS_PACKS = frozenset({"", "ubuntu-22.04", "builtin"})
TOKEN_PREFIX = "fsp_"


def is_PackToken(value: str) -> bool:
	return str(value or "").startswith(TOKEN_PREFIX)


def is_BuiltinFsPack(value: str) -> bool:
	return str(value or "").strip() in BUILTIN_FS_PACKS


def packs_Dir() -> Path:
	settings = get_Settings()
	path = Path(settings.FS_PACKS_DIR)
	path.mkdir(parents=True, exist_ok=True)
	return path


def pack_FilePath(token: str) -> Path:
	return packs_Dir() / token


def _new_Token() -> str:
	return TOKEN_PREFIX + secrets.token_hex(8)


def _detect_Format(filename: str) -> str:
	lower = (filename or "").lower()
	if lower.endswith(".zip"):
		return "zip"
	if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
		return "tar_gz"
	raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_FS_PACK_BAD_FORMAT)


def _pack_ToOut(row: models.FsPack) -> FsPackOut:
	return FsPackOut(
		token=row.token,
		name=row.name,
		original_filename=row.original_filename or "",
		format=row.format,
		size_bytes=int(row.size_bytes or 0),
		sha256=row.sha256 or "",
		created_at=row.created_at,
	)


def list_FsPacks(db: Session) -> FsPackListOut:
	rows = db.query(models.FsPack).order_by(models.FsPack.created_at.desc()).all()
	items = [_pack_ToOut(row) for row in rows]
	return FsPackListOut(items=items, total=len(items))


def get_FsPack(db: Session, token: str) -> FsPackOut:
	row = db.query(models.FsPack).filter(models.FsPack.token == token).one_or_none()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_FS_PACK_NOT_FOUND)
	return _pack_ToOut(row)


def get_FsPackRow(db: Session, token: str) -> models.FsPack:
	row = db.query(models.FsPack).filter(models.FsPack.token == token).one_or_none()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_FS_PACK_NOT_FOUND)
	return row


def read_PackBytes(token: str) -> bytes:
	path = pack_FilePath(token)
	if not path.is_file():
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_FS_PACK_NOT_FOUND)
	return path.read_bytes()


async def create_FsPack(
	db: Session,
	*,
	upload: UploadFile,
	name: str | None,
) -> FsPackOut:
	settings = get_Settings()
	filename = (upload.filename or "").strip() or "archive"
	fmt = _detect_Format(filename)
	raw = await upload.read()
	if not raw:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_FS_PACK_EMPTY)
	if len(raw) > settings.FS_PACK_MAX_BYTES:
		limit_mib = settings.FS_PACK_MAX_BYTES // (1024 * 1024)
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=MSG_FS_PACK_TOO_LARGE.format(limit_mib=limit_mib),
		)

	pack_name = (name or "").strip() or Path(filename).stem or "fs-pack"
	if not pack_name:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_FS_PACK_BAD_NAME)

	token = _new_Token()
	# На случай коллизии - перегенерируем
	for _ in range(5):
		exists = db.query(models.FsPack).filter(models.FsPack.token == token).one_or_none()
		if exists is None:
			break
		token = _new_Token()

	digest = hashlib.sha256(raw).hexdigest()
	path = pack_FilePath(token)
	path.write_bytes(raw)

	row = models.FsPack(
		token=token,
		name=pack_name,
		original_filename=filename,
		format=fmt,
		size_bytes=len(raw),
		sha256=digest,
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return _pack_ToOut(row)


def delete_FsPack(db: Session, token: str) -> None:
	row = get_FsPackRow(db, token)
	path = pack_FilePath(token)
	db.delete(row)
	db.commit()
	if path.is_file():
		path.unlink()


def assert_FsPacksExist(db: Session, blocks) -> None:
	"""Если shell.fs_pack - токен пакета, он должен быть в БД."""
	for service in getattr(blocks, "services", []) or []:
		if getattr(service, "type", None) != "ssh":
			continue
		modules = getattr(service, "modules", None)
		shell = getattr(modules, "shell", None) if modules is not None else None
		if shell is None:
			continue
		pack = str(getattr(shell, "fs_pack", "") or "").strip()
		if is_BuiltinFsPack(pack):
			continue
		if not is_PackToken(pack):
			# Свободная метка без токена - как раньше (только issue), не валидируем
			continue
		row = db.query(models.FsPack).filter(models.FsPack.token == pack).one_or_none()
		if row is None:
			raise HTTPException(
				status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
				detail=MSG_FS_PACK_UNKNOWN.format(token=pack),
			)
