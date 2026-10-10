from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))


def main() -> int:
	import os

	os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
	os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")

	from fastapi.testclient import TestClient

	from app.config import get_Settings
	from app.main import app

	get_Settings.cache_clear()
	client = TestClient(app)

	checks: list[tuple[str, bool, str]] = []

	health = client.get("/health")
	ok_health = health.status_code == 200 and health.json().get("status") == "ok"
	checks.append(("GET /health", ok_health, health.text[:120]))

	schema = client.get("/api/v1/profiles/schema")
	ok_schema = schema.status_code == 200 and "interaction_levels" in schema.json()
	checks.append(("GET /api/v1/profiles/schema", ok_schema, schema.text[:120]))

	validate = client.post(
		"/api/v1/profiles/validate",
		json={
			"name": "smoke",
			"interaction_level": "low",
			"blocks": {},
		},
	)
	ok_validate = validate.status_code == 200 and validate.json().get("valid") is True
	checks.append(("POST /api/v1/profiles/validate", ok_validate, validate.text[:120]))

	stub = client.get("/api/v1/profiles/")
	ok_stub = stub.status_code == 501
	checks.append(("GET /api/v1/profiles/ -> 501", ok_stub, stub.text[:120]))

	openapi = client.get("/openapi.json")
	paths = openapi.json().get("paths", {}) if openapi.status_code == 200 else {}
	need = [
		"/health",
		"/api/v1/profiles/schema",
		"/api/v1/pairing/start",
		"/api/v1/agent/heartbeat",
		"/api/v1/events/",
	]
	missing = [p for p in need if p not in paths]
	ok_openapi = openapi.status_code == 200 and not missing
	checks.append(
		(
			"OpenAPI paths",
			ok_openapi,
			"ok" if ok_openapi else f"missing={missing}",
		)
	)

	print("HoneyForge core-api smoke (без Docker)")
	failed = 0
	for name, ok, detail in checks:
		mark = "OK" if ok else "FAIL"
		print(f"  [{mark}] {name}")
		if not ok:
			print(f"         {detail}")
			failed += 1

	db_status = health.json().get("database", "?") if health.status_code == 200 else "?"
	redis_status = health.json().get("redis", "?") if health.status_code == 200 else "?"
	print(f"  [info] database: {db_status}")
	print(f"  [info] redis: {redis_status}")
	if "unreachable" in str(db_status):
		print("  [info] Postgres нет - для CRUD/миграций поставьте PG или Docker позже")

	return 1 if failed else 0


if __name__ == "__main__":
	raise SystemExit(main())
