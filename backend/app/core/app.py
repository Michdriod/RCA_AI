"""FastAPI application factory.

Keeps startup/shutdown minimal; other concerns (settings, redis, ai) plug in later.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
from app.core.logging import configure_logging, get_logger
from app.core.errors import register_exception_handlers
from app.ai.agent import FiveWhysAI
from app.services.five_whys_engine import FiveWhysEngine
from app.services.redis_client import init_redis, close_redis, ping as redis_ping
from app.api import (
    session_start,
    session_answer,
    session_next,
    session_complete,
)

# Future: central settings module (lazy import to avoid hard dependency now)
try:  # pragma: no cover - defensive until settings module exists
    from .settings import Settings  # type: ignore
    _settings = Settings()  # noqa: N816
except Exception:  # noqa: BLE001
    _settings = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """App lifespan events.

    Startup: (later) init redis connection, warm AI prompts, health checks.
    Shutdown: close redis connection, flush metrics buffers.
    """
    # STARTUP PHASE
    # Placeholder hooks; they will be filled once corresponding modules exist.
    # Example (to be added later): await redis_client.connect()
    logger = get_logger()

    # Redis initialization (with graceful in-memory fallback if initialization fails)
    try:
        await init_redis()
        ok = await redis_ping()
        if not ok:
            logger.warning("redis_unreachable", detail="Ping failed after init")
        app.state.redis_backend = "redis"
    except Exception as exc:  # noqa: BLE001
        logger.error("redis_init_fail", error=str(exc))

        class InMemoryRedis:  # minimal async-compatible subset used by repository
            def __init__(self):
                self._store: dict[str, tuple[str, float | None]] = {}

            async def set(self, key: str, value: str, ex: int | None = None):
                expire = (time.time() + ex) if ex else None
                self._store[key] = (value, expire)

            async def get(self, key: str) -> str | None:
                item = self._store.get(key)
                if not item:
                    return None
                value, expire = item
                if expire and time.time() > expire:
                    # expired; remove
                    self._store.pop(key, None)
                    return None
                return value

            async def ttl(self, key: str) -> int:
                item = self._store.get(key)
                if not item:
                    return -2  # key does not exist
                _, expire = item
                if expire is None:
                    return -1  # no expire set
                remaining = int(expire - time.time())
                if remaining < 0:
                    # treat as expired and delete
                    self._store.pop(key, None)
                    return -2
                return remaining

            async def close(self):  # parity with redis close
                self._store.clear()

            async def ping(self):  # used only by health check helper
                return True

        # monkey-patch global redis reference for repository module
        try:
            from app.services import redis_client as _redis_client_mod
            _redis_client_mod._redis = InMemoryRedis()  # type: ignore[attr-defined]
            app.state.redis_backend = "memory"
            logger.warning("redis_fallback_memory", detail="Using in-memory volatile store; data not persisted")
        except Exception as patch_exc:  # noqa: BLE001
            logger.error("redis_fallback_fail", error=str(patch_exc))

    # Initialize AI engine (could be extended with settings-driven model selection)
    ai = FiveWhysAI()
    app.state.engine = FiveWhysEngine(ai)

    yield

    # SHUTDOWN PHASE
    try:
        if getattr(app.state, "redis_backend", None) == "redis":
            await close_redis()
        elif getattr(app.state, "redis_backend", None) == "memory":
            # memory backend close
            from app.services import redis_client as _redis_client_mod
            redis_obj = getattr(_redis_client_mod, "_redis", None)
            if redis_obj is not None:
                try:
                    await redis_obj.close()  # type: ignore[func-returns-value]
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        logger = get_logger()
        logger.error("shutdown_redis_error", error=str(exc))


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance.

    Returns:
        FastAPI: configured app.
    """
    # Load environment variables from .env (non-destructive) before settings are accessed
    # Attempt to load .env from multiple candidate locations (project root & CWD)
    try:  # pragma: no cover - defensive
        env_candidates: list[Path] = []
        # Explicit override via ENV_FILE
        explicit = os.getenv("ENV_FILE")
        if explicit:
            env_candidates.append(Path(explicit))
        cwd_env = Path.cwd() / ".env"
        env_candidates.append(cwd_env)
        # Project root inferred by walking up from this file (backend/app/core/app.py -> project_root)
        project_root = Path(__file__).resolve().parents[3]
        root_env = project_root / ".env"
        if root_env not in env_candidates:
            env_candidates.append(root_env)
        loaded_any = False
        for candidate in env_candidates:
            try:
                if candidate.exists():
                    load_dotenv(dotenv_path=candidate, override=False)
                    loaded_any = True
            except Exception:  # noqa: BLE001
                continue
        if not loaded_any:
            # Minimal diagnostic (avoid noisy logs at runtime)
            try:
                # Use module-level get_logger to avoid creating a local binding that breaks later usage
                get_logger("env").info(
                    "env_load_skipped",
                    reason="no .env found",
                    searched=[str(p) for p in env_candidates],
                )
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass

    # Configure logging early so middleware & handlers use correct level
    try:  # pragma: no cover
        configure_logging()
    except Exception:  # noqa: BLE001
        pass

    app = FastAPI(
        title="RCA 5 Whys API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Request ID / correlation middleware
    logger = get_logger()

    class RequestIDMiddleware(BaseHTTPMiddleware):  # noqa: D401 - simple middleware
        async def dispatch(self, request: Request, call_next):
            incoming = request.headers.get("X-Request-ID")
            request_id = incoming or uuid.uuid4().hex
            request.state.request_id = request_id
            try:
                from structlog.contextvars import bind_contextvars  # local import to avoid hard dep issues
                bind_contextvars(request_id=request_id)
            except Exception:  # noqa: BLE001
                pass
            start = time.perf_counter()
            try:
                response = await call_next(request)
            except Exception:
                # Error logging handled by exception handlers; still ensure header set
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000.0
                logger.info(
                    "request_complete",
                    request_id=request_id,
                    method=request.method,
                    path=str(request.url.path),
                    duration_ms=round(duration_ms, 2),
                )
                try:
                    from structlog.contextvars import clear_contextvars
                    clear_contextvars()
                except Exception:  # noqa: BLE001
                    pass
            response.headers["X-Request-ID"] = request_id
            return response

    app.add_middleware(RequestIDMiddleware)

    # CORS configuration (handles browser preflight OPTIONS requests)
    origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "*")
    if origins_raw == "*":  # allow all
        allow_origins = ["*"]
    else:
        allow_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],  # allow all methods incl. POST for session endpoints
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Routers
    app.include_router(session_start.router)
    app.include_router(session_answer.router)
    app.include_router(session_next.router)
    app.include_router(session_complete.router)

    @app.get("/health", tags=["system"], summary="Health check")
    async def health() -> dict[str, str | int]:  # noqa: D401 - simple
        from app.core.settings import get_settings
        settings = get_settings()
        ai_key_present = bool(getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY"))
        redis_backend = getattr(app.state, "redis_backend", None) or "none"
        ai_model = getattr(settings, "AI_MODEL", None) or "unknown"
        # Metrics from AI (if initialized)
        metrics: dict[str, int] = {}
        try:  # pragma: no cover - defensive
            engine = getattr(app.state, "engine", None)
            if engine and hasattr(engine, "ai"):
                metrics = engine.ai.get_metrics()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        return {
            "status": "ok",
            "redis_backend": str(redis_backend),
            "ai_model": str(ai_model),
            "ai_key": "present" if ai_key_present else "missing",
            **metrics,
        }

    return app


__all__ = ["create_app"]
