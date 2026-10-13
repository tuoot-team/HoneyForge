from pydantic import BaseModel, Field


class DeployAgentIn(BaseModel):
	host: str = Field(min_length=1, description="IP или hostname хоста ловушки")
	user: str = Field(default="root", min_length=1)
	password: str = Field(min_length=1)
	port: int = Field(default=22, ge=1, le=65535)
	# Адрес центра, который видит хост. Пусто - PUBLIC_BASE_URL из .env
	center_url: str | None = None


class DeployAgentOut(BaseModel):
	device_code: str
	host: str
	user: str
	port: int
	center_url: str
