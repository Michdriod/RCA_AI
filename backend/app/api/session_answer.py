"""Answer submission endpoint.
POST /session/answer
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.services.five_whys_engine import FiveWhysEngine
from app.core.errors import InvalidStep, AIServiceError

router = APIRouter(prefix="/session", tags=["session"])

class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    answer: str = Field(..., min_length=1, description="User's answer to the current question")

class SessionState(BaseModel):
    session_id: str
    step: int
    status: str
    question_count: int
    answer_count: int

class SubmitAnswerResponse(BaseModel):
    session: SessionState

def get_engine(request: Request) -> FiveWhysEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return engine


@router.post("/answer", response_model=SubmitAnswerResponse, summary="Submit answer to current question")
async def submit_answer(payload: SubmitAnswerRequest, engine: FiveWhysEngine = Depends(get_engine)):
    try:
        session = await engine.submit_answer(payload.session_id, payload.answer)
    except InvalidStep as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    state = SessionState(
        session_id=session.session_id,
        step=session.step,
        status=session.status.value,
        question_count=len(session.questions),
        answer_count=len(session.answers),
    )
    return SubmitAnswerResponse(session=state)

__all__ = ["router"]
