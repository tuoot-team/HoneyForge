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
	SetupRoutesTipText,
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
}


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
	choice = _ask("Роль приманки (1-4)", "1") or "1"
	preset = dict(ROLE_PRESETS.get(choice, ROLE_PRESETS["1"]))
	if preset["key"] == "custom":
		preset["service"] = (_ask("Сервис (ssh/http/tcp_banner)", "ssh") or "ssh").lower()
		if preset["service"] == "https":
			preset["service"] = "http"
		if preset["service"] not in ("ssh", "http", "tcp_banner"):
			preset["service"] = "ssh"
		default_port = {"ssh": "22", "http": "8080", "tcp_banner": "2121"}[preset["service"]]
		preset["port"] = _ask_Int("Порт", int(default_port), 1, 65535)
		if preset["service"] == "tcp_banner":
			preset["auth_mode"] = "off"
			preset["shell"] = False
			preset["banner"] = "220 ftp ready"
		elif preset["service"] == "http":
			preset["banner"] = "nginx/1.24.0"
			preset["auth_mode"] = "allow_listed"
			preset["shell"] = False
	return preset


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
	_step_Header(SetupStep2Header)
	print_SetupTip(SetupStep2TipService)
	service = role["service"]
	port = int(role["port"])
	print_OpsLine("сервис", f"{service}:{port}")

	if service == "tcp_banner":
		print_OpsLine("модуль", "banner")
		banner = _ask("Текст баннера", role.get("banner") or "220 ftp ready") or "220 ftp ready"
		face = {
			"banner": banner,
			"credentials": [],
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
	else:
		print_OpsLine("модуль", "personality")
		banner = _ask("Заголовок Server", role.get("banner") or "nginx/1.24.0") or "nginx/1.24.0"
		auth = _ask_AuthModule(role, service)
		print_OpsLine("модуль", "routes")
		print_SetupTip(SetupRoutesTipText)
		shell_enabled = False
		fs_pack = ""
		level = "medium"

	face = {
		"banner": banner,
		"credentials": auth["credentials"],
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


def _save_Profile(
	trap_name: str,
	role: dict,
	face: dict,
	stealth: dict,
) -> tuple[str, str]:
	profile_name = f"{role['key']}-{trap_name}"
	service = role["service"]
	port = int(role["port"])
	level = face.get("level") or ("medium" if service == "http" else "low")
	credentials = face.get("credentials") or []
	credential_ids = [item["id"] for item in credentials]
	auth_mode = face.get("auth_mode") or "off"
	auth_enabled = auth_mode != "off"
	linked_ids = credential_ids if auth_mode in ("allow_listed", "second_attempt_sticky") else []
	auth_module = {
		"enabled": auth_enabled,
		"mode": "allow_all" if not auth_enabled else auth_mode,
		"credential_ids": linked_ids,
		"delay_ms_min": 150 if auth_enabled else 0,
		"delay_ms_max": 900 if auth_enabled else 0,
	}
	if auth_mode == "second_attempt_sticky":
		auth_module["sticky_ttl_hours"] = int(face.get("sticky_ttl") or 72)

	if service == "tcp_banner":
		service_block = {
			"type": "tcp_banner",
			"id": "banner-1",
			"port": port,
			"enabled": True,
			"modules": {"banner": face.get("banner") or ""},
		}
	elif service == "ssh":
		service_block = {
			"type": "ssh",
			"id": "ssh-main",
			"port": port,
			"enabled": True,
			"modules": {
				"banner": {"enabled": True, "version": face.get("banner") or "SSH-2.0-OpenSSH_8.9p1"},
				"auth": auth_module,
				"shell": {
					"enabled": bool(face.get("shell_enabled")) and auth_enabled,
					"fs_pack": face.get("fs_pack") or "ubuntu-22.04",
				},
			},
		}
	else:
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
		service_block = {
			"type": "http",
			"id": "http-main",
			"port": port,
			"enabled": True,
			"modules": {
				"personality": {
					"enabled": True,
					"server": face.get("banner") or "nginx/1.24.0",
					"title": "Administration",
				},
				"auth": http_auth,
				"routes": {"routes": routes},
			},
		}

	body = {
		"name": profile_name,
		"description": f"ловушка {trap_name} / {role['label']}",
		"interaction_level": level,
		"blocks": {
			"services": [service_block],
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

		face = _configure_Modules(role)
		stealth = _ask_Stealth()
		profile_id, profile_name = _save_Profile(trap_name, role, face, stealth)

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
