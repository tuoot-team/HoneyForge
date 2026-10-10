from colorama import Fore, Style

import client
from texts import LogoutSuccessText, MeErrorText, MsgApiError


def auth_Login(password: str) -> str | None:
	try:
		data = client.post_Login(password)
		return data.get("access_token")
	except client.ApiError as exc:
		if client.is_Debug():
			print(f"[DEBUG] login failed: {exc}")
		return None


def cmd_Logout(_args) -> None:
	try:
		client.post_Logout()
		print(Fore.YELLOW + LogoutSuccessText + Style.RESET_ALL)
	except client.ApiError as exc:
		client.clear_Token()
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_Me(_args) -> None:
	try:
		data = client.get_Me()
		client.print_Json(data)
	except client.ApiError as exc:
		print(Fore.RED + MeErrorText.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_Health(_args) -> None:
	try:
		client.print_Json(client.get_Health())
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
