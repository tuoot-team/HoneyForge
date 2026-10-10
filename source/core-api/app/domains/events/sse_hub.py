from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any


class EventSseHub:
	def __init__(self) -> None:
		self._subscribers: list[asyncio.Queue[str]] = []

	def publish_Event(self, payload: dict[str, Any]) -> None:
		message = json.dumps(payload, default=str, ensure_ascii=False)
		dead: list[asyncio.Queue[str]] = []
		for queue in self._subscribers:
			try:
				queue.put_nowait(message)
			except asyncio.QueueFull:
				dead.append(queue)
		for queue in dead:
			if queue in self._subscribers:
				self._subscribers.remove(queue)

	async def subscribe(self, *, ping_interval_sec: float = 15.0) -> AsyncIterator[str | None]:
		queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
		self._subscribers.append(queue)
		try:
			while True:
				try:
					item = await asyncio.wait_for(queue.get(), timeout=ping_interval_sec)
					yield item
				except asyncio.TimeoutError:
					yield None
		finally:
			if queue in self._subscribers:
				self._subscribers.remove(queue)


event_sse_hub = EventSseHub()
