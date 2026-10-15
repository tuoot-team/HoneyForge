from __future__ import annotations

import time
from pathlib import Path

from colorama import Fore, Style

import client
from commands.deploy import (
	center_IsLoopback,
	check_CenterUrl,
	install_AgentOverSsh,
	public_Agent_Center_Url,
)
from cat_mode import maybe_Meow
from line_input import AnswerStack, LineGoBack, read_Line
from texts import (
	MsgApiError,
	SetupAbortText,
	SetupDoneText,
	SetupEventsTailSkipText,
	SetupRewindText,
	SetupAskReachableCenterText,
	SetupAskSshHostText,
	SetupAskSshInstallText,
	SetupAskSshPasswordText,
	SetupAskSshPortText,
	SetupAskSshUserText,
	SetupCourierInstallCard,
	SetupInstallCard,
	SetupIntroText,
	SetupStep1Header,
	SetupStep1TipSite,
	SetupStep2Header,
	SetupStep2TipCreds,
	SetupStep2TipService,
	SetupAskHighVmText,
	SetupAskImageTokenText,
	SetupAskVmNameText,
	SetupAskVmSnapshotText,
	SetupAskRdpHostPortText,
	SetupAskVmAutoStartText,
	SetupHighNeedsImageText,
	SetupHighConfiguredText,
	DeployHighVmNoteText,
	SetupAskLinkCredsText,
	SetupLinkCredsTipText,
	SetupAskCollectIntervalText,
	SetupAskCreateCourierText,
	SetupAskCourierCenterText,
	SetupAskCourierDeployText,
	SetupAskCourierHostText,
	SetupAskCourierNameText,
	SetupAskDeliveryText,
	SetupAskOwnerReassignText,
	SetupAskTrapCourierSshText,
	SetupApproveNodeText,
	SetupAskOwnerUserIdText,
	SetupAskPairListRetryText,
	SetupCourierCodeMissingText,
	SetupCourierCommissionOkText,
	SetupCourierConnectingText,
	SetupCourierCreatedText,
	SetupCourierDeployFailedText,
	SetupCourierDeployTip,
	SetupCourierManualLaterText,
	SetupDeliveryCourierTip,
	SetupDoneTipText,
	SetupHostWillFinishText,
	SetupOwnerSetOkText,
	SetupOwnerSetSkipText,
	SetupOwnerUsersEmptyText,
	SetupOwnerUsersListDeniedText,
	SetupStep3Header,
	SetupStep3TipJitter,
	SetupStep3TipMask,
	SetupStep4ApprovedText,
	SetupStep4BadCodeText,
	SetupStep4BadCodeTipText,
	SetupStep4Header,
	SetupStep4TipCodeTtl,
	SetupStep4TipInstall,
	SetupStep4TipOwner,
	SetupStep4WaitingText,
	TrapCourierSshSavedText,
	SetupStep5Header,
	SetupStep5TipOnline,
	SetupStep5TipProbe,
	SetupAskBeaconText,
	SetupAskCoverText,
	SetupAskCoverUrlsText,
	SetupAskFsPackFileText,
	SetupAskPersonalityPackText,
	SetupPersonalityPackTipText,
	SetupAskFsPackModeText,
	SetupAskFsPackNameText,
	SetupAskFsPackPickText,
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
	SetupFsPackBadFileText,
	SetupFsPackBadPickText,
	SetupFsPackHelp,
	SetupFsPackNoExistingText,
	SetupFsPackUploadOkText,
	SetupProcessNameBadText,
	SetupUserAgentDefault,
	ProfilePortConflictText,
	SetupAskTrapSetText,
	SetupHttpPlainText,
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

DEFAULT_PORTS = {
	"ssh": 22,
	"http": 8080,
	"tcp_banner": 2121,
	"postgres": 5432,
	"redis": 6379,
	"mysql": 3306,
}
DEFAULT_BANNERS = {
	# Как у OpenSSH на Ubuntu: softwareversion + comment (пакет).
	"ssh": "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
	"http": "nginx/1.24.0",
	"tcp_banner": "220 ftp ready",
	"postgres": "14.10 (Ubuntu 14.10-0ubuntu0.22.04.1)",
	"mysql": "5.7.42-log",
	"redis": "6.2.14",
}
KNOWN_SERVICES = tuple(DEFAULT_PORTS)

_answers = AnswerStack()


class SetupGoBack(Exception):
	"""Esc: снять последний ответ и пройти мастер заново."""


def _prompt_Text(prompt: str, default: str | None, *, secret: bool) -> str:
	if secret:
		text = prompt.rstrip()
		if not text.endswith(":"):
			text += ":"
		return Fore.GREEN + text + " " + Style.RESET_ALL
	suffix = f" [{default}]" if default is not None else ""
	return Fore.GREEN + f"{prompt}{suffix}: " + Style.RESET_ALL


def _print_Replayed(shown_prompt: str, raw: str, *, mask: bool) -> None:
	shown = ("*" * len(raw)) if mask else raw
	print(shown_prompt + shown)


def _ask(prompt: str, default: str | None = None, *, secret: bool = False) -> str | None:
	shown_prompt = _prompt_Text(prompt, default, secret=secret)
	replayed = _answers.take_Replay()
	if replayed is not None:
		raw, stored_secret = replayed
		_print_Replayed(shown_prompt, raw, mask=secret or stored_secret)
	else:
		prefill = _answers.take_Prefill() or ""
		try:
			raw = read_Line(
				shown_prompt,
				history=None if secret else _answers.text_history,
				prefill=prefill,
				echo=not secret,
				allow_back=bool(_answers.answers),
			)
		except LineGoBack:
			raise SetupGoBack
		if not secret:
			raw = raw.strip()
			if raw.lower() in ("q", "quit", "exit", "abort"):
				raise KeyboardInterrupt
		_answers.commit(raw, secret=secret)
	if secret:
		return raw
	if not raw:
		return default
	return raw


def _ask_Secret(prompt: str) -> str:
	value = _ask(prompt, secret=True)
	return "" if value is None else value


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
	maybe_Meow()


def _status_Color(status: str) -> str:
	key = (status or "?").lower()
	if key == "online":
		return Fore.GREEN + status + Style.RESET_ALL
	if key == "pending":
		return Fore.YELLOW + status + Style.RESET_ALL
	if key == "offline":
		return Fore.RED + status + Style.RESET_ALL
	return status


def _ask_Int(prompt: str, default: int, low: int, high: int) -> int:
	raw = _ask(prompt, str(default)) or str(default)
	try:
		value = int(raw)
	except ValueError:
		value = default
	return max(low, min(high, value))


def _is_ArchivePath(path: Path) -> bool:
	lower = path.name.lower()
	return lower.endswith(".zip") or lower.endswith(".tar.gz") or lower.endswith(".tgz")


def _parse_UserPath(raw: str) -> Path:
	"""Путь из ввода: срезать кавычки, ~ и сделать абсолютным от cwd."""
	text = (raw or "").strip()
	if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
		text = text[1:-1].strip()
	return Path(text).expanduser().resolve()


def _ask_FsPack(default: str = "ubuntu-22.04") -> str:
	"""Выбор: builtin / upload / existing на центре."""
	print(SetupFsPackHelp)
	default_mode = "1"
	if str(default or "").startswith("fsp_"):
		default_mode = "3"
	mode = (_ask(SetupAskFsPackModeText, default_mode) or default_mode).strip()
	if mode in ("1", "builtin", "ubuntu-22.04"):
		return "ubuntu-22.04"
	if mode in ("2", "new", "upload", "create"):
		while True:
			raw_path = _ask(SetupAskFsPackFileText, "") or ""
			path = _parse_UserPath(raw_path)
			if path.is_file() and _is_ArchivePath(path):
				break
			print_Attention(SetupFsPackBadFileText)
		name = _ask(SetupAskFsPackNameText, path.stem) or path.stem
		try:
			data = _answers.run_Once(
				"fs_pack_upload",
				lambda: client.upload_FsPack(str(path), name=name),
			)
		except client.ApiError as exc:
			print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
			return "ubuntu-22.04"
		token = data.get("token") or "ubuntu-22.04"
		print_OpsLine(
			"fs_pack",
			SetupFsPackUploadOkText.format(token=token, name=data.get("name") or name),
		)
		return token
	# existing
	try:
		data = client.list_FsPacks()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return "ubuntu-22.04"
	items = data.get("items") or []
	if not items:
		print_Attention(SetupFsPackNoExistingText)
		return "ubuntu-22.04"
	for index, item in enumerate(items, start=1):
		token = item.get("token") or "?"
		name = item.get("name") or ""
		fmt = item.get("format") or ""
		print(f"  {index}) {token}  {name}  ({fmt})")
	while True:
		pick = (_ask(SetupAskFsPackPickText, default if str(default).startswith("fsp_") else "1") or "").strip()
		if pick.startswith("fsp_"):
			for item in items:
				if item.get("token") == pick:
					return pick
			print_Attention(SetupFsPackBadPickText)
			continue
		try:
			num = int(pick)
		except ValueError:
			print_Attention(SetupFsPackBadPickText)
			continue
		if 1 <= num <= len(items):
			return items[num - 1].get("token") or "ubuntu-22.04"
		print_Attention(SetupFsPackBadPickText)


def _ask_Bait(defaults: dict, service: str, *, shared_id: str | None = None) -> dict:
	print_SetupTip(SetupStep2TipCreds)
	username = _ask("Логин приманки", defaults.get("username") or "root") or "root"
	password = _ask("Пароль приманки", defaults.get("password") or "admin") or "admin"
	return {
		"id": shared_id or f"{service}-bait",
		"username": username,
		"password": password,
		"note": "bait",
	}


def _ask_AuthModule(
	defaults: dict,
	service: str,
	*,
	shared_bait: dict | None = None,
) -> dict:
	print_OpsLine("модуль", "auth")
	print(SetupAuthModesHelp)
	default_choice = {
		"off": "0",
		"allow_all": "1",
		"allow_listed": "2",
		"second_attempt_sticky": "3",
	}.get(str(defaults.get("auth_mode") or "off"), "0")
	raw_choice = (_ask("Режим входа (0-3)", default_choice) or default_choice).strip()
	auth_mode = {
		"0": "off",
		"1": "allow_all",
		"2": "allow_listed",
		"3": "second_attempt_sticky",
	}.get(raw_choice, "allow_all")

	credentials: list[dict] = []
	sticky_ttl = int(defaults.get("sticky_ttl") or 72)
	if auth_mode == "allow_listed":
		if shared_bait is not None:
			credentials.append(dict(shared_bait))
		else:
			credentials.append(_ask_Bait(defaults, service))
	elif auth_mode == "second_attempt_sticky":
		if _ask_YesNo("Пускать только учётку-приманку, не любой пароль", True):
			if shared_bait is not None:
				credentials.append(dict(shared_bait))
			else:
				credentials.append(_ask_Bait(defaults, service))
		else:
			print_SetupTip("Со второй попытки примется любой пароль и привяжется к IP.")
		sticky_ttl = _ask_Int("Сколько часов помнить пароль за IP", sticky_ttl, 1, 8760)
	elif auth_mode == "off" and service == "ssh":
		print_Attention(SetupAuthBecomesLowText)

	auth_path = "/admin"
	if service == "http" and auth_mode != "off":
		auth_path = _ask("Путь входа", defaults.get("auth_path") or "/admin") or "/admin"
		if not auth_path.startswith("/"):
			auth_path = "/" + auth_path
	return {
		"auth_mode": auth_mode,
		"credentials": credentials,
		"sticky_ttl": sticky_ttl,
		"auth_path": auth_path,
	}


def _configure_Modules(defaults: dict, *, shared_bait: dict | None = None) -> dict:
	"""Слоты сервиса: banner/auth/shell или personality/auth/routes."""
	service = defaults["service"]
	port = int(defaults["port"])
	print_OpsLine("сервис", f"{service}:{port}")

	if service == "tcp_banner":
		print_OpsLine("модуль", "banner")
		banner = _ask("Текст баннера", defaults.get("banner") or "220 ftp ready") or "220 ftp ready"
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
			defaults.get("banner") or DEFAULT_BANNERS["ssh"],
		) or DEFAULT_BANNERS["ssh"]
		auth = _ask_AuthModule(defaults, service, shared_bait=shared_bait)
		shell_enabled = False
		fs_pack = defaults.get("fs_pack") or "ubuntu-22.04"
		if auth["auth_mode"] == "off":
			print_Attention(SetupShellNeedsAuthText)
		else:
			print_OpsLine("модуль", "shell")
			shell_enabled = _ask_YesNo("Пускать в ограниченный shell", bool(defaults.get("shell", True)))
			if shell_enabled:
				fs_pack = _ask_FsPack(fs_pack)
		level = "low" if auth["auth_mode"] == "off" else "medium"
	elif service in ("postgres", "redis", "mysql"):
		print_OpsLine("модуль", "banner")
		banner = _ask("Версия", defaults.get("banner") or DEFAULT_BANNERS[service]) or DEFAULT_BANNERS[service]
		auth = _ask_AuthModule(defaults, service, shared_bait=shared_bait)
		shell_enabled = False
		fs_pack = ""
		level = "medium"
	else:
		print_OpsLine("модуль", "personality")
		banner = _ask("Заголовок Server", defaults.get("banner") or "nginx/1.24.0") or "nginx/1.24.0"
		auth = _ask_AuthModule(defaults, service, shared_bait=shared_bait)
		print_OpsLine("модуль", "routes")
		print_SetupTip(SetupRoutesTipText)
		print_SetupTip(SetupHttpPlainText.format(port=port))
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


