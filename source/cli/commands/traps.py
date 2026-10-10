from colorama import Fore, Style

import client
from texts import MsgApiError, PairConfirmText, TrapBoundText


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
