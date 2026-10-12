from __future__ import annotations

import getpass
import time

from colorama import Fore, Style

import client
from commands.deploy import DeployError, center_IsLoopback, install_AgentOverSsh
from texts import (
	MsgApiError,
	SetupAbortText,
	SetupDoneText,
	SetupAskReachableCenterText,
	SetupAskSshHostText,
	SetupAskSshInstallText,
	SetupAskSshPasswordText,
	SetupAskSshPortText,
	SetupAskSshUserText,
	SetupInstallCard,
	SetupIntroText,
	SetupRolePresetsHelp,
	SetupStep1Header,
	SetupStep1TipRole,
	SetupStep1TipSite,
	SetupStep2Header,
	SetupStep2TipCreds,
	SetupStep2TipService,
	SetupStep3Header,
	SetupStep3TipJitter,
	SetupStep3TipMask,
	SetupStep4ApprovedText,
	SetupStep4Header,
	SetupStep4TipCodeTtl,
	SetupStep4TipInstall,
	SetupStep4WaitingText,
	SetupStep5Header,
	SetupStep5TipOnline,
	SetupStep5TipProbe,
	SetupAskBeaconText,
	SetupAskCoverText,
	SetupAskCoverUrlsText,
	SetupAskJitterPctText,
	SetupAskJitterText,
	SetupAskMimicryText,
	SetupAskPathRotationText,
	SetupAskProcessMaskText,
	SetupAskProcessNameAgainText,
	SetupAskProcessNameText,
	SetupAskUserAgentText,
	SetupAuthBecomesLowText,
	SetupAuthModesHelp,
	SetupConcealHelp,
	SetupCoverUrlsDefault,
	SetupProcessNameBadText,
	SetupUserAgentDefault,
	ProfilePortConflictText,
	SetupAskTrapSetText,
	SetupRoutesTipText,
	SetupTrapListHelp,
	SetupTrapProgressText,
	SetupTrapSetBadText,
	SetupTrapSetEmptyText,
	SetupShellNeedsAuthText,
	SetupSshCodeText,
	SetupSshFailedText,
	SetupSshInstallTip,
	SetupSshLocalCenterText,
	SetupSshManualFallbackText,
	print_Attention,
	print_OpsLine,
	print_SetupTip,
)

ROLE_PRESETS: dict[str, dict] = {
	"1": {
		"key": "corp-ssh",
		"label": "корпоративный SSH (DMZ)",
		"level": "medium",
		"service": "ssh",
		"port": 22,
		"banner": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1",
		"creds": True,
		"username": "root",
		"password": "admin",
		"auth_mode": "second_attempt_sticky",
		"shell": True,
		"fs_pack": "ubuntu-22.04",
		"auth_path": "/admin",
		"sticky_ttl": 72,
	},
	"2": {
		"key": "edge-http",
		"label": "веб-админка / edge HTTP",
		"level": "medium",
		"service": "http",
		"port": 8080,
		"banner": "nginx/1.24.0",
		"creds": True,
		"username": "admin",
		"password": "admin123",
		"auth_mode": "allow_listed",
		"shell": False,
		"fs_pack": "",
		"auth_path": "/admin",
		"sticky_ttl": 72,
	},
	"3": {
		"key": "scan-bait",
		"label": "детектор сканов (только баннер)",
		"level": "low",
		"service": "ssh",
		"port": 22,
		"banner": "SSH-2.0-OpenSSH_7.4",
		"creds": False,
		"username": "",
		"password": "",
		"auth_mode": "off",
		"shell": False,
		"fs_pack": "ubuntu-22.04",
		"auth_path": "/admin",
		"sticky_ttl": 72,
	},
	"4": {
		"key": "custom",
		"label": "ручная сборка модулей",
		"level": "medium",
		"service": "ssh",
		"port": 22,
		"banner": "SSH-2.0-OpenSSH_8.9p1",
		"creds": True,
		"username": "root",
		"password": "admin",
		"auth_mode": "second_attempt_sticky",
		"shell": True,
		"fs_pack": "ubuntu-22.04",
		"auth_path": "/admin",
		"sticky_ttl": 72,
	},
	"5": {
		"key": "data-stores",
		"label": "Postgres + Redis + MySQL",
		"bundle": True,
		"level": "medium",
		"service": "postgres",
		"port": 5432,
		"banner": "14.10 (Ubuntu 14.10-0ubuntu0.22.04.1)",
		"creds": True,
		"username": "postgres",
		"password": "postgres",
		"auth_mode": "allow_listed",
		"shell": False,
		"fs_pack": "",
		"auth_path": "/admin",
		"sticky_ttl": 72,
		"services": [
			{"service": "postgres", "port": 5432, "banner": "14.10 (Ubuntu 14.10-0ubuntu0.22.04.1)"},
			{"service": "redis", "port": 6379, "banner": "6.2.14"},
			{"service": "mysql", "port": 3306, "banner": "5.7.42-log"},
		],
	},
}

