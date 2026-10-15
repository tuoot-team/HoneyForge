from datetime import datetime

from pydantic import BaseModel, Field


class VmImageOut(BaseModel):
	token: str
	name: str
	original_filename: str = ""
	format: str
	size_bytes: int
	sha256: str = ""
	created_at: datetime

	model_config = {"from_attributes": True}


class VmImageListOut(BaseModel):
	items: list[VmImageOut] = Field(default_factory=list)
	total: int = 0
