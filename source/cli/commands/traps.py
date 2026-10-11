from colorama import Fore, Style

import client
import display
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
		display.print_PairingList(items, total=total, status=args.status)
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
		display.print_PairConfirm(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapsList(_args) -> None:
	try:
		display.print_TrapList(client.list_Traps())
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapShow(args) -> None:
	try:
		display.print_Trap(client.get_Trap(args.trap_id))
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_TrapBind(args) -> None:
	try:
		data = client.bind_TrapProfile(args.trap_id, args.profile_id)
		print(Fore.GREEN + TrapBoundText + Style.RESET_ALL)
		display.print_Trap(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