DEFAULT_PORTS = {
	"ssh": 22,
	"http": 8080,
	"tcp_banner": 2121,
	"postgres": 5432,
	"redis": 6379,
	"mysql": 3306,
}
DEFAULT_BANNERS = {
	"ssh": "SSH-2.0-OpenSSH_8.9p1",
	"http": "nginx/1.24.0",
	"tcp_banner": "220 ftp ready",
	"postgres": "14.10 (Ubuntu 14.10-0ubuntu0.22.04.1)",
	"mysql": "5.7.42-log",
	"redis": "6.2.14",
}
KNOWN_SERVICES = tuple(DEFAULT_PORTS)


def _ask(prompt: str, default: str | None = None) -> str | None:
	suffix = f" [{default}]" if default is not None else ""
	raw = input(Fore.GREEN + f"{prompt}{suffix}: " + Style.RESET_ALL).strip()
	if raw.lower() in ("q", "quit", "exit", "abort"):
		raise KeyboardInterrupt
	if not raw:
		return default
	return raw


def _ask_YesNo(prompt: str, default_yes: bool = True) -> bool:
	hint = "Y/n" if default_yes else "y/N"
	raw = _ask(f"{prompt} ({hint})", "y" if default_yes else "n")
	if raw is None:
		return default_yes
	return raw.lower() in ("y", "yes", "д", "да", "1")


def _pause(msg: str = "Enter - продолжить") -> None:
	_ask(msg, "")


def _step_Header(text: str) -> None:
	print()
	print(Fore.CYAN + Style.BRIGHT + text + Style.RESET_ALL)
	print(Fore.CYAN + ("-" * min(56, max(20, len(text)))) + Style.RESET_ALL)


def _status_Color(status: str) -> str:
	key = (status or "?").lower()
	if key == "online":
		return Fore.GREEN + status + Style.RESET_ALL
	if key == "pending":
		return Fore.YELLOW + status + Style.RESET_ALL
	if key == "offline":
		return Fore.RED + status + Style.RESET_ALL
	return status


def _pick_Role() -> dict:
	print(SetupRolePresetsHelp)
	print_SetupTip(SetupStep1TipRole)
	choice = _ask("Роль приманки (1-5)", "1") or "1"
	return dict(ROLE_PRESETS.get(choice, ROLE_PRESETS["1"]))


def _ask_Int(prompt: str, default: int, low: int, high: int) -> int:
	raw = _ask(prompt, str(default)) or str(default)
	try:
		value = int(raw)
	except ValueError:
		value = default
	return max(low, min(high, value))


def _ask_Bait(role: dict, service: str) -> dict:
	print_SetupTip(SetupStep2TipCreds)
	username = _ask("Логин приманки", role.get("username") or "root") or "root"
	password = _ask("Пароль приманки", role.get("password") or "admin") or "admin"
	return {
		"id": f"{service}-bait",
		"username": username,
		"password": password,
		"note": "bait",
	}


