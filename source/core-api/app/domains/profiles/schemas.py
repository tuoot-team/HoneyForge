from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.texts import (
	MSG_PROFILE_AUTH_LIST,
	MSG_PROFILE_DELAY,
	MSG_PROFILE_DUP_CRED,
	MSG_PROFILE_DUP_PORT,
	MSG_PROFILE_DUP_SERVICE_ID,
	MSG_PROFILE_HIGH_UNAVAILABLE,
	MSG_PROFILE_LEVEL_MISMATCH,
	MSG_PROFILE_SSH_BANNER,
	MSG_PROFILE_SSH_SHELL_AUTH,
	MSG_PROFILE_BAIT_SERVICE,
	MSG_PROFILE_DUP_TOKEN,
	MSG_PROFILE_TOKEN_CRED,
	MSG_PROFILE_TOKEN_PATH,
	MSG_PROFILE_TOKEN_SERVICE,
	MSG_PROFILE_UNKNOWN_CREDS,
)


class InteractionLevel(str, Enum):
	low = "low"
	medium = "medium"
	high = "high"


class BannerModule(BaseModel):
	enabled: bool = True
	version: str = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"


class AuthMode(str, Enum):
	allow_all = "allow_all"
	allow_listed = "allow_listed"
	second_attempt_sticky = "second_attempt_sticky"


class AuthModule(BaseModel):
	enabled: bool = True
	mode: AuthMode = AuthMode.allow_all
	credential_ids: list[str] = Field(default_factory=list)
	delay_ms_min: int = Field(default=0, ge=0)
	delay_ms_max: int = Field(default=0, ge=0)
	sticky_ttl_hours: int = Field(default=72, ge=1, le=8760)

	@model_validator(mode="before")
	@classmethod
	def accept_DelayPair(cls, value: Any) -> Any:
		# В наброске схемы задержка была парой delay_ms: [min, max].
		if not isinstance(value, dict) or "delay_ms" not in value:
			return value
		raw = dict(value)
		pair = raw.pop("delay_ms")
		if isinstance(pair, (list, tuple)) and len(pair) == 2:
			raw.setdefault("delay_ms_min", pair[0])
			raw.setdefault("delay_ms_max", pair[1])
		return raw

	@model_validator(mode="after")
	def validate_Auth(self) -> "AuthModule":
		if self.delay_ms_max < self.delay_ms_min:
			raise ValueError(MSG_PROFILE_DELAY)
		if self.enabled and self.mode == AuthMode.allow_listed and not self.credential_ids:
			raise ValueError(MSG_PROFILE_AUTH_LIST)
		return self


class ShellModule(BaseModel):
	enabled: bool = True
	fs_pack: str = "ubuntu-22.04"
	max_session_sec: int = Field(default=600, ge=10, le=86400)


class SshModules(BaseModel):
	banner: BannerModule = Field(default_factory=BannerModule)
	auth: AuthModule = Field(default_factory=AuthModule)
	shell: ShellModule = Field(default_factory=ShellModule)

	@model_validator(mode="after")
	def validate_Dependencies(self) -> "SshModules":
		if not self.banner.enabled:
			raise ValueError(MSG_PROFILE_SSH_BANNER)
		if self.shell.enabled and not self.auth.enabled:
			raise ValueError(MSG_PROFILE_SSH_SHELL_AUTH)
		return self


class SshServiceBlock(BaseModel):
	type: Literal["ssh"] = "ssh"
	id: str = Field(default="ssh", min_length=1)
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	modules: SshModules = Field(default_factory=SshModules)


class HttpPersonalityModule(BaseModel):
	enabled: bool = True
	server: str = "Microsoft-IIS/10.0"
	title: str = "IIS Windows Server"
	headers: dict[str, str] = Field(default_factory=dict)


class HttpAuthModule(AuthModule):
	enabled: bool = False
	path: str = "/admin"
	realm: str = "Restricted"


class HttpRoute(BaseModel):
	path: str
	methods: list[str] = Field(default_factory=lambda: ["GET"])
	status: int = Field(default=200, ge=100, le=599)
	content_type: str = "text/html; charset=utf-8"
	body: str = ""


class HttpRoutesModule(BaseModel):
	routes: list[HttpRoute] = Field(default_factory=list)
	default_status: int = Field(default=404, ge=100, le=599)
	default_body: str = "404 - File or directory not found."


