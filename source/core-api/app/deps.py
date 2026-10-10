from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.db.session import get_DbSession
from app.security import hash_Secret, verify_OperatorToken
from app.texts import MSG_AGENT_UNAUTHORIZED, MSG_AUTH_BAD_TOKEN, MSG_AUTH_REQUIRED


DbSession = Annotated[Session, Depends(get_DbSession)]


def require_Operator(
	authorization: Annotated[str | None, Header()] = None,
) -> str:
	"""Bearer-токен оператора после /auth/login."""
	settings = get_Settings()
	if not authorization or not authorization.lower().startswith("bearer "):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_REQUIRED)
	token = authorization.split(" ", 1)[1].strip()
	if not verify_OperatorToken(settings.OPERATOR_TOKEN_SECRET, token):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_BAD_TOKEN)
	return "operator"


Operator = Annotated[str, Depends(require_Operator)]


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
