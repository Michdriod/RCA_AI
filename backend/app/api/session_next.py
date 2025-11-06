"""Next-step and session state endpoints.
GET /session/next?session_id=...
GET /session/{id}
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from app.services.five_whys_engine import FiveWhysEngine
from app.core.errors import InvalidStep, AIServiceError, SessionNotFound
from app.models.root_cause import RootCause

router = APIRouter(prefix="/session", tags=["session"])

class QuestionOut(BaseModel):
    id: str
    text: str
    index: int

class RootCauseOut(BaseModel):
    summary: str
    contributing_factors: list[str]

class SessionSnapshot(BaseModel):
    session_id: str
    problem: str
    step: int
    status: str
    question_count: int
    answer_count: int

class NextResponse(BaseModel):
    type: str  # 'question' | 'root_cause'
    session: SessionSnapshot
    question: QuestionOut | None = None
    root_cause: RootCauseOut | None = None

class SessionStateResponse(BaseModel):
    session: SessionSnapshot

def get_engine(request: Request) -> FiveWhysEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return engine

def _snapshot(session) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=session.session_id,
        problem=session.problem,
        step=session.step,
        status=session.status.value,
        question_count=len(session.questions),
        answer_count=len(session.answers),
    )


@router.get("/next", response_model=NextResponse, summary="Get next question or finalize root cause")
async def next_step(session_id: str = Query(...), engine: FiveWhysEngine = Depends(get_engine)):
    try:
        session, result = await engine.next_step(session_id)
    except SessionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidStep as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    snap = _snapshot(session)
    if isinstance(result, RootCause):
        return NextResponse(
            type="root_cause",
            session=snap,
            root_cause=RootCauseOut(summary=result.summary, contributing_factors=result.contributing_factors),
        )
    return NextResponse(
        type="question",
        session=snap,
        question=QuestionOut(id=result.id, text=result.text, index=result.index),
    )

@router.get("/{session_id}", response_model=SessionStateResponse, summary="Get current session state")
async def get_session_state(session_id: str, engine: FiveWhysEngine = Depends(get_engine)):
    try:
        session = await engine.get_session(session_id)
    except SessionNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    snap = _snapshot(session)
    return SessionStateResponse(session=snap)

__all__ = ["router"]
