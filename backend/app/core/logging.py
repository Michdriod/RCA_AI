"""Structured logging utilities and a timing decorator.

Lightweight setup using structlog. Designed for low overhead and clarity.
"""
from __future__ import annotations
import functools
import time
from typing import Any, Callable, TypeVar
import structlog
from structlog.contextvars import merge_contextvars

try:
    from .settings import get_settings  # type: ignore
except Exception:  # noqa: BLE001
    get_settings = None  # type: ignore

F = TypeVar("F", bound=Callable[..., Any])


def configure_logging(level: int | None = None) -> None:
    """Configure structlog processors (idempotent).

    Args:
        level: Optional numeric log level override. If None, uses settings.LOG_LEVEL or INFO.
    """
    if level is None and get_settings:
        try:
            level = get_settings().log_level_numeric  # type: ignore[operator]
        except Exception:  # noqa: BLE001
            level = 20
    if level is None:
        level = 20
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "rca") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def log_timed(operation: str | None = None) -> Callable[[F], F]:
    """Decorator to log function execution duration in ms.

    Example:
        @log_timed("generate_question")
        def generate_question(...): ...
    """

    def decorator(func: F) -> F:
        op = operation or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger()
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start) * 1000.0
                logger.info("timing", event=op, duration_ms=round(duration_ms, 2))

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = ["configure_logging", "get_logger", "log_timed"]
