from __future__ import annotations

import json
from pathlib import Path

from colorama import Fore, Style

import client
from texts import MsgApiError, ProfileCreatedText, ProfileDeletedText


def _load_Body_FromFile(path: str) -> dict:
	raw = Path(path).read_text(encoding="utf-8")
	return json.loads(raw)


def _build_SimpleBody(args) -> dict:
	service = {
		"name": args.service,
		"protocol": "tcp",
		"port": args.port,
		"enabled": True,
		"options": {},
	}
	return {
		"name": args.name,
		"description": args.description or "",
		"interaction_level": args.level,
		"blocks": {
			"services": [service],
			"banners": [],
			"credentials": [],
			"logging": {},
			"mask": {},
		},
	}


def cmd_ProfileSchema(_args) -> None:
	try:
		client.print_Json(client.get_ProfileSchema())
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileList(_args) -> None:
	try:
		items = client.list_Profiles()
		client.print_Json(items)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileShow(args) -> None:
	try:
		client.print_Json(client.get_Profile(args.profile_id))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileCreate(args) -> None:
	try:
		if args.file:
			body = _load_Body_FromFile(args.file)
		else:
			if not args.name or not args.level or not args.port:
				print(Fore.RED + "нужны --file ИЛИ --name --level --port [--service]" + Style.RESET_ALL)
				return
			body = _build_SimpleBody(args)

		client.validate_Profile(body)
		created = client.create_Profile(body)
		print(Fore.GREEN + ProfileCreatedText.format(profile_id=created.get("id")) + Style.RESET_ALL)
		client.print_Json(created)
	except (client.ApiError, OSError, json.JSONDecodeError) as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_ProfileDelete(args) -> None:
	try:
		client.delete_Profile(args.profile_id)
		print(Fore.GREEN + ProfileDeletedText.format(profile_id=args.profile_id) + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
