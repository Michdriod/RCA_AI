"""Pydantic model: RootCause.
Represents the synthesized root cause analysis after 5 Whys.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_serializer


class RootCause(BaseModel):
    summary: str = Field(..., min_length=1, description="Final root cause statement")
    contributing_factors: list[str] = Field(default_factory=list, description="List of supporting factors")

    @field_validator("contributing_factors")
    def factors_non_empty(cls, v: list[str]) -> list[str]:
        for f in v:
            if not f.strip():
                raise ValueError("Contributing factors must be non-empty strings")
        return v

    @model_serializer
    def serialize_model(self):
        """Exclude contributing_factors from output if empty."""
        result = {"summary": self.summary}
        if self.contributing_factors:
            result["contributing_factors"] = self.contributing_factors
        return result

    model_config = {
        "extra": "forbid",
    }

__all__ = ["RootCause"]
