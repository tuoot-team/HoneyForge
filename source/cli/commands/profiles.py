from __future__ import annotations

import json
from pathlib import Path

from colorama import Fore, Style

import client
import display
from texts import (
	MsgApiError,
	ProfileAuthNeedsMediumText,
	ProfileAuthOnBannerText,
	ProfileBannerNeedsLowText,
	ProfileCreateUsageText,
	ProfileCreatedText,
	ProfileDelayOrderText,
	ProfileDelayPairText,
	ProfileDeletedText,
	ProfileHighUnavailableText,
	ProfileHttpNeedsMediumText,
	ProfileListedNeedsCredsText,
	ProfilePasswordRequiredText,
	ProfileServiceUnknownText,
	ProfileUpdatedText,
	ProfileUpdateUsageText,
)


def _load_Body_FromFile(path: str) -> dict:
	raw = Path(path).read_text(encoding="utf-8")
	return json.loads(raw)


def _credential_Pair(args, service_name: str) -> tuple[list[dict], list[str]]:
	username = (args.username or "").strip()
	if not username and args.password is None:
		return [], []
	if not username or args.password is None or args.password == "":
		raise ValueError(ProfilePasswordRequiredText)
	credential_id = f"{service_name}-bait"
	return [
		{
			"id": credential_id,
			"username": username,
			"password": args.password,
			"note": "bait",
		}
	], [credential_id]


def _delay_Pair(args, auth_enabled: bool) -> tuple[int, int]:
	has_min = args.delay_min is not None
	has_max = args.delay_max is not None
	if has_min != has_max:
		raise ValueError(ProfileDelayPairText)
	if has_min and args.delay_max < args.delay_min:
		raise ValueError(ProfileDelayOrderText)
	if has_min:
		return args.delay_min, args.delay_max
	if auth_enabled:
		return 200, 800
	return 0, 0


def _resolve_AuthMode(args, service_name: str, has_credentials: bool) -> str:
	mode = (args.auth or "").lower()
	if mode == "allow_listed" and not has_credentials:
		raise ValueError(ProfileListedNeedsCredsText)
	if mode:
		return mode
	if has_credentials:
		return "allow_listed"
	if (args.level or "").lower() == "low" or service_name == "tcp_banner":
		return "off"
	if service_name == "http":
		return "off"
	return "allow_all"


def _http_Routes(auth_path: str) -> list[dict]:
	home = {
		"path": "/",
		"methods": ["GET"],
		"status": 200,
		"content_type": "text/html; charset=utf-8",
		"body": "<html><body>It works.</body></html>",
	}
	routes = [home]
	if auth_path and auth_path != "/":
		routes.append({
			"path": auth_path,
			"methods": ["GET"],
			"status": 200,
			"content_type": "text/html; charset=utf-8",
			"body": "<html><body>Administration</body></html>",
		})
	return routes


