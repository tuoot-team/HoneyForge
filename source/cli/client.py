from __future__ import annotations

import os
import queue
import threading
from collections.abc import Iterator
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


class ApiError(Exception):

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


def is_CatMode() -> bool:
	return os.getenv("CAT_MODE", "false").lower() in ("1", "true", "yes")


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


def request_Api_Text(
	method: str,
	path: str,
	*,
	params: dict | None = None,
	auth: bool = True,
	timeout: float = 60.0,
	accept: str = "*/*",
) -> str:
	"""Сырой текст ответа (CSV / STIX), не JSON."""
	url = get_BaseUrl() + path
	headers: dict[str, str] = {"Accept": accept}
	if auth:
		token = get_Token()
		if not token:
			raise ApiError("нет ACCESS_TOKEN - сначала login")
		headers["Authorization"] = f"Bearer {token}"
	if is_Debug():
		print(f"[DEBUG] {method} {url}")
	try:
		response = httpx.request(method, url, headers=headers, params=params, timeout=timeout)
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
	return response.text


class SseStream:

	def __init__(self, path: str, *, auth: bool = True):
		self.path = path
		self.auth = auth
		self._queue: queue.Queue[Any] = queue.Queue()
		self._stop = threading.Event()
		self._client: httpx.Client | None = None
		self._response: httpx.Response | None = None
		self._thread: threading.Thread | None = None

	def start(self) -> None:
		self._thread = threading.Thread(target=self._run_Reader, name="sse-tail", daemon=True)
		self._thread.start()

	def lines(self) -> Iterator[str]:
		while not self._stop.is_set():
			try:
				item = self._queue.get(timeout=0.25)
			except queue.Empty:
				continue
			if item is None:
				return
			if isinstance(item, ApiError):
				raise item
			if isinstance(item, Exception):
				raise ApiError(f"SSE: {type(item).__name__}: {item}") from item
			yield item

	def close(self) -> None:
		self._stop.set()
		response = self._response
		client = self._client
		try:
			if response is not None:
				response.close()
		except Exception:
			pass
		try:
			if client is not None:
				client.close()
		except Exception:
			pass
		if self._thread is not None and self._thread.is_alive():
			self._thread.join(timeout=2.0)

	def _run_Reader(self) -> None:
		url = get_BaseUrl() + self.path
		headers: dict[str, str] = {"Accept": "text/event-stream"}
		if self.auth:
			token = get_Token()
			if not token:
				self._queue.put(ApiError("нет ACCESS_TOKEN - сначала login"))
				self._queue.put(None)
				return
			headers["Authorization"] = f"Bearer {token}"

		try:
			timeout = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)
			self._client = httpx.Client(timeout=timeout)
			with self._client.stream("GET", url, headers=headers) as response:
				self._response = response
				if response.status_code >= 400:
					body = response.read().decode("utf-8", errors="replace")
					self._queue.put(ApiError(body, response.status_code))
					return
				for line in response.iter_lines():
					if self._stop.is_set():
						break
					self._queue.put(line)
		except httpx.HTTPError as exc:
			if not self._stop.is_set():
				self._queue.put(ApiError(f"сеть: {type(exc).__name__}: {exc}"))
		except Exception as exc:
			if not self._stop.is_set():
				self._queue.put(exc)
		finally:
			self._queue.put(None)


def stream_Api(path: str, *, auth: bool = True) -> SseStream:
	stream = SseStream(path, auth=auth)
	stream.start()
	return stream


def post_Login(username: str, password: str) -> dict:
	data = request_Api(
		"POST",
		"/api/v1/auth/login",
		json_body={"username": username, "password": password},
		auth=False,
	)
	token = data.get("access_token")
	if not token:
		raise ApiError("в ответе login нет access_token")
	save_Token(token)
	return data


def list_Users() -> list:
	return request_Api("GET", "/api/v1/users/") or []


