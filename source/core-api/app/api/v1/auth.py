from fastapi import APIRouter, HTTPException, status

from app.config import get_Settings
from app.deps import Operator
from app.domains.auth.schemas import LoginIn, LoginOut, MeOut
from app.security import sign_OperatorToken
from app.texts import MSG_AUTH_BAD_PASSWORD

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def post_Login(body: LoginIn) -> LoginOut:
	settings = get_Settings()
	if body.password != settings.OPERATOR_PASSWORD:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_AUTH_BAD_PASSWORD)
	token = sign_OperatorToken(settings.OPERATOR_TOKEN_SECRET)
	return LoginOut(access_token=token)


@router.post("/logout")
def post_Logout(_operator: Operator) -> dict:
	# stateless HMAC - клиент просто забывает токен
	return {"ok": True}


@router.get("/me", response_model=MeOut)
def get_Me(_operator: Operator) -> MeOut:
	return MeOut(role="operator", authenticated=True)
