from __future__ import annotations

import re
import socket
import urllib.parse

import paramiko
from fastapi import HTTPException, status

from app.config import get_Settings
from app.domains.couriers.schemas import DeployCourierIn, DeployCourierOut
from app.domains.deploy.schemas import DeployAgentIn, DeployAgentOut
from app.texts import (
	MSG_DEPLOY_AUTH,
	MSG_DEPLOY_BAD_CENTER,
	MSG_DEPLOY_CODE_TIMEOUT,
	MSG_DEPLOY_CONNECT,
	MSG_DEPLOY_NEED_HOST,
	MSG_DEPLOY_NEED_PASSWORD,
	MSG_DEPLOY_RUN,
	MSG_DEPLOY_TIMEOUT,
)

_PAIR_CODE_MARK = "Подтверди код у оператора:"
_COURIER_CODE_MARK = "Подтверди код курьера у оператора:"
_CODE_RE = re.compile(r"Подтверди код у оператора:\s*([A-Z0-9]{4,16})")
_COURIER_CODE_RE = re.compile(r"Подтверди код курьера у оператора:\s*([A-Z0-9]{4,16})")
_LOOPBACK = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
# Connect может быть нестабильным с контейнера наружу; команда тянет бинарь ~10MB.
_SSH_CONNECT_TIMEOUT_SEC = 45
_SSH_COMMAND_TIMEOUT_SEC = 600
_SSH_BANNER_TIMEOUT_SEC = 45
_SSH_AUTH_TIMEOUT_SEC = 45


def center_IsLoopback(url: str) -> bool:
	host = (urllib.parse.urlparse(url.strip()).hostname or "").lower()
	return host in _LOOPBACK


def check_CenterUrl(raw: str) -> str:
	url = raw.strip().rstrip("/")
	# host:port без схемы - https (агент/курьер ходят в публичный канал).
	if url and "://" not in url:
		url = "https://" + url
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme not in ("http", "https") or not parsed.hostname:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_BAD_CENTER)
	if any(char in url for char in "\"'`\\\n\r$;|&<> "):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_BAD_CENTER)
	return url


def build_RemoteInstallScript(center_url: str) -> str:
	url = check_CenterUrl(center_url)
	# setsid отвязывает агент от SSH-сессии, иначе он умрёт вместе с каналом.
	# Лог обязательно обнуляем: иначе grep цепляет старый device_code → «неверный device_code».
	return f"""set -eu
if [ "$(id -u)" -eq 0 ]; then
	dest=/var/lib/metricsd
else
	dest="$HOME/.local/share/metricsd"
fi
export API_BASE='{url}'
export HF_INSTALL_DIR="$dest"
export HF_NO_START=1
curl -fsSL --connect-timeout 20 --max-time 300 --retry 3 --retry-delay 2 \\
	-o /tmp/hf-install.sh "$API_BASE/downloads/install.sh"
sh /tmp/hf-install.sh
cd "$dest"
if [ ! -x ./metricsd ]; then
	echo "HF_NO_BINARY"
	ls -la "$dest" || true
	exit 1
fi
# Старый процесс и хвост лога мешают: код из прошлого запуска уже не в БД.
if [ -f daemon.pid ]; then
	old_pid=$(cat daemon.pid 2>/dev/null || true)
	if [ -n "$old_pid" ]; then
		kill -TERM "$old_pid" 2>/dev/null || true
		sleep 1
		kill -KILL "$old_pid" 2>/dev/null || true
	fi
fi
pkill -KILL -x metricsd 2>/dev/null || true
# Свежий pairing на каждый deploy (иначе Has_Token - кода в логе не будет).
rm -f .runtime.json .agent_state.json 2>/dev/null || true
: > daemon.log
if command -v setsid >/dev/null 2>&1; then
	setsid nohup ./metricsd >> daemon.log 2>&1 < /dev/null &
else
	nohup ./metricsd >> daemon.log 2>&1 < /dev/null &
fi
echo $! > daemon.pid
found=""
i=0
while [ "$i" -lt 60 ]; do
	if grep -q "{_PAIR_CODE_MARK}" daemon.log 2>/dev/null; then
		found=$(grep "{_PAIR_CODE_MARK}" daemon.log | tail -n 1)
		break
	fi
	i=$((i + 1))
	sleep 1
done
if [ -z "$found" ]; then
	echo "HF_CODE_TIMEOUT"
	tail -n 40 daemon.log 2>/dev/null || true
	exit 1
fi
printf '%s\\n' "$found"
"""


