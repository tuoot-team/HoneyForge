from __future__ import annotations

from pathlib import Path

from colorama import Fore, Style

import client
from texts import (
	FsPackDeletedText,
	FsPackListEmptyText,
	FsPackListHeaderText,
	FsPackUploadedText,
	MsgApiError,
)


def _format_Size(size_bytes: int) -> str:
	n = int(size_bytes or 0)
	if n < 1024:
		return f"{n} B"
	if n < 1024 * 1024:
		return f"{n / 1024:.1f} KiB"
	return f"{n / (1024 * 1024):.1f} MiB"


def cmd_FsPackList(_args) -> None:
	try:
		data = client.list_FsPacks()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	items = data.get("items") or []
	if not items:
		print(Fore.YELLOW + FsPackListEmptyText + Style.RESET_ALL)
		return
	print(Fore.CYAN + FsPackListHeaderText + Style.RESET_ALL)
	for item in items:
		token = item.get("token") or "?"
		name = item.get("name") or ""
		fmt = item.get("format") or ""
		size = _format_Size(item.get("size_bytes") or 0)
		print(f"  {token}  {name}  ({fmt}, {size})")


def _parse_UserPath(raw: str) -> Path:
	text = (raw or "").strip()
	if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
		text = text[1:-1].strip()
	return Path(text).expanduser().resolve()


def cmd_FsPackUpload(args) -> None:
	path = _parse_UserPath(args.file)
	if not path.is_file():
		print(Fore.RED + MsgApiError.format(detail=f"нет файла: {path}") + Style.RESET_ALL)
		return
	try:
		data = client.upload_FsPack(str(path), name=args.name or None)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + FsPackUploadedText.format(
		token=data.get("token") or "?",
		name=data.get("name") or "",
		size=_format_Size(data.get("size_bytes") or 0),
	) + Style.RESET_ALL)


def cmd_FsPackDelete(args) -> None:
	token = (args.token or "").strip()
	if not token:
		print(Fore.RED + MsgApiError.format(detail="нужен token") + Style.RESET_ALL)
		return
	try:
		client.delete_FsPack(token)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	print(Fore.GREEN + FsPackDeletedText.format(token=token) + Style.RESET_ALL)
