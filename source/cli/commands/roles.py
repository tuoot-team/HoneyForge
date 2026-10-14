from __future__ import annotations

from colorama import Fore, Style

import client
from texts import (
	MsgApiError,
	RoleCreatedText,
	RoleDeletedText,
	RoleListEmptyText,
	RoleListHeaderText,
	RolePermsHeaderText,
	RoleUpdatedText,
)


def cmd_RoleList(_args) -> None:
	try:
		items = client.list_Roles()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	if not items:
		print(Fore.YELLOW + RoleListEmptyText + Style.RESET_ALL)
		return
	print(Fore.CYAN + RoleListHeaderText + Style.RESET_ALL)
	for item in items:
		sys_mark = " (system)" if item.get("is_system") else ""
		perms = ",".join(item.get("permissions") or [])
		print(f"  {item.get('id')}  {item.get('name')}{sys_mark}")
		print(f"      {perms}")


def cmd_RolePerms(_args) -> None:
	try:
		data = client.list_Role_Permissions()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.CYAN + RolePermsHeaderText + Style.RESET_ALL)
	for name in data.get("permissions") or []:
		print(f"  {name}")


def cmd_RoleCreate(args) -> None:
	name = (args.name or "").strip()
	raw = (args.permissions or "").strip()
	perms = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
	if not name:
		print(Fore.RED + MsgApiError.format(detail="нужен --name") + Style.RESET_ALL)
		return
	try:
		data = client.create_Role(name, perms)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + RoleCreatedText.format(
		name=data.get("name"),
		role_id=data.get("id"),
	) + Style.RESET_ALL)


def cmd_RoleSetPerms(args) -> None:
	raw = (args.permissions or "").strip()
	perms = [p.strip() for p in raw.split(",") if p.strip()]
	try:
		data = client.update_Role(args.role_id, permissions=perms)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + RoleUpdatedText.format(name=data.get("name")) + Style.RESET_ALL)


def cmd_RoleDelete(args) -> None:
	try:
		client.delete_Role(args.role_id)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + RoleDeletedText.format(role_id=args.role_id) + Style.RESET_ALL)
