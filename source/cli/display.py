from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from colorama import Fore, Style

import client
from texts import (
	DispEmptyListText,
	DispMaskMethodsTitle,
	DispEventsHeaderText,
	DispPairConfirmHintText,
	DispProfilesHeaderText,
	DispSchemaHeaderText,
	DispTrapsHeaderText,
	print_OpsLine,
)


def paint_Status(status: str | None) -> str:
	raw = (status or "?").lower()
	label = status or "?"
	palette = {
		"online": Fore.GREEN + Style.BRIGHT,
		"completed": Fore.GREEN + Style.BRIGHT,
		"confirmed": Fore.CYAN + Style.BRIGHT,
		"pending": Fore.YELLOW + Style.BRIGHT,
		"offline": Fore.RED + Style.BRIGHT,
		"expired": Fore.RED,
	}
	color = palette.get(raw, Fore.WHITE)
	return f"{color}{label}{Style.RESET_ALL}"


def paint_Level(level: str | None) -> str:
	raw = (level or "?").lower()
	palette = {
		"low": Fore.GREEN,
		"medium": Fore.YELLOW,
		"high": Fore.RED + Style.BRIGHT,
	}
	color = palette.get(raw, Fore.WHITE)
	return f"{color}{level or '?'}{Style.RESET_ALL}"


def paint_EventType(event_type: str | None) -> str:
	raw = event_type or "?"
	hot = ("auth_attempt", "login", "credential", "db_command")
	warm = ("http_request", "banner_grab", "port_connect")
	if any(k in raw for k in hot):
		color = Fore.RED + Style.BRIGHT
	elif any(k in raw for k in warm):
		color = Fore.YELLOW
	else:
		color = Fore.CYAN
	return f"{color}{raw}{Style.RESET_ALL}"


def short_Id(value: Any, *, width: int = 8) -> str:
	text = str(value or "")
	if not text or text == "None":
		return "-"
	if len(text) <= width:
		return text
	return text[:width]


def format_Time(value: Any) -> str:
	if value is None or value == "":
		return "-"
	text = str(value).strip()
	if text.endswith("Z"):
		text = text[:-1] + "+00:00"
	try:
		dt = datetime.fromisoformat(text)
		return dt.strftime("%Y-%m-%d %H:%M:%S")
	except ValueError:
		return str(value)


def print_Section(title: str) -> None:
	print()
	print(Fore.CYAN + Style.BRIGHT + title + Style.RESET_ALL)
	print(Fore.CYAN + ("-" * min(56, max(12, len(title)))) + Style.RESET_ALL)


def print_Empty(what: str) -> None:
	print(Fore.YELLOW + DispEmptyListText.format(what=what) + Style.RESET_ALL)


def maybe_Print_RawJson(data: Any) -> None:
	if not client.is_Debug():
		return
	print(Style.DIM + "[DEBUG] raw json:" + Style.RESET_ALL)
	print(Style.DIM + json.dumps(data, ensure_ascii=False, indent=2, default=str) + Style.RESET_ALL)


def print_Health(data: dict) -> None:
	print_Section("health")
	status = data.get("status", "?")
	ok = str(status).lower() in ("ok", "healthy", "up")
	status_paint = (Fore.GREEN if ok else Fore.RED) + str(status) + Style.RESET_ALL
	print_OpsLine("status", status_paint)
	for key, value in data.items():
		if key == "status":
			continue
		print_OpsLine(key, str(value))
	maybe_Print_RawJson(data)


def print_Me(data: dict) -> None:
	print_Section("user")
	print_OpsLine("username", str(data.get("username", "?")))
	print_OpsLine("role", str(data.get("role", "?")))
	for key, value in data.items():
		if key in ("username", "role"):
			continue
		if key == "permissions" and isinstance(value, list):
			print_OpsLine(key, ", ".join(str(item) for item in value))
			continue
		print_OpsLine(key, str(value))
	maybe_Print_RawJson(data)


def print_ProfileList(items: list) -> None:
	if not items:
		print_Empty("профилей")
		return
	print_Section(DispProfilesHeaderText.format(total=len(items)))
	print(
		f"  {Style.DIM}"
		f"{'id':<10} {'level':<8} {'ver':>4}  name"
		f"{Style.RESET_ALL}"
	)
	for item in items:
		pid = short_Id(item.get("id"))
		level = paint_Level(item.get("interaction_level"))
		ver = item.get("config_version", "?")
		name = item.get("name", "?")
		raw_level = str(item.get("interaction_level") or "?")
		pad = " " * max(0, 8 - len(raw_level))
		print(f"  {Fore.GREEN}{pid:<10}{Style.RESET_ALL}{level}{pad} {ver:>4}  {Style.BRIGHT}{name}{Style.RESET_ALL}")
	maybe_Print_RawJson(items)


