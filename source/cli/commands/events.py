from pathlib import Path

from colorama import Fore, Style

import client
import display
from texts import (
	EventsExportSavedText,
	EventsTailHintText,
	EventsTailStoppedText,
	MsgApiError,
)


def cmd_EventsList(args) -> None:
	try:
		data = client.list_Events(
			trap_id=args.trap_id,
			event_type=args.type,
			source_ip=args.source_ip,
			min_priority=getattr(args, "min_priority", None),
			limit=args.limit,
		)
		display.print_EventList(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_EventsChains(args) -> None:
	try:
		data = client.list_Event_Chains(
			trap_id=args.trap_id,
			window_sec=args.window_sec,
		)
		display.print_EventChains(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_EventsExport(args) -> None:
	fmt = getattr(args, "format", None) or "csv"
	try:
		body = client.export_Events(
			fmt=fmt,
			trap_id=args.trap_id,
			event_type=args.type,
			source_ip=args.source_ip,
			min_priority=getattr(args, "min_priority", None),
			since=getattr(args, "since", None),
			until=getattr(args, "until", None),
			limit=args.limit,
		)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
		return
	out = getattr(args, "output", None) or ""
	if out:
		path = Path(out)
		path.write_text(body, encoding="utf-8")
		print(Fore.GREEN + EventsExportSavedText.format(path=str(path), bytes=len(body.encode("utf-8"))) + Style.RESET_ALL)
		return
	print(body)


def cmd_EventsTail(_args) -> None:
	print(Fore.YELLOW + EventsTailHintText + Style.RESET_ALL)
	stream = client.stream_Events()
	try:
		for line in stream.lines():
			if not line:
				continue
			if line.startswith("data:"):
				display.print_SseDataLine(line[5:])
			elif line.startswith(":"):
				continue
			else:
				display.print_SseDataLine(line)
	except KeyboardInterrupt:
		print()
		print(Fore.YELLOW + EventsTailStoppedText + Style.RESET_ALL)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
	finally:
		stream.close()
