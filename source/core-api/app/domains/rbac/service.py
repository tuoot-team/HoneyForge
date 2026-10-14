from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.domains.rbac.permissions import ALL_PERMISSIONS, is_Known_Permission
from app.domains.rbac.schemas import (
	RoleCreate,
	RoleOut,
	RoleUpdate,
	UserCreate,
	UserOut,
	UserUpdate,
)
from app.security import hash_Password
from app.texts import (
	MSG_PERM_FORBIDDEN,
	MSG_ROLE_DUP,
	MSG_ROLE_IN_USE,
	MSG_ROLE_NOT_FOUND,
	MSG_ROLE_SYSTEM_LOCKED,
	MSG_USER_BAD_PERMS,
	MSG_USER_DUP,
	MSG_USER_NOT_FOUND,
	MSG_USER_ROLE_MISSING,
)


def list_Roles(db: Session) -> list[RoleOut]:
	rows = db.query(models.Role).order_by(models.Role.name.asc()).all()
	return [RoleOut.model_validate(row) for row in rows]


def create_Role(db: Session, body: RoleCreate) -> RoleOut:
	name = body.name.strip()
	perms = _normalize_Permissions(body.permissions)
	if db.query(models.Role).filter(models.Role.name == name).one_or_none():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_ROLE_DUP)
	row = models.Role(name=name, is_system=False, permissions=perms)
	db.add(row)
	db.commit()
	db.refresh(row)
	return RoleOut.model_validate(row)


def update_Role(db: Session, role_id: UUID, body: RoleUpdate) -> RoleOut:
	row = db.query(models.Role).filter(models.Role.id == role_id).one_or_none()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_ROLE_NOT_FOUND)
	if row.is_system and body.permissions is not None:
		# Системные имена нельзя переименовать; права admin/operator/viewer фиксированы bootstrap'ом.
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_ROLE_SYSTEM_LOCKED)
	if body.name is not None:
		if row.is_system:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_ROLE_SYSTEM_LOCKED)
		new_name = body.name.strip()
		clash = (
			db.query(models.Role)
			.filter(models.Role.name == new_name, models.Role.id != role_id)
			.one_or_none()
		)
		if clash:
			raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_ROLE_DUP)
		row.name = new_name
	if body.permissions is not None:
		row.permissions = _normalize_Permissions(body.permissions)
	db.commit()
	db.refresh(row)
	return RoleOut.model_validate(row)


def delete_Role(db: Session, role_id: UUID) -> None:
	row = db.query(models.Role).filter(models.Role.id == role_id).one_or_none()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_ROLE_NOT_FOUND)
	if row.is_system:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_ROLE_SYSTEM_LOCKED)
	in_use = db.query(models.User).filter(models.User.role_id == role_id).count()
	if in_use:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_ROLE_IN_USE)
	db.delete(row)
	db.commit()


def list_Users(db: Session) -> list[UserOut]:
	rows = (
		db.query(models.User, models.Role)
		.join(models.Role, models.User.role_id == models.Role.id)
		.order_by(models.User.username.asc())
		.all()
	)
	return [_user_Out(user, role) for user, role in rows]


def create_User(db: Session, body: UserCreate) -> UserOut:
	username = body.username.strip()
	if db.query(models.User).filter(models.User.username == username).one_or_none():
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_USER_DUP)
	role = db.query(models.Role).filter(models.Role.id == body.role_id).one_or_none()
	if role is None:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_USER_ROLE_MISSING)
	user = models.User(
		username=username,
		password_hash=hash_Password(body.password),
		is_superadmin=bool(body.is_superadmin),
		disabled=False,
		role_id=role.id,
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return _user_Out(user, role)


def update_User(db: Session, user_id: UUID, body: UserUpdate) -> UserOut:
	user = db.query(models.User).filter(models.User.id == user_id).one_or_none()
	if user is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_USER_NOT_FOUND)
	role = db.query(models.Role).filter(models.Role.id == user.role_id).one()
	if body.role_id is not None:
		role = db.query(models.Role).filter(models.Role.id == body.role_id).one_or_none()
		if role is None:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_USER_ROLE_MISSING)
		user.role_id = role.id
	if body.disabled is not None:
		user.disabled = body.disabled
	if body.is_superadmin is not None:
		user.is_superadmin = body.is_superadmin
	if body.password is not None:
		user.password_hash = hash_Password(body.password)
	db.commit()
	db.refresh(user)
	role = db.query(models.Role).filter(models.Role.id == user.role_id).one()
	return _user_Out(user, role)


def write_Audit(
	db: Session,
	*,
	actor: str,
	action: str,
	resource_type: str | None = None,
	resource_id: str | None = None,
	payload: dict | None = None,
) -> None:
	db.add(
		models.AuditLog(
			actor=actor,
			action=action,
			resource_type=resource_type,
			resource_id=resource_id,
			payload=payload or {},
		)
	)
	db.commit()


def _normalize_Permissions(raw: list[str]) -> list[str]:
	cleaned: list[str] = []
	seen: set[str] = set()
	for item in raw:
		name = str(item).strip()
		if not name:
			continue
		if not is_Known_Permission(name):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=MSG_USER_BAD_PERMS.format(perm=name),
			)
		if name not in seen:
			seen.add(name)
			cleaned.append(name)
	# Стабильный порядок по каталогу.
	order = {name: idx for idx, name in enumerate(ALL_PERMISSIONS)}
	cleaned.sort(key=lambda p: order.get(p, 999))
	return cleaned


def _user_Out(user: models.User, role: models.Role) -> UserOut:
	return UserOut(
		id=user.id,
		username=user.username,
		is_superadmin=user.is_superadmin,
		disabled=user.disabled,
		role_id=user.role_id,
		role_name=role.name,
		created_at=user.created_at,
	)


def assert_Permission(user: models.User, role: models.Role | None, perm: str) -> None:
	if user.is_superadmin:
		return
	perms = list(role.permissions) if role is not None else []
	if perm not in perms:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_PERM_FORBIDDEN)
