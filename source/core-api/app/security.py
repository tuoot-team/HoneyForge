from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode


def hash_Secret(raw: str) -> str:
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_Password(password: str, *, iterations: int = 200_000) -> str:
	salt = secrets.token_bytes(16)
	digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
	return (
		f"pbkdf2_sha256${iterations}$"
		f"{urlsafe_b64encode(salt).decode('ascii').rstrip('=')}$"
		f"{urlsafe_b64encode(digest).decode('ascii').rstrip('=')}"
	)


def verify_Password(password: str, encoded: str) -> bool:
	try:
		algo, iterations_raw, salt_b64, digest_b64 = encoded.split("$", 3)
		if algo != "pbkdf2_sha256":
			return False
		iterations = int(iterations_raw)
		salt = urlsafe_b64decode(salt_b64 + "=" * (-len(salt_b64) % 4))
		expected = urlsafe_b64decode(digest_b64 + "=" * (-len(digest_b64) % 4))
		got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
		return hmac.compare_digest(expected, got)
	except Exception:
		return False


def generate_AgentToken() -> str:
	return secrets.token_urlsafe(32)


def generate_DeviceCode() -> str:
	alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	return "".join(secrets.choice(alphabet) for _ in range(6))


def sign_UserToken(secret: str, user_id: uuid.UUID, ttl_sec: int = 86400) -> str:
	expires_at = int(time.time()) + ttl_sec
	uid = str(user_id)
	payload = f"user:{uid}:{expires_at}"
	sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
	return f"{uid}.{expires_at}.{urlsafe_b64encode(sig).decode('ascii').rstrip('=')}"


def verify_UserToken(secret: str, token: str) -> uuid.UUID | None:
	"""Возвращает user_id или None. Старые operator-токены без sub отклоняются."""
	try:
		uid_raw, expires_raw, sig_b64 = token.split(".", 2)
		expires_at = int(expires_raw)
		if expires_at < int(time.time()):
			return None
		user_id = uuid.UUID(uid_raw)
		payload = f"user:{user_id}:{expires_at}"
		expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
		pad = "=" * (-len(sig_b64) % 4)
		got = urlsafe_b64decode(sig_b64 + pad)
		if not hmac.compare_digest(expected, got):
			return None
		return user_id
	except Exception:
		return None


def compute_ConfigHash(blocks_json: str, interaction_level: str, version: int) -> str:
	raw = f"{interaction_level}|{version}|{blocks_json}"
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
