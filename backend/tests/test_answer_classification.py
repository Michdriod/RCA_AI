"""Test answer classification and depth tracking."""
import pytest
from app.ai.agent import FiveWhysAI, AnswerType


def test_classify_unknown_answers():
    """Test UNKNOWN classification for various 'I don't know' patterns."""
    ai = FiveWhysAI()
    
    assert ai._classify_answer("I don't know") == AnswerType.UNKNOWN
    assert ai._classify_answer("i dont know") == AnswerType.UNKNOWN
    assert ai._classify_answer("not sure") == AnswerType.UNKNOWN
    assert ai._classify_answer("can't say") == AnswerType.UNKNOWN
    assert ai._classify_answer("idk") == AnswerType.UNKNOWN
    assert ai._classify_answer("no idea") == AnswerType.UNKNOWN
    assert ai._classify_answer("?") == AnswerType.UNKNOWN


def test_classify_mechanism_answers():
    """Test MECHANISM classification for concrete technical answers."""
    ai = FiveWhysAI()
    
    assert ai._classify_answer("The database query took too long") == AnswerType.MECHANISM
    assert ai._classify_answer("CPU usage spiked to 100%") == AnswerType.MECHANISM
    assert ai._classify_answer("The connection pool was exhausted") == AnswerType.MECHANISM
    assert ai._classify_answer("WindowServer process was using high memory") == AnswerType.MECHANISM
    assert ai._classify_answer("The API timeout was set too low") == AnswerType.MECHANISM


def test_classify_vague_answers():
    """Test VAGUE classification for generic non-specific answers."""
    ai = FiveWhysAI()
    
    assert ai._classify_answer("They improved it") == AnswerType.VAGUE
    assert ai._classify_answer("Better UI") == AnswerType.VAGUE
    assert ai._classify_answer("Enhanced security") == AnswerType.VAGUE
    assert ai._classify_answer("Things changed") == AnswerType.VAGUE


def test_classify_context_answers():
    """Test CONTEXT classification for informational but non-mechanism answers."""
    ai = FiveWhysAI()
    
    # These provide context but don't reference concrete mechanisms
    assert ai._classify_answer("After the macOS update") == AnswerType.CONTEXT
    assert ai._classify_answer("During peak hours in the morning") == AnswerType.CONTEXT
    assert ai._classify_answer("When multiple users are active") == AnswerType.CONTEXT


def test_depth_score_computation():
    """Test depth score counting only MECHANISM answers."""
    from app.models.session import Session, SessionStatus
    from app.models.answer import Answer
    import time
    
    ai = FiveWhysAI()
    
    session = Session(
        session_id="test",
        problem="Test problem",
        questions=[],
        answers=[
            Answer(question_id="q1", text="I don't know", index=1, created_at=time.time()),
            Answer(question_id="q2", text="The CPU was at 100%", index=2, created_at=time.time()),
            Answer(question_id="q3", text="Better design", index=3, created_at=time.time()),
            Answer(question_id="q4", text="The database connection pool was full", index=4, created_at=time.time()),
            Answer(question_id="q5", text="After the upgrade", index=5, created_at=time.time()),
        ],
        step=5,
        status=SessionStatus.ACTIVE,
        created_at=time.time(),
    )
    
    depth = ai._compute_depth_score(session)
    assert depth == 2, f"Expected 2 MECHANISM answers, got {depth}"