def create_User(username: str, password: str, role_id: str, *, is_superadmin: bool = False) -> dict:
	return request_Api(
		"POST",
		"/api/v1/users/",
		json_body={
			"username": username,
			"password": password,
			"role_id": role_id,
			"is_superadmin": is_superadmin,
		},
	)


def update_User(user_id: str, **fields) -> dict:
	body = {key: value for key, value in fields.items() if value is not None}
	return request_Api("PATCH", f"/api/v1/users/{user_id}", json_body=body)


def list_Roles() -> list:
	return request_Api("GET", "/api/v1/roles/") or []


def list_Role_Permissions() -> dict:
	return request_Api("GET", "/api/v1/roles/permissions")


def create_Role(name: str, permissions: list[str]) -> dict:
	return request_Api(
		"POST",
		"/api/v1/roles/",
		json_body={"name": name, "permissions": permissions},
	)


def update_Role(role_id: str, *, name: str | None = None, permissions: list[str] | None = None) -> dict:
	body: dict = {}
	if name is not None:
		body["name"] = name
	if permissions is not None:
		body["permissions"] = permissions
	return request_Api("PATCH", f"/api/v1/roles/{role_id}", json_body=body)


def delete_Role(role_id: str) -> None:
	request_Api("DELETE", f"/api/v1/roles/{role_id}")


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


def list_Pairings(status: str = "pending") -> dict:
	params = {"status": status}
	return request_Api("GET", "/api/v1/pairing/", params=params)


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


def set_Trap_Owner(trap_id: str, user_id: str) -> dict:
	return request_Api(
		"PATCH",
		f"/api/v1/traps/{trap_id}/owner",
		json_body={"user_id": user_id},
	)


def set_Trap_Courier_Ssh(
	trap_id: str,
	*,
	host: str,
	user: str = "root",
	password: str | None = None,
	private_key: str | None = None,
	port: int = 22,
	remote_data_dir: str = "/var/lib/metricsd",
) -> dict:
	body: dict[str, Any] = {
		"host": host,
		"user": user,
		"port": port,
		"remote_data_dir": remote_data_dir,
	}
	if password:
		body["password"] = password
	if private_key:
		body["private_key"] = private_key
	return request_Api("PATCH", f"/api/v1/traps/{trap_id}/courier-ssh", json_body=body)


def list_Couriers() -> list:
	return request_Api("GET", "/api/v1/couriers/") or []


def get_Courier(courier_id: str) -> dict:
	return request_Api("GET", f"/api/v1/couriers/{courier_id}")


def list_Courier_Pairings(status: str = "pending") -> dict:
	return request_Api("GET", "/api/v1/courier-pairing/", params={"status": status})


def confirm_Courier_Pairing(device_code: str, name: str = "courier") -> dict:
	return request_Api(
		"POST",
		"/api/v1/courier-pairing/confirm",
		json_body={"device_code": device_code, "name": name},
	)


def deploy_Courier(
	*,
	host: str,
	user: str = "root",
	password: str,
	port: int = 22,
	center_url: str | None = None,
) -> dict:
	body: dict[str, Any] = {
		"host": host,
		"user": user,
		"password": password,
		"port": port,
	}
	if center_url:
		body["center_url"] = center_url
	return request_Api("POST", "/api/v1/deploy/courier", json_body=body)


