from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.profiles.schemas import ProfileOut


class AgentHeartbeatIn(BaseModel):
	status_payload: dict[str, Any] = Field(default_factory=dict)
	agent_version: str = ""


class AgentHeartbeatOut(BaseModel):
	ok: bool = True
	config_version: int | None = None


class AgentConfigOut(BaseModel):
	trap_id: UUID
	profile: ProfileOut | None


class AgentEventItem(BaseModel):
	event_type: str
	source_ip: str | None = None
	source_port: int | None = None
	occurred_at: str | None = None
	payload: dict[str, Any] = Field(default_factory=dict)


class AgentEventsBatchIn(BaseModel):
	events: list[AgentEventItem]