def _ask_AuthModule(role: dict, service: str) -> dict:
	print_OpsLine("модуль", "auth")
	print(SetupAuthModesHelp)
	default_choice = {
		"off": "0",
		"allow_all": "1",
		"allow_listed": "2",
		"second_attempt_sticky": "3",
	}.get(str(role.get("auth_mode") or "off"), "0")
	raw_choice = (_ask("Режим входа (0-3)", default_choice) or default_choice).strip()
	auth_mode = {
		"0": "off",
		"1": "allow_all",
		"2": "allow_listed",
		"3": "second_attempt_sticky",
	}.get(raw_choice, "allow_all")

	credentials: list[dict] = []
	sticky_ttl = int(role.get("sticky_ttl") or 72)
	if auth_mode == "allow_listed":
		credentials.append(_ask_Bait(role, service))
	elif auth_mode == "second_attempt_sticky":
		if _ask_YesNo("Пускать только учётку-приманку, не любой пароль", True):
			credentials.append(_ask_Bait(role, service))
		else:
			print_SetupTip("Со второй попытки примется любой пароль и привяжется к IP.")
		sticky_ttl = _ask_Int("Сколько часов помнить пароль за IP", sticky_ttl, 1, 8760)
	elif auth_mode == "off" and service == "ssh":
		print_Attention(SetupAuthBecomesLowText)

	auth_path = "/admin"
	if service == "http" and auth_mode != "off":
		auth_path = _ask("Путь входа", role.get("auth_path") or "/admin") or "/admin"
		if not auth_path.startswith("/"):
			auth_path = "/" + auth_path
	return {
		"auth_mode": auth_mode,
		"credentials": credentials,
		"sticky_ttl": sticky_ttl,
		"auth_path": auth_path,
	}


def _configure_Modules(role: dict) -> dict:
	"""Слоты сервиса: banner/auth/shell или personality/auth/routes."""
	service = role["service"]
	port = int(role["port"])
	print_OpsLine("сервис", f"{service}:{port}")

	if service == "tcp_banner":
		print_OpsLine("модуль", "banner")
		banner = _ask("Текст баннера", role.get("banner") or "220 ftp ready") or "220 ftp ready"
		face = {
			"service": service,
			"port": port,
			"banner": banner,
			"credentials": [],
			"credential_ids": [],
			"auth_mode": "off",
			"sticky_ttl": 72,
			"shell_enabled": False,
			"fs_pack": "",
			"auth_path": "/",
			"level": "low",
		}
		print_OpsLine("уровень", "low")
		return face

	if service == "ssh":
		print_OpsLine("модуль", "banner")
		banner = _ask(
			"Версия баннера",
			role.get("banner") or "SSH-2.0-OpenSSH_8.9p1",
		) or "SSH-2.0-OpenSSH_8.9p1"
		auth = _ask_AuthModule(role, service)
		shell_enabled = False
		fs_pack = role.get("fs_pack") or "ubuntu-22.04"
		if auth["auth_mode"] == "off":
			print_Attention(SetupShellNeedsAuthText)
		else:
			print_OpsLine("модуль", "shell")
			shell_enabled = _ask_YesNo("Пускать в ограниченный shell", bool(role.get("shell", True)))
			if shell_enabled:
				fs_pack = _ask("Пакет файловой системы", fs_pack) or fs_pack
		level = "low" if auth["auth_mode"] == "off" else "medium"
	elif service in ("postgres", "redis", "mysql"):
		print_OpsLine("модуль", "banner")
		banner = _ask("Версия", role.get("banner") or DEFAULT_BANNERS[service]) or DEFAULT_BANNERS[service]
		auth = _ask_AuthModule(role, service)
		shell_enabled = False
		fs_pack = ""
		level = "medium"
	else:
		print_OpsLine("модуль", "personality")
		banner = _ask("Заголовок Server", role.get("banner") or "nginx/1.24.0") or "nginx/1.24.0"
		auth = _ask_AuthModule(role, service)
		print_OpsLine("модуль", "routes")
		print_SetupTip(SetupRoutesTipText)
		shell_enabled = False
		fs_pack = ""
		level = "medium"

	linked_ids = []
	if auth["auth_mode"] in ("allow_listed", "second_attempt_sticky"):
		linked_ids = [item["id"] for item in auth["credentials"]]
	face = {
		"service": service,
		"port": port,
		"banner": banner,
		"credentials": auth["credentials"],
		"credential_ids": linked_ids,
		"auth_mode": auth["auth_mode"],
		"sticky_ttl": auth["sticky_ttl"],
		"shell_enabled": shell_enabled,
		"fs_pack": fs_pack,
		"auth_path": auth["auth_path"],
		"level": level,
	}
	print_OpsLine("уровень", level)
	return face


