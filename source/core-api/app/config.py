from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	DEBUG: bool = False
	# true = локальная SQLite без Docker/Postgres (фаза 1 удобно гонять на ноуте)
	USE_SQLITE: bool = False

	API_HOST: str = "0.0.0.0"
	API_PORT: int = 8000

	POSTGRES_HOST: str = "localhost"
	POSTGRES_PORT: int = 5432
	POSTGRES_USER: str = "honeyforge"
	POSTGRES_PASSWORD: str = "honeyforge"
	POSTGRES_DB: str = "honeyforge"

	REDIS_URL: str = "redis://localhost:6379/0"

	OPERATOR_PASSWORD: str = "change-me"
	OPERATOR_TOKEN_SECRET: str = "dev-change-me-operator-secret"
	PUBLIC_BASE_URL: str = "http://localhost"

	# минуты без heartbeat -> offline
	AGENT_STALE_MINUTES: int = 5
	PAIRING_TTL_MINUTES: int = 15

	@property
	def database_url(self) -> str:
		if self.USE_SQLITE:
			return "sqlite+pysqlite:///./honeyforge_local.db"
		return (
			f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
			f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
		)


@lru_cache
def get_Settings() -> Settings:
	return Settings()
