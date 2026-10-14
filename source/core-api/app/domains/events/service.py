from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.domains.events.schemas import EventListOut, EventOut
from app.texts import MSG_TRAP_NOT_FOUND


def list_Events(
	db: Session,
	*,
	trap_id: UUID | None,
	event_type: str | None,
	source_ip: str | None,
	limit: int,
	offset: int,
	visible_trap_ids: set[UUID] | None = None,
) -> EventListOut:
	"""visible_trap_ids=None - без ограничения по владельцу."""
	query = db.query(models.Event)
	if visible_trap_ids is not None:
		if trap_id is not None:
			if trap_id not in visible_trap_ids:
				raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
			query = query.filter(models.Event.trap_id == trap_id)
		elif not visible_trap_ids:
			return EventListOut(items=[], total=0)
		else:
			query = query.filter(models.Event.trap_id.in_(visible_trap_ids))
	elif trap_id is not None:
		query = query.filter(models.Event.trap_id == trap_id)
	if event_type:
		query = query.filter(models.Event.event_type == event_type)
	if source_ip:
		query = query.filter(models.Event.source_ip == source_ip)

	total = query.count()
	rows = (
		query.order_by(models.Event.occurred_at.desc())
		.offset(offset)
		.limit(limit)
		.all()
	)
	items = [
		EventOut(
			id=row.id,
			trap_id=row.trap_id,
			event_type=row.event_type,
			source_ip=row.source_ip,
			source_port=row.source_port,
			occurred_at=row.occurred_at,
			payload=row.payload or {},
			created_at=row.created_at,
		)
		for row in rows
	]
	return EventListOut(items=items, total=total)