def _ask_UrlList(prompt: str, default: str) -> list[str]:
	raw = _ask(prompt, default) or default
	parts = []
	for item in raw.split(","):
		path = item.strip()
		if path:
			parts.append(path)
	return parts


def _ask_Stealth() -> dict:
	_step_Header(SetupStep3Header)
	print_SetupTip(SetupStep3TipMask)
	print(SetupConcealHelp)

	jitter_enabled = _ask_YesNo(SetupAskJitterText, True)
	beacon = 30
	jitter = 35
	if jitter_enabled:
		print_Attention(SetupStep3TipJitter)
		beacon = _ask_Int(SetupAskBeaconText, 30, 5, 3600)
		jitter = _ask_Int(SetupAskJitterPctText, 35, 0, 100)

	cover_enabled = _ask_YesNo(SetupAskCoverText, True)
	cover_urls = ["/favicon.ico", "/robots.txt"]
	if cover_enabled:
		cover_urls = _ask_UrlList(SetupAskCoverUrlsText, SetupCoverUrlsDefault)
		if not cover_urls:
			cover_enabled = False

	path_rotation = _ask_YesNo(SetupAskPathRotationText, True)
	mimicry = _ask_YesNo(SetupAskMimicryText, True)
	user_agent = SetupUserAgentDefault
	if mimicry:
		user_agent = _ask(SetupAskUserAgentText, user_agent) or user_agent

	process_enabled = _ask_YesNo(SetupAskProcessMaskText, True)
	process_name = "svchost"
	if process_enabled:
		process_name = _ask(SetupAskProcessNameText, "svchost") or "svchost"
		if "honey" in process_name.lower() or "c2" in process_name.lower():
			print_Attention(SetupProcessNameBadText)
			process_name = _ask(SetupAskProcessNameAgainText, "svchost") or "svchost"

	return {
		"jitter_enabled": jitter_enabled,
		"beacon": beacon,
		"jitter": jitter,
		"cover_enabled": cover_enabled,
		"cover_urls": cover_urls,
		"path_rotation": path_rotation,
		"mimicry": mimicry,
		"user_agent": user_agent,
		"process_enabled": process_enabled,
		"process_name": process_name,
	}


def _ask_FreePort(taken: set[int], default: int) -> int:
	while True:
		port = _ask_Int("Порт", default, 1, 65535)
		if port not in taken:
			return port
		owner = "уже выбранная ловушка"
		print_Attention(ProfilePortConflictText.format(port=port, first=owner, second="новая"))
		default = port + 1 if port < 65535 else 1


def _assert_TrapsFit(faces: list[dict]) -> None:
	seen: dict[int, str] = {}
	for face in faces:
		port = int(face["port"])
		name = str(face["service"])
		if port in seen:
			raise ValueError(ProfilePortConflictText.format(port=port, first=seen[port], second=name))
		seen[port] = name


TRAP_ORDER = ("ssh", "http", "tcp_banner", "postgres", "redis", "mysql")


def _default_TrapNumbers(role: dict) -> str:
	if role.get("bundle"):
		numbers = []
		for spec in role.get("services") or []:
			service = spec["service"]
			if service in TRAP_ORDER:
				numbers.append(str(TRAP_ORDER.index(service) + 1))
		if numbers:
			return ",".join(numbers)
	service = role.get("service") or "ssh"
	if service not in TRAP_ORDER:
		service = "ssh"
	return str(TRAP_ORDER.index(service) + 1)


def _parse_TrapList(raw: str) -> list[str]:
	names: list[str] = []
	for part in raw.replace(";", ",").split(","):
		token = part.strip().lower()
		if not token:
			continue
		if token.isdigit():
			index = int(token)
			if index < 1 or index > len(TRAP_ORDER):
				raise ValueError(SetupTrapSetBadText)
			names.append(TRAP_ORDER[index - 1])
			continue
		if token == "https":
			token = "http"
		if token not in TRAP_ORDER:
			raise ValueError(SetupTrapSetBadText)
		names.append(token)
	return names


