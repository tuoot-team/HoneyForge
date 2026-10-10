from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TrapStatus(str, Enum):
	pending = "pending"
	online = "online"
	offline = "offline"


class TrapOut(BaseModel):
	id: UUID
	name: str
	profile_id: UUID | None
	status: TrapStatus
	last_seen_at: datetime | None
	meta: dict[str, Any] = Field(default_factory=dict)
	created_at: datetime
	updated_at: datetime

	model_config = {"from_attributes": True}


class TrapBindProfile(BaseModel):
	profile_id: UUID