def resolve_CenterUrl(requested: str | None) -> str:
	settings = get_Settings()
	raw = (requested or "").strip() or settings.PUBLIC_BASE_URL
	return check_CenterUrl(raw)


def _tail(text: str, limit: int = 400) -> str:
	text = text.strip()
	if len(text) <= limit:
		return text
	return text[-limit:]


def _is_Timeout(exc: BaseException) -> bool:
	text = str(exc).lower()
	return (
		isinstance(exc, (TimeoutError, socket.timeout))
		or "timed out" in text
		or "timeout" in text
	)


def _ssh_Connect(host: str, port: int, user: str, password: str) -> paramiko.SSHClient:
	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	try:
		client.connect(
			hostname=host,
			port=port,
			username=user,
			password=password,
			timeout=_SSH_CONNECT_TIMEOUT_SEC,
			banner_timeout=_SSH_BANNER_TIMEOUT_SEC,
			auth_timeout=_SSH_AUTH_TIMEOUT_SEC,
			allow_agent=False,
			look_for_keys=False,
		)
	except paramiko.AuthenticationException:
		client.close()
		raise
	except Exception:
		client.close()
		raise
	transport = client.get_transport()
	if transport is not None:
		transport.set_keepalive(30)
		# Чтение длинного install (скачивание бинаря) не должно рваться на дефолте.
		transport.sock.settimeout(_SSH_COMMAND_TIMEOUT_SEC)
	return client


def _ssh_Exec(client: paramiko.SSHClient, script: str) -> tuple[int, str, str]:
	_stdin, stdout, stderr = client.exec_command(
		script,
		timeout=_SSH_COMMAND_TIMEOUT_SEC,
		get_pty=True,
	)
	channel = stdout.channel
	channel.settimeout(_SSH_COMMAND_TIMEOUT_SEC)
	exit_code = channel.recv_exit_status()
	out = stdout.read().decode("utf-8", errors="replace")
	err = stderr.read().decode("utf-8", errors="replace")
	return exit_code, out, err


def install_AgentOverSsh(body: DeployAgentIn) -> DeployAgentOut:
	host = body.host.strip()
	user = body.user.strip() or "root"
	password = body.password
	port = body.port
	if not host:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_NEED_HOST)
	if not password or "\n" in password or "\r" in password:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_NEED_PASSWORD)

	center_url = resolve_CenterUrl(body.center_url)
	script = build_RemoteInstallScript(center_url)
	settings = get_Settings()

	try:
		client = _ssh_Connect(host, port, user, password)
	except paramiko.AuthenticationException as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_AUTH) from exc
	except Exception as exc:
		detail = MSG_DEPLOY_CONNECT.format(host=host, port=port, detail=str(exc) or "ssh")
		if settings.DEBUG:
			print(f"[DEBUG] deploy connect failed: {type(exc).__name__}: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

	try:
		exit_code, out, err = _ssh_Exec(client, script)
	except Exception as exc:
		if settings.DEBUG:
			print(f"[DEBUG] deploy exec failed: {type(exc).__name__}: {exc}")
		if _is_Timeout(exc):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=MSG_DEPLOY_TIMEOUT.format(detail=str(exc), center=center_url),
			) from exc
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=MSG_DEPLOY_RUN.format(detail=str(exc) or MSG_DEPLOY_CODE_TIMEOUT),
		) from exc
	finally:
		client.close()

	match = _CODE_RE.search(out)
	if exit_code == 0 and match:
		return DeployAgentOut(
			device_code=match.group(1),
			host=host,
			user=user,
			port=port,
			center_url=center_url,
		)

	if "HF_CODE_TIMEOUT" in out:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=MSG_DEPLOY_RUN.format(detail=MSG_DEPLOY_CODE_TIMEOUT),
		)
	combined = _tail(err or out) or MSG_DEPLOY_CODE_TIMEOUT
	raise HTTPException(
		status_code=status.HTTP_400_BAD_REQUEST,
		detail=MSG_DEPLOY_RUN.format(detail=combined),
	)