def _ask_TrapSelection(role: dict) -> list[str]:
	print(SetupTrapListHelp)
	default = _default_TrapNumbers(role)
	while True:
		raw = _ask(SetupAskTrapSetText, default) or default
		try:
			names = _parse_TrapList(raw)
		except ValueError:
			print_Attention(SetupTrapSetBadText)
			continue
		if not names:
			print_Attention(SetupTrapSetEmptyText)
			continue
		return names


def _role_ForService(role: dict, service: str) -> dict:
	if role.get("service") == service and not role.get("bundle"):
		item = dict(role)
		item["service"] = service
		item["banner"] = role.get("banner") or DEFAULT_BANNERS[service]
		return item
	username = "root"
	password = "admin"
	auth_mode = "allow_listed"
	if service == "postgres":
		username = "postgres"
		password = "postgres"
	elif service == "redis":
		username = "default"
		password = "redis"
	elif service == "tcp_banner":
		auth_mode = "off"
	elif service == "ssh":
		auth_mode = "second_attempt_sticky"
	return {
		"service": service,
		"port": DEFAULT_PORTS[service],
		"banner": DEFAULT_BANNERS[service],
		"username": username,
		"password": password,
		"auth_mode": auth_mode,
		"shell": service == "ssh",
		"fs_pack": "ubuntu-22.04",
		"auth_path": "/admin",
		"sticky_ttl": 72,
	}


def _configure_Bundle(role: dict, selected: list[str]) -> list[dict]:
	auth = _ask_AuthModule(role, "db")
	linked_ids = []
	if auth["auth_mode"] in ("allow_listed", "second_attempt_sticky"):
		linked_ids = [item["id"] for item in auth["credentials"]]
	banners = {
		spec["service"]: spec["banner"]
		for spec in role.get("services") or []
	}
	faces = []
	taken: set[int] = set()
	total = len(selected)
	for index, service in enumerate(selected, start=1):
		print()
		print(Fore.CYAN + Style.BRIGHT + SetupTrapProgressText.format(index=index, total=total) + Style.RESET_ALL)
		port = _ask_FreePort(taken, DEFAULT_PORTS[service])
		taken.add(port)
		print_OpsLine("сервис", f"{service}:{port}")
		faces.append({
			"service": service,
			"port": port,
			"banner": banners.get(service) or DEFAULT_BANNERS[service],
			"credentials": auth["credentials"] if not faces else [],
			"credential_ids": list(linked_ids),
			"auth_mode": auth["auth_mode"],
			"sticky_ttl": auth["sticky_ttl"],
			"shell_enabled": False,
			"fs_pack": "",
			"auth_path": auth["auth_path"],
			"level": "medium",
		})
	print_OpsLine("уровень", "medium")
	return faces


def _configure_All(role: dict) -> list[dict]:
	_step_Header(SetupStep2Header)
	print_SetupTip(SetupStep2TipService)
	selected = _ask_TrapSelection(role)
	db_services = {"postgres", "redis", "mysql"}
	if role.get("bundle") and set(selected) <= db_services:
		faces = _configure_Bundle(role, selected)
		_assert_TrapsFit(faces)
		return faces
	faces = []
	taken: set[int] = set()
	total = len(selected)
	for index, service in enumerate(selected, start=1):
		item = _role_ForService(role, service)
		default_port = int(item.get("port") or DEFAULT_PORTS[service])
		print()
		print(Fore.CYAN + Style.BRIGHT + SetupTrapProgressText.format(index=index, total=total) + Style.RESET_ALL)
		item["port"] = _ask_FreePort(taken, default_port)
		face = _configure_Modules(item)
		faces.append(face)
		taken.add(int(face["port"]))
	_assert_TrapsFit(faces)
	return faces


