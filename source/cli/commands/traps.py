from colorama import Fore, Style

import client
from texts import (
	MsgApiError,
	PairConfirmText,
	PairListEmptyText,
	PairListHeaderText,
	TrapBoundText,
)


def cmd_PairList(args) -> None:
	try:
		data = client.list_Pairings(status=args.status)
		items = data.get("items") or []
		total = data.get("total", len(items))
		if not items:
			print(Fore.YELLOW + PairListEmptyText.format(status=args.status) + Style.RESET_ALL)
			return
		print(Fore.CYAN + PairListHeaderText.format(total=total, status=args.status) + Style.RESET_ALL)
		for item in items:
			code = item.get("device_code", "?")
			status = item.get("status", "?")
			expires = item.get("expires_at", "")
			created = item.get("created_at", "")
			pairing_id = item.get("pairing_id", "")
			print(
				f"  {Fore.GREEN}{code}{Style.RESET_ALL}"
				f"  status={status}"
				f"  created={created}"
				f"  expires={expires}"
				f"  id={pairing_id}"
			)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_PairConfirm(args) -> None:
	try:
		data = client.confirm_Pairing(
			device_code=args.device_code,
			trap_name=args.name,
			profile_id=args.profile_id,
		)
		print(Fore.GREEN + PairConfirmText + Style.RESET_ALL)
		client.print_Json(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapsList(_args) -> None:
	try:
		client.print_Json(client.list_Traps())
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapShow(args) -> None:
	try:
		client.print_Json(client.get_Trap(args.trap_id))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapBind(args) -> None:
	try:
		data = client.bind_TrapProfile(args.trap_id, args.profile_id)
		print(Fore.GREEN + TrapBoundText + Style.RESET_ALL)
		client.print_Json(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
