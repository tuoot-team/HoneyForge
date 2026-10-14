from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
	name: str = Field(min_length=1, max_length=64)
	permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
	name: str | None = Field(default=None, min_length=1, max_length=64)
	permissions: list[str] | None = None


class RoleOut(BaseModel):
	id: UUID
	name: str
	is_system: bool
	permissions: list[str]
	created_at: datetime | None = None

	model_config = {"from_attributes": True}


class UserCreate(BaseModel):
	username: str = Field(min_length=1, max_length=64)
	password: str = Field(min_length=1)
	role_id: UUID
	is_superadmin: bool = False


class UserUpdate(BaseModel):
	role_id: UUID | None = None
	disabled: bool | None = None
	password: str | None = Field(default=None, min_length=1)
	is_superadmin: bool | None = None


class UserOut(BaseModel):
	id: UUID
	username: str
	is_superadmin: bool
	disabled: bool
	role_id: UUID
	role_name: str
	created_at: datetime | None = None


class PermissionsCatalogOut(BaseModel):
	permissions: list[str]
