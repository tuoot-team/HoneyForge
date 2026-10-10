from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InteractionLevel(str, Enum):
	low = "low"
	medium = "medium"
	high = "high"


class ServiceBlock(BaseModel):
	"""One emulated service in the constructor."""
	name: str = Field(examples=["ssh", "http"])
	protocol: str = Field(default="tcp", examples=["tcp", "udp"])
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	options: dict[str, Any] = Field(default_factory=dict)


class BannerBlock(BaseModel):
	service: str = Field(description="service name this banner belongs to")
	text: str = Field(description="banner / fake version string")


class CredentialBlock(BaseModel):
	username: str
	password: str
	service: str | None = None
	note: str = ""


class LoggingBlock(BaseModel):
	capture_credentials: bool = True
	capture_payloads: bool = True
	capture_source_meta: bool = True
	# timing realism for Mid emulators (ms); 0 = off
	auth_delay_ms_min: int = Field(default=0, ge=0)
	auth_delay_ms_max: int = Field(default=0, ge=0)


class MaskBlock(BaseModel):
	beacon_interval_sec: int = Field(default=30, ge=5)
	jitter_pct: int = Field(default=30, ge=0, le=100)
	beacon_jitter_sec: int = Field(default=10, ge=0)
	collector_path_set: list[str] = Field(
		default_factory=lambda: ["/v1/metrics", "/cdn/edge-check", "/api/telemetry/batch"]
	)
	user_agent: str = Field(default="Mozilla/5.0 HoneyForgeAgent/0.1")
	tls_fingerprint_profile: str = Field(default="browser-like")
	cover_urls: list[str] = Field(
		default_factory=lambda: ["/favicon.ico", "/robots.txt"]
	)
	process_name: str = Field(default="svchost")
	decoy_content_seed: str = Field(
		default="",
		description="per-instance seed for canary asymmetry; empty = derive from trap id",
	)
	service_personality: str = Field(
		default="",
		description="personality pack key, e.g. ubuntu-22.04-ssh",
	)


class ProfileBlocks(BaseModel):
	services: list[ServiceBlock] = Field(default_factory=list)
	banners: list[BannerBlock] = Field(default_factory=list)
	credentials: list[CredentialBlock] = Field(default_factory=list)
	logging: LoggingBlock = Field(default_factory=LoggingBlock)
	mask: MaskBlock = Field(default_factory=MaskBlock)


class ProfileCreate(BaseModel):
	name: str
	description: str = ""
	interaction_level: InteractionLevel
	blocks: ProfileBlocks = Field(default_factory=ProfileBlocks)


class ProfileUpdate(BaseModel):
	name: str | None = None
	description: str | None = None
	interaction_level: InteractionLevel | None = None
	blocks: ProfileBlocks | None = None


class ProfileOut(BaseModel):
	id: UUID
	name: str
	description: str
	interaction_level: InteractionLevel
	blocks: ProfileBlocks
	config_version: int
	config_hash: str
	created_at: datetime
	updated_at: datetime

	model_config = {"from_attributes": True}


class ProfileSchemaDoc(BaseModel):
	interaction_levels: list[str]
	block_keys: list[str]
	example: ProfileCreate
