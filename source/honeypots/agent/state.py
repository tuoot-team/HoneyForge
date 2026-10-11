from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent import texts

STATE_FILE = Path(__file__).resolve().parents[1] / ".fake_agent_state.json"

def now_Iso() -> str:
	return datetime.now(timezone.utc).isoformat()

def has_Token(path: Path = STATE_FILE) -> bool:
	if not path.exists():
		return False
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError):
		return False
	return bool(data.get("agent_token"))

def save_State(trap_id: str, agent_token: str, path: Path = STATE_FILE) -> None:
	payload = {
		"trap_id": trap_id,
		"agent_token": agent_token,
		"saved_at": now_Iso(),
	}
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	print(texts.MSG_TOKEN_SAVED.format(path=path))

def load_Token(path: Path = STATE_FILE) -> str:
	data = json.loads(path.read_text(encoding="utf-8"))
	token = data.get("agent_token")
	if not token:
		raise RuntimeError(texts.MSG_ERR_NO_AGENT_TOKEN.format(path=path))
	print(texts.MSG_TOKEN_LOADED.format(path=path, trap_id=data.get("trap_id", "?")))
	return token
