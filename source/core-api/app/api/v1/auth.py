from fastapi import APIRouter, HTTPException, status

from app.config import get_Settings
from app.db import models
from app.deps import DbSession, Operator
from app.domains.auth.schemas import LoginIn, LoginOut, MeOut
from app.domains.rbac.permissions import ALL_PERMISSIONS
from app.security import sign_UserToken, verify_Password
from app.texts import MSG_AUTH_BAD_PASSWORD, MSG_AUTH_DISABLED

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def post_Login(db: DbSession, body: LoginIn) -> LoginOut:
	settings = get_Settings()
	username = body.username.strip()
	row = (
		db.query(models.User)
		.filter(models.User.username == username)
		.one_or_none()
	)
	if row is None or not verify_Password(body.password, row.password_hash):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_BAD_PASSWORD)
	if row.disabled:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_DISABLED)
	token = sign_UserToken(settings.OPERATOR_TOKEN_SECRET, row.id)
	return LoginOut(access_token=token)


@router.post("/logout")
def post_Logout(_operator: Operator) -> dict:
	# Stateless token - клиент забывает Bearer.
	return {"ok": True}


@router.get("/me", response_model=MeOut)
def get_Me(operator: Operator) -> MeOut:
	perms = list(ALL_PERMISSIONS) if operator.is_superadmin else list(operator.permissions)
	return MeOut(
		authenticated=True,
		username=operator.username,
		role=operator.role_name,
		role_id=str(operator.role_id),
		is_superadmin=operator.is_superadmin,
		permissions=perms,
	)
