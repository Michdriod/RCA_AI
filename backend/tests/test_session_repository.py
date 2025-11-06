import asyncio
import time
import pytest

from app.services import session_repository as repo
from app.models.root_cause import RootCause


class StubRedis:
    def __init__(self):
        self.store = {}
        self.expiry = {}

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        self.expiry[key] = ex if ex is not None else -1

    async def get(self, key: str):
        return self.store.get(key)

    async def ttl(self, key: str) -> int:
        if key not in self.store:
            return -2  # redis: key missing
        return self.expiry.get(key, -1)


@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr("app.services.redis_client.get_redis", lambda: stub)
    # Provide settings stub
    class SettingsStub:
        SESSION_TTL_SECONDS = 3600
        redis_session_prefix = "rca:session:"
    monkeypatch.setattr("app.core.settings.get_settings", lambda: SettingsStub())
    return stub


@pytest.mark.asyncio
async def test_create_and_basic_flow():
    session = await repo.create_session("Test problem")
    assert session.session_id
    assert session.step == 0
    q = await repo.append_question(session.session_id, "Why 1?")
    assert q.index == 1
    a = await repo.append_answer(session.session_id, "Because reason 1")
    assert a.index == 1
    loaded = await repo.get_session(session.session_id)
    assert loaded.step == 1
    assert len(loaded.questions) == 1
    assert len(loaded.answers) == 1


@pytest.mark.asyncio
async def test_mark_complete():
    session = await repo.create_session("Problem")
    await repo.append_question(session.session_id, "Q1")
    await repo.append_answer(session.session_id, "A1")
    rc = RootCause(summary="Root cause", contributing_factors=["Factor"])
    completed = await repo.mark_complete(session.session_id, rc)
    assert completed.status.value == "COMPLETED"
    assert completed.root_cause.summary == "Root cause"
