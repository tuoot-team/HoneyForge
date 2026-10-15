import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.events import service as event_service
from app.domains.events.schemas import EventChainListOut, EventListOut
from app.domains.events.sse_hub import event_sse_hub
from app.domains.rbac.permissions import PERM_EVENTS_READ
from app.domains.traps import access as trap_access

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EventListOut)
def list_Events(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_EVENTS_READ)),
	trap_id: UUID | None = None,
	event_type: str | None = None,
	source_ip: str | None = None,
	min_priority: Literal["low", "medium", "high"] | None = None,
	limit: int = Query(default=50, ge=1, le=500),
	offset: int = Query(default=0, ge=0),
) -> EventListOut:
	visible = trap_access.visible_Trap_Ids(db, operator)
	return event_service.list_Events(
		db,
		trap_id=trap_id,
		event_type=event_type,
		source_ip=source_ip,
		limit=limit,
		offset=offset,
		visible_trap_ids=visible,
		min_priority=min_priority,
	)


@router.get("/export")
def export_Events(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_EVENTS_READ)),
	format: Literal["csv", "stix"] = Query(default="csv", alias="format"),
	trap_id: UUID | None = None,
	event_type: str | None = None,
	source_ip: str | None = None,
	min_priority: Literal["low", "medium", "high"] | None = None,
	since: str | None = None,
	until: str | None = None,
	limit: int = Query(default=5000, ge=1, le=20000),
) -> Response:
	"""IoC-выгрузка: CSV или минимальный STIX 2.1 bundle."""
	visible = trap_access.visible_Trap_Ids(db, operator)
	body, media = event_service.export_Events(
		db,
		fmt=format,
		trap_id=trap_id,
		event_type=event_type,
		source_ip=source_ip,
		min_priority=min_priority,
		since_raw=since,
		until_raw=until,
		limit=limit,
		visible_trap_ids=visible,
	)
	filename = "events.stix.json" if format == "stix" else "events.csv"
	return Response(
		content=body,
		media_type=media,
		headers={"Content-Disposition": f'attachment; filename="{filename}"'},
	)


@router.get("/chains", response_model=EventChainListOut)
def list_Event_Chains(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_EVENTS_READ)),
	trap_id: UUID | None = None,
	window_sec: int = Query(default=3600, ge=60, le=86400),
) -> EventChainListOut:
	"""Цепочки source_ip по портам ловушки за окно времени."""
	visible = trap_access.visible_Trap_Ids(db, operator)
	return event_service.list_Event_Chains(
		db,
		trap_id=trap_id,
		window_sec=window_sec,
		visible_trap_ids=visible,
	)


@router.get("/stream")
async def stream_Events_SSE(
	db: DbSession,
	operator: CurrentUser = Depends(require_Permission(PERM_EVENTS_READ)),
):
	"""SSE-лента для CLI tail / Web UI. Без traps.all - только события своих ловушек."""
	visible = trap_access.visible_Trap_Ids(db, operator)
	allowed_ids = None if visible is None else {str(tid) for tid in visible}

	async def event_generator():
		yield ": connected\n\n"
		async for payload in event_sse_hub.subscribe():
			if payload is None:
				yield ": ping\n\n"
				continue
			if allowed_ids is not None:
				try:
					data = json.loads(payload)
					trap_raw = data.get("trap_id")
					if trap_raw is None or str(trap_raw) not in allowed_ids:
						continue
				except (json.JSONDecodeError, TypeError):
					continue
			yield f"data: {payload}\n\n"

	return StreamingResponse(
		event_generator(),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"Connection": "keep-alive",
			"X-Accel-Buffering": "no",
		},
	)
