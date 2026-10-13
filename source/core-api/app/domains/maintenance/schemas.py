from pydantic import BaseModel, Field


class WipeOut(BaseModel):
	deleted: dict[str, int] = Field(default_factory=dict)