def _build_SimpleBody(args) -> dict:
	level_arg = (args.level or "").lower()
	if level_arg == "high":
		raise ValueError(ProfileHighUnavailableText)
	service_name = (args.service or "ssh").lower()
	if service_name == "https":
		service_name = "http"
	if service_name not in ("ssh", "http", "tcp_banner"):
		raise ValueError(ProfileServiceUnknownText)

	credentials, credential_ids = _credential_Pair(args, service_name)
	auth_mode = _resolve_AuthMode(args, service_name, bool(credentials))
	if service_name == "tcp_banner" and auth_mode != "off":
		raise ValueError(ProfileAuthOnBannerText)

	auth_enabled = auth_mode != "off"
	if service_name == "http":
		derived = "medium"
	elif auth_enabled:
		derived = "medium"
	else:
		derived = "low"
	if level_arg and level_arg != derived:
		if service_name == "http":
			raise ValueError(ProfileHttpNeedsMediumText)
		if service_name == "tcp_banner" or not auth_enabled:
			raise ValueError(ProfileBannerNeedsLowText)
		raise ValueError(ProfileAuthNeedsMediumText)

	delay_min, delay_max = _delay_Pair(args, auth_enabled)
	banner = (args.banner or "").strip()

	if service_name == "ssh":
		auth = {
			"enabled": auth_enabled,
			"mode": "allow_all" if not auth_enabled else auth_mode,
			"credential_ids": credential_ids if auth_mode in ("allow_listed", "second_attempt_sticky") else [],
			"delay_ms_min": delay_min,
			"delay_ms_max": delay_max,
		}
		if auth_mode == "second_attempt_sticky":
			auth["sticky_ttl_hours"] = args.sticky_ttl if args.sticky_ttl is not None else 72
		service = {
			"type": "ssh",
			"id": "ssh-1",
			"port": args.port,
			"enabled": True,
			"modules": {
				"banner": {
					"enabled": True,
					"version": banner or "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
				},
				"auth": auth,
				"shell": {
					"enabled": auth_enabled and not args.no_shell,
					"fs_pack": "ubuntu-22.04",
				},
			},
		}
	elif service_name == "http":
		auth = {
			"enabled": auth_enabled,
			"mode": "allow_all" if not auth_enabled else auth_mode,
			"credential_ids": credential_ids if auth_mode in ("allow_listed", "second_attempt_sticky") else [],
			"path": (args.auth_path or "/admin").strip() or "/admin",
			"delay_ms_min": delay_min,
			"delay_ms_max": delay_max,
		}
		if auth_mode == "second_attempt_sticky":
			auth["sticky_ttl_hours"] = args.sticky_ttl if args.sticky_ttl is not None else 72
		service = {
			"type": "http",
			"id": "http-1",
			"port": args.port,
			"enabled": True,
			"modules": {
				"personality": {
					"enabled": True,
					"server": (args.server or banner or "nginx/1.24.0"),
					"title": "Welcome",
				},
				"auth": auth,
				"routes": {
					"routes": _http_Routes(auth["path"] if auth_enabled else ""),
					"default_status": 404,
					"default_body": "404 - File or directory not found.",
				},
			},
		}
	else:
		service = {
			"type": "tcp_banner",
			"id": "banner-1",
			"port": args.port,
			"enabled": True,
			"modules": {"banner": banner},
		}

	return {
		"name": args.name,
		"description": args.description or "",
		"interaction_level": derived,
		"blocks": {
			"services": [service],
			"credentials": credentials,
			"logging": {
				"capture_credentials": True,
				"capture_payloads": True,
				"capture_source_meta": True,
			},
			"mask": {},
		},
	}


def cmd_ProfileSchema(_args) -> None:
	try:
		display.print_ProfileSchema(client.get_ProfileSchema())
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileList(_args) -> None:
	try:
		display.print_ProfileList(client.list_Profiles())
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileShow(args) -> None:
	try:
		display.print_Profile(client.get_Profile(args.profile_id))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileCreate(args) -> None:
	try:
		if args.file:
			body = _load_Body_FromFile(args.file)
		else:
			if not args.name or not args.port:
				print(Fore.RED + ProfileCreateUsageText + Style.RESET_ALL)
				return
			body = _build_SimpleBody(args)

		client.validate_Profile(body)
		created = client.create_Profile(body)
		print(Fore.GREEN + ProfileCreatedText.format(profile_id=created.get("id")) + Style.RESET_ALL)
		display.print_Profile(created)
	except (client.ApiError, OSError, json.JSONDecodeError, ValueError) as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileUpdate(args) -> None:
	try:
		body: dict = {}
		if args.file:
			loaded = _load_Body_FromFile(args.file)
			for key in ("name", "description", "interaction_level", "blocks"):
				if key in loaded:
					body[key] = loaded[key]
		if args.name:
			body["name"] = args.name
		if args.description:
			body["description"] = args.description
		if not body:
			print(Fore.RED + ProfileUpdateUsageText + Style.RESET_ALL)
			return
		updated = client.update_Profile(args.profile_id, body)
		print(Fore.GREEN + ProfileUpdatedText.format(profile_id=updated.get("id")) + Style.RESET_ALL)
		display.print_Profile(updated)
	except (client.ApiError, OSError, json.JSONDecodeError, ValueError) as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileDelete(args) -> None:
	try:
		client.delete_Profile(args.profile_id)
		print(Fore.GREEN + ProfileDeletedText.format(profile_id=args.profile_id) + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
