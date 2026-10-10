from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.deps import DbSession, Operator
from app.domains.events import service as event_service
from app.domains.events.schemas import EventListOut
from app.domains.events.sse_hub import event_sse_hub

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EventListOut)
def list_Events(
	db: DbSession,
	_operator: Operator,
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
async def stream_Events_SSE(_operator: Operator):
	"""SSE-лента для CLI tail / Web UI."""

	async def event_generator():
		# стартовый комментарий - некоторые прокси так держат соединение
		yield ": connected\n\n"
		async for payload in event_sse_hub.subscribe():
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
