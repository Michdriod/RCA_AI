"""Pydantic model: Session.
Represents an active or completed 5 Whys analysis session.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

from .question import Question
from .answer import Answer
from .root_cause import RootCause


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class Session(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    problem: str = Field(..., min_length=1, description="Original problem statement")
    questions: list[Question] = Field(default_factory=list, description="Ordered list of generated questions")
    answers: list[Answer] = Field(default_factory=list, description="Ordered list of user answers")
    step: int = Field(0, ge=0, le=5, description="Number of completed Q/A pairs")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Lifecycle status")
    created_at: float = Field(..., description="Unix epoch seconds when session created")
    completed_at: float | None = Field(None, description="Unix epoch seconds when session completed (if any)")
    root_cause: RootCause | None = Field(None, description="Final root cause analysis once completed")

    model_config = {
        "extra": "forbid",
    }

__all__ = ["Session", "SessionStatus"]