class HttpModules(BaseModel):
	personality: HttpPersonalityModule = Field(default_factory=HttpPersonalityModule)
	auth: HttpAuthModule = Field(default_factory=HttpAuthModule)
	routes: HttpRoutesModule = Field(default_factory=HttpRoutesModule)


class HttpServiceBlock(BaseModel):
	type: Literal["http"] = "http"
	id: str = Field(default="http", min_length=1)
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	modules: HttpModules = Field(default_factory=HttpModules)


class TcpBannerModules(BaseModel):
	banner: str = ""


class TcpBannerServiceBlock(BaseModel):
	type: Literal["tcp_banner"] = "tcp_banner"
	id: str = Field(default="tcp", min_length=1)
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	modules: TcpBannerModules = Field(default_factory=TcpBannerModules)


class DbBannerModule(BaseModel):
	enabled: bool = True
	version: str = ""


class SessionModule(BaseModel):
	enabled: bool = True
	max_session_sec: int = Field(default=120, ge=5, le=86400)


class DbModules(BaseModel):
	banner: DbBannerModule = Field(default_factory=DbBannerModule)
	auth: AuthModule = Field(default_factory=AuthModule)
	session: SessionModule = Field(default_factory=SessionModule)


class PostgresServiceBlock(BaseModel):
	type: Literal["postgres"] = "postgres"
	id: str = Field(default="postgres", min_length=1)
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	modules: DbModules = Field(default_factory=DbModules)


class RedisServiceBlock(BaseModel):
	type: Literal["redis"] = "redis"
	id: str = Field(default="redis", min_length=1)
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	modules: DbModules = Field(default_factory=DbModules)


class MysqlServiceBlock(BaseModel):
	type: Literal["mysql"] = "mysql"
	id: str = Field(default="mysql", min_length=1)
	port: int = Field(ge=1, le=65535)
	enabled: bool = True
	modules: DbModules = Field(default_factory=DbModules)


ServiceBlock = Annotated[
	SshServiceBlock | HttpServiceBlock | TcpBannerServiceBlock | PostgresServiceBlock | RedisServiceBlock | MysqlServiceBlock,
	Field(discriminator="type"),
]


class CredentialBlock(BaseModel):
	id: str = Field(min_length=1)
	username: str
	password: str
	note: str = ""


class LoggingBlock(BaseModel):
	capture_credentials: bool = True
	capture_payloads: bool = True
	capture_source_meta: bool = True
	# Задержка входа живёт в modules.auth, не здесь.
	# Старые ключи auth_delay_ms_* читает только миграция плоского профиля.


class JitterMethod(BaseModel):
	enabled: bool = True
	beacon_interval_sec: int = Field(default=30, ge=5)
	jitter_pct: int = Field(default=30, ge=0, le=100)


class CoverMethod(BaseModel):
	enabled: bool = True
	urls: list[str] = Field(default_factory=lambda: ["/favicon.ico", "/robots.txt"])


class PathRotationMethod(BaseModel):
	enabled: bool = True
	paths: list[str] = Field(
		default_factory=lambda: ["/v1/metrics", "/cdn/edge-check"]
	)


class MimicryMethod(BaseModel):
	enabled: bool = True
	user_agent: str = Field(
		default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
	)
	tls_fingerprint_profile: str = Field(default="browser-like")


class ProcessMaskMethod(BaseModel):
	enabled: bool = True
	name: str = "metricsd"


class CollectionMode(str, Enum):
	agent = "agent"
	courier = "courier"


class CourierMethod(BaseModel):
	"""Доставка логов через третьего агента-курьера (без исходящего batch с ловушки)."""

	enabled: bool = False
	collect_interval_sec: int = Field(default=300, ge=15, le=86400)


