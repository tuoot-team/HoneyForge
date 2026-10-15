from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.config import get_Settings
from app.domains.personality_packs.schemas import PersonalityPackListOut, PersonalityPackOut
from app.domains.profiles.schemas import (
	HttpServiceBlock,
	MaskBlock,
	MysqlServiceBlock,
	PostgresServiceBlock,
	ProfileBlocks,
	RedisServiceBlock,
	SshServiceBlock,
	TcpBannerServiceBlock,
)
from app.texts import MSG_PERSONALITY_PACK_NOT_FOUND


def _packs_Dir() -> Path:
	return Path(get_Settings().PERSONALITY_PACKS_DIR)


def list_PersonalityPacks() -> PersonalityPackListOut:
	root = _packs_Dir()
	items: list[PersonalityPackOut] = []
	if not root.is_dir():
		return PersonalityPackListOut(items=[], total=0)
	for path in sorted(root.glob("*.json")):
		try:
			raw = json.loads(path.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError):
			continue
		if not isinstance(raw, dict):
			continue
		key = str(raw.get("key") or path.stem).strip()
		if not key:
			continue
		items.append(
			PersonalityPackOut(
				key=key,
				title=str(raw.get("title") or key),
			)
		)
	return PersonalityPackListOut(items=items, total=len(items))


def load_PersonalityPack(key: str) -> dict[str, Any]:
	key = (key or "").strip()
	if not key:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=MSG_PERSONALITY_PACK_NOT_FOUND.format(key=key or "?"),
		)
	root = _packs_Dir()
	path = root / f"{key}.json"
	if not path.is_file():
		# ключ может отличаться от имени файла
		for candidate in root.glob("*.json"):
			try:
				raw = json.loads(candidate.read_text(encoding="utf-8"))
			except (OSError, json.JSONDecodeError):
				continue
			if isinstance(raw, dict) and str(raw.get("key") or "").strip() == key:
				return raw
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=MSG_PERSONALITY_PACK_NOT_FOUND.format(key=key),
		)
	try:
		raw = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError) as exc:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=MSG_PERSONALITY_PACK_NOT_FOUND.format(key=key),
		) from exc
	if not isinstance(raw, dict):
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=MSG_PERSONALITY_PACK_NOT_FOUND.format(key=key),
		)
	return raw


# Схема профиля подставляет эти дефолты - для pack считаем их «пустыми».
_SCHEMA_DEFAULT_SSH_BANNER = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"
_SCHEMA_DEFAULT_HTTP_SERVER = "Microsoft-IIS/10.0"
_SCHEMA_DEFAULT_HTTP_TITLE = "IIS Windows Server"


def _is_Unset(current: str, *schema_defaults: str) -> bool:
	text = str(current or "").strip()
	if not text:
		return True
	return text in schema_defaults


def _merge_Mask(mask: MaskBlock, pack_mask: dict[str, Any]) -> MaskBlock:
	data = mask.model_dump(mode="json")
	if pack_mask.get("decoy_content_seed") and not str(data.get("decoy_content_seed") or "").strip():
		data["decoy_content_seed"] = pack_mask["decoy_content_seed"]
	mim = pack_mask.get("mimicry") or {}
	if isinstance(mim, dict):
		cur = data.get("mimicry") or {}
		if mim.get("user_agent") and not str(cur.get("user_agent") or "").strip():
			cur["user_agent"] = mim["user_agent"]
		if mim.get("tls_fingerprint_profile") and not str(cur.get("tls_fingerprint_profile") or "").strip():
			cur["tls_fingerprint_profile"] = mim["tls_fingerprint_profile"]
		if "enabled" in mim and cur.get("enabled") is None:
			cur["enabled"] = mim["enabled"]
		data["mimicry"] = cur
	proc = pack_mask.get("process_mask") or {}
	if isinstance(proc, dict):
		cur = data.get("process_mask") or {}
		if proc.get("name") and not str(cur.get("name") or "").strip():
			cur["name"] = proc["name"]
		if "enabled" in proc and cur.get("enabled") is None:
			cur["enabled"] = proc["enabled"]
		data["process_mask"] = cur
	return MaskBlock.model_validate(data)


def _merge_Service(service: Any, defaults: dict[str, Any]) -> Any:
	stype = getattr(service, "type", None)
	if stype == "ssh" and isinstance(service, SshServiceBlock):
		banner = defaults.get("banner_version") or ""
		if banner and _is_Unset(service.modules.banner.version, _SCHEMA_DEFAULT_SSH_BANNER):
			service.modules.banner.version = str(banner)
		return service
	if stype == "http" and isinstance(service, HttpServiceBlock):
		pers = service.modules.personality
		if defaults.get("server") and _is_Unset(pers.server, _SCHEMA_DEFAULT_HTTP_SERVER):
			pers.server = str(defaults["server"])
		if defaults.get("title") and _is_Unset(pers.title, _SCHEMA_DEFAULT_HTTP_TITLE):
			pers.title = str(defaults["title"])
		headers = defaults.get("headers")
		if isinstance(headers, dict) and headers and not pers.headers:
			pers.headers = {str(k): str(v) for k, v in headers.items()}
		return service
	if stype == "tcp_banner" and isinstance(service, TcpBannerServiceBlock):
		banner = defaults.get("banner") or defaults.get("banner_version") or ""
		if banner and _is_Unset(service.modules.banner):
			service.modules.banner = str(banner)
		return service
	if stype in ("postgres", "redis", "mysql") and isinstance(
		service, (PostgresServiceBlock, RedisServiceBlock, MysqlServiceBlock)
	):
		banner = defaults.get("banner_version") or ""
		if banner and _is_Unset(service.modules.banner.version):
			service.modules.banner.version = str(banner)
		return service
	return service


def apply_PersonalityPack(blocks: ProfileBlocks) -> ProfileBlocks:
	"""Дозаполняет пустые поля из pack по mask.service_personality."""
	key = (blocks.mask.service_personality or "").strip()
	if not key:
		return blocks
	pack = load_PersonalityPack(key)
	mask_patch = pack.get("mask") if isinstance(pack.get("mask"), dict) else {}
	new_mask = _merge_Mask(blocks.mask, mask_patch)
	new_mask.service_personality = key
	defaults_root = pack.get("service_defaults") if isinstance(pack.get("service_defaults"), dict) else {}
	merged_services = []
	for service in blocks.services:
		stype = getattr(service, "type", "")
		svc_defaults = defaults_root.get(stype) if isinstance(defaults_root.get(stype), dict) else {}
		# model_copy + merge через dump/validate чтобы не мутировать исходник неожиданно
		data = service.model_dump(mode="json")
		cloned = type(service).model_validate(data)
		merged_services.append(_merge_Service(cloned, svc_defaults))
	return blocks.model_copy(update={"mask": new_mask, "services": merged_services})


def assert_PersonalityPackExists(blocks: ProfileBlocks) -> None:
	key = (blocks.mask.service_personality or "").strip()
	if key:
		load_PersonalityPack(key)
