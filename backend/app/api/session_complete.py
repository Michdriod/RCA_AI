"""Session completion endpoint.
POST /session/complete

Optional external callback:
If the environment variable `EXTERNAL_CALLBACK_URL` is set the service will POST a JSON payload
with the finalized session data and root cause analysis to that URL.

Callback POST is fire-and-forget: failures are logged but do not affect the API response.
"""
from __future__ import annotations
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.services.five_whys_engine import FiveWhysEngine
from app.core.errors import InvalidStep, SessionNotFound, AIServiceError
from app.models.root_cause import RootCause
from app.core.settings import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/session", tags=["session"])

class CompleteRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")

class RootCauseOut(BaseModel):
    summary: str
    contributing_factors: list[str]

class CompleteResponse(BaseModel):
    session_id: str
    step: int
    status: str
    root_cause: RootCauseOut

def get_engine(request: Request) -> FiveWhysEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return engine

async def _push_callback(session, root_cause: RootCause) -> None:  # session typed dynamically to avoid circular import
    settings = get_settings()
    url = settings.EXTERNAL_CALLBACK_URL  # single source of truth
    if not url:
        return
    logger = get_logger("callback")
    payload = {
        "session_id": session.session_id,
        "problem": session.problem,
        "step": session.step,
        "status": session.status.value,
        "completed_at": session.completed_at,
        "root_cause": {
            "summary": root_cause.summary,
            "contributing_factors": root_cause.contributing_factors,
        },
        "questions": [
            {"index": q.index, "text": q.text} for q in session.questions
        ],
        "answers": [
            {"index": a.index, "text": a.text} for a in session.answers
        ],
    }
    timeout = httpx.Timeout(5.0, connect=2.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            logger.info(
                "callback_dispatched",
                url=url,
                status_code=resp.status_code,
                success=resp.status_code < 400,
            )
        except Exception as e:  # swallow errors but log
            logger.warning("callback_failed", url=url, error=str(e))

@router.post("/complete", response_model=CompleteResponse, summary="Finalize session root cause explicitly")
async def finalize_session(payload: CompleteRequest, engine: FiveWhysEngine = Depends(get_engine)):
    try:
        session, root_cause = await engine.finalize(payload.session_id)
    except SessionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidStep as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    await _push_callback(session, root_cause)

    return CompleteResponse(
        session_id=session.session_id,
        step=session.step,
        status=session.status.value,
        root_cause=RootCauseOut(summary=root_cause.summary, contributing_factors=root_cause.contributing_factors),
    )

__all__ = ["router"]
