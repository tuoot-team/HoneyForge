from colorama import Fore, Style

import client
import display
from texts import EventsTailHintText, EventsTailStoppedText, MsgApiError


def cmd_EventsList(args) -> None:
	try:
		data = client.list_Events(
			trap_id=args.trap_id,
			event_type=args.type,
			source_ip=args.source_ip,
			limit=args.limit,
		)
		display.print_EventList(data)
	except client.ApiError as exc:
		print(Fore.RED + MsgApiError.format(detail=str(exc)) + Style.RESET_ALL)


def cmd_EventsTail(_args) -> None:
	print(Fore.YELLOW + EventsTailHintText + Style.RESET_ALL)
	stream = client.stream_Events()
	try:
		for line in stream.lines():
			if not line:
				continue
			# SSE: data: {...} ; комментарии (: ping) глушим
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