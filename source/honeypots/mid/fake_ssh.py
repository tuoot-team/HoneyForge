from __future__ import annotations

import asyncio
import hashlib
import random
from pathlib import Path
from typing import Any, Callable

from agent import texts
from agent.state import now_Iso

EventHandler = Callable[[dict], None]

HOST_KEY_FILE = Path(__file__).resolve().parents[1] / ".ssh_host_key"

def is_SshBanner(banner: str) -> bool:
	return banner.lstrip().upper().startswith("SSH-")

def parse_ServerVersion(banner: str) -> str:
	line = ""
	for raw in banner.splitlines():
		if raw.strip():
			line = raw.strip()
			break
	if line.upper().startswith("SSH-2.0-"):
		line = line[8:]
	line = line.split(" ")[0].strip()
	return line or "OpenSSH_8.2p1"

def build_Hostname(seed: str) -> str:
	cleaned = (seed or "").strip()
	if not cleaned:
		return "web-01"
	digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:6]
	return "srv-" + digest

def pick_AuthDelay_Sec(delay_min_ms: int, delay_max_ms: int) -> float:
	low = max(0, int(delay_min_ms))
	high = max(0, int(delay_max_ms))
	if high < low:
		low, high = high, low
	if high <= 0:
		return 0.0
	return random.randint(low, high) / 1000.0

def peer_Addr(conn: Any) -> tuple:
	peer = None
	getter = getattr(conn, "get_extra_info", None)
	if getter is not None:
		peer = getter("peername")
	if not peer:
		return None, None
	source_ip = peer[0]
	source_port = peer[1] if len(peer) > 1 else None
	return source_ip, source_port

def normalize_Path(cwd: str, raw: str) -> str:
	if raw.startswith("/"):
		path = raw
	else:
		base = cwd if cwd != "/" else ""
		path = base + "/" + raw
	parts = []
	for part in path.split("/"):
		if part in ("", "."):
			continue
		if part == "..":
			if parts:
				parts.pop()
			continue
		parts.append(part)
	if not parts:
		return "/"
	return "/" + "/".join(parts)

def build_Tree(username: str, hostname: str) -> dict:
	if username == "root":
		home = "/root"
	else:
		home = "/home/" + username
	return {
		"/etc/hostname": hostname + "\n",
		"/etc/issue": texts.MSG_SHELL_ISSUE.format(host=hostname),
		home + "/readme.txt": texts.MSG_SHELL_README,
	}

def list_Names(tree: dict, path: str) -> list:
	prefix = "" if path == "/" else path
	names = []
	seen = set()
	for full in tree:
		if path == "/":
			rest = full[1:]
		elif full == path:
			continue
		elif full.startswith(prefix + "/"):
			rest = full[len(prefix) + 1:]
		else:
			continue
		name = rest.split("/")[0]
		if name and name not in seen:
			seen.add(name)
			names.append(name)
	names.sort()
	return names

def is_Dir(tree: dict, path: str) -> bool:
	if path == "/":
		return True
	prefix = path + "/"
	for full in tree:
		if full.startswith(prefix):
			return True
	return False

class FakeShell:

	def __init__(self, username: str, hostname: str, source_ip, source_port, port: int, on_event: EventHandler):
		self.username = username or "user"
		self.hostname = hostname
		self.source_ip = source_ip
		self.source_port = source_port
		self.port = port
		self.on_event = on_event
		if self.username == "root":
			self.cwd = "/root"
			self.prompt_suffix = "#"
		else:
			self.cwd = "/home/" + self.username
			self.prompt_suffix = "$"
		self.tree = build_Tree(self.username, hostname)

	def prompt(self) -> str:
		return texts.MSG_SHELL_PROMPT.format(
			user=self.username,
			host=self.hostname,
			cwd=self.cwd,
			suffix=self.prompt_suffix,
		)

	def emit_Command(self, command: str) -> None:
		self.on_event({
			"event_type": "shell_command",
			"source_ip": self.source_ip,
			"source_port": self.source_port,
			"occurred_at": now_Iso(),
			"payload": {
				"port": self.port,
				"username": self.username,
				"cwd": self.cwd,
				"command": command[:200],
			},
		})

	def run_Line(self, line: str) -> tuple:
		stripped = line.strip()
		if not stripped:
			return "", False
		self.emit_Command(stripped)
		parts = stripped.split()
		cmd = parts[0]
		args = [item for item in parts[1:] if not item.startswith("-")]
		if cmd in ("exit", "logout", "quit"):
			return texts.MSG_SHELL_LOGOUT, True
		if cmd == "help":
			return texts.MSG_SHELL_HELP, False
		if cmd == "whoami":
			return self.username + "\n", False
		if cmd == "hostname":
			return self.hostname + "\n", False
		if cmd == "pwd":
			return self.cwd + "\n", False
		if cmd == "id":
			return texts.MSG_SHELL_ID.format(user=self.username), False
		if cmd == "uname":
			return texts.MSG_SHELL_UNAME.format(host=self.hostname), False
		if cmd == "echo":
			return " ".join(parts[1:]) + "\n", False
		if cmd == "ls":
			return self.cmd_Ls(args), False
		if cmd == "cd":
			return self.cmd_Cd(args), False
		if cmd == "cat":
			return self.cmd_Cat(args), False
		return texts.MSG_SHELL_NOT_FOUND.format(cmd=cmd), False

	def cmd_Ls(self, args: list) -> str:
		path = self.cwd if not args else normalize_Path(self.cwd, args[0])
		if path in self.tree and not is_Dir(self.tree, path):
			return path.rsplit("/", 1)[-1] + "\n"
		if path != "/" and path not in self.tree and not is_Dir(self.tree, path):
			return texts.MSG_SHELL_NO_FILE.format(path=path).replace("cat:", "ls:", 1)
		names = list_Names(self.tree, path)
		if not names:
			return ""
		return "  ".join(names) + "\n"

	def cmd_Cd(self, args: list) -> str:
		raw = args[0] if args else ("/root" if self.username == "root" else "/home/" + self.username)
		path = normalize_Path(self.cwd, raw)
		if path in self.tree and not is_Dir(self.tree, path):
			return texts.MSG_SHELL_NOT_DIR.format(path=path)
		if path != "/" and not is_Dir(self.tree, path) and path not in (
			"/root",
			"/home",
			"/home/" + self.username,
			"/etc",
		):
			return texts.MSG_SHELL_NO_FILE.format(path=path).replace("cat:", "cd:", 1)
		self.cwd = path
		return ""

	def cmd_Cat(self, args: list) -> str:
		if not args:
			return texts.MSG_SHELL_CAT_USAGE
		path = normalize_Path(self.cwd, args[0])
		body = self.tree.get(path)
		if body is None:
			return texts.MSG_SHELL_NO_FILE.format(path=path)
		return body