class MaskBlock(BaseModel):
	"""Способы сокрытия канала агент → центр. Каждый способ включается отдельно."""

	collection_mode: CollectionMode = CollectionMode.agent
	courier: CourierMethod = Field(default_factory=CourierMethod)
	jitter: JitterMethod = Field(default_factory=JitterMethod)
	cover: CoverMethod = Field(default_factory=CoverMethod)
	path_rotation: PathRotationMethod = Field(default_factory=PathRotationMethod)
	mimicry: MimicryMethod = Field(default_factory=MimicryMethod)
	process_mask: ProcessMaskMethod = Field(default_factory=ProcessMaskMethod)
	decoy_content_seed: str = Field(
		default="",
		description="per-instance seed for canary asymmetry; empty = derive from trap id",
	)
	service_personality: str = Field(
		default="",
		description="personality pack key, e.g. ubuntu-22.04-ssh",
	)

	@model_validator(mode="before")
	@classmethod
	def migrate_FlatMask(cls, value: Any) -> Any:
		if not isinstance(value, dict):
			return value
		flat_keys = {
			"beacon_interval_sec",
			"jitter_pct",
			"beacon_jitter_sec",
			"collector_path_set",
			"cover_urls",
			"user_agent",
			"tls_fingerprint_profile",
			"process_name",
		}
		if not flat_keys.intersection(value) or "jitter" in value:
			return value
		cover_urls = value.get("cover_urls", ["/favicon.ico", "/robots.txt"])
		paths = value.get("collector_path_set", ["/v1/metrics", "/cdn/edge-check"])
		process_name = value.get("process_name", "metricsd") or "metricsd"
		return {
			"collection_mode": value.get("collection_mode", "agent"),
			"courier": value.get("courier") or {"enabled": False, "collect_interval_sec": 300},
			"jitter": {
				"enabled": True,
				"beacon_interval_sec": value.get("beacon_interval_sec", 30),
				"jitter_pct": value.get("jitter_pct", 30),
			},
			"cover": {
				"enabled": bool(cover_urls),
				"urls": cover_urls or ["/favicon.ico", "/robots.txt"],
			},
			"path_rotation": {
				"enabled": bool(paths),
				"paths": paths or ["/v1/metrics", "/cdn/edge-check"],
			},
			"mimicry": {
				"enabled": True,
				"user_agent": value.get(
					"user_agent",
					"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
				),
				"tls_fingerprint_profile": value.get("tls_fingerprint_profile", "browser-like"),
			},
			"process_mask": {
				"enabled": True,
				"name": process_name,
			},
			"decoy_content_seed": value.get("decoy_content_seed", ""),
			"service_personality": value.get("service_personality", ""),
		}

	@model_validator(mode="after")
	def sync_Collection_Mode(self) -> "MaskBlock":
		# Курьер и классические mask взаимоисключающи.
		if self.courier.enabled or self.collection_mode == CollectionMode.courier:
			self.collection_mode = CollectionMode.courier
			self.courier = CourierMethod(
				enabled=True,
				collect_interval_sec=self.courier.collect_interval_sec,
			)
			self.jitter = self.jitter.model_copy(update={"enabled": False})
			self.cover = self.cover.model_copy(update={"enabled": False})
			self.path_rotation = self.path_rotation.model_copy(update={"enabled": False})
			self.mimicry = self.mimicry.model_copy(update={"enabled": False})
			self.process_mask = self.process_mask.model_copy(update={"enabled": False})
			return self
		classic_on = any(
			(
				self.jitter.enabled,
				self.cover.enabled,
				self.path_rotation.enabled,
				self.mimicry.enabled,
				self.process_mask.enabled,
			)
		)
		if classic_on:
			self.collection_mode = CollectionMode.agent
			self.courier = CourierMethod(
				enabled=False,
				collect_interval_sec=self.courier.collect_interval_sec,
			)
		return self


class BaitKind(str, Enum):
	file = "file"
	http_route = "http_route"


class BaitBlock(BaseModel):
	"""Подсказка на соседний порт мини-парка (файл shell FS или HTTP route)."""

	kind: BaitKind
	path: str = Field(min_length=1, max_length=512)
	body: str = Field(default="", max_length=16384)
	service_id: str = Field(default="", max_length=128)


class HoneytokenKind(str, Enum):
	file = "file"
	url = "url"
	key = "key"
	credential = "credential"


class HoneytokenBlock(BaseModel):
	"""Canary-токен: hit → событие honeytoken_hit."""

	id: str = Field(min_length=1, max_length=128)
	kind: HoneytokenKind
	path: str = Field(default="", max_length=512)
	body: str = Field(default="", max_length=16384)
	service_id: str = Field(default="", max_length=128)
	username: str = Field(default="", max_length=256)
	password: str = Field(default="", max_length=256)


