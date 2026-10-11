from __future__ import annotations

from typing import Any

import httpx

from agent import texts

AGENT_HEADER = "X-Agent-Token"

PATH_PAIRING_START = "/api/v1/pairing/start"
PATH_PAIRING_COMPLETE = "/api/v1/pairing/{pairing_id}/complete"
PATH_AGENT_CONFIG = "/api/v1/agent/config"
PATH_AGENT_HEARTBEAT = "/api/v1/agent/heartbeat"
PATH_AGENT_EVENTS = "/api/v1/agent/events"
PATH_AGENT_COMMANDS_CLAIM = "/api/v1/agent/commands/claim"

class AgentClient:

	def __init__(self, base_url: str, agent_token: str | None = None, debug: bool = False):
		self.base_url = base_url.rstrip("/")
		self.agent_token = agent_token
		self.debug = debug
		self._client = httpx.Client(
			timeout=30.0,
			trust_env=False,
		)

	def close(self) -> None:
		self._client.close()

	def debug_Log(self, message: str) -> None:
		if self.debug:
			print(f"[DEBUG] {message}")

	def _headers(self, *, agent: bool = False) -> dict[str, str]:
		headers = {"Accept": "application/json"}
		if agent:
			if not self.agent_token:
				raise RuntimeError(texts.MSG_ERR_NO_TOKEN_CLIENT)
			headers[AGENT_HEADER] = self.agent_token
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
		self.debug_Log(texts.MSG_DEBUG_REQUEST.format(method=method, url=url))
		response = self._client.request(
			method,
			url,
			json=json_body,
			headers=self._headers(agent=agent),
		)
		if response.status_code not in ok_statuses:
			raise RuntimeError(texts.MSG_ERR_HTTP.format(
				status=response.status_code,
				body=response.text[:500],
			))
		if not response.content:
			return None
		return response.json()

	def start_Pairing(self) -> dict:
		return self.request_Json("POST", PATH_PAIRING_START)

	def try_Complete_Pairing(self, pairing_id: str) -> dict | None:
		url = self.base_url + PATH_PAIRING_COMPLETE.format(pairing_id=pairing_id)
		self.debug_Log(texts.MSG_DEBUG_REQUEST.format(method="POST", url=url))
		response = self._client.post(url, headers=self._headers())
		if response.status_code == 200:
			return response.json()
		if response.status_code == 409:
			return None
		raise RuntimeError(texts.MSG_ERR_HTTP.format(
			status=response.status_code,
			body=response.text[:500],
		))

	def get_Config(self) -> dict:
		return self.request_Json("GET", PATH_AGENT_CONFIG, agent=True)

	def post_Heartbeat(self, agent_version: str, status_payload: dict | None = None) -> dict:
		body = {
			"agent_version": agent_version,
			"status_payload": status_payload or {},
		}
		return self.request_Json("POST", PATH_AGENT_HEARTBEAT, json_body=body, agent=True)

	def post_Events(self, events: list[dict]) -> dict:
		return self.request_Json(
			"POST",
			PATH_AGENT_EVENTS,
			json_body={"events": events},
			agent=True,
		)

	def claim_Commands(self) -> dict:
		return self.request_Json("POST", PATH_AGENT_COMMANDS_CLAIM, agent=True)
