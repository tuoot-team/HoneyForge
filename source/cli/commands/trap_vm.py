from __future__ import annotations

from colorama import Fore, Style

import client
import display
from texts import MsgApiError, TrapVmCommandText


def cmd_TrapVm(args) -> None:
	action = (args.action or "").strip().lower()
	trap_id = (args.trap_id or "").strip()
	if not trap_id:
		print(Fore.RED + MsgApiError.format(detail="нужен --trap-id") + Style.RESET_ALL)
		return
	if action not in ("ensure", "start", "stop", "revert", "status"):
		print(Fore.RED + MsgApiError.format(detail=f"неизвестное действие: {action}") + Style.RESET_ALL)
		return
	try:
		data = client.trap_Vm_Action(trap_id, action)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + TrapVmCommandText.format(action=action, trap_id=trap_id) + Style.RESET_ALL)
	display.print_Trap(data)
