from __future__ import annotations

import getpass
import os
import re
import shlex
import subprocess
import tempfile
import urllib.parse

import client
from texts import (
	DeployBadCenterText,
	DeployCodeTimeoutText,
	DeployNeedHostText,
	DeployNeedPasswordText,
	DeployNoSshText,
	DeploySshAuthText,
	DeploySshConnectText,
	DeploySshRunText,
	SetupAskSshPasswordText,
	SetupSshCodeText,
	SetupSshConnectingText,
	SetupSshHostKeyText,
	print_OpsLine,
)

_PAIR_CODE_MARK = "Подтверди код у оператора:"
_CODE_RE = re.compile(r"Подтверди код у оператора:\s*([A-Z0-9]{4,16})")
_LOOPBACK = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


class DeployError(Exception):
	pass


def center_IsLoopback(url: str) -> bool:
	host = (urllib.parse.urlparse(url.strip()).hostname or "").lower()
	return host in _LOOPBACK


def check_CenterUrl(raw: str) -> str:
	url = raw.strip().rstrip("/")
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme not in ("http", "https") or not parsed.hostname:
		raise DeployError(DeployBadCenterText)
	if any(char in url for char in "\"'`\\\n\r$;|&<> "):
		raise DeployError(DeployBadCenterText)
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


def _tail(text: str, limit: int = 400) -> str:
	text = text.strip()
	if len(text) <= limit:
		return text
	return text[-limit:]


def _write_Askpass(password: str) -> str:
	handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="hf-askpass-")
	# Пароль только в этом файле, не в argv ssh.
	quoted = shlex.quote(password)
	handle.write(f"#!/bin/sh\nprintf '%s\\n' {quoted}\n")
	handle.close()
	os.chmod(handle.name, 0o700)
	return handle.name


def install_AgentOverSsh(
	*,
	host: str,
	user: str,
	password: str,
	port: int,
	center_url: str,
) -> str:
	host = host.strip()
	user = user.strip()
	if not host:
		raise DeployError(DeployNeedHostText)
	if not password or "\n" in password or "\r" in password:
		raise DeployError(DeployNeedPasswordText)
	if port < 1 or port > 65535:
		raise DeployError(DeploySshConnectText.format(host=host, port=port, detail="порт"))
	script = build_RemoteInstallScript(center_url)
	ssh_bin = "ssh"
	if not any(
		os.path.isfile(os.path.join(path, ssh_bin)) and os.access(os.path.join(path, ssh_bin), os.X_OK)
		for path in os.environ.get("PATH", "").split(os.pathsep)
	):
		raise DeployError(DeployNoSshText)

	print(SetupSshConnectingText.format(user=user, host=host, port=port))
	askpass_path = _write_Askpass(password)
	env = os.environ.copy()
	env["SSH_ASKPASS"] = askpass_path
	env["SSH_ASKPASS_REQUIRE"] = "force"
	command = [
		ssh_bin,
		"-o", "StrictHostKeyChecking=accept-new",
		"-o", "PreferredAuthentications=password",
		"-o", "PubkeyAuthentication=no",
		"-o", "NumberOfPasswordPrompts=1",
		"-o", "ConnectTimeout=20",
		"-p", str(port),
		f"{user}@{host}",
		script,
	]
	try:
		try:
			completed = subprocess.run(
				command,
				env=env,
				capture_output=True,
				timeout=180,
				start_new_session=True,
				check=False,
			)
		except subprocess.TimeoutExpired as exc:
			raise DeployError(DeploySshRunText.format(detail=DeployCodeTimeoutText)) from exc
	finally:
		os.unlink(askpass_path)

	out = completed.stdout.decode("utf-8", errors="replace")
	err = completed.stderr.decode("utf-8", errors="replace")
	for line in err.splitlines():
		if "Permanently added" in line or "permanently added" in line.lower():
			print(SetupSshHostKeyText.format(host=host, fingerprint=line.strip()))
			break
	match = _CODE_RE.search(out)
	if completed.returncode == 0 and match:
		return match.group(1)
	lower_err = err.lower()
	if "permission denied" in lower_err or "authentication failed" in lower_err:
		raise DeployError(DeploySshAuthText)
	if completed.returncode != 0 and not out.strip():
		raise DeployError(
			DeploySshConnectText.format(host=host, port=port, detail=_tail(err) or "ssh")
		)
	detail = DeployCodeTimeoutText if "HF_CODE_TIMEOUT" in out else (_tail(err or out) or DeployCodeTimeoutText)
	raise DeployError(DeploySshRunText.format(detail=detail))


def cmd_Deploy(args) -> None:
	from colorama import Fore, Style

	host = (getattr(args, "host", "") or "").strip()
	if not host:
		host = input("IP хоста ловушки: ").strip()
	user = (getattr(args, "user", "") or "root").strip() or "root"
	port = int(getattr(args, "port", 22) or 22)
	center = (getattr(args, "api_base", "") or "").strip() or client.get_BaseUrl()
	password = getattr(args, "password", "") or ""
	if not password:
		password = getpass.getpass(SetupAskSshPasswordText)
	try:
		code = install_AgentOverSsh(
			host=host,
			user=user,
			password=password,
			port=port,
			center_url=center,
		)
	except DeployError as exc:
		print(Fore.RED + str(exc) + Style.RESET_ALL)
		return
	print(Fore.GREEN + SetupSshCodeText.format(code=code) + Style.RESET_ALL)
	print_OpsLine("дальше", f"pair-confirm {code}")