def _setup_Courier_Agent() -> None:
	"""Как установка ловушки: SSH deploy → код из лога → сразу confirm, без ручного ввода."""
	if not _ask_YesNo(SetupAskCreateCourierText, True):
		return
	name = _ask(SetupAskCourierNameText, "courier-01") or "courier-01"
	print_SetupTip(SetupCourierDeployTip)
	if not _ask_YesNo(SetupAskCourierDeployText, True):
		_print_Courier_InstallCard(name)
		print_SetupTip(SetupCourierManualLaterText)
		return

	host = (_ask(SetupAskCourierHostText, "") or "").strip()
	if not host:
		_print_Courier_InstallCard(name)
		print_SetupTip(SetupCourierManualLaterText)
		return
	user = (_ask(SetupAskSshUserText, "root") or "root").strip()
	port = _ask_Int(SetupAskSshPortText, 22, 1, 65535)
	password = _ask_Secret(SetupAskSshPasswordText)
	api_base = client.get_BaseUrl()
	default_center = _public_Center_For_Card()
	if center_IsLoopback(api_base):
		print_Attention(SetupSshLocalCenterText)
		center_raw = (_ask(SetupAskCourierCenterText, "") or "").strip()
	else:
		center_raw = (
			_ask(SetupAskCourierCenterText, default_center) or default_center
		).strip()

	try:
		center = check_CenterUrl(center_raw)
		# downloads/courier только на публичном канале
		center = public_Agent_Center_Url(center)

		def _deploy_Courier():
			print(SetupCourierConnectingText.format(user=user, host=host, port=port))
			return client.deploy_Courier(
				host=host,
				user=user,
				password=password,
				center_url=center,
				port=port,
			)

		result = _answers.run_Once("deploy_courier", _deploy_Courier)
		code = str(result.get("device_code") or "").strip()
		if not code:
			print_Attention(
				SetupCourierDeployFailedText.format(detail=SetupCourierCodeMissingText)
			)
			_print_Courier_InstallCard(name)
			print_SetupTip(SetupCourierManualLaterText)
			return
		print(Fore.GREEN + SetupSshCodeText.format(code=code) + Style.RESET_ALL)
		out = _answers.run_Once(
			"confirm_courier",
			lambda: client.confirm_Courier_Pairing(code, name=name),
		)
		print(
			Fore.GREEN
			+ SetupCourierCreatedText.format(
				name=name, courier_id=out.get("courier_id", "?")
			)
			+ Style.RESET_ALL
		)
	except client.ApiError as exc:
		print_Attention(SetupCourierDeployFailedText.format(detail=str(exc)))
		_print_Courier_InstallCard(name)
		print_SetupTip(SetupCourierManualLaterText)