def _print_Services(services: list) -> None:
	if not services:
		print_OpsLine("services", "-")
		return
	print_OpsLine("services", str(len(services)))
	for svc in services:
		enabled = svc.get("enabled", True)
		mark = Fore.GREEN + "on " if enabled else Style.DIM + "off"
		name = svc.get("type") or svc.get("name", "?")
		service_id = svc.get("id") or name
		port = svc.get("port", "?")
		proto = svc.get("protocol", "tcp")
		print(
			f"    {mark}{Style.RESET_ALL} "
			f"{Fore.YELLOW}{service_id}{Style.RESET_ALL} "
			f"[{name}] "
			f"{proto}/{Fore.CYAN}{port}{Style.RESET_ALL}"
		)
		modules = svc.get("modules") or {}
		if name == "ssh":
			banner = modules.get("banner") or {}
			auth = modules.get("auth") or {}
			shell = modules.get("shell") or {}
			auth_label = "off"
			if auth.get("enabled", True):
				auth_label = str(auth.get("mode") or "allow_all")
			shell_label = "on" if shell.get("enabled", True) else "off"
			pack = shell.get("fs_pack") or ""
			pack_label = f" pack={pack}" if pack and shell_label == "on" else ""
			print(
				f"        banner={banner.get('version', '')} "
				f"auth={auth_label} shell={shell_label}{pack_label}"
				f"{_format_AuthDelay(auth)}{_format_AuthRefs(auth)}"
			)
		elif name == "http":
			personality = modules.get("personality") or {}
			auth = modules.get("auth") or {}
			auth_label = "off"
			if auth.get("enabled"):
				auth_label = str(auth.get("mode") or "allow_all")
			print(
				f"        server={personality.get('server', '?')} "
				f"auth={auth_label}"
				f"{_format_AuthDelay(auth)}{_format_AuthRefs(auth)}"
			)
		elif name in ("postgres", "redis", "mysql"):
			banner = modules.get("banner") or {}
			auth = modules.get("auth") or {}
			session = modules.get("session") or {}
			auth_label = "off"
			if auth.get("enabled", True):
				auth_label = str(auth.get("mode") or "allow_all")
			session_label = "on" if session.get("enabled", True) else "off"
			print(
				f"        version={banner.get('version', '')} "
				f"auth={auth_label} session={session_label}"
				f"{_format_AuthDelay(auth)}{_format_AuthRefs(auth)}"
			)
		elif name == "tcp_banner":
			banner = (modules.get("banner") or "").strip()
			if banner:
				print(f"        banner={banner}")


def _format_AuthDelay(auth: dict) -> str:
	delay_min = auth.get("delay_ms_min") or 0
	delay_max = auth.get("delay_ms_max") or 0
	if not delay_min and not delay_max:
		return ""
	return f" delay={delay_min}-{delay_max}ms"


def _format_AuthRefs(auth: dict) -> str:
	parts: list[str] = []
	credential_ids = auth.get("credential_ids") or []
	if credential_ids:
		parts.append("creds=" + ",".join(str(item) for item in credential_ids))
	if auth.get("mode") == "second_attempt_sticky" and auth.get("sticky_ttl_hours"):
		parts.append(f"ttl={auth.get('sticky_ttl_hours')}h")
	path = auth.get("path")
	if path and auth.get("enabled"):
		parts.append(f"path={path}")
	if not parts:
		return ""
	return " " + " ".join(parts)


def _print_Credentials(creds: list) -> None:
	if not creds:
		print_OpsLine("creds", "-")
		return
	print_OpsLine("creds", str(len(creds)))
	for cred in creds:
		credential_id = cred.get("id", "?")
		user = cred.get("username", "?")
		password = cred.get("password", "?")
		print(
			f"    {credential_id}  {Fore.RED}{user}{Style.RESET_ALL}"
			f":{Fore.RED}{password}{Style.RESET_ALL}"
		)


def _method_Mark(method: dict) -> str:
	if method.get("enabled", True):
		return Fore.GREEN + "on " + Style.RESET_ALL
	return Style.DIM + "off" + Style.RESET_ALL