def _auth_Module(face: dict) -> dict:
	auth_mode = face.get("auth_mode") or "off"
	auth_enabled = auth_mode != "off"
	auth_module = {
		"enabled": auth_enabled,
		"mode": "allow_all" if not auth_enabled else auth_mode,
		"credential_ids": list(face.get("credential_ids") or []),
		"delay_ms_min": 150 if auth_enabled else 0,
		"delay_ms_max": 900 if auth_enabled else 0,
	}
	if auth_mode == "second_attempt_sticky":
		auth_module["sticky_ttl_hours"] = int(face.get("sticky_ttl") or 72)
	return auth_module


def _service_Block(face: dict, service_id: str) -> dict:
	service = face["service"]
	port = int(face["port"])
	auth_module = _auth_Module(face)
	auth_enabled = bool(auth_module["enabled"])
	if service == "tcp_banner":
		return {
			"type": "tcp_banner",
			"id": service_id,
			"port": port,
			"enabled": True,
			"modules": {"banner": face.get("banner") or ""},
		}
	if service == "ssh":
		return {
			"type": "ssh",
			"id": service_id,
			"port": port,
			"enabled": True,
			"modules": {
				"banner": {"enabled": True, "version": face.get("banner") or DEFAULT_BANNERS["ssh"]},
				"auth": auth_module,
				"shell": {
					"enabled": bool(face.get("shell_enabled")) and auth_enabled,
					"fs_pack": face.get("fs_pack") or "ubuntu-22.04",
				},
			},
		}
	if service == "http":
		http_auth = dict(auth_module)
		auth_path = face.get("auth_path") or "/admin"
		http_auth["path"] = auth_path
		routes = [
			{
				"path": "/",
				"methods": ["GET"],
				"status": 200,
				"body": "<html><body>It works.</body></html>",
			}
		]
		if auth_enabled and auth_path != "/":
			routes.append({
				"path": auth_path,
				"methods": ["GET"],
				"status": 200,
				"body": "<html><body>Administration</body></html>",
			})
		return {
			"type": "http",
			"id": service_id,
			"port": port,
			"enabled": True,
			"modules": {
				"personality": {
					"enabled": True,
					"server": face.get("banner") or DEFAULT_BANNERS["http"],
					"title": "Administration",
				},
				"auth": http_auth,
				"routes": {"routes": routes},
			},
		}
	return {
		"type": service,
		"id": service_id,
		"port": port,
		"enabled": True,
		"modules": {
			"banner": {
				"enabled": True,
				"version": face.get("banner") or DEFAULT_BANNERS.get(service, ""),
			},
			"auth": auth_module,
			"session": {"enabled": True, "max_session_sec": 120},
		},
	}


def _save_Profile(
	trap_name: str,
	role: dict,
	faces: list[dict],
	stealth: dict,
) -> tuple[str, str]:
	profile_name = f"{role['key']}-{trap_name}"
	_assert_TrapsFit(faces)
	level = "low"
	credentials = []
	seen_ids: set[str] = set()
	service_blocks = []
	counts: dict[str, int] = {}
	for face in faces:
		if face.get("level") == "medium":
			level = "medium"
		for item in face.get("credentials") or []:
			if item["id"] in seen_ids:
				continue
			seen_ids.add(item["id"])
			credentials.append(item)
		kind = str(face["service"])
		counts[kind] = counts.get(kind, 0) + 1
		service_blocks.append(_service_Block(face, f"{kind}-{counts[kind]}"))

	body = {
		"name": profile_name,
		"description": f"ловушка {trap_name} / {role['label']}",
		"interaction_level": level,
		"blocks": {
			"services": service_blocks,
			"credentials": credentials,
			"logging": {
				"capture_credentials": True,
				"capture_payloads": True,
				"capture_source_meta": True,
			},
			"mask": {
				"jitter": {
					"enabled": stealth["jitter_enabled"],
					"beacon_interval_sec": stealth["beacon"],
					"jitter_pct": stealth["jitter"],
				},
				"cover": {
					"enabled": stealth["cover_enabled"],
					"urls": stealth["cover_urls"],
				},
				"path_rotation": {
					"enabled": stealth["path_rotation"],
					"paths": ["/v1/metrics", "/cdn/edge-check"],
				},
				"mimicry": {
					"enabled": stealth["mimicry"],
					"user_agent": stealth["user_agent"],
					"tls_fingerprint_profile": "browser-like",
				},
				"process_mask": {
					"enabled": stealth["process_enabled"],
					"name": stealth["process_name"],
				},
				"decoy_content_seed": trap_name,
				"service_personality": role["key"],
			},
		},
	}

	client.validate_Profile(body)
	created = client.create_Profile(body)
	profile_id = str(created["id"])
	print()
	print(Fore.GREEN + "Конфиг приманки сохранён в центре." + Style.RESET_ALL)
	print_OpsLine("Профиль", profile_name)
	print_OpsLine("ID", profile_id)
	print_OpsLine("Роль", role["label"])
	return profile_id, profile_name