def load_HostKey(asyncssh: Any):
	if HOST_KEY_FILE.exists():
		return str(HOST_KEY_FILE)
	key = asyncssh.generate_private_key("ssh-rsa")
	try:
		key.write_private_key(str(HOST_KEY_FILE))
	except OSError:
		return key
	return str(HOST_KEY_FILE)

async def start_FakeSsh(
	port: int,
	banner: str,
	on_event: EventHandler,
	service_name: str = "ssh",
	delay_min_ms: int = 0,
	delay_max_ms: int = 0,
	seed: str = "",
	debug: bool = False,
) -> None:

	try:
		import asyncssh
	except ImportError:
		print(texts.MSG_ERR_NO_ASYNCSSH)
		raise

	hostname = build_Hostname(seed)
	server_version = parse_ServerVersion(banner)
	host_key = load_HostKey(asyncssh)

	class HoneyServer(asyncssh.SSHServer):
		def connection_made(self, conn: Any) -> None:
			source_ip, source_port = peer_Addr(conn)
			self._source_ip = source_ip
			self._source_port = source_port
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
				"payload": {"port": port, "service": service_name},
			})
			on_event({
				"event_type": "banner_grab",
				"source_ip": source_ip,
				"source_port": source_port,
				"occurred_at": now_Iso(),
				"payload": {"port": port, "banner": banner.strip()},
			})

		def password_auth_supported(self) -> bool:
			return True

		def public_key_auth_supported(self) -> bool:
			return False

		async def validate_password(self, username: str, password: str) -> bool:
			await asyncio.sleep(pick_AuthDelay_Sec(delay_min_ms, delay_max_ms))
			source_ip = getattr(self, "_source_ip", None)
			source_port = getattr(self, "_source_port", None)
			if debug:
				print(texts.MSG_FAKE_SSH_AUTH.format(user=username, ip=source_ip))
			on_event({
				"event_type": "auth_attempt",
				"source_ip": source_ip,
				"source_port": source_port,
				"occurred_at": now_Iso(),
				"payload": {
					"username": username,
					"password": password,
					"service": service_name,
					"success": True,
				},
			})
			return True

	async def handle_Client(process: Any) -> None:
		source_ip, source_port = peer_Addr(process)
		username = process.get_extra_info("username") or "user"
		shell = FakeShell(
			username, hostname, source_ip, source_port, port, on_event,
		)
		process.stdout.write(texts.MSG_SHELL_WELCOME.format(host=hostname, ip=source_ip or "?"))
		try:
			while True:
				process.stdout.write(shell.prompt())
				line = await process.stdin.readline()
				if not line:
					break
				output, must_exit = shell.run_Line(line)
				if output:
					process.stdout.write(output)
				if must_exit:
					break
		except asyncssh.BreakReceived:
			pass
		process.exit(0)

	if debug:
		print(texts.MSG_FAKE_SSH_STARTED.format(port=port, host=hostname))

	acceptor = await asyncssh.create_server(
		HoneyServer,
		"",
		port,
		server_host_keys=[host_key],
		server_version=server_version,
		process_factory=handle_Client,
		encoding="utf-8",
	)
	try:
		await asyncio.Future()
	except asyncio.CancelledError:
		acceptor.close()
		wait_closed = getattr(acceptor, "wait_closed", None)
		if wait_closed is not None:
			await wait_closed()
		raise
