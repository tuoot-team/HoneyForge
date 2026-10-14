from __future__ import annotations

from getpass import getpass

from colorama import Fore, Style

import client
from texts import (
	MsgApiError,
	UserCreatedText,
	UserDisabledText,
	UserListEmptyText,
	UserListHeaderText,
	UserUpdatedText,
)


def cmd_UserList(_args) -> None:
	try:
		items = client.list_Users()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	if not items:
		print(Fore.YELLOW + UserListEmptyText + Style.RESET_ALL)
		return
	print(Fore.CYAN + UserListHeaderText + Style.RESET_ALL)
	for item in items:
		flags = []
		if item.get("is_superadmin"):
			flags.append("superadmin")
		if item.get("disabled"):
			flags.append("disabled")
		flag_s = f" [{', '.join(flags)}]" if flags else ""
		print(
			f"  {item.get('id')}  {item.get('username')}  "
			f"role={item.get('role_name')}{flag_s}"
		)


def cmd_UserCreate(args) -> None:
	username = (args.username or "").strip()
	role_id = (args.role_id or "").strip()
	password = args.password or ""
	if not password:
		password = getpass("Пароль нового пользователя: ")
	if not username or not role_id or not password:
		print(Fore.RED + MsgApiError.format(detail="нужны --username --role-id и пароль") + Style.RESET_ALL)
		return
	try:
		data = client.create_User(
			username,
			password,
			role_id,
			is_superadmin=bool(args.superadmin),
		)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + UserCreatedText.format(
		username=data.get("username"),
		user_id=data.get("id"),
		role=data.get("role_name"),
	) + Style.RESET_ALL)


def cmd_UserSetRole(args) -> None:
	try:
		data = client.update_User(args.user_id, role_id=args.role_id)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + UserUpdatedText.format(
		username=data.get("username"),
		role=data.get("role_name"),
	) + Style.RESET_ALL)


def cmd_UserDisable(args) -> None:
	disabled = not bool(args.enable)
	try:
		data = client.update_User(args.user_id, disabled=disabled)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + UserDisabledText.format(
		username=data.get("username"),
		state="отключён" if data.get("disabled") else "включён",
	) + Style.RESET_ALL)
