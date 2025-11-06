"""Session start endpoint.
POST /session/start
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.services.five_whys_engine import FiveWhysEngine
from app.core.errors import AIServiceError, InvalidStep

router = APIRouter(prefix="/session", tags=["session"])

class StartSessionRequest(BaseModel):
    problem: str = Field(..., min_length=3, description="Problem statement to analyze")

class QuestionOut(BaseModel):
    id: str
    text: str
    index: int

class SessionMeta(BaseModel):
    session_id: str
    step: int
    status: str
    problem: str

class StartSessionResponse(BaseModel):
    session: SessionMeta
    question: QuestionOut

def get_engine(request: Request) -> FiveWhysEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return engine

@router.post("/start", response_model=StartSessionResponse, summary="Start a new 5 Whys session")
async def start_session(payload: StartSessionRequest, engine: FiveWhysEngine = Depends(get_engine)):
    try:
        session, question = await engine.start_session(payload.problem)
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    meta = SessionMeta(
        session_id=session.session_id,
        step=session.step,
        status=session.status.value,
        problem=session.problem,
    )
    q_out = QuestionOut(id=question.id, text=question.text, index=question.index)
    return StartSessionResponse(session=meta, question=q_out)

__all__ = ["router"]
