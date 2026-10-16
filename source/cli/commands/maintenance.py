from colorama import Fore, Style

import client
from texts import (
	DbResetText,
	LogsClearedText,
	MsgApiError,
	WipeAbortedText,
	WipeConfirmLogsText,
	WipeConfirmResetText,
)


def _confirm(prompt: str) -> bool:
	raw = input(Fore.GREEN + prompt + " " + Style.RESET_ALL).strip().lower()
	return raw in ("y", "yes", "д", "да")


def cmd_LogsClear(args) -> None:
	if not args.yes and not _confirm(WipeConfirmLogsText):
		print(Fore.YELLOW + WipeAbortedText + Style.RESET_ALL)
		return
	try:
		data = client.clear_Logs()
		deleted = data.get("deleted") or {}
		print(Fore.GREEN + LogsClearedText.format(
			events=deleted.get("events", 0),
			audit_log=deleted.get("audit_log", 0),
		) + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_DbReset(args) -> None:
	if not args.yes and not _confirm(WipeConfirmResetText):
		print(Fore.YELLOW + WipeAbortedText + Style.RESET_ALL)
		return
	try:
		data = client.reset_Database()
		deleted = data.get("deleted") or {}
		print(Fore.GREEN + DbResetText.format(
			profiles=deleted.get("profiles", 0),
			traps=deleted.get("traps", 0),
			courier_visits=deleted.get("courier_visits", 0),
			pairing_sessions=deleted.get("pairing_sessions", 0),
			trap_commands=deleted.get("trap_commands", 0),
			events=deleted.get("events", 0),
			audit_log=deleted.get("audit_log", 0),
		) + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
