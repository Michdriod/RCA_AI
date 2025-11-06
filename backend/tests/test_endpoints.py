import pytest
from fastapi.testclient import TestClient

from app.core.app import create_app
from app.services.five_whys_engine import FiveWhysEngine
from app.models.session import Session
from app.models.root_cause import RootCause
from app.models.question import Question

# Stub AI for deterministic behavior
class StubAI:
    async def generate_question_async(self, session: Session) -> Question:
        idx = len(session.questions) + 1
        return Question(id=f"q{idx}", text=f"Why {idx}?", index=idx, created_at=0.0)

    async def analyze_root_cause_async(self, session: Session) -> RootCause:
        return RootCause(summary="Stub root cause", contributing_factors=["Factor1"])

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

@pytest.fixture
def client():
    app = create_app()
    # override engine with stub AI
    app.state.engine = FiveWhysEngine(StubAI())
    return TestClient(app)

def test_start_and_progress(client):
    r = client.post("/session/start", json={"problem": "Latency spike"})
    assert r.status_code == 200
    data = r.json()
    session_id = data["session"]["session_id"]
    assert data["question"]["index"] == 1

    # Answer 1
    ra = client.post("/session/answer", json={"session_id": session_id, "answer": "Because X"})
    assert ra.status_code == 200

    # Next -> question 2
    rn = client.get(f"/session/next", params={"session_id": session_id})
    assert rn.status_code == 200
    assert rn.json()["type"] == "question"
    assert rn.json()["question"]["index"] == 2

    # Complete remaining Q/A quickly
    for i in range(2,6):
        client.post("/session/answer", json={"session_id": session_id, "answer": f"Ans {i}"})
        resp = client.get("/session/next", params={"session_id": session_id})
    final = resp.json()
    assert final["type"] == "root_cause"
    assert final["root_cause"]["summary"] == "Stub root cause"

    # Fetch state
    state = client.get(f"/session/{session_id}")
    assert state.status_code == 200
    assert state.json()["session"]["status"] == "COMPLETED"
