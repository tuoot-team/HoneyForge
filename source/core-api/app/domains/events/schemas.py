from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

EventPriority = Literal["low", "medium", "high"]


class EventOut(BaseModel):
	id: int
	trap_id: UUID | None
	event_type: str
	source_ip: str | None
	source_port: int | None
	occurred_at: datetime
	payload: dict[str, Any] = Field(default_factory=dict)
	created_at: datetime
	priority: EventPriority = "low"

	model_config = {"from_attributes": True}


class EventListOut(BaseModel):
	items: list[EventOut]
	total: int


class EventChainOut(BaseModel):
	trap_id: UUID | None
	source_ip: str
	event_count: int
	ports: list[int] = Field(default_factory=list)
	services: list[str] = Field(default_factory=list)
	event_types: list[str] = Field(default_factory=list)
	first_at: datetime | None = None
	last_at: datetime | None = None
	is_lateral: bool = False
	max_priority: EventPriority = "low"


class EventChainListOut(BaseModel):
	items: list[EventChainOut]
	total: int
