from __future__ import annotations

import time

from colorama import Fore, Style

import client
from texts import (
	MsgApiError,
	SetupAbortText,
	SetupDoneText,
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
	},
	"3": {
		"key": "scan-bait",
		"label": "детектор сканов (только баннеры)",
		"level": "low",
		"service": "ssh",
		"port": 22,
		"banner": "SSH-2.0-OpenSSH_7.4",
		"creds": False,
		"username": "",
		"password": "",
	},
	"4": {
		"key": "custom",
		"label": "ручная настройка",
		"level": "medium",
		"service": "ssh",
		"port": 22,
		"banner": "SSH-2.0-OpenSSH_8.9p1",
		"creds": True,
		"username": "root",
		"password": "admin",
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
		preset["level"] = (_ask("Глубина: low / medium", "medium") or "medium").lower()
		if preset["level"] not in ("low", "medium", "high"):
			preset["level"] = "medium"
		preset["service"] = (_ask("Сервис (ssh/http)", "ssh") or "ssh").lower()
		preset["port"] = int(_ask("Порт", "22" if preset["service"] == "ssh" else "8080") or "22")
		preset["creds"] = preset["level"] != "low"
	return preset


def _configure_ServiceFace(role: dict) -> dict:
	"""Что увидит атакующий на порту."""
	_step_Header(SetupStep2Header)
	print_SetupTip(SetupStep2TipService)
	service = role["service"]
	port = int(role["port"])
	print_OpsLine("Сервис", f"{service}:{port}")
	banner = _ask("Баннер / версия для сканера", role.get("banner") or "") or role.get("banner") or ""

	credentials: list[dict] = []
	if role.get("creds") and role["level"] != "low":
		print_SetupTip(SetupStep2TipCreds)
		if _ask_YesNo("Оставить слабую учётку-приманку", True):
			username = _ask("Логин приманки", role.get("username") or "root") or "root"
			password = _ask("Пароль приманки", role.get("password") or "admin") or "admin"
			credentials.append(
				{
					"username": username,
					"password": password,
					"service": service,
					"note": "bait",
				}
			)

	return {"banner": banner, "credentials": credentials}


def _ask_Stealth() -> dict:
	_step_Header(SetupStep3Header)
	print_SetupTip(SetupStep3TipMask)
	print_Attention(SetupStep3TipJitter)
	beacon = int(_ask("Как часто узел связывается с центром, сек", "30") or "30")
	jitter = int(_ask("Разброс по времени, %", "35") or "35")
	process_name = _ask("Под каким именем процесса жить агенту", "svchost") or "svchost"
	if "honey" in process_name.lower() or "c2" in process_name.lower():
		print_Attention("Имя выдаёт приманку. Лучше: svchost, systemd-net, mDNSResponder.")
		process_name = _ask("Имя процесса ещё раз", "svchost") or "svchost"
	return {
		"beacon": max(5, beacon),
		"jitter": max(0, min(100, jitter)),
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
	level = role["level"]

	body = {
		"name": profile_name,
		"description": f"ловушка {trap_name} / {role['label']}",
		"interaction_level": level,
		"blocks": {
			"services": [
				{
					"name": service,
					"protocol": "tcp",
					"port": port,
					"enabled": True,
					"options": {},
				}
			],
			"banners": (
				[{"service": service, "text": face["banner"]}] if face.get("banner") else []
			),
			"credentials": face.get("credentials") or [],
			"logging": {
				"capture_credentials": True,
				"capture_payloads": True,
				"capture_source_meta": True,
				"auth_delay_ms_min": 150 if level != "low" else 0,
				"auth_delay_ms_max": 900 if level != "low" else 0,
			},
			"mask": {
				"beacon_interval_sec": stealth["beacon"],
				"jitter_pct": stealth["jitter"],
				"collector_path_set": [
					"/v1/metrics",
					"/cdn/edge-check",
					"/api/telemetry/batch",
				],
				"cover_urls": ["/favicon.ico", "/robots.txt"],
				"process_name": stealth["process_name"],
				"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
				"tls_fingerprint_profile": "browser-like",
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


def _wait_AndApprove(profile_id: str, trap_name: str) -> str | None:
	_step_Header(SetupStep4Header)
	print_SetupTip(SetupStep4TipInstall)
	print_Attention(SetupStep4TipCodeTtl)
	_pause("Когда на хосте запущен агент и есть код - Enter")

	device_code: str | None = None
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

		face = _configure_ServiceFace(role)
		stealth = _ask_Stealth()
		profile_id, profile_name = _save_Profile(trap_name, role, face, stealth)

		_print_InstallCard(trap_name, role, profile_name)
		_pause("Отдай карточку на хост ловушки, затем Enter")

		trap_id = _wait_AndApprove(profile_id, trap_name)
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