class ProfileBlocks(BaseModel):
	services: list[ServiceBlock] = Field(default_factory=list)
	credentials: list[CredentialBlock] = Field(default_factory=list)
	baits: list[BaitBlock] = Field(default_factory=list)
	honeytokens: list[HoneytokenBlock] = Field(default_factory=list)
	logging: LoggingBlock = Field(default_factory=LoggingBlock)
	mask: MaskBlock = Field(default_factory=MaskBlock)

	@model_validator(mode="before")
	@classmethod
	def migrate_LegacyBlocks(cls, value: Any) -> Any:
		if not isinstance(value, dict):
			return value
		services = value.get("services") or []
		has_legacy_services = any(
			isinstance(item, dict) and "type" not in item
			for item in services
		)
		migrated = dict(value)
		credentials, credential_ids_for_service = _normalize_Credentials(
			value.get("credentials") or []
		)
		migrated["credentials"] = credentials
		if not has_legacy_services:
			return migrated
		banners = {
			item.get("service"): item.get("text", "")
			for item in value.get("banners", [])
			if isinstance(item, dict)
		}
		logging = value.get("logging") or {}
		migrated_services: list[dict[str, Any]] = []
		for index, item in enumerate(services):
			if not isinstance(item, dict):
				continue
			if "type" in item:
				migrated_services.append(item)
				continue
			name = str(item.get("name") or "tcp_banner")
			common = {
				"id": f"{name}-{index + 1}",
				"port": item.get("port"),
				"enabled": item.get("enabled", True),
			}
			banner = banners.get(name, "")
			service_ids = _ids_ForService(name, credential_ids_for_service)
			# Плоский ssh без кредов и без delay был баннером (low), не fake-shell.
			interactive = bool(service_ids) or int(logging.get("auth_delay_ms_min") or 0) > 0
			if "ssh" in name.lower() or str(banner).lstrip().upper().startswith("SSH-"):
				migrated_services.append({
					"type": "ssh",
					**common,
					"modules": _legacy_SshModules(banner, logging, service_ids, interactive),
				})
			elif name.lower() in ("http", "https"):
				migrated_services.append({
					"type": "http",
					**common,
					"modules": _legacy_HttpModules(banner, logging, service_ids, interactive),
				})
			else:
				migrated_services.append({
					"type": "tcp_banner",
					**common,
					"modules": {"banner": banner},
				})
		migrated["services"] = migrated_services
		migrated.pop("banners", None)
		return migrated

	@model_validator(mode="after")
	def validate_References(self) -> "ProfileBlocks":
		credential_ids = [item.id for item in self.credentials]
		if len(credential_ids) != len(set(credential_ids)):
			raise ValueError(MSG_PROFILE_DUP_CRED)
		service_ids = [item.id for item in self.services]
		if len(service_ids) != len(set(service_ids)):
			raise ValueError(MSG_PROFILE_DUP_SERVICE_ID)
		enabled_ports = [item.port for item in self.services if item.enabled]
		if len(enabled_ports) != len(set(enabled_ports)):
			raise ValueError(MSG_PROFILE_DUP_PORT)
		known = set(credential_ids)
		for service in self.services:
			auth = _auth_Module(service)
			if auth is None:
				continue
			missing = set(auth.credential_ids) - known
			if missing:
				raise ValueError(
					MSG_PROFILE_UNKNOWN_CREDS.format(
						service_id=service.id,
						missing=sorted(missing),
					)
				)
		known_services = set(service_ids)
		for bait in self.baits:
			if bait.kind == BaitKind.http_route and bait.service_id:
				if bait.service_id not in known_services:
					raise ValueError(
						MSG_PROFILE_BAIT_SERVICE.format(service_id=bait.service_id)
					)
		token_ids = [item.id for item in self.honeytokens]
		if len(token_ids) != len(set(token_ids)):
			raise ValueError(MSG_PROFILE_DUP_TOKEN)
		for token in self.honeytokens:
			if token.kind == HoneytokenKind.url:
				if not token.path:
					raise ValueError(
						MSG_PROFILE_TOKEN_PATH.format(kind=token.kind.value, token_id=token.id)
					)
				if not token.service_id or token.service_id not in known_services:
					raise ValueError(
						MSG_PROFILE_TOKEN_SERVICE.format(service_id=token.service_id or "?")
					)
			elif token.kind == HoneytokenKind.credential:
				if not token.username or not token.password:
					raise ValueError(MSG_PROFILE_TOKEN_CRED.format(token_id=token.id))
			elif token.kind in (HoneytokenKind.file, HoneytokenKind.key):
				if not token.path:
					raise ValueError(
						MSG_PROFILE_TOKEN_PATH.format(kind=token.kind.value, token_id=token.id)
					)
		return self