def _print_Mask(mask: dict) -> None:
	if not mask:
		print_OpsLine("mask", "-")
		return
	if "jitter" not in mask and "beacon_interval_sec" in mask:
		mask = {
			"jitter": {
				"enabled": True,
				"beacon_interval_sec": mask.get("beacon_interval_sec"),
				"jitter_pct": mask.get("jitter_pct"),
			},
			"cover": {"enabled": bool(mask.get("cover_urls")), "urls": mask.get("cover_urls") or []},
			"path_rotation": {
				"enabled": bool(mask.get("collector_path_set")),
				"paths": mask.get("collector_path_set") or [],
			},
			"mimicry": {"enabled": True, "user_agent": mask.get("user_agent", "")},
			"process_mask": {"enabled": True, "name": mask.get("process_name", "")},
		}
	print_OpsLine("mask", DispMaskMethodsTitle)
	jitter = mask.get("jitter") or {}
	print(
		f"    {_method_Mark(jitter)} jitter  "
		f"interval={jitter.get('beacon_interval_sec', '?')}s  "
		f"spread={jitter.get('jitter_pct', '?')}%"
	)
	cover = mask.get("cover") or {}
	print(
		f"    {_method_Mark(cover)} cover   "
		+ ", ".join(str(item) for item in (cover.get("urls") or []))
	)
	paths = mask.get("path_rotation") or {}
	print(
		f"    {_method_Mark(paths)} paths   "
		+ ", ".join(str(item) for item in (paths.get("paths") or []))
	)
	mimicry = mask.get("mimicry") or {}
	print(f"    {_method_Mark(mimicry)} mimicry {mimicry.get('user_agent', '')}")
	process_mask = mask.get("process_mask") or {}
	print(f"    {_method_Mark(process_mask)} process {process_mask.get('name', '')}")


def print_Profile(data: dict) -> None:
	print_Section(f"profile  {data.get('name', '?')}")
	print_OpsLine("id", str(data.get("id", "?")))
	print_OpsLine("level", paint_Level(data.get("interaction_level")))
	print_OpsLine("version", str(data.get("config_version", "?")))
	print_OpsLine("hash", short_Id(data.get("config_hash"), width=12))
	desc = data.get("description") or ""
	if desc:
		print_OpsLine("desc", desc)
	print_OpsLine("updated", format_Time(data.get("updated_at")))

	blocks = data.get("blocks") or {}
	_print_Services(blocks.get("services") or [])
	_print_Credentials(blocks.get("credentials") or [])
	_print_Mask(blocks.get("mask") or {})

	logging = blocks.get("logging") or {}
	if logging:
		print_OpsLine(
			"logging",
			f"creds={logging.get('capture_credentials')}  "
			f"payloads={logging.get('capture_payloads')}  "
			f"source={logging.get('capture_source_meta')}",
		)
	maybe_Print_RawJson(data)


def print_ProfileSchema(data: dict) -> None:
	print_Section(DispSchemaHeaderText)
	levels = data.get("interaction_levels") or []
	keys = data.get("block_keys") or []
	print_OpsLine("levels", ", ".join(str(x) for x in levels))
	print_OpsLine("blocks", ", ".join(str(x) for x in keys))
	service_types = data.get("service_types") or []
	auth_modes = data.get("auth_modes") or []
	if service_types:
		print_OpsLine("services", ", ".join(str(x) for x in service_types))
	if auth_modes:
		print_OpsLine("auth", ", ".join(str(x) for x in auth_modes))
	mask_methods = data.get("mask_methods") or []
	if mask_methods:
		print_OpsLine("mask", ", ".join(str(x) for x in mask_methods))
	example = data.get("example")
	if example:
		print()
		print(Style.DIM + "example:" + Style.RESET_ALL)
		print_Profile(example if isinstance(example, dict) else {})
	else:
		maybe_Print_RawJson(data)


def print_TrapList(items: list) -> None:
	if not items:
		print_Empty("ловушек")
		return
	print_Section(DispTrapsHeaderText.format(total=len(items)))
	print(
		f"  {Style.DIM}"
		f"{'id':<10} {'status':<10} {'last_seen':<19}  name"
		f"{Style.RESET_ALL}"
	)
	for item in items:
		tid = short_Id(item.get("id"))
		raw_status = str(item.get("status") or "?")
		status = paint_Status(raw_status)
		pad = " " * max(0, 10 - len(raw_status))
		seen = format_Time(item.get("last_seen_at"))
		name = item.get("name", "?")
		print(
			f"  {Fore.GREEN}{tid:<10}{Style.RESET_ALL}"
			f"{status}{pad} {seen:<19}  {Style.BRIGHT}{name}{Style.RESET_ALL}"
		)
	maybe_Print_RawJson(items)


