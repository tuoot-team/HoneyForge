from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_Settings
from app.db import models
from app.domains.pairing.schemas import (
	PairingCompleteOut,
	PairingConfirmIn,
	PairingStartOut,
	PairingStatus,
)
from app.security import generate_AgentToken, generate_DeviceCode, hash_Secret
from app.texts import (
	MSG_PAIRING_BAD_CODE,
	MSG_PAIRING_EXPIRED,
	MSG_PAIRING_NOT_FOUND,
	MSG_PAIRING_NOT_READY,
	MSG_PROFILE_NOT_FOUND,
)


def start_Pairing(db: Session) -> PairingStartOut:
	settings = get_Settings()
	now = datetime.now(timezone.utc)
	expires_at = now + timedelta(minutes=settings.PAIRING_TTL_MINUTES)
	device_code = generate_DeviceCode()
	#ебучая хуйня, вымотовшая нервы
	for _ in range(5):
		exists = db.query(models.PairingSession).filter_by(device_code=device_code).first()
		if not exists:
			break
		device_code = generate_DeviceCode()

	row = models.PairingSession(
		device_code=device_code,
		status="pending",
		expires_at=expires_at,
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return PairingStartOut(pairing_id=row.id, device_code=row.device_code, expires_at=row.expires_at)


def confirm_Pairing(db: Session, body: PairingConfirmIn) -> dict:
	settings = get_Settings()
	now = datetime.now(timezone.utc)
	row = (
		db.query(models.PairingSession)
		.filter(models.PairingSession.device_code == body.device_code.upper())
		.one_or_none()
	)
	if row is None:
		# пробуем как есть (на случай уже upper)
		row = (
			db.query(models.PairingSession)
			.filter(models.PairingSession.device_code == body.device_code)
			.one_or_none()
		)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PAIRING_BAD_CODE)

	expires = row.expires_at
	if expires.tzinfo is None:
		expires = expires.replace(tzinfo=timezone.utc)
	if expires < now or row.status == "expired":
		row.status = "expired"
		db.commit()
		raise HTTPException(status_code=status.HTTP_410_GONE, detail=MSG_PAIRING_EXPIRED)

	if body.profile_id is not None:
		profile = db.get(models.Profile, body.profile_id)
		if profile is None:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PROFILE_NOT_FOUND)

	agent_token = generate_AgentToken()
	trap = models.Trap(
		name=body.trap_name,
		profile_id=body.profile_id,
		status="pending",
		agent_token_hash=hash_Secret(agent_token),
	)
	db.add(trap)
	db.flush()

	row.trap_id = trap.id
	row.status = "confirmed"
	row.pending_agent_token = agent_token
	row.registration_token_hash = hash_Secret(agent_token)
	db.commit()
	return {
		"ok": True,
		"pairing_id": str(row.id),
		"trap_id": str(trap.id),
		"status": row.status,
		"stale_minutes": settings.AGENT_STALE_MINUTES,
	}


def complete_Pairing(db: Session, pairing_id: UUID) -> PairingCompleteOut:
	now = datetime.now(timezone.utc)
	row = db.get(models.PairingSession, pairing_id)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_PAIRING_NOT_FOUND)

	expires = row.expires_at
	if expires.tzinfo is None:
		expires = expires.replace(tzinfo=timezone.utc)
	if expires < now:
		row.status = "expired"
		db.commit()
		raise HTTPException(status_code=status.HTTP_410_GONE, detail=MSG_PAIRING_EXPIRED)

	if row.status == "pending":
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_PAIRING_NOT_READY)

	if row.status == "completed":
		# повторный complete не отдаёт токен повторно
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="pairing уже завершён")

	if row.status != "confirmed" or not row.trap_id or not row.pending_agent_token:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_PAIRING_NOT_READY)

	token = row.pending_agent_token
	row.status = "completed"
	row.completed_at = now
	row.pending_agent_token = None
	db.commit()

	return PairingCompleteOut(
		trap_id=row.trap_id,
		agent_token=token,
		status=PairingStatus.completed,
	)
