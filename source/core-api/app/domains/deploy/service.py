from __future__ import annotations

import re
import urllib.parse

import paramiko
from fastapi import HTTPException, status

from app.config import get_Settings
from app.domains.deploy.schemas import DeployAgentIn, DeployAgentOut
from app.texts import (
	MSG_DEPLOY_AUTH,
	MSG_DEPLOY_BAD_CENTER,
	MSG_DEPLOY_CODE_TIMEOUT,
	MSG_DEPLOY_CONNECT,
	MSG_DEPLOY_NEED_HOST,
	MSG_DEPLOY_NEED_PASSWORD,
	MSG_DEPLOY_RUN,
)

_PAIR_CODE_MARK = "Подтверди код у оператора:"
_CODE_RE = re.compile(r"Подтверди код у оператора:\s*([A-Z0-9]{4,16})")
_LOOPBACK = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
_SSH_CONNECT_TIMEOUT_SEC = 20
_SSH_COMMAND_TIMEOUT_SEC = 180


def center_IsLoopback(url: str) -> bool:
	host = (urllib.parse.urlparse(url.strip()).hostname or "").lower()
	return host in _LOOPBACK


def check_CenterUrl(raw: str) -> str:
	url = raw.strip().rstrip("/")
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme not in ("http", "https") or not parsed.hostname:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_BAD_CENTER)
	if any(char in url for char in "\"'`\\\n\r$;|&<> "):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_BAD_CENTER)
	return url


def build_RemoteInstallScript(center_url: str) -> str:
	url = check_CenterUrl(center_url)
	# setsid отвязывает агент от SSH-сессии, иначе он умрёт вместе с каналом.
	return f"""set -eu
if [ "$(id -u)" -eq 0 ]; then
	dest=/opt/honeyforge
else
	dest="$HOME/.honeyforge"
fi
export API_BASE='{url}'
export HF_INSTALL_DIR="$dest"
export HF_NO_START=1
curl -fsSL "$API_BASE/downloads/install.sh" | sh
cd "$dest"
if command -v setsid >/dev/null 2>&1; then
	setsid nohup ./agent >> agent.log 2>&1 < /dev/null &
else
	nohup ./agent >> agent.log 2>&1 < /dev/null &
fi
echo $! > agent.pid
found=""
i=0
while [ "$i" -lt 40 ]; do
	if grep -q "{_PAIR_CODE_MARK}" agent.log 2>/dev/null; then
		found=$(grep "{_PAIR_CODE_MARK}" agent.log | tail -n 1)
		break
	fi
	i=$((i + 1))
	sleep 1
done
if [ -z "$found" ]; then
	echo "HF_CODE_TIMEOUT"
	exit 1
fi
printf '%s\\n' "$found"
"""


def resolve_CenterUrl(requested: str | None) -> str:
	settings = get_Settings()
	raw = (requested or "").strip() or settings.PUBLIC_BASE_URL
	return check_CenterUrl(raw)


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

	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	try:
		client.connect(
			hostname=host,
			port=port,
			username=user,
			password=password,
			timeout=_SSH_CONNECT_TIMEOUT_SEC,
			banner_timeout=_SSH_CONNECT_TIMEOUT_SEC,
			auth_timeout=_SSH_CONNECT_TIMEOUT_SEC,
			allow_agent=False,
			look_for_keys=False,
		)
	except paramiko.AuthenticationException as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MSG_DEPLOY_AUTH) from exc
	except Exception as exc:
		detail = MSG_DEPLOY_CONNECT.format(host=host, port=port, detail=str(exc) or "ssh")
		if settings.DEBUG:
			print(f"[DEBUG] deploy connect failed: {type(exc).__name__}: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

	try:
		_stdin, stdout, stderr = client.exec_command(
			script,
			timeout=_SSH_COMMAND_TIMEOUT_SEC,
			get_pty=True,
		)
		exit_code = stdout.channel.recv_exit_status()
		out = stdout.read().decode("utf-8", errors="replace")
		err = stderr.read().decode("utf-8", errors="replace")
	except Exception as exc:
		if settings.DEBUG:
			print(f"[DEBUG] deploy exec failed: {type(exc).__name__}: {exc}")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=MSG_DEPLOY_RUN.format(detail=MSG_DEPLOY_CODE_TIMEOUT),
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


def _tail(text: str, limit: int = 400) -> str:
	text = text.strip()
	if len(text) <= limit:
		return text
	return text[-limit:]