def list_Events(
	*,
	trap_id: str | None = None,
	event_type: str | None = None,
	source_ip: str | None = None,
	min_priority: str | None = None,
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
	if min_priority:
		params["min_priority"] = min_priority
	return request_Api("GET", "/api/v1/events/", params=params)


def list_Event_Chains(*, trap_id: str | None = None, window_sec: int = 3600) -> dict:
	params: dict[str, Any] = {"window_sec": window_sec}
	if trap_id:
		params["trap_id"] = trap_id
	return request_Api("GET", "/api/v1/events/chains", params=params)


def export_Events(
	*,
	fmt: str = "csv",
	trap_id: str | None = None,
	event_type: str | None = None,
	source_ip: str | None = None,
	min_priority: str | None = None,
	since: str | None = None,
	until: str | None = None,
	limit: int = 5000,
) -> str:
	params: dict[str, Any] = {"format": fmt, "limit": limit}
	if trap_id:
		params["trap_id"] = trap_id
	if event_type:
		params["event_type"] = event_type
	if source_ip:
		params["source_ip"] = source_ip
	if min_priority:
		params["min_priority"] = min_priority
	if since:
		params["since"] = since
	if until:
		params["until"] = until
	accept = "application/stix+json" if fmt == "stix" else "text/csv"
	return request_Api_Text("GET", "/api/v1/events/export", params=params, accept=accept)


def stream_Events() -> SseStream:
	return stream_Api("/api/v1/events/stream")


def clear_Logs() -> dict:
	return request_Api("POST", "/api/v1/maintenance/clear-logs")


def reset_Database() -> dict:
	return request_Api("POST", "/api/v1/maintenance/reset")


def deploy_Agent(
	*,
	host: str,
	user: str,
	password: str,
	port: int = 22,
	center_url: str | None = None,
	timeout: float = 200.0,
) -> dict:
	body: dict[str, Any] = {
		"host": host,
		"user": user,
		"password": password,
		"port": port,
	}
	if center_url:
		body["center_url"] = center_url
	return request_Api("POST", "/api/v1/deploy/agent", json_body=body, timeout=timeout)


def list_FsPacks() -> dict:
	return request_Api("GET", "/api/v1/fs-packs/")


def list_PersonalityPacks() -> dict:
	return request_Api("GET", "/api/v1/personality-packs/")


def upload_FsPack(path: str, name: str | None = None, *, timeout: float = 120.0) -> dict:
	url = get_BaseUrl() + "/api/v1/fs-packs/"
	headers: dict[str, str] = {"Accept": "application/json"}
	token = get_Token()
	if not token:
		raise ApiError("нет ACCESS_TOKEN - сначала login")
	headers["Authorization"] = f"Bearer {token}"
	if is_Debug():
		print(f"[DEBUG] POST {url}")
	data: dict[str, str] = {}
	if name:
		data["name"] = name
	try:
		with open(path, "rb") as handle:
			files = {"file": (os.path.basename(path), handle)}
			response = httpx.post(
				url,
				headers=headers,
				data=data or None,
				files=files,
				timeout=timeout,
			)
	except OSError as exc:
		raise ApiError(f"файл: {exc}") from exc
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
	return response.json()


def delete_FsPack(token: str) -> None:
	request_Api("DELETE", f"/api/v1/fs-packs/{token}")


def list_VmImages() -> dict:
	return request_Api("GET", "/api/v1/vm-images/")


def upload_VmImage(path: str, name: str | None = None, *, timeout: float = 3600.0) -> dict:
	url = get_BaseUrl() + "/api/v1/vm-images/"
	headers: dict[str, str] = {"Accept": "application/json"}
	token = get_Token()
	if not token:
		raise ApiError("нет ACCESS_TOKEN - сначала login")
	headers["Authorization"] = f"Bearer {token}"
	if is_Debug():
		print(f"[DEBUG] POST {url}")
	data: dict[str, str] = {}
	if name:
		data["name"] = name
	try:
		with open(path, "rb") as handle:
			files = {"file": (os.path.basename(path), handle)}
			response = httpx.post(
				url,
				headers=headers,
				data=data or None,
				files=files,
				timeout=timeout,
			)
	except OSError as exc:
		raise ApiError(f"файл: {exc}") from exc
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
	return response.json()


def delete_VmImage(token: str) -> None:
	request_Api("DELETE", f"/api/v1/vm-images/{token}")


def trap_Vm_Action(trap_id: str, action: str) -> dict:
	return request_Api("POST", f"/api/v1/traps/{trap_id}/vm/{action}")