def _print_InstallCard(trap_name: str, role: dict, profile_name: str) -> None:
	card = SetupInstallCard.format(
		trap_name=trap_name,
		role_label=role["label"],
		profile_name=profile_name,
		api_base=client.get_BaseUrl(),
	)
	print(Fore.MAGENTA + card + Style.RESET_ALL)


def _install_OverSsh(trap_name: str, role: dict, profile_name: str) -> str | None:
	print_SetupTip(SetupSshInstallTip)
	if not _ask_YesNo(SetupAskSshInstallText, True):
		_print_InstallCard(trap_name, role, profile_name)
		_pause("Отдай карточку на хост ловушки, затем Enter")
		return None

	host = (_ask(SetupAskSshHostText, "") or "").strip()
	user = (_ask(SetupAskSshUserText, "root") or "root").strip()
	port = _ask_Int(SetupAskSshPortText, 22, 1, 65535)
	password = getpass.getpass(Fore.GREEN + SetupAskSshPasswordText + Style.RESET_ALL)
	api_base = client.get_BaseUrl()
	if center_IsLoopback(api_base):
		print_Attention(SetupSshLocalCenterText)
		center = (_ask(SetupAskReachableCenterText, "") or "").strip()
	else:
		center = (_ask(SetupAskReachableCenterText, api_base) or api_base).strip()
	try:
		return install_AgentOverSsh(
			host=host,
			user=user,
			password=password,
			port=port,
			center_url=center,
		)
	except DeployError as exc:
		print_Attention(SetupSshFailedText.format(detail=str(exc)))
		print_SetupTip(SetupSshManualFallbackText)
		_print_InstallCard(trap_name, role, profile_name)
		return None


def _wait_AndApprove(
	profile_id: str,
	trap_name: str,
	known_code: str | None = None,
) -> str | None:
	_step_Header(SetupStep4Header)
	if known_code:
		device_code: str | None = known_code
		print(Fore.GREEN + SetupSshCodeText.format(code=known_code) + Style.RESET_ALL)
	else:
		print_SetupTip(SetupStep4TipInstall)
		print_Attention(SetupStep4TipCodeTtl)
		_pause("Когда на хосте запущен агент и есть код - Enter")
		device_code = None
	while device_code is None:
		print(SetupStep4WaitingText)
		data = client.list_Pairings(status="pending")
		items = data.get("items") or []

		if items:
			print()
			print(Fore.CYAN + "Запросы на регистрацию с хостов:" + Style.RESET_ALL)
			for idx, item in enumerate(items, start=1):
				code = item.get("device_code", "?")
				expires = item.get("expires_at", "")
				print(
					f"  [{idx}]  код {Fore.GREEN}{Style.BRIGHT}{code}{Style.RESET_ALL}"
					f"   до {expires}"
				)
			choice = _ask("Какой узел принять? (номер / код)", "1")
			if not choice:
				continue
			try:
				num = int(choice)
				if 1 <= num <= len(items):
					device_code = str(items[num - 1]["device_code"])
				else:
					device_code = choice.upper()
			except ValueError:
				device_code = choice.upper()
		else:
			print(Fore.YELLOW + "  Хост ещё не запросил регистрацию." + Style.RESET_ALL)
			print_SetupTip("Выполни команды из INSTALL CARD на машине-приманке.")
			if _ask_YesNo("Проверить снова", True):
				time.sleep(0.3)
				continue
			manual = _ask("Или введи код с консоли хоста", "")
			if manual:
				device_code = manual.upper()
			else:
				print_Attention("Приём узла отложен. Позже можно принять через pair-list.")
				return None

		if not device_code:
			device_code = None

	final_name = _ask("Позывной узла в парке", trap_name) or trap_name
	print()
	print_Attention(f"Принимаю узел '{final_name}' и накатываю конфиг приманки...")
	result = client.confirm_Pairing(
		device_code=device_code,
		trap_name=final_name,
		profile_id=profile_id,
	)
	trap_id = str(result.get("trap_id") or "")
	print(
		Fore.GREEN
		+ SetupStep4ApprovedText.format(trap_name=final_name, trap_id=trap_id)
		+ Style.RESET_ALL
	)
	print_SetupTip("На хосте агент завершит регистрацию и подтянет конфиг сам.")
	return trap_id


