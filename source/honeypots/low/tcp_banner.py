from __future__ import annotations

import asyncio
from typing import Callable

from agent import texts
from agent.state import now_Iso

EventHandler = Callable[[dict], None]

async def _handle_Connection(
	reader: asyncio.StreamReader,
	writer: asyncio.StreamWriter,
	port: int,
	banner: str,
	service_name: str,
	on_event: EventHandler,
	debug: bool,
) -> None:

	peer = writer.get_extra_info("peername")
	source_ip = peer[0] if peer else None
	source_port = peer[1] if peer else None

	if debug:
		print(texts.MSG_LOW_CONNECT.format(
			source_ip=source_ip,
			source_port=source_port,
			port=port,
		))

	on_event({
		"event_type": "port_connect",
		"source_ip": source_ip,
		"source_port": source_port,
		"occurred_at": now_Iso(),
		"payload": {
			"port": port,
			"service": service_name,
		},
	})

	try:
		writer.write(banner.encode("utf-8", errors="ignore"))
		await writer.drain()
		on_event({
			"event_type": "banner_grab",
			"source_ip": source_ip,
			"source_port": source_port,
			"occurred_at": now_Iso(),
			"payload": {
				"port": port,
				"banner": banner,
			},
		})
		if debug:
			print(texts.MSG_LOW_BANNER_SENT.format(banner=banner))
	except Exception:
		pass
	finally:
		writer.close()
		try:
			await writer.wait_closed()
		except Exception:
			pass

async def start_TcpBanner(
	port: int,
	banner: str,
	on_event: EventHandler,
	service_name: str = "tcp_banner",
	debug: bool = False,
) -> None:

	if debug:
		print(texts.MSG_LOW_STARTED.format(port=port, banner=banner))

	server = await asyncio.start_server(
		lambda r, w: _handle_Connection(
			r, w, port=port, banner=banner,
			service_name=service_name, on_event=on_event, debug=debug,
		),
		"0.0.0.0",
		port,
	)

	async with server:
		await server.serve_forever()
