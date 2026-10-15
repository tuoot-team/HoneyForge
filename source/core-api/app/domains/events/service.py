from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.domains.events.schemas import (
	EventChainListOut,
	EventChainOut,
	EventListOut,
	EventOut,
	EventPriority,
)
from app.texts import MSG_TRAP_NOT_FOUND

_PRIORITY_RANK: dict[EventPriority, int] = {"low": 0, "medium": 1, "high": 2}


def event_Priority(event_type: str, payload: dict[str, Any] | None) -> EventPriority:
	payload = payload or {}
	etype = (event_type or "").strip()
	if etype in ("shell_command", "db_command", "honeytoken_hit"):
		return "high"
	if etype == "auth_attempt":
		if bool(payload.get("success")):
			return "high"
		return "medium"
	if etype == "http_request":
		return "medium"
	return "low"


def _priority_At_Least(value: EventPriority, minimum: EventPriority) -> bool:
	return _PRIORITY_RANK[value] >= _PRIORITY_RANK[minimum]


def _to_EventOut(row: models.Event) -> EventOut:
	payload = row.payload or {}
	return EventOut(
		id=row.id,
		trap_id=row.trap_id,
		event_type=row.event_type,
		source_ip=row.source_ip,
		source_port=row.source_port,
		occurred_at=row.occurred_at,
		payload=payload,
		created_at=row.created_at,
		priority=event_Priority(row.event_type, payload),
	)


def list_Events(
	db: Session,
	*,
	trap_id: UUID | None,
	event_type: str | None,
	source_ip: str | None,
	limit: int,
	offset: int,
	visible_trap_ids: set[UUID] | None = None,
	min_priority: EventPriority | None = None,
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

	# min_priority считаем в Python: колонки priority нет.
	if min_priority:
		rows = query.order_by(models.Event.occurred_at.desc()).all()
		filtered = [
			row
			for row in rows
			if _priority_At_Least(event_Priority(row.event_type, row.payload or {}), min_priority)
		]
		total = len(filtered)
		page = filtered[offset : offset + limit]
		return EventListOut(items=[_to_EventOut(row) for row in page], total=total)

	total = query.count()
	rows = (
		query.order_by(models.Event.occurred_at.desc())
		.offset(offset)
		.limit(limit)
		.all()
	)
	return EventListOut(items=[_to_EventOut(row) for row in rows], total=total)


def _payload_Port(payload: dict[str, Any]) -> int | None:
	raw = payload.get("port")
	if isinstance(raw, int):
		return raw
	if isinstance(raw, str) and raw.isdigit():
		return int(raw)
	return None


def _payload_Service(payload: dict[str, Any]) -> str | None:
	raw = payload.get("service")
	if isinstance(raw, str) and raw.strip():
		return raw.strip()
	return None


def list_Event_Chains(
	db: Session,
	*,
	trap_id: UUID | None,
	window_sec: int,
	visible_trap_ids: set[UUID] | None = None,
) -> EventChainListOut:
	now = datetime.now(timezone.utc)
	since = now - timedelta(seconds=max(60, window_sec))
	query = db.query(models.Event).filter(models.Event.occurred_at >= since)
	if visible_trap_ids is not None:
		if trap_id is not None:
			if trap_id not in visible_trap_ids:
				raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_TRAP_NOT_FOUND)
			query = query.filter(models.Event.trap_id == trap_id)
		elif not visible_trap_ids:
			return EventChainListOut(items=[], total=0)
		else:
			query = query.filter(models.Event.trap_id.in_(visible_trap_ids))
	elif trap_id is not None:
		query = query.filter(models.Event.trap_id == trap_id)

	rows = query.order_by(models.Event.occurred_at.asc()).all()
	groups: dict[tuple[UUID | None, str], list[models.Event]] = {}
	for row in rows:
		ip = (row.source_ip or "").strip()
		if not ip:
			continue
		groups.setdefault((row.trap_id, ip), []).append(row)

	items: list[EventChainOut] = []
	for (tid, ip), events in groups.items():
		ports: set[int] = set()
		services: set[str] = set()
		types: set[str] = set()
		max_prio: EventPriority = "low"
		auth_success_ports: set[int] = set()
		other_ports: set[int] = set()
		for row in events:
			payload = row.payload or {}
			prio = event_Priority(row.event_type, payload)
			if _PRIORITY_RANK[prio] > _PRIORITY_RANK[max_prio]:
				max_prio = prio
			types.add(row.event_type)
			port = _payload_Port(payload)
			svc = _payload_Service(payload)
			if port is not None:
				ports.add(port)
			if svc:
				services.add(svc)
			if row.event_type == "auth_attempt" and bool(payload.get("success")) and port is not None:
				auth_success_ports.add(port)
			elif port is not None:
				other_ports.add(port)
		is_lateral = bool(auth_success_ports) and bool(other_ports - auth_success_ports)
		items.append(
			EventChainOut(
				trap_id=tid,
				source_ip=ip,
				event_count=len(events),
				ports=sorted(ports),
				services=sorted(services),
				event_types=sorted(types),
				first_at=events[0].occurred_at if events else None,
				last_at=events[-1].occurred_at if events else None,
				is_lateral=is_lateral,
				max_priority=max_prio,
			)
		)

	items.sort(key=lambda item: (not item.is_lateral, -_PRIORITY_RANK[item.max_priority], -(item.event_count)))
	return EventChainListOut(items=items, total=len(items))