def _ask_Stealth() -> dict:
	_step_Header(SetupStep3Header)
	print_SetupTip(SetupStep3TipMask)
	print(SetupConcealHelp)

	delivery_raw = (_ask(SetupAskDeliveryText, "1") or "1").strip()
	courier_mode = delivery_raw in ("2", "courier", "c", "курьер")

	if courier_mode:
		print_SetupTip(SetupDeliveryCourierTip)
		interval = _ask_Int(SetupAskCollectIntervalText, 300, 15, 86400)
		_setup_Courier_Agent()
		return {
			"collection_mode": "courier",
			"courier_enabled": True,
			"collect_interval_sec": interval,
			"jitter_enabled": False,
			"beacon": 30,
			"jitter": 0,
			"cover_enabled": False,
			"cover_urls": [],
			"path_rotation": False,
			"mimicry": False,
			"user_agent": SetupUserAgentDefault,
			"process_enabled": False,
			"process_name": "metricsd",
			"service_personality": _ask_PersonalityPackKey(),
		}

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
	process_name = "metricsd"
	if process_enabled:
		process_name = _ask(SetupAskProcessNameText, "metricsd") or "metricsd"
		if "honey" in process_name.lower() or "c2" in process_name.lower():
			print_Attention(SetupProcessNameBadText)
			process_name = _ask(SetupAskProcessNameAgainText, "metricsd") or "metricsd"

	return {
		"collection_mode": "agent",
		"courier_enabled": False,
		"collect_interval_sec": 300,
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
		"service_personality": _ask_PersonalityPackKey(),
	}


