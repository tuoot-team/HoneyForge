from pydantic import BaseModel, Field


class LoginIn(BaseModel):
	username: str = Field(min_length=1)
	password: str = Field(min_length=1)


class LoginOut(BaseModel):
	access_token: str
	token_type: str = "bearer"


class MeOut(BaseModel):
	authenticated: bool = True
	username: str
	role: str
	role_id: str
	is_superadmin: bool
	permissions: list[str]
