from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.texts import MSG_COURIER_SSH_INCOMPLETE


class CourierStatus(str, Enum):
	pending = "pending"
	online = "online"
	offline = "offline"


class CourierOut(BaseModel):
	id: UUID
	name: str
	status: CourierStatus
	owner_user_id: UUID | None = None
	last_seen_at: datetime | None
	meta: dict[str, Any] = Field(default_factory=dict)
	created_at: datetime
	updated_at: datetime

	model_config = {"from_attributes": True}


class CourierConfirmIn(BaseModel):
	device_code: str = Field(min_length=4, max_length=32)
	name: str = Field(default="courier", min_length=1, max_length=128)


class CourierPairingStartOut(BaseModel):
	pairing_id: UUID
	device_code: str
	expires_at: datetime


class CourierPairingCompleteOut(BaseModel):
	courier_id: UUID
	courier_token: str


class CourierPairingListItem(BaseModel):
	id: UUID
	device_code: str
	status: str
	courier_id: UUID | None
	expires_at: datetime
	created_at: datetime


class CourierPairingListOut(BaseModel):
	total: int
	items: list[CourierPairingListItem]


class TrapCourierSshIn(BaseModel):
	host: str = Field(min_length=1, max_length=255)
	port: int = Field(default=22, ge=1, le=65535)
	user: str = Field(default="root", min_length=1, max_length=64)
	password: str | None = None
	private_key: str | None = None
	remote_data_dir: str = Field(default="/var/lib/metricsd", min_length=1, max_length=512)

	@model_validator(mode="after")
	def require_Auth(self) -> "TrapCourierSshIn":
		has_password = bool(self.password and self.password.strip())
		has_key = bool(self.private_key and self.private_key.strip())
		if not has_password and not has_key:
			raise ValueError(MSG_COURIER_SSH_INCOMPLETE)
		if not self.host.strip():
			raise ValueError(MSG_COURIER_SSH_INCOMPLETE)
		return self


class CourierVisitEventIn(BaseModel):
	"""Событие из буфера ловушки (поле agent_buffer_id - для дедупа)."""

	event_type: str
	source_ip: str | None = None
	source_port: int | None = None
	occurred_at: str | None = None
	payload: dict[str, Any] = Field(default_factory=dict)
	agent_buffer_id: int | None = None


class CourierVisitCompleteIn(BaseModel):
	ok: bool = True
	error: str | None = None
	events: list[CourierVisitEventIn] = Field(default_factory=list)


class CourierVisitClaimOut(BaseModel):
	visit_id: UUID | None = None
	trap_id: UUID | None = None
	ssh: dict[str, Any] | None = None
	buffer_path: str | None = None
	wipe_hints: list[str] = Field(default_factory=list)


class CourierConfigOut(BaseModel):
	courier_id: UUID
	name: str
	ok: bool = True


class DeployCourierIn(BaseModel):
	host: str
	user: str = "root"
	password: str
	port: int = Field(default=22, ge=1, le=65535)
	center_url: str | None = None


class DeployCourierOut(BaseModel):
	ok: bool
	device_code: str | None = None
	detail: str = ""