def _ask_PersonalityPackKey() -> str:
	print_SetupTip(SetupPersonalityPackTipText)
	keys: list[str] = []
	try:
		data = client.list_PersonalityPacks()
		for item in data.get("items") or []:
			key = str(item.get("key") or "").strip()
			if key:
				keys.append(key)
				title = item.get("title") or ""
				print(f"  {len(keys)}. {Fore.GREEN}{key}{Style.RESET_ALL}  {title}")
	except client.ApiError:
		pass
	raw = (_ask(SetupAskPersonalityPackText, "") or "").strip()
	if not raw:
		return ""
	if raw.isdigit() and keys:
		idx = int(raw)
		if 1 <= idx <= len(keys):
			return keys[idx - 1]
	return raw


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


def _ask_TrapSelection() -> list[str]:
	print(SetupTrapListHelp)
	default = "1"
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


def _defaults_ForService(service: str) -> dict:
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


def _ask_Emulation() -> dict | None:
	"""High VirtualBox: образ из реестра + NAT RDP."""
	if not _ask_YesNo(SetupAskHighVmText, False):
		return None
	try:
		data = client.list_VmImages()
	except client.ApiError:
		data = {"items": []}
	items = data.get("items") or []
	if not items:
		print_Attention(SetupHighNeedsImageText)
		return None
	print_OpsLine("образы", str(len(items)))
	for item in items[:20]:
		print(f"  {item.get('token')}  {item.get('name')}  ({item.get('format')})")
	token = (_ask(SetupAskImageTokenText, str(items[0].get("token") or "")) or "").strip()
	if not token:
		print_Attention(SetupHighNeedsImageText)
		return None
	vm_name = (_ask(SetupAskVmNameText, "hf-guest") or "hf-guest").strip() or "hf-guest"
	snapshot = (_ask(SetupAskVmSnapshotText, "clean") or "clean").strip() or "clean"
	rdp = _ask_Int(SetupAskRdpHostPortText, 3389, 1, 65535)
	auto_start = _ask_YesNo(SetupAskVmAutoStartText, True)
	print(Fore.GREEN + SetupHighConfiguredText.format(vm_name=vm_name, image_token=token) + Style.RESET_ALL)
	print_Attention(DeployHighVmNoteText)
	return {
		"enabled": True,
		"runtime": "virtualbox",
		"image_token": token,
		"vm_name": vm_name,
		"cpus": 2,
		"memory_mb": 4096,
		"snapshot": snapshot,
		"expose": [{"host_port": rdp, "guest_port": 3389, "proto": "tcp"}],
		"auto_start": auto_start,
	}