def build_RemoteCourierInstallScript(center_url: str) -> str:
	"""Как агент-ловушка: хост сам качает install-courier.sh и бинарь с центра."""
	url = check_CenterUrl(center_url)
	return f"""set -eu
if [ "$(id -u)" -eq 0 ]; then
	dest=/var/lib/metricsd-relay
else
	dest="$HOME/.local/share/metricsd-relay"
fi
export API_BASE='{url}'
export HF_INSTALL_DIR="$dest"
export HF_NO_START=1
curl -fsSL --connect-timeout 20 --max-time 300 --retry 3 --retry-delay 2 \\
	-o /tmp/hf-cinst.sh "$API_BASE/downloads/install-courier.sh"
sh /tmp/hf-cinst.sh
cd "$dest"
if [ ! -x ./metricsd-relay ]; then
	echo "HF_NO_BINARY"
	ls -la "$dest" || true
	exit 1
fi
if [ -f daemon.pid ]; then
	old_pid=$(cat daemon.pid 2>/dev/null || true)
	if [ -n "$old_pid" ]; then
		kill -TERM "$old_pid" 2>/dev/null || true
		sleep 1
		kill -KILL "$old_pid" 2>/dev/null || true
	fi
fi
pkill -KILL -x metricsd-relay 2>/dev/null || true
rm -f .runtime.json .courier_state.json 2>/dev/null || true
: > daemon.log
if command -v setsid >/dev/null 2>&1; then
	setsid nohup ./metricsd-relay >> daemon.log 2>&1 < /dev/null &
else
	nohup ./metricsd-relay >> daemon.log 2>&1 < /dev/null &
fi
echo $! > daemon.pid
found=""
i=0
while [ "$i" -lt 90 ]; do
	if grep -q "{_COURIER_CODE_MARK}" daemon.log 2>/dev/null; then
		found=$(grep "{_COURIER_CODE_MARK}" daemon.log | tail -n 1)
		break
	fi
	i=$((i + 1))
	sleep 1
done
if [ -z "$found" ]; then
	echo "HF_CODE_TIMEOUT"
	tail -n 40 daemon.log 2>/dev/null || true
	exit 1
fi
printf '%s\\n' "$found"
"""


def install_CourierOverSsh(body: DeployCourierIn) -> DeployCourierOut:
	host = body.host.strip()
	user = body.user.strip() or "root"
	password = body.password
	port = body.port
	if not host:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_NEED_HOST)
	if not password or "\n" in password or "\r" in password:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_NEED_PASSWORD)

	center_url = resolve_CenterUrl(body.center_url)
	script = build_RemoteCourierInstallScript(center_url)
	settings = get_Settings()

	try:
		client = _ssh_Connect(host, port, user, password)
	except paramiko.AuthenticationException as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_AUTH) from exc
	except Exception as exc:
		detail = MSG_DEPLOY_CONNECT.format(host=host, port=port, detail=str(exc) or "ssh")
		if settings.DEBUG:
			print(f"[DEBUG] courier deploy connect failed: {type(exc).__name__}: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

	try:
		exit_code, out, err = _ssh_Exec(client, script)
	except Exception as exc:
		if settings.DEBUG:
			print(f"[DEBUG] courier deploy exec failed: {type(exc).__name__}: {exc}")
		if _is_Timeout(exc):
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail=MSG_DEPLOY_TIMEOUT.format(detail=str(exc), center=center_url),
			) from exc
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=MSG_DEPLOY_RUN.format(detail=str(exc) or MSG_DEPLOY_CODE_TIMEOUT),
		) from exc
	finally:
		client.close()

	match = _COURIER_CODE_RE.search(out)
	if exit_code == 0 and match:
		return DeployCourierOut(ok=True, device_code=match.group(1), detail="")

	if "HF_CODE_TIMEOUT" in out or "HF_NO_BINARY" in out:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=MSG_DEPLOY_RUN.format(detail=_tail(out or err) or MSG_DEPLOY_CODE_TIMEOUT),
		)
	combined = _tail(err or out) or MSG_DEPLOY_CODE_TIMEOUT
	raise HTTPException(
		status_code=status.HTTP_400_BAD_REQUEST,
		detail=MSG_DEPLOY_RUN.format(detail=combined),
	)
