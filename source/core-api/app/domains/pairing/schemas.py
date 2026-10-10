from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class PairingStatus(str, Enum):
	pending = "pending"
	confirmed = "confirmed"
	completed = "completed"
	expired = "expired"


class PairingStartOut(BaseModel):
	pairing_id: UUID
	device_code: str
	expires_at: datetime


class PairingConfirmIn(BaseModel):
	device_code: str = Field(min_length=4, max_length=16)
	trap_name: str = Field(default="trap")
	profile_id: UUID | None = None


class PairingCompleteOut(BaseModel):
	trap_id: UUID
	agent_token: str = Field(description="shown once; store on agent host")
	status: PairingStatus
