"""Redis client utilities.

Provides a lazy, reusable asyncio Redis connection plus a health check.
Designed minimal: no connection pool tweaks yet; can extend if needed.
"""
from __future__ import annotations
from typing import Optional
from redis.asyncio import Redis
from app.core.settings import get_settings
from app.core.logging import get_logger

_logger = get_logger("redis")

_redis: Optional[Redis] = None


def get_redis() -> Redis:
    """Return existing Redis instance (assumes init_redis called during startup)."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() at startup.")
    return _redis


async def init_redis() -> None:
    """Initialize global Redis connection using settings."""
    global _redis  # noqa: PLW0603
    if _redis is not None:
        return
    settings = get_settings()
    _redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    _logger.info("redis_init", url=settings.REDIS_URL)


async def close_redis() -> None:
    """Close Redis connection if present."""
    global _redis  # noqa: PLW0603
    if _redis is not None:
        await _redis.close()
        _logger.info("redis_close")
        _redis = None


async def ping() -> bool:
    """Ping Redis and return True if successful."""
    try:
        client = get_redis()
        resp = await client.ping()
        _logger.info("redis_ping", ok=resp)
        return bool(resp)
    except Exception as exc:  # noqa: BLE001
        _logger.error("redis_ping_fail", error=str(exc))
        return False


__all__ = ["init_redis", "close_redis", "get_redis", "ping"]
