from __future__ import annotations

import getpass

from colorama import Fore, Style

import client
from texts import (
	CourierConfirmText,
	CourierDeployNextText,
	CourierDeployText,
	CourierListEmptyText,
	CourierListHeaderText,
	CourierPairListEmptyText,
	CourierPairListHeaderText,
	MsgApiError,
	SetupAskSshPasswordText,
	TrapCourierSshSavedText,
	print_OpsLine,
)


def cmd_CourierList(_args) -> None:
	try:
		items = client.list_Couriers()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	if not items:
		print(Fore.YELLOW + CourierListEmptyText + Style.RESET_ALL)
		return
	print(Fore.CYAN + CourierListHeaderText.format(total=len(items)) + Style.RESET_ALL)
	for item in items:
		print(
			f"  {item.get('id')}  {item.get('name')}  "
			f"status={item.get('status')}  owner={item.get('owner_user_id') or '-'}"
		)


def cmd_CourierShow(args) -> None:
	try:
		data = client.get_Courier(args.courier_id)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print_OpsLine("id", str(data.get("id", "?")))
	print_OpsLine("name", str(data.get("name", "?")))
	print_OpsLine("status", str(data.get("status", "?")))
	print_OpsLine("owner", str(data.get("owner_user_id") or "-"))
	print_OpsLine("last_seen", str(data.get("last_seen_at") or "-"))


def cmd_CourierPairList(args) -> None:
	try:
		data = client.list_Courier_Pairings(status=args.status)
		items = data.get("items") or []
		total = data.get("total", len(items))
		if not items:
			print(
				Fore.YELLOW
				+ CourierPairListEmptyText.format(status=args.status)
				+ Style.RESET_ALL
			)
			return
		print(
			Fore.CYAN
			+ CourierPairListHeaderText.format(total=total, status=args.status)
			+ Style.RESET_ALL
		)
		for item in items:
			print(
				f"  {item.get('device_code')}  id={item.get('id')}  "
				f"status={item.get('status')}"
			)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_CourierConfirm(args) -> None:
	try:
		data = client.confirm_Courier_Pairing(args.device_code, name=args.name)
		print(Fore.GREEN + CourierConfirmText + Style.RESET_ALL)
		print_OpsLine("courier_id", str(data.get("courier_id", "?")))
		print_OpsLine("pairing", str(data.get("pairing_id", "-")))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_CourierDeploy(args) -> None:
	password = getattr(args, "password", "") or ""
	if not password:
		password = getpass.getpass(SetupAskSshPasswordText)
	try:
		data = client.deploy_Courier(
			host=args.host,
			user=args.user,
			password=password,
			port=args.port,
			center_url=args.api_base or None,
		)
		code = data.get("device_code") or "?"
		print(Fore.GREEN + CourierDeployText.format(code=code) + Style.RESET_ALL)
		print_OpsLine("дальше", CourierDeployNextText.format(code=code))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapSetCourierSsh(args) -> None:
	password = getattr(args, "password", "") or ""
	if not password and not getattr(args, "private_key", None):
		password = getpass.getpass(SetupAskSshPasswordText)
	try:
		data = client.set_Trap_Courier_Ssh(
			args.trap_id,
			host=args.host,
			user=args.user,
			password=password or None,
			private_key=getattr(args, "private_key", None),
			port=args.port,
			remote_data_dir=args.data_dir,
		)
		print(Fore.GREEN + TrapCourierSshSavedText + Style.RESET_ALL)
		print_OpsLine("host", str(data.get("host", args.host)))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
