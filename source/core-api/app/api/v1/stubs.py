from fastapi import HTTPException, status

from app.texts import MSG_NOT_IMPLEMENTED


def raise_NotImplemented_Stub() -> None:
	"""Phase 0: route exists in OpenAPI, logic arrives in phase 1+."""
	raise HTTPException(
		status_code=status.HTTP_501_NOT_IMPLEMENTED,
		detail=MSG_NOT_IMPLEMENTED,
	)
