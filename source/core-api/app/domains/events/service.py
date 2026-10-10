from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db import models
from app.domains.events.schemas import EventListOut, EventOut


def list_Events(
	db: Session,
	*,
	trap_id: UUID | None,
	event_type: str | None,
	source_ip: str | None,
	limit: int,
	offset: int,
) -> EventListOut:
	query = db.query(models.Event)
	if trap_id is not None:
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
