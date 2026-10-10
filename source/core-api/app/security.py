from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode


def hash_Secret(raw: str) -> str:
	"""SHA-256 hex для хранения agent_token / registration_token."""
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_AgentToken() -> str:
	return secrets.token_urlsafe(32)


def generate_DeviceCode() -> str:
	alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	return "".join(secrets.choice(alphabet) for _ in range(6))


def sign_OperatorToken(secret: str, ttl_sec: int = 86400) -> str:
	"""Простой HMAC-токен: exp.ts.sig (без внешних JWT-зависимостей)."""
	expires_at = int(time.time()) + ttl_sec
	payload = f"operator:{expires_at}"
	sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
	return f"{expires_at}.{urlsafe_b64encode(sig).decode('ascii').rstrip('=')}"


def verify_OperatorToken(secret: str, token: str) -> bool:
	try:
		expires_raw, sig_b64 = token.split(".", 1)
		expires_at = int(expires_raw)
		if expires_at < int(time.time()):
			return False
		payload = f"operator:{expires_at}"
		expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
		pad = "=" * (-len(sig_b64) % 4)
		got = urlsafe_b64decode(sig_b64 + pad)
		return hmac.compare_digest(expected, got)
	except Exception:
		return False


def compute_ConfigHash(blocks_json: str, interaction_level: str, version: int) -> str:
	raw = f"{interaction_level}|{version}|{blocks_json}"
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
