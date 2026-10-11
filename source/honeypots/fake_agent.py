from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / "cli" / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / "core-api" / ".env")

TOKEN_FILE = Path(__file__).resolve().parent / ".fake_agent_state.json"
AGENT_VERSION = "0.0.1-fake"
PAIR_WAIT_SEC = 300
PAIR_POLL_SEC = 2.0

TEXT_PAIR_STARTED = "Pairing стартовал. Подтверди код у оператора (CLI: pair-confirm {code})"
TEXT_PAIR_WAIT = "Жду confirm... ({attempt})"
TEXT_PAIR_DONE = "Pairing готов. trap_id={trap_id}"
TEXT_TOKEN_SAVED = "Токен сохранён в {path}"
TEXT_TOKEN_LOADED = "Токен загружен из {path} (trap_id={trap_id})"
TEXT_HEARTBEAT_OK = "Heartbeat ok, config_version={version}"
TEXT_EVENTS_OK = "События приняты: accepted={accepted}"
TEXT_FIRE_DONE = "Отправлено событий: {count} (preset=both)"
TEXT_HTTP_ERR = "HTTP {status}: {body}"
TEXT_PAIR_TIMEOUT = "таймаут ожидания confirm ({wait_sec}s). Код был: {code}"


def is_Debug() -> bool:
	return os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")


def get_BaseUrl() -> str:
	return os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")


def get_TokenFile() -> Path:
	env_path = os.getenv("FAKE_AGENT_STATE")
	if env_path:
		return Path(env_path)
	return TOKEN_FILE


def debug_Log(message: str) -> None:
	if is_Debug():
		print(f"[DEBUG] {message}")


def fail_Exit(message: str, code: int = 1) -> None:
	print(f"[ERR] {message}", file=sys.stderr)
	raise SystemExit(code)


def now_Iso() -> str:
	return datetime.now(timezone.utc).isoformat()


class FakeAgentClient:
	"""HTTP-клиент под контракт агента core-api."""

	def __init__(self, base_url: str, agent_token: str | None = None):
		self.base_url = base_url.rstrip("/")
		self.agent_token = agent_token
		self._client = httpx.Client(timeout=30.0)

	def close(self) -> None:
		self._client.close()

	def _headers(self, *, agent: bool = False) -> dict[str, str]:
		headers = {"Accept": "application/json"}
		if agent:
			if not self.agent_token:
				fail_Exit("нет agent_token")
			headers["X-Agent-Token"] = self.agent_token
		return headers

	def request_Json(
		self,
		method: str,
		path: str,
		*,
		json_body: dict | None = None,
		agent: bool = False,
		ok_statuses: tuple[int, ...] = (200, 201),
	) -> Any:
		url = self.base_url + path
		debug_Log(f"{method} {url}")
		response = self._client.request(
			method,
			url,
			json=json_body,
			headers=self._headers(agent=agent),
		)
		if response.status_code not in ok_statuses:
			fail_Exit(TEXT_HTTP_ERR.format(status=response.status_code, body=response.text[:500]))
		if not response.content:
			return None
		return response.json()

	def start_Pairing(self) -> dict:
		return self.request_Json("POST", "/api/v1/pairing/start")

	def try_Complete_Pairing(self, pairing_id: str) -> dict | None:
		"""Поллинг: 409 = ещё не confirm / уже завершён."""
		url = self.base_url + f"/api/v1/pairing/{pairing_id}/complete"
		response = self._client.post(url, headers=self._headers())
		if response.status_code == 200:
			return response.json()
		if response.status_code == 409:
			return None
		fail_Exit(TEXT_HTTP_ERR.format(status=response.status_code, body=response.text[:500]))
		return None

	def post_Heartbeat(self) -> dict:
		body = {"agent_version": AGENT_VERSION, "status_payload": {"fake": True}}
		return self.request_Json("POST", "/api/v1/agent/heartbeat", json_body=body, agent=True)

	def post_Events(self, events: list[dict]) -> dict:
		return self.request_Json(
			"POST",
			"/api/v1/agent/events",
			json_body={"events": events},
			agent=True,
		)


def has_AgentToken(path: Path) -> bool:
	if not path.exists():
		return False
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError):
		return False
	return bool(data.get("agent_token"))


