from pydantic import BaseModel, Field


class LoginIn(BaseModel):
	password: str = Field(min_length=1)


class LoginOut(BaseModel):
	access_token: str
	token_type: str = "bearer"


class MeOut(BaseModel):
	role: str = "operator"
	authenticated: bool
