"""Видимость ловушек: owner или traps.all / superadmin."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.deps import CurrentUser
from app.domains.rbac.permissions import PERM_TRAPS_ALL
from app.texts import MSG_PERM_FORBIDDEN, MSG_TRAP_NOT_FOUND, MSG_USER_NOT_FOUND


def can_See_All_Traps(user: CurrentUser) -> bool:
	return user.is_superadmin or user.has(PERM_TRAPS_ALL)


def trap_Visible(user: CurrentUser, trap: models.Trap) -> bool:
	if can_See_All_Traps(user):
		return True
	return trap.owner_user_id is not None and trap.owner_user_id == user.id


def visible_Trap_Ids(db: Session, user: CurrentUser) -> set[UUID] | None:
	"""None = все ловушки; иначе набор id, видимых пользователю."""
	if can_See_All_Traps(user):
		return None
	rows = (
		db.query(models.Trap.id)
		.filter(models.Trap.owner_user_id == user.id)
		.all()
	)
	return {row[0] for row in rows}


def get_Visible_Trap(db: Session, user: CurrentUser, trap_id: UUID) -> models.Trap:
	trap = db.get(models.Trap, trap_id)
	if trap is None or not trap_Visible(user, trap):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
	return trap


def can_Assign_Owner(user: CurrentUser, trap: models.Trap) -> bool:
	if user.is_superadmin or user.has(PERM_TRAPS_ALL):
		return True
	return trap.owner_user_id is not None and trap.owner_user_id == user.id


def require_Assign_Owner(user: CurrentUser, trap: models.Trap) -> None:
	if not can_Assign_Owner(user, trap):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_PERM_FORBIDDEN)


def require_User_Exists(db: Session, user_id: UUID) -> models.User:
	row = db.get(models.User, user_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_USER_NOT_FOUND)
	return row
