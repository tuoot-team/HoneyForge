from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.domains.traps.schemas import TrapBindProfile, TrapOut, TrapStatus
from app.texts import MSG_PROFILE_NOT_FOUND, MSG_TRAP_NOT_FOUND


def _refresh_Status(trap: models.Trap) -> str:
	settings = get_Settings()
	if trap.last_seen_at is None:
		return trap.status if trap.status == "pending" else "offline"
	last = trap.last_seen_at
	if last.tzinfo is None:
		last = last.replace(tzinfo=timezone.utc)
	stale_after = timedelta(minutes=settings.AGENT_STALE_MINUTES)
	if datetime.now(timezone.utc) - last > stale_after:
		return "offline"
	return "online"


def _trap_ToOut(trap: models.Trap) -> TrapOut:
	status_value = _refresh_Status(trap)
	return TrapOut(
		id=trap.id,
		name=trap.name,
		profile_id=trap.profile_id,
		status=TrapStatus(status_value),
		last_seen_at=trap.last_seen_at,
		meta=trap.meta or {},
		created_at=trap.created_at,
		updated_at=trap.updated_at,
	)


def list_Traps(db: Session) -> list[TrapOut]:
	rows = db.query(models.Trap).order_by(models.Trap.created_at.desc()).all()
	changed = False
	out: list[TrapOut] = []
	for row in rows:
		new_status = _refresh_Status(row)
		if row.status != new_status and row.agent_token_hash:
			row.status = new_status
			changed = True
		out.append(_trap_ToOut(row))
	if changed:
		db.commit()
	return out


def get_Trap(db: Session, trap_id: UUID) -> TrapOut:
	row = db.get(models.Trap, trap_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
	new_status = _refresh_Status(row)
	if row.status != new_status and row.agent_token_hash:
		row.status = new_status
		db.commit()
		db.refresh(row)
	return _trap_ToOut(row)


def bind_TrapProfile(db: Session, trap_id: UUID, body: TrapBindProfile) -> TrapOut:
	trap = db.get(models.Trap, trap_id)
	if trap is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
	profile = db.get(models.Profile, body.profile_id)
	if profile is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PROFILE_NOT_FOUND)
	trap.profile_id = body.profile_id
	trap.updated_at = datetime.now(timezone.utc)
	db.add(
		models.TrapCommand(
			trap_id=trap.id,
			command_type="reload_config",
			payload={"profile_id": str(body.profile_id)},
			status="pending",
		)
	)
	db.commit()
	db.refresh(trap)
	return _trap_ToOut(trap)