def save_AgentState(path: Path, trap_id: str, agent_token: str) -> None:
	payload = {
		"trap_id": trap_id,
		"agent_token": agent_token,
		"saved_at": now_Iso(),
	}
	path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	print(TEXT_TOKEN_SAVED.format(path=path))


def load_AgentToken(path: Path) -> str:
	data = json.loads(path.read_text(encoding="utf-8"))
	token = data.get("agent_token")
	if not token:
		fail_Exit("в state-файле нет agent_token")
	print(TEXT_TOKEN_LOADED.format(path=path, trap_id=data.get("trap_id", "?")))
	return token


def build_BothEvents() -> list[dict]:
	"""Low + Mid события одной пачкой."""
	low_ip = f"203.0.113.{random.randint(1, 250)}"
	low_port = random.choice([22, 80, 443, 3306, 8080])
	mid_ip = f"198.51.100.{random.randint(1, 250)}"
	user = random.choice(["root", "admin", "ubuntu", "postgres"])
	password = random.choice(["admin", "123456", "password", "toor"])
	return [
		{
			"event_type": "port_connect",
			"source_ip": low_ip,
			"source_port": random.randint(1024, 65535),
			"occurred_at": now_Iso(),
			"payload": {"port": low_port, "service": "listen"},
		},
		{
			"event_type": "banner_grab",
			"source_ip": low_ip,
			"source_port": random.randint(1024, 65535),
			"occurred_at": now_Iso(),
			"payload": {"port": low_port, "banner": "SSH-2.0-OpenSSH_fake"},
		},
		{
			"event_type": "auth_attempt",
			"source_ip": mid_ip,
			"source_port": random.randint(1024, 65535),
			"occurred_at": now_Iso(),
			"payload": {
				"username": user,
				"password": password,
				"service": "ssh",
				"success": False,
			},
		},
		{
			"event_type": "http_request",
			"source_ip": mid_ip,
			"source_port": random.randint(1024, 65535),
			"occurred_at": now_Iso(),
			"payload": {
				"method": "GET",
				"path": random.choice(["/admin", "/wp-login.php", "/.env"]),
				"user_agent": "Mozilla/5.0 (fake-scanner)",
			},
		},
	]


def run_Pair(client: FakeAgentClient, state_path: Path) -> None:
	"""start → poll complete → сохранить токен."""
	started = client.start_Pairing()
	pairing_id = str(started["pairing_id"])
	device_code = started["device_code"]
	print(TEXT_PAIR_STARTED.format(code=device_code))
	debug_Log(f"pairing_id={pairing_id} expires_at={started.get('expires_at')}")

	deadline = time.time() + PAIR_WAIT_SEC
	attempt = 0
	while time.time() < deadline:
		attempt += 1
		result = client.try_Complete_Pairing(pairing_id)
		if result is not None:
			trap_id = str(result["trap_id"])
			agent_token = result["agent_token"]
			print(TEXT_PAIR_DONE.format(trap_id=trap_id))
			save_AgentState(state_path, trap_id, agent_token)
			return
		print(TEXT_PAIR_WAIT.format(attempt=attempt), end="\r")
		time.sleep(PAIR_POLL_SEC)

	fail_Exit(TEXT_PAIR_TIMEOUT.format(wait_sec=PAIR_WAIT_SEC, code=device_code))


def run_Both(client: FakeAgentClient) -> None:
	"""Heartbeat + события low и mid."""
	hb = client.post_Heartbeat()
	print(TEXT_HEARTBEAT_OK.format(version=hb.get("config_version")))

	events = build_BothEvents()
	data = client.post_Events(events)
	print(TEXT_EVENTS_OK.format(accepted=data.get("accepted", len(events))))
	print(TEXT_FIRE_DONE.format(count=len(events)))
	if is_Debug():
		print(json.dumps(events, ensure_ascii=False, indent=2))


def main() -> None:
	state_path = get_TokenFile()
	client = FakeAgentClient(get_BaseUrl())
	try:
		print(f"API: {get_BaseUrl()}")
		if has_AgentToken(state_path):
			client.agent_token = load_AgentToken(state_path)
			run_Both(client)
		else:
			run_Pair(client, state_path)
	finally:
		client.close()


if __name__ == "__main__":
	main()
