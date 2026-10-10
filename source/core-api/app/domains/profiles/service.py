from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.domains.profiles.schemas import ProfileBlocks, ProfileCreate, ProfileOut, ProfileUpdate
from app.security import compute_ConfigHash
from app.texts import MSG_PROFILE_NOT_FOUND


def _blocks_ToDict(blocks: ProfileBlocks) -> dict:
	return blocks.model_dump(mode="json")


def _profile_ToOut(row: models.Profile) -> ProfileOut:
	blocks = ProfileBlocks.model_validate(row.blocks or {})
	return ProfileOut(
		id=row.id,
		name=row.name,
		description=row.description,
		interaction_level=row.interaction_level,
		blocks=blocks,
		config_version=row.config_version,
		config_hash=row.config_hash,
		created_at=row.created_at,
		updated_at=row.updated_at,
	)


def list_Profiles(db: Session) -> list[ProfileOut]:
	rows = db.query(models.Profile).order_by(models.Profile.created_at.desc()).all()
	return [_profile_ToOut(row) for row in rows]


def get_Profile(db: Session, profile_id: UUID) -> ProfileOut:
	row = db.get(models.Profile, profile_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PROFILE_NOT_FOUND)
	return _profile_ToOut(row)


def create_Profile(db: Session, body: ProfileCreate) -> ProfileOut:
	blocks_dict = _blocks_ToDict(body.blocks)
	version = 1
	config_hash = compute_ConfigHash(
		json.dumps(blocks_dict, sort_keys=True, ensure_ascii=False),
		body.interaction_level.value,
		version,
	)
	row = models.Profile(
		name=body.name,
		description=body.description,
		interaction_level=body.interaction_level.value,
		blocks=blocks_dict,
		config_version=version,
		config_hash=config_hash,
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return _profile_ToOut(row)


def update_Profile(db: Session, profile_id: UUID, body: ProfileUpdate) -> ProfileOut:
	row = db.get(models.Profile, profile_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PROFILE_NOT_FOUND)

	if body.name is not None:
		row.name = body.name
	if body.description is not None:
		row.description = body.description
	if body.interaction_level is not None:
		row.interaction_level = body.interaction_level.value
	if body.blocks is not None:
		row.blocks = _blocks_ToDict(body.blocks)

	row.config_version = int(row.config_version) + 1
	row.config_hash = compute_ConfigHash(
		json.dumps(row.blocks or {}, sort_keys=True, ensure_ascii=False),
		row.interaction_level,
		row.config_version,
	)
	row.updated_at = datetime.now(timezone.utc)
	db.commit()
	db.refresh(row)
	return _profile_ToOut(row)


def delete_Profile(db: Session, profile_id: UUID) -> None:
	row = db.get(models.Profile, profile_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PROFILE_NOT_FOUND)
	db.delete(row)
	db.commit()
