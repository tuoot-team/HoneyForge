"""Протокол агента: heartbeat, config, events, claim."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.domains.agent.schemas import (
	AgentConfigOut,
	AgentEventsBatchIn,
	AgentHeartbeatIn,
	AgentHeartbeatOut,
)
from app.domains.events.sse_hub import event_sse_hub
from app.domains.profiles.schemas import ProfileBlocks, ProfileOut
from app.texts import MSG_AGENT_NO_PROFILE


def post_Heartbeat(db: Session, trap: models.Trap, body: AgentHeartbeatIn) -> AgentHeartbeatOut:
	now = datetime.now(timezone.utc)
	trap.last_seen_at = now
	trap.status = "online"
	meta = dict(trap.meta or {})
	meta["agent_version"] = body.agent_version
	meta["status_payload"] = body.status_payload
	trap.meta = meta
	trap.updated_at = now
	db.commit()

	config_version = None
	if trap.profile_id:
		profile = db.get(models.Profile, trap.profile_id)
		if profile:
			config_version = profile.config_version
	return AgentHeartbeatOut(ok=True, config_version=config_version)


def get_Config(db: Session, trap: models.Trap) -> AgentConfigOut:
	if not trap.profile_id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_AGENT_NO_PROFILE)
	profile = db.get(models.Profile, trap.profile_id)
	if profile is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_AGENT_NO_PROFILE)

	blocks = ProfileBlocks.model_validate(profile.blocks or {})
	profile_out = ProfileOut(
		id=profile.id,
		name=profile.name,
		description=profile.description,
		interaction_level=profile.interaction_level,
		blocks=blocks,
		config_version=profile.config_version,
		config_hash=profile.config_hash,
		created_at=profile.created_at,
		updated_at=profile.updated_at,
	)
	return AgentConfigOut(trap_id=trap.id, profile=profile_out)


def post_Events(db: Session, trap: models.Trap, body: AgentEventsBatchIn) -> dict:
	saved = 0
	for item in body.events:
		occurred_at = datetime.now(timezone.utc)
		if item.occurred_at:
			try:
				occurred_at = datetime.fromisoformat(item.occurred_at.replace("Z", "+00:00"))
			except ValueError:
				pass
		row = models.Event(
			trap_id=trap.id,
			event_type=item.event_type,
			source_ip=item.source_ip,
			source_port=item.source_port,
			occurred_at=occurred_at,
			payload=item.payload or {},
		)
		db.add(row)
		db.flush()
		from app.domains.events.service import event_Priority

		event_sse_hub.publish_Event(
			{
				"id": row.id,
				"trap_id": str(trap.id),
				"event_type": row.event_type,
				"source_ip": row.source_ip,
				"source_port": row.source_port,
				"occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
				"payload": row.payload,
				"priority": event_Priority(row.event_type, row.payload or {}),
			}
		)
		saved += 1
	trap.last_seen_at = datetime.now(timezone.utc)
	trap.status = "online"
	db.commit()
	return {"accepted": saved}


def claim_Command(db: Session, trap: models.Trap) -> dict:
	row = (
		db.query(models.TrapCommand)
		.filter(
			models.TrapCommand.trap_id == trap.id,
			models.TrapCommand.status == "pending",
		)
		.order_by(models.TrapCommand.created_at.asc())
		.first()
	)
	if row is None:
		return {"command": None}
	row.status = "claimed"
	row.claimed_at = datetime.now(timezone.utc)
	db.commit()
	return {
		"command": {
			"id": str(row.id),
			"command_type": row.command_type,
			"payload": row.payload or {},
		}
	}


def ack_Command(db: Session, trap: models.Trap, command_id: str, body: dict) -> dict:
	from uuid import UUID

	from fastapi import HTTPException, status

	from app.texts import MSG_TRAP_COMMAND_NOT_FOUND

	try:
		cid = UUID(str(command_id))
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=MSG_TRAP_COMMAND_NOT_FOUND,
		) from exc
	row = (
		db.query(models.TrapCommand)
		.filter(
			models.TrapCommand.id == cid,
			models.TrapCommand.trap_id == trap.id,
		)
		.one_or_none()
	)
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_COMMAND_NOT_FOUND)
	ok = bool(body.get("ok", True))
	detail = str(body.get("detail") or "")
	row.status = "done" if ok else "failed"
	payload = dict(row.payload or {})
	payload["ack_ok"] = ok
	if detail:
		payload["ack_detail"] = detail[:2000]
	row.payload = payload
	db.commit()
	return {"id": str(row.id), "status": row.status}
