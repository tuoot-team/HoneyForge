from __future__ import annotations

import getpass
import urllib.parse

import client
from texts import (
	DeployBadCenterText,
	DeployNoDeviceCodeText,
	DeployPairNextText,
	MsgApiError,
	SetupAskSshPasswordText,
	SetupSshCodeText,
	SetupSshConnectingText,
	print_OpsLine,
)

_LOOPBACK = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def center_IsLoopback(url: str) -> bool:
	host = (urllib.parse.urlparse(url.strip()).hostname or "").lower()
	return host in _LOOPBACK


def check_CenterUrl(raw: str) -> str:
	url = raw.strip().rstrip("/")
	# host:port без схемы - считаем https (как у публичного канала центра).
	if url and "://" not in url:
		url = "https://" + url
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme not in ("http", "https") or not parsed.hostname:
		raise client.ApiError(DeployBadCenterText)
	if any(char in url for char in "\"'`\\\n\r$;|&<> "):
		raise client.ApiError(DeployBadCenterText)
	return url


def public_Agent_Center_Url(raw: str) -> str:
	"""URL для агента/курьера/downloads: без операторского :8088."""
	url = check_CenterUrl(raw)
	parsed = urllib.parse.urlparse(url)
	if parsed.port == 8088 and parsed.hostname:
		return f"{parsed.scheme}://{parsed.hostname}"
	return url


def install_AgentOverSsh(
	*,
	host: str,
	user: str,
	password: str,
	port: int,
	center_url: str,
) -> str:
	center = check_CenterUrl(center_url)
	print(SetupSshConnectingText.format(user=user, host=host, port=port))
	result = client.deploy_Agent(
		host=host,
		user=user,
		password=password,
		port=port,
		center_url=center,
	)
	code = str(result.get("device_code") or "").strip()
	if not code:
		raise client.ApiError(DeployNoDeviceCodeText)
	return code


def cmd_Deploy(args) -> None:
	from colorama import Fore, Style

	host = (getattr(args, "host", "") or "").strip()
	if not host:
		host = input("IP хоста ловушки: ").strip()
	user = (getattr(args, "user", "") or "root").strip() or "root"
	port = int(getattr(args, "port", 22) or 22)
	center = (getattr(args, "api_base", "") or "").strip() or client.get_BaseUrl()
	password = getattr(args, "password", "") or ""
	if not password:
		password = getpass.getpass(SetupAskSshPasswordText)
	try:
		code = install_AgentOverSsh(
			host=host,
			user=user,
			password=password,
			port=port,
			center_url=center,
		)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + SetupSshCodeText.format(code=code) + Style.RESET_ALL)
	print_OpsLine("дальше", DeployPairNextText.format(code=code))