def _configure_All() -> tuple[list[dict], dict | None]:
	_step_Header(SetupStep2Header)
	emulation = _ask_Emulation()
	if emulation:
		return [], emulation
	print_SetupTip(SetupStep2TipService)
	selected = _ask_TrapSelection()
	faces = []
	taken: set[int] = set()
	total = len(selected)
	auth_capable = [s for s in selected if s != "tcp_banner"]
	shared_bait: dict | None = None
	if len(auth_capable) >= 2:
		print_SetupTip(SetupLinkCredsTipText)
		if _ask_YesNo(SetupAskLinkCredsText, True):
			shared_bait = _ask_Bait(
				{"username": "ops", "password": "Winter2024!"},
				"park",
				shared_id="park-bait",
			)
	for index, service in enumerate(selected, start=1):
		item = _defaults_ForService(service)
		print()
		print(Fore.CYAN + Style.BRIGHT + SetupTrapProgressText.format(index=index, total=total) + Style.RESET_ALL)
		item["port"] = _ask_FreePort(taken, int(item["port"]))
		face = _configure_Modules(item, shared_bait=shared_bait)
		faces.append(face)
		taken.add(int(face["port"]))
	_assert_TrapsFit(faces)
	return faces, None


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


def _park_Baits(service_blocks: list[dict], credentials: list[dict]) -> list[dict]:
	"""Same-host подсказки между сервисами мини-парка (если есть общие креды)."""
	if len(service_blocks) < 2 or not credentials:
		return []
	by_type: dict[str, dict] = {}
	for block in service_blocks:
		by_type.setdefault(str(block.get("type")), block)
	cred = credentials[0]
	cred_id = str(cred.get("id") or "park-bait")
	http = by_type.get("http")
	pg = by_type.get("postgres") or by_type.get("mysql") or by_type.get("redis")
	ssh = by_type.get("ssh")
	if not ssh:
		return []
	baits: list[dict] = []
	lines = ["todo:"]
	if http:
		sid = str(http.get("id") or "http-1")
		lines.append(
			f"- portal http://127.0.0.1:{{{{port:{sid}}}}}/admin "
			f"({{{{cred:{cred_id}.username}}}}/{{{{cred:{cred_id}.password}}}})"
		)
	if pg:
		sid = str(pg.get("id") or "postgres-1")
		lines.append(
			f"- db 127.0.0.1:{{{{port:{sid}}}}}"
			f" user={{{{cred:{cred_id}.username}}}} pass={{{{cred:{cred_id}.password}}}}"
		)
	if len(lines) == 1:
		return []
	baits.append({
		"kind": "file",
		"path": "/home/{{user}}/NOTES.txt",
		"body": "\n".join(lines) + "\n",
	})
	env_lines = ["APP_ENV=staging"]
	if http:
		env_lines.append(f"HTTP_URL=http://127.0.0.1:{{{{port:{http.get('id')}}}}}")
	if pg:
		env_lines.extend([
			"DB_HOST=127.0.0.1",
			f"DB_PORT={{{{port:{pg.get('id')}}}}}",
			f"DB_USER={{{{cred:{cred_id}.username}}}}",
			f"DB_PASSWORD={{{{cred:{cred_id}.password}}}}",
		])
	baits.append({
		"kind": "file",
		"path": "/opt/app/config.env",
		"body": "\n".join(env_lines) + "\n",
	})
	if http:
		body = "<html><body><h1>ops portal</h1>"
		if pg:
			body += (
				f"<p>db postgres://{{{{cred:{cred_id}.username}}}}:"
				f"{{{{cred:{cred_id}.password}}}}@127.0.0.1:{{{{port:{pg.get('id')}}}}}/ops</p>"
			)
		body += "</body></html>"
		baits.append({
			"kind": "http_route",
			"service_id": str(http.get("id")),
			"path": "/internal",
			"body": body,
		})
	return baits


