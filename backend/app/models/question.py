"""Pydantic model: Question.
Represents a single generated 5 Whys question.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str = Field(..., description="Unique question identifier")
    text: str = Field(..., min_length=1, description="Question text")
    index: int = Field(..., ge=1, le=5, description="1-based position in sequence")
    created_at: float = Field(..., description="Unix epoch seconds when created")

    model_config = {
        "extra": "forbid",
    }

__all__ = ["Question"]
