from colorama import Fore, Style

import client
from texts import EventsTailHintText, MsgApiError


def cmd_EventsList(args) -> None:
	try:
		data = client.list_Events(
			trap_id=args.trap_id,
			event_type=args.type,
			source_ip=args.source_ip,
			limit=args.limit,
		)
		client.print_Json(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_EventsTail(_args) -> None:
	print(Fore.YELLOW + EventsTailHintText + Style.RESET_ALL)
	try:
		for line in client.stream_Events():
			if not line:
				continue
			# SSE: data: {...}
			if line.startswith("data:"):
				print(line[5:].strip())
			elif line.startswith(":"):
				continue
			else:
				print(line)
	except KeyboardInterrupt:
		print()
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)
