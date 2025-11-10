"""Application settings module.

Centralized environment-driven configuration using Pydantic BaseSettings (v2).
Fields kept minimal for clarity and performance.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import field_validator

EnvironmentName = Literal["dev", "prod", "test"]

class Settings(BaseSettings):
    APP_ENV: EnvironmentName = Field("dev", description="Runtime environment")
    REDIS_URL: str = Field("redis://localhost:6379/0", description="Redis connection URL")
    SESSION_TTL_SECONDS: int = Field(1800, description="TTL for session keys in seconds")
    GROQ_API_KEY: Optional[str] = Field(None, description="Groq API key for model access")
    AI_MODEL: str = Field("openai/gpt-oss-20b", description="Groq model name (e.g. 'llama-3.3-70b-versatile')")
    AI_TEMPERATURE: float = Field(
        0.3,
        description="LLM temperature (0.0-1.0). Lower = more deterministic, focused. Recommended: 0.2-0.4 for RCA.",
        ge=0.0,
        le=1.0,
    )
    AI_TOP_P: float = Field(
        0.85,
        description="LLM nucleus sampling top_p (0.0-1.0). Controls diversity. Recommended: 0.8-0.9 for RCA.",
        ge=0.0,
        le=1.0,
    )
    EXTERNAL_CALLBACK_URL: Optional[str] = Field(
        None,
        description="Optional URL to receive a POST callback with final root cause payload when a session completes.",
    )
    LOG_LEVEL: str = Field(
        "INFO",
        description="Application log level (DEBUG, INFO, WARNING, ERROR). Avoid DEBUG in production.",
    )

    @field_validator("SESSION_TTL_SECONDS")
    def _validate_ttl(cls, v: int) -> int:  # noqa: D401 - simple validator
        if v <= 0:
            raise ValueError("SESSION_TTL_SECONDS must be positive")
        return v

    @property
    def debug(self) -> bool:
        return self.APP_ENV == "dev"

    @property
    def redis_session_prefix(self) -> str:
        return "rca:session:"

    @property
    def log_level_numeric(self) -> int:
        mapping = {
            "CRITICAL": 50,
            "ERROR": 40,
            "WARNING": 30,
            "INFO": 20,
            "DEBUG": 10,
        }
        return mapping.get(self.LOG_LEVEL.upper(), 20)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "case_sensitive": False,
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance (singleton style)."""
    return Settings()


def reset_settings_cache() -> None:  # testing helper
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


__all__ = ["Settings", "get_settings", "reset_settings_cache"]
