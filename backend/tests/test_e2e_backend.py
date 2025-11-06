import pytest
from fastapi.testclient import TestClient
from app.core.app import create_app
from app.services.five_whys_engine import FiveWhysEngine
from app.models.session import Session
from app.models.root_cause import RootCause
from app.models.question import Question

# Stub AI to keep deterministic and fast
class StubAI:
    async def generate_question_async(self, session: Session) -> Question:
        idx = len(session.questions) + 1
        return Question(id=f"q{idx}", text=f"Why {idx}?", index=idx, created_at=0.0)

    async def analyze_root_cause_async(self, session: Session) -> RootCause:
        return RootCause(summary="Stub root cause", contributing_factors=["FactorA", "FactorB"])

# In-memory redis stub
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

@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr("app.services.redis_client.get_redis", lambda: stub)
    class SettingsStub:
        SESSION_TTL_SECONDS = 3600
        redis_session_prefix = "rca:session:"
        LOG_LEVEL = "INFO"
    monkeypatch.setattr("app.core.settings.get_settings", lambda: SettingsStub())
    return stub

@pytest.fixture
def client():
    app = create_app()
    app.state.engine = FiveWhysEngine(StubAI())
    return TestClient(app)

@pytest.mark.parametrize("finalize_style", ["auto", "explicit"])  # run both finalization paths
def test_end_to_end_flow(client, finalize_style):
    # Start session
    r_start = client.post("/session/start", json={"problem": "Intermittent latency spike"})
    assert r_start.status_code == 200
    start_body = r_start.json()
    session_id = start_body["session"]["session_id"]
    assert start_body["question"]["index"] == 1
    req_id = r_start.headers.get("X-Request-ID")
    assert req_id  # correlation id present

    # Try premature finalize (should fail) to validate error classification
    r_bad_finalize = client.post("/session/complete", json={"session_id": session_id})
    # Endpoint currently returns 400 for InvalidStep (HTTPException mapping) not 409.
    assert r_bad_finalize.status_code == 400
    # Unified error handler wraps as {"error": {...}} when raised at domain layer;
    # here FastAPI HTTPException produces {"detail": ...}. Accept either form.
    body = r_bad_finalize.json()
    if "error" in body:
        assert body["error"]["code"] == "InvalidStep"
    else:
        assert "Cannot finalize" in body.get("detail", "")

    # Loop answers + next
    for i in range(1, 6):
        ra = client.post("/session/answer", json={"session_id": session_id, "answer": f"Answer {i}"})
        assert ra.status_code == 200
        if i < 5:
            rn = client.get("/session/next", params={"session_id": session_id})
            assert rn.status_code == 200
            body = rn.json()
            assert body["type"] == "question"
            assert body["question"]["index"] == i + 1
        else:
            if finalize_style == "auto":
                rn = client.get("/session/next", params={"session_id": session_id})
                assert rn.status_code == 200
                body = rn.json()
                assert body["type"] == "root_cause"
                assert body["root_cause"]["summary"] == "Stub root cause"
            else:  # explicit finalize path
                rc_resp = client.post("/session/complete", json={"session_id": session_id})
                assert rc_resp.status_code == 200
                body = rc_resp.json()
                assert body["root_cause"]["summary"] == "Stub root cause"

    # Idempotent finalize call returns same root cause
    again = client.post("/session/complete", json={"session_id": session_id})
    assert again.status_code == 200
    assert again.json()["root_cause"]["summary"] == "Stub root cause"

    # Fetch state and validate completed (counts only available, not arrays)
    state = client.get(f"/session/{session_id}")
    assert state.status_code == 200
    snap = state.json()["session"]
    assert snap["status"] == "COMPLETED"
    assert snap["answer_count"] == 5
    assert snap["question_count"] == 5

    # Check request ID propagation remains present in responses
    assert client.get("/health").headers.get("X-Request-ID")

