from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.db.session import get_DbSession
from app.security import hash_Secret, verify_UserToken
from app.texts import (
	MSG_AGENT_UNAUTHORIZED,
	MSG_AUTH_BAD_TOKEN,
	MSG_AUTH_DISABLED,
	MSG_AUTH_REQUIRED,
	MSG_PERM_FORBIDDEN,
)


DbSession = Annotated[Session, Depends(get_DbSession)]

bearer_Scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
	id: UUID
	username: str
	is_superadmin: bool
	role_id: UUID
	role_name: str
	permissions: list[str]

	def has(self, perm: str) -> bool:
		if self.is_superadmin:
			return True
		return perm in self.permissions


def require_Operator(
	db: DbSession,
	credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_Scheme)] = None,
) -> CurrentUser:
	settings = get_Settings()
	if credentials is None or not credentials.credentials:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_REQUIRED)
	if credentials.scheme.lower() != "bearer":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_REQUIRED)
	token = credentials.credentials.strip()
	if not token:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_REQUIRED)
	user_id = verify_UserToken(settings.OPERATOR_TOKEN_SECRET, token)
	if user_id is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_BAD_TOKEN)
	row = (
		db.query(models.User, models.Role)
		.join(models.Role, models.User.role_id == models.Role.id)
		.filter(models.User.id == user_id)
		.one_or_none()
	)
	if row is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_BAD_TOKEN)
	user, role = row
	if user.disabled:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_DISABLED)
	perms = list(role.permissions or [])
	if user.is_superadmin:
		# Superadmin всегда полный каталог, даже если роль урезали вручную в БД.
		from app.domains.rbac.permissions import ALL_PERMISSIONS

		perms = list(ALL_PERMISSIONS)
	return CurrentUser(
		id=user.id,
		username=user.username,
		is_superadmin=user.is_superadmin,
		role_id=role.id,
		role_name=role.name,
		permissions=perms,
	)


Operator = Annotated[CurrentUser, Depends(require_Operator)]


def require_Permission(perm: str):
	def _dependency(operator: Operator) -> CurrentUser:
		if not operator.has(perm):
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MSG_PERM_FORBIDDEN)
		return operator

	return _dependency


def require_AgentTrap(
	db: DbSession,
	x_agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> models.Trap:
	if not x_agent_token:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AGENT_UNAUTHORIZED)
	token_hash = hash_Secret(x_agent_token)
	trap = db.query(models.Trap).filter(models.Trap.agent_token_hash == token_hash).one_or_none()
	if trap is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AGENT_UNAUTHORIZED)
	return trap


AgentTrap = Annotated[models.Trap, Depends(require_AgentTrap)]
