from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.deps import CurrentUser
from app.domains.traps import access as trap_access
from app.domains.traps.schemas import TrapBindProfile, TrapOut, TrapSetOwner, TrapStatus
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
	ssh = trap.courier_ssh or {}
	host = str(ssh.get("host") or "").strip() or None
	return TrapOut(
		id=trap.id,
		name=trap.name,
		profile_id=trap.profile_id,
		owner_user_id=trap.owner_user_id,
		status=TrapStatus(status_value),
		last_seen_at=trap.last_seen_at,
		meta=trap.meta or {},
		has_courier_ssh=bool(host),
		courier_ssh_host=host,
		created_at=trap.created_at,
		updated_at=trap.updated_at,
	)


def list_Traps(db: Session, user: CurrentUser) -> list[TrapOut]:
	query = db.query(models.Trap)
	if not trap_access.can_See_All_Traps(user):
		query = query.filter(models.Trap.owner_user_id == user.id)
	rows = query.order_by(models.Trap.created_at.desc()).all()
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


def get_Trap(db: Session, user: CurrentUser, trap_id: UUID) -> TrapOut:
	row = trap_access.get_Visible_Trap(db, user, trap_id)
	new_status = _refresh_Status(row)
	if row.status != new_status and row.agent_token_hash:
		row.status = new_status
		db.commit()
		db.refresh(row)
	return _trap_ToOut(row)


def bind_TrapProfile(
	db: Session, user: CurrentUser, trap_id: UUID, body: TrapBindProfile
) -> TrapOut:
	trap = trap_access.get_Visible_Trap(db, user, trap_id)
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


def set_Trap_Owner(
	db: Session, user: CurrentUser, trap_id: UUID, body: TrapSetOwner
) -> TrapOut:
	trap = db.get(models.Trap, trap_id)
	if trap is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
	# Назначение: нужны traps.write (на роутере) + all/owner/superadmin.
	# Чужой/бесхозный trap без traps.all не показываем как 404.
	if not trap_access.can_See_All_Traps(user) and not trap_access.trap_Visible(user, trap):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
	trap_access.require_Assign_Owner(user, trap)
	trap_access.require_User_Exists(db, body.user_id)
	trap.owner_user_id = body.user_id
	trap.updated_at = datetime.now(timezone.utc)
	db.commit()
	db.refresh(trap)
	return _trap_ToOut(trap)
