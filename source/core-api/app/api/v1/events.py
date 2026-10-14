from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.events import service as event_service
from app.domains.events.schemas import EventListOut
from app.domains.events.sse_hub import event_sse_hub
from app.domains.rbac.permissions import PERM_EVENTS_READ

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EventListOut)
def list_Events(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_EVENTS_READ)),
	trap_id: UUID | None = None,
	event_type: str | None = None,
	source_ip: str | None = None,
	limit: int = Query(default=50, ge=1, le=500),
	offset: int = Query(default=0, ge=0),
) -> EventListOut:
	return event_service.list_Events(
		db,
		trap_id=trap_id,
		event_type=event_type,
		source_ip=source_ip,
		limit=limit,
		offset=offset,
	)


@router.get("/stream")
async def stream_Events_SSE(
	_operator: CurrentUser = Depends(require_Permission(PERM_EVENTS_READ)),
):
	"""SSE-лента для CLI tail / Web UI."""

	async def event_generator():
		yield ": connected\n\n"
		async for payload in event_sse_hub.subscribe():
			if payload is None:
				yield ": ping\n\n"
			else:
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
