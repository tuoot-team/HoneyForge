from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventOut(BaseModel):
	id: int
	trap_id: UUID | None
	event_type: str
	source_ip: str | None
	source_port: int | None
	occurred_at: datetime
	payload: dict[str, Any] = Field(default_factory=dict)
	created_at: datetime

	model_config = {"from_attributes": True}


class EventListOut(BaseModel):
	items: list[EventOut]
	total: int
