import time
import pytest
from app.ai.agent import FiveWhysAI
from app.models.session import Session, SessionStatus
from app.models.question import Question
from app.models.answer import Answer


class StubAsyncAgent:
    def __init__(self):
        self.calls = 0

    async def run(self, prompt, output_type=None, model_settings=None):  # async path used by generate_question_async
        self.calls += 1
        text = (
            "Why did the database timeout?"
            if self.calls == 1
            else "Why was the connection pool exhausted during peak load?"
        )

        class R:  # minimal stub matching expected shape
            def __init__(self, t):
                self.output = type("O", (), {"question": t})()

        return R(text)


@pytest.mark.asyncio
async def test_semantic_dedup_retry(monkeypatch):
    ai = FiveWhysAI(model_name="test-model")
    monkeypatch.setattr(ai, "_resolve_model", lambda: StubAsyncAgent())
    q1 = Question(id="q1", text="Why did the database timeout?", index=1, created_at=time.time())
    a1 = Answer(question_id="q1", text="Because the connection pool was full", index=1, created_at=time.time())
    session = Session(
        session_id="s1",
        problem="Intermittent API latency spikes",
        questions=[q1],
        answers=[a1],
        step=1,
        status=SessionStatus.ACTIVE,
        created_at=time.time(),
        completed_at=None,
        root_cause=None,
    )
    new_q = await ai.generate_question_async(session)
    assert new_q.text != q1.text, "Dedup logic should have retried to produce a non-duplicate question"
    assert "connection pool" in new_q.text.lower(), "Expected deeper causal focus in regenerated question"
