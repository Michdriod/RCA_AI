import time
import pytest
from app.ai.agent import FiveWhysAI
from app.models.session import Session, SessionStatus
from app.models.question import Question
from app.models.answer import Answer


class StubAlwaysDuplicateAgent:
    def __init__(self):
        self.calls = 0

    async def run(self, prompt, output_type=None):
        self.calls += 1
        # Always return the same question text to force duplicate acceptance path
        text = "Why did the database timeout?"
        class R:
            def __init__(self, t):
                self.output = type("O", (), {"question": t})()
        return R(text)


class StubDuplicateThenUniqueAgent:
    def __init__(self):
        self.calls = 0

    async def run(self, prompt, output_type=None):
        self.calls += 1
        if self.calls == 1:
            text = "Why did the database timeout?"  # duplicate of existing
        else:
            text = "Why was the connection pool exhausted during peak load?"  # distinct
        class R:
            def __init__(self, t):
                self.output = type("O", (), {"question": t})()
        return R(text)


@pytest.mark.asyncio
async def test_dedup_metrics_retry(monkeypatch):
    ai = FiveWhysAI(model_name="test-model")
    monkeypatch.setattr(ai, "_resolve_model", lambda: StubDuplicateThenUniqueAgent())
    # Existing Q/A history
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
    assert new_q.text != q1.text
    metrics = ai.get_metrics()
    # One retry performed to avoid duplication; duplicate not accepted
    assert metrics["dedup_retries_total"] >= 1
    assert metrics["dedup_duplicates_accepted"] == 0


@pytest.mark.asyncio
async def test_dedup_metrics_duplicate_accepted(monkeypatch):
    ai = FiveWhysAI(model_name="test-model")
    monkeypatch.setattr(ai, "_resolve_model", lambda: StubAlwaysDuplicateAgent())
    q1 = Question(id="q1", text="Why did the database timeout?", index=1, created_at=time.time())
    a1 = Answer(question_id="q1", text="Because the connection pool was full", index=1, created_at=time.time())
    session = Session(
        session_id="s2",
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
    # Duplicate will be accepted after max attempts (3); question text unchanged
    assert new_q.text == q1.text
    metrics = ai.get_metrics()
    assert metrics["dedup_retries_total"] >= 3  # attempted retries
    assert metrics["dedup_duplicates_accepted"] == 1
