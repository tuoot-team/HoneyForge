from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

os.environ["USE_SQLITE"] = "true"
os.environ["DEBUG"] = "true"
os.environ["OPERATOR_PASSWORD"] = "change-me"
os.environ["OPERATOR_TOKEN_SECRET"] = "dev-change-me-operator-secret"

db_file = ROOT / "honeyforge_local.db"
if db_file.exists():
	db_file.unlink()


def main() -> int:
	from app.config import get_Settings
	from app.db.session import reset_Engine_ForTests

	get_Settings.cache_clear()
	reset_Engine_ForTests()

	from fastapi.testclient import TestClient

	from app.main import app, ensure_SqliteSchema

	ensure_SqliteSchema()

	def fail(msg: str) -> int:
		print(f"[FAIL] {msg}")
		return 1

	with TestClient(app) as client:
		r = client.post("/api/v1/auth/login", json={"password": "change-me"})
		if r.status_code != 200:
			return fail(f"login {r.status_code} {r.text}")
		token = r.json()["access_token"]
		headers = {"Authorization": f"Bearer {token}"}
		print("[OK] login")

		r = client.post(
			"/api/v1/profiles/",
			headers=headers,
			json={
				"name": "mid-ssh",
				"description": "smoke",
				"interaction_level": "medium",
				"blocks": {
					"services": [{"name": "ssh", "port": 22}],
					"mask": {"jitter_pct": 25, "cover_urls": ["/favicon.ico"]},
				},
			},
		)
		if r.status_code != 201:
			return fail(f"create profile {r.status_code} {r.text}")
		profile_id = r.json()["id"]
		config_hash = r.json()["config_hash"]
		print("[OK] create profile", profile_id, "hash", config_hash)

		r = client.post("/api/v1/pairing/start")
		if r.status_code != 200:
			return fail(f"pairing start {r.status_code} {r.text}")
		pairing_id = r.json()["pairing_id"]
		device_code = r.json()["device_code"]
		print("[OK] pairing start", device_code)

		r = client.post(
			"/api/v1/pairing/confirm",
			headers=headers,
			json={
				"device_code": device_code,
				"trap_name": "trap-1",
				"profile_id": profile_id,
			},
		)
		if r.status_code != 200:
			return fail(f"pairing confirm {r.status_code} {r.text}")
		print("[OK] pairing confirm")

		r = client.post(f"/api/v1/pairing/{pairing_id}/complete")
		if r.status_code != 200:
			return fail(f"pairing complete {r.status_code} {r.text}")
		agent_token = r.json()["agent_token"]
		trap_id = r.json()["trap_id"]
		agent_headers = {"X-Agent-Token": agent_token}
		print("[OK] pairing complete", trap_id)

		r = client.post(
			"/api/v1/agent/heartbeat",
			headers=agent_headers,
			json={"agent_version": "0.1.0", "status_payload": {}},
		)
		if r.status_code != 200:
			return fail(f"heartbeat {r.status_code} {r.text}")
		print("[OK] heartbeat")

		r = client.get("/api/v1/agent/config", headers=agent_headers)
		if r.status_code != 200 or r.json()["profile"]["id"] != profile_id:
			return fail(f"config {r.status_code} {r.text}")
		print("[OK] agent config")

		r = client.post(
			"/v1/metrics",
			headers=agent_headers,
			json={"agent_version": "0.1.0"},
		)
		if r.status_code != 200 or r.json().get("server") != "edge-cache":
			return fail(f"mimicry metrics {r.status_code} {r.text}")
		print("[OK] mimicry /v1/metrics")

		r = client.post(
			"/api/v1/agent/events",
			headers=agent_headers,
			json={
				"events": [
					{
						"event_type": "auth_attempt",
						"source_ip": "203.0.113.10",
						"source_port": 54321,
						"payload": {"username": "root", "password": "admin"},
					}
				]
			},
		)
		if r.status_code != 200 or r.json().get("accepted") != 1:
			return fail(f"events {r.status_code} {r.text}")
		print("[OK] events batch")

		r = client.get("/api/v1/events/", headers=headers)
		if r.status_code != 200 or r.json()["total"] < 1:
			return fail(f"list events {r.status_code} {r.text}")
		print("[OK] list events", r.json()["total"])

		r = client.post(
			f"/api/v1/traps/{trap_id}/bind-profile",
			headers=headers,
			json={"profile_id": profile_id},
		)
		if r.status_code != 200:
			return fail(f"bind {r.status_code} {r.text}")
		r = client.post("/api/v1/agent/commands/claim", headers=agent_headers)
		if r.status_code != 200 or not r.json().get("command"):
			return fail(f"claim {r.status_code} {r.text}")
		print("[OK] claim reload_config", r.json()["command"]["command_type"])

	print("phase1 smoke OK")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
