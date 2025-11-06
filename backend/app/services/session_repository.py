"""Session repository backed by Redis.

Persists a `Session` model (including nested `Question` / `Answer` / optional `RootCause`) as a single JSON blob.
Provides operations: create, fetch, append question, append answer, mark complete, TTL check.
Automatically handles legacy dict-based records for backward compatibility by upgrading them into model instances.
"""
from __future__ import annotations
import time
import uuid
from typing import Optional

try:  # Favor orjson for speed; graceful fallback to std json
    import orjson as json  # type: ignore
except Exception:  # noqa: BLE001
    import json  # type: ignore

from app.core.settings import get_settings
from app.core.errors import SessionNotFound, SessionExpired, InvalidStep
from . import redis_client
from app.models.session import Session, SessionStatus
from app.models.question import Question
from app.models.answer import Answer
from app.models.root_cause import RootCause


def _key(session_id: str) -> str:
    return f"{get_settings().redis_session_prefix}{session_id}"

async def create_session(problem: str) -> Session:
    """Create a new session with initial problem state."""
    session_id = uuid.uuid4().hex
    now = time.time()
    session = Session(
        session_id=session_id,
        problem=problem.strip(),
        questions=[],
        answers=[],
        step=0,
        status=SessionStatus.ACTIVE,
        created_at=now,
        completed_at=None,
        root_cause=None,
    )
    ttl = get_settings().SESSION_TTL_SECONDS
    r = redis_client.get_redis()
    await r.set(_key(session_id), json.dumps(session.model_dump()), ex=ttl)
    return session


async def _load(session_id: str) -> Session:
    r = redis_client.get_redis()
    raw = await r.get(_key(session_id))
    if raw is None:
        raise SessionNotFound()
    try:
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise SessionNotFound("Corrupted session data") from exc
    ttl = await r.ttl(_key(session_id))
    if ttl == -2:
        raise SessionExpired()
    # Upgrade legacy dict to Session model if needed
    if isinstance(data, dict) and "session_id" in data:
        # Provide defaults for new fields if absent
        data.setdefault("created_at", time.time())
        data.setdefault("completed_at", None)
        data.setdefault("root_cause", None)
        # Map status strings to Enum
        status_val = data.get("status")
        if isinstance(status_val, str):
            try:
                data["status"] = SessionStatus(status_val.upper())
            except Exception:
                data["status"] = SessionStatus.ACTIVE
        # Convert nested questions/answers to models
        data["questions"] = [Question(**q) for q in data.get("questions", [])]
        data["answers"] = [Answer(**a) for a in data.get("answers", [])]
        rc = data.get("root_cause")
        if rc:
            try:
                data["root_cause"] = RootCause(**rc)
            except Exception:
                data["root_cause"] = None
        # Build Session instance
        return Session(**data)
    raise SessionNotFound("Unrecognized session format")


async def get_session(session_id: str) -> Session:
    return await _load(session_id)


async def append_question(session_id: str, text: str) -> Question:
    session = await _load(session_id)
    if session.status != SessionStatus.ACTIVE:
        raise InvalidStep("Cannot add question to completed session")
    idx = len(session.questions) + 1
    if idx > 5:
        raise InvalidStep("Cannot add more than 5 questions")
    q = Question(
        id=uuid.uuid4().hex,
        text=text.strip(),
        index=idx,
        created_at=time.time(),
    )
    session.questions.append(q)
    await _persist(session)
    return q


async def append_answer(session_id: str, text: str) -> Answer:
    session = await _load(session_id)
    if session.status != SessionStatus.ACTIVE:
        raise InvalidStep("Cannot add answer to completed session")
    if len(session.answers) >= len(session.questions):
        raise InvalidStep("Answer without corresponding question")
    idx = len(session.answers) + 1
    if idx > 5:
        raise InvalidStep("Cannot add more than 5 answers")
    a = Answer(
        question_id=session.questions[idx - 1].id,
        text=text.strip(),
        index=idx,
        created_at=time.time(),
    )
    session.answers.append(a)
    session.step = idx
    await _persist(session)
    return a


async def mark_complete(session_id: str, root_cause: RootCause) -> Session:
    session = await _load(session_id)
    if session.status == SessionStatus.COMPLETED:
        return session
    session.status = SessionStatus.COMPLETED
    session.completed_at = time.time()
    session.root_cause = root_cause
    await _persist(session)
    return session


async def get_ttl_seconds(session_id: str) -> int:
    r = redis_client.get_redis()
    ttl = await r.ttl(_key(session_id))
    # Redis returns -2 if key does not exist, -1 if no expire set
    if ttl < 0:
        raise SessionNotFound() if ttl == -2 else SessionExpired()
    return ttl


async def _persist(session: Session) -> None:
    r = redis_client.get_redis()
    ttl = await r.ttl(_key(session.session_id))
    if ttl == -2:
        raise SessionExpired()
    if ttl == -1:
        ttl = get_settings().SESSION_TTL_SECONDS
    await r.set(_key(session.session_id), json.dumps(session.model_dump()), ex=ttl)


__all__ = [
    "create_session",
    "get_session",
    "append_question",
    "append_answer",
    "mark_complete",
    "get_ttl_seconds",
]
