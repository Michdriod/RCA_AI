"""Central error types and FastAPI exception handlers.
Minimal, focused; each custom error carries an HTTP status code.
"""
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.logging import get_logger


class RCAError(Exception):
    status_code: int = 400
    detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)

class SessionNotFound(RCAError):
    status_code = 404
    details = "Session not found"

class SessionExpired(RCAError):
    status_code = 410  # Gone
    detail = "Session expired"


class InvalidStep(RCAError):
    status_code = 409  # Conflict
    detail = "Invalid step sequence"


class AIServiceError(RCAError):
    status_code = 502  # Bad Gateway (upstream model failure)
    detail = "AI service failure"


def _classification(exc: RCAError) -> str:
    if isinstance(exc, SessionNotFound):
        return "not_found"
    if isinstance(exc, SessionExpired):
        return "expired"
    if isinstance(exc, InvalidStep):
        return "invalid_step"
    if isinstance(exc, AIServiceError):
        return "upstream_error"
    return "domain_error"


def _error_body(exc: RCAError, request_id: str | None) -> dict[str, str | None]:
    return {
        "code": exc.__class__.__name__,
        "message": exc.detail,
        "classification": _classification(exc),
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers for custom + generic exceptions."""

    logger = get_logger()

    @app.exception_handler(RCAError)
    async def rca_error_handler(request: Request, exc: RCAError):  # noqa: D401 - FastAPI signature
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "error",
            error_type=exc.__class__.__name__,
            classification=_classification(exc),
            detail=exc.detail,
            request_id=request_id,
            path=request.url.path,
        )
        return JSONResponse(status_code=exc.status_code, content={"error": _error_body(exc, request_id)})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):  # pragma: no cover (fallback)
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "error",
            error_type="InternalServerError",
            classification="internal_error",
            detail=str(exc) or "Unexpected error",
            request_id=request_id,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "InternalServerError", "message": str(exc) or "Unexpected error", "classification": "internal_error", "request_id": request_id}},
        )


__all__ = [
    "RCAError",
    "SessionNotFound",
    "SessionExpired",
    "InvalidStep",
    "AIServiceError",
    "register_exception_handlers",
]
