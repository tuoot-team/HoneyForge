from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


class ApiError(Exception):
	"""Ошибка ответа API или клиента."""

	def __init__(self, message: str, status_code: int | None = None):
		super().__init__(message)
		self.status_code = status_code


def get_BaseUrl() -> str:
	base = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
	return base


def get_Token() -> str | None:
	return os.environ.get("ACCESS_TOKEN")


def save_Token(token: str) -> None:
	os.environ["ACCESS_TOKEN"] = token


def clear_Token() -> None:
	os.environ.pop("ACCESS_TOKEN", None)


def is_Debug() -> bool:
	return os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")


def request_Api(
	method: str,
	path: str,
	*,
	json_body: dict | list | None = None,
	params: dict | None = None,
	auth: bool = True,
	timeout: float = 30.0,
) -> Any:
	url = get_BaseUrl() + path
	headers: dict[str, str] = {"Accept": "application/json"}

	if auth:
		token = get_Token()
		if not token:
			raise ApiError("нет ACCESS_TOKEN - сначала login")
		headers["Authorization"] = f"Bearer {token}"

	if is_Debug():
		print(f"[DEBUG] {method} {url}")

	try:
		response = httpx.request(
			method,
			url,
			headers=headers,
			json=json_body,
			params=params,
			timeout=timeout,
		)
	except httpx.HTTPError as exc:
		raise ApiError(f"сеть: {type(exc).__name__}: {exc}") from exc

	if response.status_code >= 400:
		detail = response.text
		try:
			payload = response.json()
			detail = str(payload.get("detail", payload))
		except Exception:
			pass
		raise ApiError(detail, status_code=response.status_code)

	if response.status_code == 204 or not response.content:
		return None
	return response.json()


def stream_Api(path: str, *, auth: bool = True, timeout: float | None = None):
	url = get_BaseUrl() + path
	headers: dict[str, str] = {"Accept": "text/event-stream"}
	if auth:
		token = get_Token()
		if not token:
			raise ApiError("нет ACCESS_TOKEN - сначала login")
		headers["Authorization"] = f"Bearer {token}"

	with httpx.stream("GET", url, headers=headers, timeout=timeout) as response:
		if response.status_code >= 400:
			raise ApiError(response.read().decode("utf-8", errors="replace"), response.status_code)
		for line in response.iter_lines():
			yield line


# --- auth ---

def post_Login(password: str) -> dict:
	data = request_Api(
		"POST",
		"/api/v1/auth/login",
		json_body={"password": password},
		auth=False,
	)
	token = data.get("access_token")
	if not token:
		raise ApiError("в ответе login нет access_token")
	save_Token(token)
	return data


def post_Logout() -> dict:
	try:
		data = request_Api("POST", "/api/v1/auth/logout")
	finally:
		clear_Token()
	return data or {"ok": True}


def get_Me() -> dict:
	return request_Api("GET", "/api/v1/auth/me")


def get_Health() -> dict:
	# health на корне приложения, не под /api/v1
	return request_Api("GET", "/health", auth=False)


# --- profiles ---

def get_ProfileSchema() -> dict:
	return request_Api("GET", "/api/v1/profiles/schema", auth=False)


def validate_Profile(body: dict) -> dict:
	return request_Api("POST", "/api/v1/profiles/validate", json_body=body, auth=False)


def list_Profiles() -> list:
	return request_Api("GET", "/api/v1/profiles/")


def get_Profile(profile_id: str) -> dict:
	return request_Api("GET", f"/api/v1/profiles/{profile_id}")


def create_Profile(body: dict) -> dict:
	return request_Api("POST", "/api/v1/profiles/", json_body=body)


def update_Profile(profile_id: str, body: dict) -> dict:
	return request_Api("PATCH", f"/api/v1/profiles/{profile_id}", json_body=body)


def delete_Profile(profile_id: str) -> None:
	request_Api("DELETE", f"/api/v1/profiles/{profile_id}")


# --- pairing / traps ---

def confirm_Pairing(device_code: str, trap_name: str = "trap", profile_id: str | None = None) -> dict:
	body: dict[str, Any] = {"device_code": device_code, "trap_name": trap_name}
	if profile_id:
		body["profile_id"] = profile_id
	return request_Api("POST", "/api/v1/pairing/confirm", json_body=body)


def list_Traps() -> list:
	return request_Api("GET", "/api/v1/traps/")


def get_Trap(trap_id: str) -> dict:
	return request_Api("GET", f"/api/v1/traps/{trap_id}")


def bind_TrapProfile(trap_id: str, profile_id: str) -> dict:
	return request_Api(
		"POST",
		f"/api/v1/traps/{trap_id}/bind-profile",
		json_body={"profile_id": profile_id},
	)


# --- events ---

def list_Events(
	*,
	trap_id: str | None = None,
	event_type: str | None = None,
	source_ip: str | None = None,
	limit: int = 50,
	offset: int = 0,
) -> dict:
	params: dict[str, Any] = {"limit": limit, "offset": offset}
	if trap_id:
		params["trap_id"] = trap_id
	if event_type:
		params["event_type"] = event_type
	if source_ip:
		params["source_ip"] = source_ip
	return request_Api("GET", "/api/v1/events/", params=params)


def stream_Events():
	return stream_Api("/api/v1/events/stream")


def print_Json(data: Any) -> None:
	print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
