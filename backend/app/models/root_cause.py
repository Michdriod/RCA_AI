"""Pydantic model: RootCause.
Represents the synthesized root cause analysis after 5 Whys.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator


class RootCause(BaseModel):
    summary: str = Field(..., min_length=1, description="Final root cause statement")
    contributing_factors: list[str] = Field(default_factory=list, description="List of supporting factors")

    @field_validator("contributing_factors")
    def factors_non_empty(cls, v: list[str]) -> list[str]:
        for f in v:
            if not f.strip():
                raise ValueError("Contributing factors must be non-empty strings")
        return v

    model_config = {
        "extra": "forbid",
    }

__all__ = ["RootCause"]
