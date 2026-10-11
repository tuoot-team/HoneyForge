from __future__ import annotations

import asyncio
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

from agent import state, texts
from agent.buffer import EventBuffer
from agent.client import AgentClient
from low.tcp_banner import start_TcpBanner
from mid.fake_ssh import is_SshBanner, start_FakeSsh

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
load_dotenv(HERE.parents[1] / "cli" / ".env")
load_dotenv(HERE.parents[1] / "core-api" / ".env")

AGENT_VERSION = "0.1.0"
HEARTBEAT_INTERVAL_DEFAULT = 30
JITTER_PCT_DEFAULT = 30

def is_Debug() -> bool:
	return os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

def get_BaseUrl() -> str:
	return os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")

def get_BannerForService(profile: dict, service_name: str) -> str:
	blocks = profile.get("blocks", {})
	for b in blocks.get("banners", []):
		if b.get("service") == service_name:
			return b.get("text", "")
	return ""

def get_MaskValue(profile: dict, key: str, default):
	blocks = profile.get("blocks", {})
	mask = blocks.get("mask", {})
	return mask.get(key, default)

class Agent:

	def __init__(self, base_url: str, debug: bool = False):
		self.base_url = base_url
		self.debug = debug
		self.client = AgentClient(base_url, debug=debug)
		self.buffer = EventBuffer(debug=debug)
		self.profile: dict = {}
		self.state_file = state.STATE_FILE
		self._stop: asyncio.Event | None = None

	def debug_Log(self, message: str) -> None:
		if self.debug:
			print(f"[DEBUG] {message}")

	def on_Event(self, event: dict) -> None:
		self.buffer.add(event)

	async def ensure_Token(self) -> None:
		if not state.has_Token(self.state_file):
			raise RuntimeError(texts.MSG_ERR_NO_TOKEN)
		token = state.load_Token(self.state_file)
		self.client.agent_token = token

	async def load_Config(self) -> None:
		raw = self.client.get_Config()
		if self.debug:
			self.debug_Log(f"конфиг: {raw}")
		self.profile = raw.get("profile") or {}

	async def heartbeat_Loop(self) -> None:
		interval = int(get_MaskValue(
			self.profile, "beacon_interval_sec", HEARTBEAT_INTERVAL_DEFAULT,
		))
		jitter = int(get_MaskValue(
			self.profile, "jitter_pct", JITTER_PCT_DEFAULT,
		))
		while not self._stop.is_set():
			try:
				result = self.client.post_Heartbeat(
					agent_version=AGENT_VERSION,
					status_payload={"pid": os.getpid()},
				)
				print(texts.MSG_HEARTBEAT_OK.format(
					version=result.get("config_version", "?")
				))
			except Exception as e:
				print(f"[WARN] heartbeat: {e}")
			delta = int(interval * jitter / 100)
			sleep_for = interval + random.randint(-delta, delta)
			sleep_for = max(5, sleep_for)
			try:
				await asyncio.wait_for(self._stop.wait(), timeout=sleep_for)
			except asyncio.TimeoutError:
				pass

	async def events_Loop(self) -> None:
		while not self._stop.is_set():
			try:
				pending = self.buffer.pending(limit=200)
				if pending:
					ids = [row[0] for row in pending]
					events = [row[1] for row in pending]
					result = self.client.post_Events(events)
					self.buffer.mark_Sent(ids)
					print(texts.MSG_EVENTS_ACCEPTED.format(
						accepted=result.get("accepted", len(events))
					))
			except Exception as e:
				print(f"[WARN] events: {e} (события остаются в буфере)")
			try:
				await asyncio.wait_for(self._stop.wait(), timeout=10)
			except asyncio.TimeoutError:
				pass

	async def run_Honeypots(self) -> None:
		blocks = self.profile.get("blocks", {})
		services = blocks.get("services", [])
		logging_block = blocks.get("logging") or {}
		mask = blocks.get("mask") or {}
		delay_min_ms = int(logging_block.get("auth_delay_ms_min") or 0)
		delay_max_ms = int(logging_block.get("auth_delay_ms_max") or 0)
		seed = str(mask.get("decoy_content_seed") or "")
		tasks = []
		for svc in services:
			if not svc.get("enabled", True):
				continue
			port = svc.get("port")
			name = svc.get("name", "tcp_banner")
			if not port:
				continue
			banner = get_BannerForService(self.profile, name) or "SSH-2.0-OpenSSH_8.2p1\r\n"
			if not banner.endswith("\n"):
				banner = banner + "\r\n"
			print(texts.MSG_AGENT_SERVICE_START.format(name=name, port=port))
			if is_SshBanner(banner) or "ssh" in name.lower():
				runner = start_FakeSsh(
					port=port,
					banner=banner,
					on_event=self.on_Event,
					service_name=name,
					delay_min_ms=delay_min_ms,
					delay_max_ms=delay_max_ms,
					seed=seed,
					debug=self.debug,
				)
			else:
				runner = start_TcpBanner(
					port=port,
					banner=banner,
					on_event=self.on_Event,
					service_name=name,
					debug=self.debug,
				)
			tasks.append(asyncio.create_task(runner))
		if not tasks:
			print(texts.MSG_AGENT_NO_SERVICES)
			return
		await asyncio.gather(*tasks)

	async def run(self) -> None:
		self._stop = asyncio.Event()
		print(texts.MSG_AGENT_STARTED.format(version=AGENT_VERSION))
		await self.ensure_Token()
		await self.load_Config()
		profile_name = self.profile.get("name", "?")
		profile_level = self.profile.get("interaction_level", "?")
		print(texts.MSG_AGENT_CONFIG_OK.format(name=profile_name, level=profile_level))

		hb_task = asyncio.create_task(self.heartbeat_Loop())
		ev_task = asyncio.create_task(self.events_Loop())

		try:
			await self.run_Honeypots()
		except asyncio.CancelledError:
			pass
		finally:
			self._stop.set()
			for t in (hb_task, ev_task):
				t.cancel()
			self.client.close()
			self.buffer.close()
			print(texts.MSG_AGENT_STOPPED)

	def stop(self) -> None:
		if self._stop is not None:
			self._stop.set()

def ensure_Utf8_Stdio() -> None:
	for stream in (sys.stdout, sys.stderr):
		reconfigure = getattr(stream, "reconfigure", None)
		if reconfigure is None:
			continue
		try:
			reconfigure(encoding="utf-8", errors="replace")
		except (OSError, ValueError):
			pass

def main() -> None:
	ensure_Utf8_Stdio()
	base_url = get_BaseUrl()
	debug = is_Debug()

	agent = Agent(base_url, debug=debug)

	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	try:
		loop.run_until_complete(agent.run())
	except KeyboardInterrupt:
		print()
		agent.stop()
	finally:
		try:
			loop.run_until_complete(asyncio.sleep(0))
		except Exception:
			pass
		loop.close()

if __name__ == "__main__":
	main()
