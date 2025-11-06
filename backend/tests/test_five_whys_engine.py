import pytest

from app.services.five_whys_engine import FiveWhysEngine
from app.models.session import Session, SessionStatus
from app.models.root_cause import RootCause
from app.models.question import Question
from app.models.answer import Answer
from app.services import session_repository as repo

class StubAI:
    async def generate_question_async(self, session: Session) -> Question:
        idx = len(session.questions) + 1
        return Question(id=f"q{idx}", text=f"Why {idx}?", index=idx, created_at=0.0)

    async def analyze_root_cause_async(self, session: Session) -> RootCause:
        return RootCause(summary="Stub root cause", contributing_factors=["Factor1", "Factor2"])

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    class StubRedis:
        def __init__(self):
            self.store = {}
            self.expiry = {}
        async def set(self, key, value, ex=None):
            self.store[key] = value
            self.expiry[key] = ex if ex is not None else -1
        async def get(self, key):
            return self.store.get(key)
        async def ttl(self, key):
            if key not in self.store:
                return -2
            return self.expiry.get(key, -1)
    stub = StubRedis()
    monkeypatch.setattr("app.services.redis_client.get_redis", lambda: stub)
    class SettingsStub:
        SESSION_TTL_SECONDS = 3600
        redis_session_prefix = "rca:session:"
    monkeypatch.setattr("app.core.settings.get_settings", lambda: SettingsStub())
    return stub

@pytest.mark.asyncio
async def test_full_engine_flow():
    engine = FiveWhysEngine(StubAI())
    session, first_q = await engine.start_session("Problem")
    assert first_q.index == 1
    # Answer and next until root cause
    for i in range(1,6):
        session = await engine.submit_answer(session.session_id, f"Answer {i}")
        if i < 5:
            session, next_q = await engine.next_step(session.session_id)
            assert next_q.index == i+1
        else:
            session, root = await engine.next_step(session.session_id)
            assert root.summary == "Stub root cause"
            assert session.status == SessionStatus.COMPLETED
