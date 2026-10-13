from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Каталог пакетов рядом с app/../fs-packs
_DEFAULT_FS_PACKS_DIR = str(Path(__file__).resolve().parents[1] / "fs-packs")


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	DEBUG: bool = False
	# true = локальная SQLite без Docker/Postgres
	USE_SQLITE: bool = False

	API_HOST: str = "0.0.0.0"
	API_PORT: int = 8000

	POSTGRES_HOST: str = "localhost"
	POSTGRES_PORT: int = 5432
	POSTGRES_USER: str = "honeyforge"
	POSTGRES_PASSWORD: str = "honeyforge"
	POSTGRES_DB: str = "honeyforge"

	OPERATOR_PASSWORD: str = "change-me"
	OPERATOR_TOKEN_SECRET: str = "dev-change-me-operator-secret"
	PUBLIC_BASE_URL: str = "http://localhost"

	AGENT_STALE_MINUTES: int = 5
	PAIRING_TTL_MINUTES: int = 15

	FS_PACKS_DIR: str = _DEFAULT_FS_PACKS_DIR
	FS_PACK_MAX_BYTES: int = 32 * 1024 * 1024

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