def _auth_Module(service: ServiceBlock) -> AuthModule | None:
	if isinstance(service, (SshServiceBlock, HttpServiceBlock, PostgresServiceBlock, RedisServiceBlock, MysqlServiceBlock)):
		return service.modules.auth
	return None


def _normalize_Credentials(
	raw_items: list[Any],
) -> tuple[list[Any], dict[str | None, list[str]]]:
	credentials: list[Any] = []
	ids_for_service: dict[str | None, list[str]] = {}
	for index, item in enumerate(raw_items):
		if not isinstance(item, dict):
			credentials.append(item)
			continue
		credential = dict(item)
		credential.setdefault("id", f"credential-{index + 1}")
		service_name = credential.pop("service", None)
		credentials.append(credential)
		key = None if service_name is None else str(service_name).lower()
		ids_for_service.setdefault(key, []).append(str(credential["id"]))
	return credentials, ids_for_service


def _ids_ForService(name: str, ids_for_service: dict[str | None, list[str]]) -> list[str]:
	specific = ids_for_service.get(name.lower(), [])
	shared = ids_for_service.get(None, [])
	return specific + shared


def _legacy_SshModules(
	banner: str,
	logging: dict[str, Any],
	credential_ids: list[str],
	interactive: bool,
) -> dict[str, Any]:
	if not interactive:
		return {
			"banner": {"enabled": True, "version": banner or BannerModule().version},
			"auth": {"enabled": False},
			"shell": {"enabled": False},
		}
	mode = "allow_listed" if credential_ids else "allow_all"
	return {
		"banner": {"enabled": True, "version": banner or BannerModule().version},
		"auth": {
			"enabled": True,
			"mode": mode,
			"credential_ids": credential_ids,
			"delay_ms_min": logging.get("auth_delay_ms_min", 0),
			"delay_ms_max": logging.get("auth_delay_ms_max", 0),
		},
		"shell": {"enabled": True},
	}


def _legacy_HttpModules(
	banner: str,
	logging: dict[str, Any],
	credential_ids: list[str],
	interactive: bool,
) -> dict[str, Any]:
	return {
		"personality": {"server": banner or "nginx/1.24.0"},
		"auth": {
			"enabled": interactive,
			"mode": "allow_listed" if credential_ids else "allow_all",
			"credential_ids": credential_ids,
			"delay_ms_min": logging.get("auth_delay_ms_min", 0) if interactive else 0,
			"delay_ms_max": logging.get("auth_delay_ms_max", 0) if interactive else 0,
			"path": "/admin",
		},
		"routes": {},
	}


def _service_Level(service: ServiceBlock) -> InteractionLevel:
	if isinstance(service, TcpBannerServiceBlock):
		return InteractionLevel.low
	if isinstance(service, (HttpServiceBlock, PostgresServiceBlock, RedisServiceBlock, MysqlServiceBlock)):
		return InteractionLevel.medium
	if isinstance(service, SshServiceBlock) and (
		service.modules.auth.enabled or service.modules.shell.enabled
	):
		return InteractionLevel.medium
	return InteractionLevel.low


def derive_InteractionLevel(blocks: ProfileBlocks) -> InteractionLevel:
	"""Честный уровень: low = баннер, medium = auth/shell/http. High здесь не возникает."""
	rank = {InteractionLevel.low: 0, InteractionLevel.medium: 1, InteractionLevel.high: 2}
	derived = InteractionLevel.low
	for service in blocks.services:
		if not service.enabled:
			continue
		current = _service_Level(service)
		if rank[current] > rank[derived]:
			derived = current
	return derived


def assert_LevelMatches(level: InteractionLevel | str, blocks: ProfileBlocks) -> None:
	declared = InteractionLevel(level)
	if declared == InteractionLevel.high:
		raise ValueError(MSG_PROFILE_HIGH_UNAVAILABLE)
	actual = derive_InteractionLevel(blocks)
	if declared != actual:
		raise ValueError(
			MSG_PROFILE_LEVEL_MISMATCH.format(
				declared=declared.value,
				actual=actual.value,
			)
		)


class ProfileCreate(BaseModel):
	name: str
	description: str = ""
	interaction_level: InteractionLevel
	blocks: ProfileBlocks = Field(default_factory=ProfileBlocks)

	@model_validator(mode="after")
	def validate_Level(self) -> "ProfileCreate":
		assert_LevelMatches(self.interaction_level, self.blocks)
		return self


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
	service_types: list[str]
	auth_modes: list[str]
	mask_methods: list[str]
	example: ProfileCreate