def print_Trap(data: dict) -> None:
	print_Section(f"trap  {data.get('name', '?')}")
	print_OpsLine("id", str(data.get("id", "?")))
	print_OpsLine("status", paint_Status(data.get("status")))
	print_OpsLine("profile", str(data.get("profile_id") or "-"))
	print_OpsLine("last_seen", format_Time(data.get("last_seen_at")))
	print_OpsLine("created", format_Time(data.get("created_at")))
	print_OpsLine("updated", format_Time(data.get("updated_at")))
	meta = data.get("meta") or {}
	if meta:
		print_OpsLine("meta", json.dumps(meta, ensure_ascii=False, default=str))
	maybe_Print_RawJson(data)


def print_PairConfirm(data: dict) -> None:
	print_Section("pairing confirm")
	print_OpsLine("trap_id", str(data.get("trap_id", "?")))
	print_OpsLine("pairing", str(data.get("pairing_id", "-")))
	print_OpsLine("status", paint_Status(data.get("status")))
	if data.get("profile_id"):
		print_OpsLine("profile", str(data.get("profile_id")))
	if data.get("stale_minutes") is not None:
		print_OpsLine("stale", f"{data.get('stale_minutes')} min")
	print(Fore.YELLOW + DispPairConfirmHintText + Style.RESET_ALL)
	maybe_Print_RawJson(data)


def print_PairingList(items: list, *, total: int, status: str) -> None:
	for item in items:
		code = item.get("device_code", "?")
		st = paint_Status(item.get("status"))
		expires = format_Time(item.get("expires_at"))
		created = format_Time(item.get("created_at"))
		pairing_id = short_Id(item.get("pairing_id") or item.get("id"))
		print(
			f"  {Fore.GREEN}{Style.BRIGHT}{code}{Style.RESET_ALL}"
			f"  {st}"
			f"  created={created}"
			f"  expires={Fore.YELLOW}{expires}{Style.RESET_ALL}"
			f"  id={pairing_id}"
		)
	maybe_Print_RawJson({"total": total, "status": status, "items": items})


def _payload_Summary(payload: dict | None) -> str:
	if not payload:
		return ""
	parts: list[str] = []
	for key in ("username", "password", "command", "database", "service", "path", "method", "port", "banner"):
		if key in payload and payload[key] not in (None, ""):
			val = payload[key]
			if key in ("username", "password", "command"):
				parts.append(f"{key}={Fore.RED}{val}{Style.RESET_ALL}")
			elif key == "path":
				parts.append(f"{key}={Fore.YELLOW}{val}{Style.RESET_ALL}")
			else:
				parts.append(f"{key}={val}")
	if not parts:
		extra = {k: v for k, v in payload.items() if k not in ("raw",)}
		if extra:
			return json.dumps(extra, ensure_ascii=False, default=str)[:80]
	return "  ".join(parts)


def print_EventRow(event: dict) -> None:
	occurred = format_Time(event.get("occurred_at") or event.get("created_at"))
	etype = paint_EventType(event.get("event_type"))
	ip = event.get("source_ip") or "-"
	port = event.get("source_port")
	src = f"{Fore.CYAN}{ip}{Style.RESET_ALL}"
	if port not in (None, ""):
		src += f":{port}"
	trap = short_Id(event.get("trap_id"))
	summary = _payload_Summary(event.get("payload") or {})
	eid = event.get("id", "")
	id_part = f"{Style.DIM}#{eid}{Style.RESET_ALL} " if eid != "" else ""
	print(f"  {id_part}{occurred}  {etype}  {src}  trap={trap}  {summary}")


def print_EventList(data: dict) -> None:
	items = data.get("items") or []
	total = data.get("total", len(items))
	if not items:
		print_Empty("событий")
		maybe_Print_RawJson(data)
		return
	print_Section(DispEventsHeaderText.format(shown=len(items), total=total))
	for event in items:
		print_EventRow(event)
	maybe_Print_RawJson(data)


def print_SseDataLine(raw: str) -> None:
	text = raw.strip()
	if not text:
		return
	try:
		payload = json.loads(text)
	except json.JSONDecodeError:
		print(text)
		return
	if isinstance(payload, dict):
		event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
		if event.get("event_type") or event.get("source_ip") is not None:
			print_EventRow(event)
			return
	print(json.dumps(payload, ensure_ascii=False, default=str))
