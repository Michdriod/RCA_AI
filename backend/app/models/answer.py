"""Pydantic model: Answer.
Represents a user's answer to a 5 Whys question.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Answer(BaseModel):
    question_id: str = Field(..., description="ID of the related question")
    text: str = Field(..., min_length=1, description="Answer text")
    index: int = Field(..., ge=1, le=5, description="1-based position matching its question")
    created_at: float = Field(..., description="Unix epoch seconds when captured")

    model_config = {
        "extra": "forbid",
    }

__all__ = ["Answer"]
