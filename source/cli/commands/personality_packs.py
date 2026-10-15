from colorama import Fore, Style

import client
from texts import (
	MsgApiError,
	PersonalityPackListEmptyText,
	PersonalityPackListHeaderText,
)


def cmd_PersonalityPackList(_args) -> None:
	try:
		data = client.list_PersonalityPacks()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	items = data.get("items") or []
	if not items:
		print(Fore.YELLOW + PersonalityPackListEmptyText + Style.RESET_ALL)
		return
	print(Fore.CYAN + PersonalityPackListHeaderText + Style.RESET_ALL)
	for item in items:
		key = item.get("key") or "?"
		title = item.get("title") or ""
		print(f"  {Fore.GREEN}{key}{Style.RESET_ALL}  {title}")
