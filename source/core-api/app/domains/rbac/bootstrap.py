from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import Settings
from app.db import models
from app.domains.rbac.permissions import (
	ALL_PERMISSIONS,
	OPERATOR_PERMISSIONS,
	SYSTEM_ROLE_ADMIN,
	SYSTEM_ROLE_OPERATOR,
	SYSTEM_ROLE_VIEWER,
	VIEWER_PERMISSIONS,
)
from app.security import hash_Password


def ensure_Rbac_Bootstrap(db: Session, settings: Settings) -> None:
	"""Системные роли + первый superadmin, если users пусто."""
	_ensure_System_Roles(db)
	if db.query(models.User).count() > 0:
		db.commit()
		return
	admin_role = (
		db.query(models.Role).filter(models.Role.name == SYSTEM_ROLE_ADMIN).one()
	)
	username = (settings.OPERATOR_USERNAME or "admin").strip() or "admin"
	password = settings.OPERATOR_PASSWORD or "change-me"
	user = models.User(
		username=username,
		password_hash=hash_Password(password),
		is_superadmin=True,
		disabled=False,
		role_id=admin_role.id,
	)
	db.add(user)
	db.commit()


def _ensure_System_Roles(db: Session) -> None:
	wanted = {
		SYSTEM_ROLE_ADMIN: list(ALL_PERMISSIONS),
		SYSTEM_ROLE_OPERATOR: list(OPERATOR_PERMISSIONS),
		SYSTEM_ROLE_VIEWER: list(VIEWER_PERMISSIONS),
	}
	for name, perms in wanted.items():
		row = db.query(models.Role).filter(models.Role.name == name).one_or_none()
		if row is None:
			db.add(
				models.Role(
					name=name,
					is_system=True,
					permissions=perms,
				)
			)
		else:
			# Системные роли всегда синхронизируем с каталогом.
			row.is_system = True
			row.permissions = perms
	db.flush()
