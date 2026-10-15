"""Курьеры, pairing, визиты, приём событий с дедупом."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.deps import CurrentUser
from app.domains.couriers.schemas import (
	CourierConfirmIn,
	CourierConfigOut,
	CourierOut,
	CourierPairingCompleteOut,
	CourierPairingListItem,
	CourierPairingListOut,
	CourierPairingStartOut,
	CourierStatus,
	CourierVisitClaimOut,
	CourierVisitCompleteIn,
	TrapCourierSshIn,
)
from app.domains.events.sse_hub import event_sse_hub
from app.domains.profiles.schemas import CollectionMode, ProfileBlocks
from app.domains.traps import access as trap_access
from app.security import generate_AgentToken, generate_DeviceCode, hash_Secret
from app.texts import (
	MSG_COURIER_NOT_FOUND,
	MSG_COURIER_PAIRING_BAD_CODE,
	MSG_COURIER_PAIRING_EXPIRED,
	MSG_COURIER_PAIRING_NOT_FOUND,
	MSG_COURIER_PAIRING_NOT_READY,
	MSG_COURIER_VISIT_BAD_STATE,
	MSG_COURIER_VISIT_NOT_FOUND,
	MSG_TRAP_NO_COURIER_SSH,
	MSG_TRAP_NOT_FOUND,
)

_DEFAULT_COLLECT_INTERVAL = 300
_WIPE_HINTS = [
	"after successful complete: clear events[], keep next_id",
	"remove /tmp/hf-courier-*",
	"do not touch metricsd binary or .runtime.json",
]


def _as_Utc(dt: datetime) -> datetime:
	if dt.tzinfo is None:
		return dt.replace(tzinfo=timezone.utc)
	return dt


def _courier_ToOut(row: models.Courier) -> CourierOut:
	return CourierOut(
		id=row.id,
		name=row.name,
		status=CourierStatus(row.status if row.status in CourierStatus.__members__ else "pending"),
		owner_user_id=row.owner_user_id,
		last_seen_at=row.last_seen_at,
		meta=row.meta or {},
		created_at=row.created_at,
		updated_at=row.updated_at,
	)


def list_Couriers(db: Session, user: CurrentUser) -> list[CourierOut]:
	query = db.query(models.Courier)
	if not user.is_superadmin and not user.has("traps.all"):
		query = query.filter(models.Courier.owner_user_id == user.id)
	rows = query.order_by(models.Courier.created_at.desc()).all()
	return [_courier_ToOut(row) for row in rows]


def get_Courier(db: Session, user: CurrentUser, courier_id: UUID) -> CourierOut:
	row = db.get(models.Courier, courier_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_COURIER_NOT_FOUND)
	if not user.is_superadmin and not user.has("traps.all"):
		if row.owner_user_id != user.id:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_COURIER_NOT_FOUND)
	return _courier_ToOut(row)


def start_Courier_Pairing(db: Session) -> CourierPairingStartOut:
	settings = get_Settings()
	now = datetime.now(timezone.utc)
	code = generate_DeviceCode()
	row = models.CourierPairingSession(
		device_code=code,
		status="pending",
		expires_at=now + timedelta(minutes=settings.PAIRING_TTL_MINUTES),
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return CourierPairingStartOut(
		pairing_id=row.id,
		device_code=row.device_code,
		expires_at=row.expires_at,
	)


def list_Courier_Pairings(
	db: Session, *, status_filter: str | None = "pending"
) -> CourierPairingListOut:
	now = datetime.now(timezone.utc)
	stale = (
		db.query(models.CourierPairingSession)
		.filter(models.CourierPairingSession.status.in_(("pending", "confirmed")))
		.filter(models.CourierPairingSession.expires_at < now)
		.all()
	)
	for row in stale:
		row.status = "expired"
	if stale:
		db.commit()

	query = db.query(models.CourierPairingSession)
	if status_filter and status_filter != "all":
		query = query.filter(models.CourierPairingSession.status == status_filter)
	rows = query.order_by(models.CourierPairingSession.created_at.desc()).all()
	items = [
		CourierPairingListItem(
			id=row.id,
			device_code=row.device_code,
			status=row.status,
			courier_id=row.courier_id,
			expires_at=row.expires_at,
			created_at=row.created_at,
		)
		for row in rows
	]
	return CourierPairingListOut(total=len(items), items=items)


def confirm_Courier_Pairing(
	db: Session, body: CourierConfirmIn, *, owner_user_id: UUID | None
) -> dict:
	now = datetime.now(timezone.utc)
	row = (
		db.query(models.CourierPairingSession)
		.filter(models.CourierPairingSession.device_code == body.device_code.upper())
		.one_or_none()
	)
	if row is None:
		row = (
			db.query(models.CourierPairingSession)
			.filter(models.CourierPairingSession.device_code == body.device_code)
			.one_or_none()
		)
	if row is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail=MSG_COURIER_PAIRING_BAD_CODE
		)
	if _as_Utc(row.expires_at) < now or row.status == "expired":
		row.status = "expired"
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_410_GONE, detail=MSG_COURIER_PAIRING_EXPIRED
		)
	if row.status != "pending":
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail=f"pairing уже в статусе {row.status}",
		)

	token = generate_AgentToken()
	courier = models.Courier(
		name=body.name,
		status="pending",
		agent_token_hash=hash_Secret(token),
		owner_user_id=owner_user_id,
	)
	db.add(courier)
	db.flush()
	row.courier_id = courier.id
	row.status = "confirmed"
	row.pending_agent_token = token
	db.commit()
	return {
		"ok": True,
		"pairing_id": str(row.id),
		"courier_id": str(courier.id),
		"status": row.status,
	}


def complete_Courier_Pairing(db: Session, pairing_id: UUID) -> CourierPairingCompleteOut:
	now = datetime.now(timezone.utc)
	row = db.get(models.CourierPairingSession, pairing_id)
	if row is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail=MSG_COURIER_PAIRING_NOT_FOUND
		)
	if _as_Utc(row.expires_at) < now:
		row.status = "expired"
		db.commit()
		raise HTTPException(
			status_code=status.HTTP_410_GONE, detail=MSG_COURIER_PAIRING_EXPIRED
		)
	if row.status == "pending":
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT, detail=MSG_COURIER_PAIRING_NOT_READY
		)
	if row.status == "completed":
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="pairing уже завершён")
	if row.status != "confirmed" or not row.courier_id or not row.pending_agent_token:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT, detail=MSG_COURIER_PAIRING_NOT_READY
		)

	token = row.pending_agent_token
	row.status = "completed"
	row.completed_at = now
	row.pending_agent_token = None
	courier = db.get(models.Courier, row.courier_id)
	if courier is not None:
		courier.status = "online"
		courier.last_seen_at = now
	db.commit()
	return CourierPairingCompleteOut(courier_id=row.courier_id, courier_token=token)


def set_Trap_Courier_Ssh(
	db: Session, user: CurrentUser, trap_id: UUID, body: TrapCourierSshIn
) -> dict:
	trap = trap_access.get_Visible_Trap(db, user, trap_id)
	trap.courier_ssh = {
		"host": body.host.strip(),
		"port": body.port,
		"user": body.user.strip(),
		"password": (body.password or "").strip() or None,
		"private_key": (body.private_key or "").strip() or None,
		"remote_data_dir": body.remote_data_dir.strip().rstrip("/") or "/var/lib/metricsd",
	}
	trap.updated_at = datetime.now(timezone.utc)
	db.commit()
	return {"ok": True, "trap_id": str(trap.id), "host": trap.courier_ssh.get("host")}


def courier_Config(db: Session, courier: models.Courier) -> CourierConfigOut:
	now = datetime.now(timezone.utc)
	courier.last_seen_at = now
	courier.status = "online"
	db.commit()
	return CourierConfigOut(courier_id=courier.id, name=courier.name, ok=True)


def claim_Visit(db: Session, courier: models.Courier) -> CourierVisitClaimOut:
	now = datetime.now(timezone.utc)
	courier.last_seen_at = now
	courier.status = "online"

	# Без FOR UPDATE: совместимо с SQLite; гонка редкая при одном курьере.
	visit = (
		db.query(models.CourierVisit)
		.filter(models.CourierVisit.status == "pending")
		.order_by(models.CourierVisit.scheduled_at.asc())
		.first()
	)
	if visit is None:
		db.commit()
		return CourierVisitClaimOut()

	trap = db.get(models.Trap, visit.trap_id)
	if trap is None:
		visit.status = "failed"
		visit.error = MSG_TRAP_NOT_FOUND
		visit.finished_at = now
		db.commit()
		return CourierVisitClaimOut()

	ssh = dict(trap.courier_ssh or {})
	if not ssh.get("host") or not ssh.get("user"):
		visit.status = "failed"
		visit.error = MSG_TRAP_NO_COURIER_SSH
		visit.finished_at = now
		db.commit()
		return CourierVisitClaimOut()

	data_dir = (ssh.get("remote_data_dir") or "/var/lib/metricsd").rstrip("/")
	buffer_path = f"{data_dir}/queue.json"

	# Атомарный claim: второй курьер не заберёт тот же pending.
	updated = (
		db.query(models.CourierVisit)
		.filter(
			models.CourierVisit.id == visit.id,
			models.CourierVisit.status == "pending",
		)
		.update(
			{
				"status": "claimed",
				"courier_id": courier.id,
				"claimed_at": now,
				"payload": {
					"ssh_host": ssh.get("host"),
					"buffer_path": buffer_path,
				},
			},
			synchronize_session=False,
		)
	)
	if not updated:
		db.commit()
		return CourierVisitClaimOut()
	db.commit()

	return CourierVisitClaimOut(
		visit_id=visit.id,
		trap_id=trap.id,
		ssh={
			"host": ssh.get("host"),
			"port": int(ssh.get("port") or 22),
			"user": ssh.get("user"),
			"password": ssh.get("password"),
			"private_key": ssh.get("private_key"),
		},
		buffer_path=buffer_path,
		wipe_hints=list(_WIPE_HINTS),
	)


def _dedupe_Key(trap_id: UUID, agent_buffer_id: int | None) -> str | None:
	if agent_buffer_id is None:
		return None
	return f"{trap_id}:{agent_buffer_id}"


def _event_Already_Saved(db: Session, trap_id: UUID, dedupe: str) -> bool:
	# Ищем по JSON payload._courier_dedupe (достаточно для MVP).
	rows = (
		db.query(models.Event)
		.filter(models.Event.trap_id == trap_id)
		.order_by(models.Event.id.desc())
		.limit(500)
		.all()
	)
	for row in rows:
		payload = row.payload or {}
		if payload.get("_courier_dedupe") == dedupe:
			return True
	return False


def complete_Visit(
	db: Session, courier: models.Courier, visit_id: UUID, body: CourierVisitCompleteIn
) -> dict:
	now = datetime.now(timezone.utc)
	visit = db.get(models.CourierVisit, visit_id)
	if visit is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail=MSG_COURIER_VISIT_NOT_FOUND
		)
	if visit.courier_id != courier.id:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail=MSG_COURIER_VISIT_NOT_FOUND
		)
	if visit.status == "succeeded":
		# Идемпотентный повтор complete.
		return {"ok": True, "accepted": 0, "status": visit.status}
	if visit.status != "claimed":
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT, detail=MSG_COURIER_VISIT_BAD_STATE
		)

	if not body.ok:
		visit.status = "failed"
		visit.error = (body.error or "visit failed")[:2000]
		visit.finished_at = now
		courier.last_seen_at = now
		db.commit()
		return {"ok": False, "accepted": 0, "status": visit.status}

	accepted = 0
	for item in body.events:
		dedupe = _dedupe_Key(visit.trap_id, item.agent_buffer_id)
		if dedupe and _event_Already_Saved(db, visit.trap_id, dedupe):
			continue
		occurred_at = now
		if item.occurred_at:
			try:
				occurred_at = datetime.fromisoformat(item.occurred_at.replace("Z", "+00:00"))
			except ValueError:
				pass
		payload = dict(item.payload or {})
		if dedupe:
			payload["_courier_dedupe"] = dedupe
		if item.agent_buffer_id is not None:
			payload["_agent_buffer_id"] = item.agent_buffer_id
		row = models.Event(
			trap_id=visit.trap_id,
			event_type=item.event_type,
			source_ip=item.source_ip,
			source_port=item.source_port,
			occurred_at=occurred_at,
			payload=payload,
		)
		db.add(row)
		db.flush()
		from app.domains.events.service import event_Priority

		event_sse_hub.publish_Event(
			{
				"id": row.id,
				"trap_id": str(visit.trap_id),
				"event_type": row.event_type,
				"source_ip": row.source_ip,
				"source_port": row.source_port,
				"occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
				"payload": row.payload,
				"priority": event_Priority(row.event_type, row.payload or {}),
			}
		)
		accepted += 1

	visit.status = "succeeded"
	visit.finished_at = now
	visit.error = None
	courier.last_seen_at = now
	courier.status = "online"
	trap = db.get(models.Trap, visit.trap_id)
	if trap is not None:
		trap.last_seen_at = now
		# Не ставим online по визиту курьера - ловушка сама не beacon'ит.
	db.commit()
	return {"ok": True, "accepted": accepted, "status": visit.status}


def _trap_Collect_Interval(db: Session, trap: models.Trap) -> int | None:
	"""None = не courier-режим."""
	if not trap.profile_id:
		return None
	profile = db.get(models.Profile, trap.profile_id)
	if profile is None:
		return None
	try:
		blocks = ProfileBlocks.model_validate(profile.blocks or {})
	except Exception:
		return None
	mask = blocks.mask
	if mask.collection_mode != CollectionMode.courier and not mask.courier.enabled:
		return None
	return mask.courier.collect_interval_sec or _DEFAULT_COLLECT_INTERVAL


def schedule_Courier_Visits(db: Session) -> int:
	"""Создаёт pending-визиты для courier-ловушек по интервалу."""
	now = datetime.now(timezone.utc)
	created = 0
	traps = db.query(models.Trap).filter(models.Trap.profile_id.isnot(None)).all()
	for trap in traps:
		interval = _trap_Collect_Interval(db, trap)
		if interval is None:
			continue
		ssh = trap.courier_ssh or {}
		if not ssh.get("host"):
			continue
		active = (
			db.query(models.CourierVisit)
			.filter(
				models.CourierVisit.trap_id == trap.id,
				models.CourierVisit.status.in_(("pending", "claimed")),
			)
			.count()
		)
		if active > 0:
			continue
		last_done = (
			db.query(models.CourierVisit)
			.filter(
				models.CourierVisit.trap_id == trap.id,
				models.CourierVisit.status.in_(("succeeded", "failed")),
			)
			.order_by(models.CourierVisit.finished_at.desc())
			.first()
		)
		if last_done and last_done.finished_at:
			elapsed = (now - _as_Utc(last_done.finished_at)).total_seconds()
			if elapsed < interval:
				continue
		db.add(
			models.CourierVisit(
				trap_id=trap.id,
				status="pending",
				scheduled_at=now,
				payload={},
			)
		)
		created += 1
	if created:
		db.commit()
	return created