def _commission_Trap(trap_id: str | None, profile_id: str, trap_name: str) -> None:
	_step_Header(SetupStep5Header)
	print_SetupTip(SetupStep5TipOnline)

	if not trap_id:
		print(Fore.YELLOW + "Узел не принят - ввод в строй пропущен." + Style.RESET_ALL)
		return

	for attempt in range(1, 6):
		traps = client.list_Traps()
		found = next((t for t in traps if str(t.get("id")) == trap_id), None)
		if not found:
			print(Fore.RED + "Узел не найден в парке." + Style.RESET_ALL)
			return

		if not found.get("profile_id"):
			client.bind_TrapProfile(trap_id, profile_id)
			found = client.get_Trap(trap_id)

		status = found.get("status", "?")
		print()
		print_OpsLine("Узел", found.get("name") or trap_name)
		print_OpsLine("Статус", _status_Color(str(status)))
		print_OpsLine("Last seen", str(found.get("last_seen_at") or "ещё не было"))

		if status == "online":
			print(Fore.GREEN + "Узел в строю." + Style.RESET_ALL)
			break

		if attempt < 5:
			print(
				Fore.YELLOW
				+ f"Жду первую отметку с хоста... ({attempt}/5)"
				+ Style.RESET_ALL
			)
			if not _ask_YesNo("Проверить статус ещё раз", True):
				break
		else:
			print_Attention("Пока не online. Когда агент оживут - статус обновится сам.")

	print()
	print_SetupTip(SetupStep5TipProbe)
	print_Attention("Не трогай ловушку из прод-сети - только lab / атакующий контур.")

	if _ask_YesNo("Открыть ленту событий (дежурство)", True):
		print_SetupTip("Оставь ленту открытой и создай активность на приманке.")
		from commands.events import cmd_EventsTail

		cmd_EventsTail(None)


def cmd_Setup(_args) -> None:
	print(SetupIntroText)
	try:
		_step_Header(SetupStep1Header)
		print_SetupTip(SetupStep1TipSite)
		trap_name = _ask("Позывной узла", "dmz-ssh-01") or "dmz-ssh-01"
		segment = _ask("Сегмент размещения", "lab-dmz") or "lab-dmz"
		print_OpsLine("Узел", trap_name)
		print_OpsLine("Сегмент", segment)
		print_Attention("Сегмент ловушки изолирован от продакшена.")

		role = _pick_Role()
		print_OpsLine("Роль", role["label"])

		faces = _configure_All(role)
		stealth = _ask_Stealth()
		profile_id, profile_name = _save_Profile(trap_name, role, faces, stealth)

		known_code = _install_OverSsh(trap_name, role, profile_name)
		trap_id = _wait_AndApprove(profile_id, trap_name, known_code)
		_commission_Trap(trap_id, profile_id, trap_name)

		print()
		print(Fore.GREEN + Style.BRIGHT + SetupDoneText.format(trap_name=trap_name) + Style.RESET_ALL)
		print_OpsLine("Сегмент", segment)
		print_OpsLine("Профиль", profile_name)
		if trap_id:
			print_OpsLine("Trap ID", trap_id)
		print()
		print_SetupTip("Смена: traps-list / events-tail / pair-list")
	except KeyboardInterrupt:
		print()
		print(Fore.YELLOW + SetupAbortText + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
	except ValueError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


cmd_Guide = cmd_Setup
