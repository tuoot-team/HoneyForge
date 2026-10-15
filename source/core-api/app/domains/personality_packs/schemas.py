from pydantic import BaseModel, Field


class PersonalityPackOut(BaseModel):
	key: str
	title: str = ""


class PersonalityPackListOut(BaseModel):
	items: list[PersonalityPackOut] = Field(default_factory=list)
	total: int = 0