def _park_Honeytokens(service_blocks: list[dict], baits: list[dict]) -> list[dict]:
	"""Canary на те же пути, что park-baits, плюс key-файл."""
	if not baits:
		return []
	tokens: list[dict] = []
	for bait in baits:
		kind = str(bait.get("kind") or "")
		path = str(bait.get("path") or "")
		if kind == "file" and path.endswith("NOTES.txt"):
			tokens.append({
				"id": "notes-canary",
				"kind": "file",
				"path": path,
			})
		elif kind == "http_route" and path:
			sid = str(bait.get("service_id") or "")
			if sid:
				tokens.append({
					"id": "internal-url",
					"kind": "url",
					"service_id": sid,
					"path": path,
				})
	by_type: dict[str, dict] = {}
	for block in service_blocks:
		by_type.setdefault(str(block.get("type")), block)
	if by_type.get("ssh"):
		tokens.append({
			"id": "aws-key",
			"kind": "key",
			"path": "/opt/app/secrets.env",
			"body": (
				"AWS_ACCESS_KEY_ID=AKIAHFDEMOCANARY01\n"
				"AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
			),
		})
	return tokens


def _save_Profile(
	trap_name: str,
	faces: list[dict],
	stealth: dict,
	emulation: dict | None = None,
) -> tuple[str, str]:
	profile_name = trap_name
	if emulation:
		level = "high"
		credentials = []
		service_blocks = []
		baits = []
		honeytokens = []
	else:
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

		baits = _park_Baits(service_blocks, credentials)
		honeytokens = _park_Honeytokens(service_blocks, baits)
	body = {
		"name": profile_name,
		"description": f"ловушка {trap_name}",
		"interaction_level": level,
		"blocks": {
			"services": service_blocks,
			"credentials": credentials,
			"baits": baits,
			"honeytokens": honeytokens,
			"emulation": emulation or {"enabled": False},
			"logging": {
				"capture_credentials": True,
				"capture_payloads": True,
				"capture_source_meta": True,
			},
			"mask": {
				"collection_mode": stealth.get("collection_mode", "agent"),
				"courier": {
					"enabled": bool(stealth.get("courier_enabled")),
					"collect_interval_sec": int(stealth.get("collect_interval_sec") or 300),
				},
				"jitter": {
					"enabled": stealth["jitter_enabled"],
					"beacon_interval_sec": stealth["beacon"],
					"jitter_pct": stealth["jitter"],
				},
				"cover": {
					"enabled": stealth["cover_enabled"],
					"urls": stealth["cover_urls"]
					or [u.strip() for u in SetupCoverUrlsDefault.split(",") if u.strip()],
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
				"service_personality": str(stealth.get("service_personality") or ""),
			},
		},
	}

	def _create_Profile():
		client.validate_Profile(body)
		return client.create_Profile(body)

	created = _answers.run_Once("create_profile", _create_Profile)
	profile_id = str(created["id"])
	print()
	print(Fore.GREEN + "Конфиг приманки сохранён в центре." + Style.RESET_ALL)
	print_OpsLine("Профиль", profile_name)
	print_OpsLine("ID", profile_id)
	return profile_id, profile_name


def _public_Center_For_Card() -> str:
	"""На карточке - публичный канал downloads/agent, не CLI :8088."""
	try:
		return public_Agent_Center_Url(client.get_BaseUrl())
	except client.ApiError:
		return client.get_BaseUrl().rstrip("/")


def _print_InstallCard(trap_name: str, profile_name: str) -> None:
	card = SetupInstallCard.format(
		trap_name=trap_name,
		profile_name=profile_name,
		api_base=_public_Center_For_Card(),
	)
	print(Fore.MAGENTA + card + Style.RESET_ALL)


def _print_Courier_InstallCard(courier_name: str) -> None:
	card = SetupCourierInstallCard.format(
		courier_name=courier_name,
		api_base=_public_Center_For_Card(),
	)
	print(Fore.MAGENTA + card + Style.RESET_ALL)


def _install_OverSsh(trap_name: str, profile_name: str) -> str | None:
	print_SetupTip(SetupSshInstallTip)
	if not _ask_YesNo(SetupAskSshInstallText, True):
		_print_InstallCard(trap_name, profile_name)
		_pause("Отдай карточку на хост ловушки, затем Enter")
		return None

	host = (_ask(SetupAskSshHostText, "") or "").strip()
	user = (_ask(SetupAskSshUserText, "root") or "root").strip()
	port = _ask_Int(SetupAskSshPortText, 22, 1, 65535)
	password = _ask_Secret(SetupAskSshPasswordText)
	api_base = client.get_BaseUrl()
	default_public = _public_Center_For_Card()
	if center_IsLoopback(api_base):
		print_Attention(SetupSshLocalCenterText)
		center = (_ask(SetupAskReachableCenterText, "") or "").strip()
	else:
		center = (_ask(SetupAskReachableCenterText, default_public) or default_public).strip()
	try:
		return _answers.run_Once(
			"install_agent",
			lambda: install_AgentOverSsh(
				host=host,
				user=user,
				password=password,
				port=port,
				center_url=check_CenterUrl(center),
			),
		)
	except client.ApiError as exc:
		print_Attention(SetupSshFailedText.format(detail=str(exc)))
		print_SetupTip(SetupSshManualFallbackText)
		_print_InstallCard(trap_name, profile_name)
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
	print_Attention(SetupApproveNodeText.format(trap_name=final_name))
	try:
		result = _answers.run_Once(
			"confirm_pairing",
			lambda: client.confirm_Pairing(
				device_code=device_code,
				trap_name=final_name,
				profile_id=profile_id,
			),
		)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		print_Attention(SetupStep4BadCodeText.format(code=device_code))
		print_SetupTip(SetupStep4BadCodeTipText)
		# Повтор: актуальный pending с центра, без stale-кода из deploy.
		if not _ask_YesNo(SetupAskPairListRetryText, True):
			return None
		return _wait_AndApprove(profile_id, final_name, known_code=None)

	trap_id = str(result.get("trap_id") or "")
	print(
		Fore.GREEN
		+ SetupStep4ApprovedText.format(trap_name=final_name, trap_id=trap_id)
		+ Style.RESET_ALL
	)
	print_SetupTip(SetupHostWillFinishText)
	print_SetupTip(SetupStep4TipOwner)
	if trap_id:
		_maybe_Assign_Owner(trap_id)
	return trap_id


def _print_User_Pick_List(users: list) -> None:
	print_OpsLine("users", str(len(users)))
	for item in users:
		uid = str(item.get("id") or "")
		name = str(item.get("username") or "?")
		role = str(item.get("role_name") or "-")
		print(f"  {Fore.GREEN}{uid}{Style.RESET_ALL}  {name}  role={role}")


def _maybe_Assign_Owner(trap_id: str) -> None:
	"""После confirm владелец = текущий оператор; можно сразу передать другому."""
	try:
		trap = client.get_Trap(trap_id)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return

	print_OpsLine("Владелец", str(trap.get("owner_user_id") or "-"))
	if not _ask_YesNo(SetupAskOwnerReassignText, False):
		print_SetupTip(SetupOwnerSetSkipText)
		return

	try:
		users = client.list_Users()
	except client.ApiError:
		print_SetupTip(SetupOwnerUsersListDeniedText)
		users = None
	else:
		if not users:
			print(Fore.YELLOW + SetupOwnerUsersEmptyText + Style.RESET_ALL)
			return
		_print_User_Pick_List(users)

	user_id = (_ask(SetupAskOwnerUserIdText) or "").strip()
	if not user_id:
		print_SetupTip(SetupOwnerSetSkipText)
		return

	try:
		updated = _answers.run_Once(
			"set_owner",
			lambda: client.set_Trap_Owner(trap_id, user_id),
		)
		print(Fore.GREEN + SetupOwnerSetOkText + Style.RESET_ALL)
		print_OpsLine("Владелец", str(updated.get("owner_user_id") or "-"))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def _maybe_Set_Courier_Ssh(trap_id: str, default_host: str = "") -> None:
	if not _ask_YesNo(SetupAskTrapCourierSshText, True):
		return
	host = _ask(SetupAskSshHostText, default_host) or default_host
	if not host:
		print_Attention("Без host визиты курьера не запланируются.")
		return
	user = _ask(SetupAskSshUserText, "root") or "root"
	password = _ask_Secret(SetupAskSshPasswordText)
	port = _ask_Int(SetupAskSshPortText, 22, 1, 65535)
	data_dir = _ask("Каталог данных агента на ловушке", "/var/lib/metricsd") or "/var/lib/metricsd"
	try:
		_answers.run_Once(
			"set_courier_ssh",
			lambda: client.set_Trap_Courier_Ssh(
				trap_id,
				host=host,
				user=user,
				password=password,
				port=port,
				remote_data_dir=data_dir,
			),
		)
		print(Fore.GREEN + TrapCourierSshSavedText + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def _commission_Trap(
	trap_id: str | None,
	profile_id: str,
	trap_name: str,
	*,
	courier_mode: bool = False,
) -> None:
	_step_Header(SetupStep5Header)
	print_SetupTip(SetupStep5TipOnline)

	if not trap_id:
		print(Fore.YELLOW + "Узел не принят - ввод в строй пропущен." + Style.RESET_ALL)
		return

	if courier_mode:
		print_SetupTip(SetupDeliveryCourierTip)
		# В courier online по heartbeat не ждём - достаточно bind профиля.
		try:
			found = client.get_Trap(trap_id)
			if not found.get("profile_id"):
				client.bind_TrapProfile(trap_id, profile_id)
				found = client.get_Trap(trap_id)
			print_OpsLine("Узел", found.get("name") or trap_name)
			print_OpsLine("Владелец", str(found.get("owner_user_id") or "-"))
			print_OpsLine("courier_ssh", "да" if found.get("has_courier_ssh") else "нет")
			print(Fore.GREEN + SetupCourierCommissionOkText + Style.RESET_ALL)
		except client.ApiError as exc:
			print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		print()
		print_SetupTip(SetupStep5TipProbe)
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
		print_OpsLine("Владелец", str(found.get("owner_user_id") or "-"))
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
		if _answers.events_tail_opened:
			print_SetupTip(SetupEventsTailSkipText)
		else:
			print_SetupTip("Оставь ленту открытой и создай активность на приманке.")
			from commands.events import cmd_EventsTail

			cmd_EventsTail(None)
			_answers.events_tail_opened = True


def cmd_Setup(_args) -> None:
	print(SetupIntroText)
	_answers.reset()
	while True:
		try:
			_run_Setup_Wizard()
			return
		except SetupGoBack:
			print(Fore.YELLOW + SetupRewindText + Style.RESET_ALL)
			_answers.prepare_Replay()
		except KeyboardInterrupt:
			print()
			print(Fore.YELLOW + SetupAbortText + Style.RESET_ALL)
			return
		except client.ApiError as exc:
			print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
			return
		except ValueError as exc:
			print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
			return


def _run_Setup_Wizard() -> None:
	_step_Header(SetupStep1Header)
	print_SetupTip(SetupStep1TipSite)
	trap_name = _ask("Позывной узла", "dmz-ssh-01") or "dmz-ssh-01"
	segment = _ask("Сегмент размещения", "lab-dmz") or "lab-dmz"
	print_OpsLine("Узел", trap_name)
	print_OpsLine("Сегмент", segment)
	print_Attention("Сегмент ловушки изолирован от продакшена.")

	faces, emulation = _configure_All()
	stealth = _ask_Stealth()
	courier_mode = stealth.get("collection_mode") == "courier"
	profile_id, profile_name = _save_Profile(
		trap_name, faces, stealth, emulation=emulation
	)

	known_code = _install_OverSsh(trap_name, profile_name)
	trap_id = _wait_AndApprove(profile_id, trap_name, known_code)
	if trap_id and courier_mode:
		_maybe_Set_Courier_Ssh(trap_id)
	_commission_Trap(
		trap_id, profile_id, trap_name, courier_mode=courier_mode
	)

	print()
	print(Fore.GREEN + Style.BRIGHT + SetupDoneText.format(trap_name=trap_name) + Style.RESET_ALL)
	print_OpsLine("Сегмент", segment)
	print_OpsLine("Профиль", profile_name)
	if trap_id:
		print_OpsLine("Trap ID", trap_id)
		try:
			trap = client.get_Trap(trap_id)
			print_OpsLine("Владелец", str(trap.get("owner_user_id") or "-"))
		except client.ApiError:
			pass
	print()
	print_SetupTip(SetupDoneTipText)


cmd_Guide = cmd_Setup
