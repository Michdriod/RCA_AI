#!/usr/bin/env python3
"""Manual test runner for answer classification (no pytest dependency)."""

import sys
import time

# Add backend to path
sys.path.insert(0, '/Users/mac/Desktop/RCA_AI/backend')

from app.ai.agent import FiveWhysAI, AnswerType
from app.models.session import Session, SessionStatus
from app.models.answer import Answer

def test_classify_unknown_answers():
    """Test UNKNOWN classification for various 'I don't know' patterns."""
    print("\n=== Testing UNKNOWN Classification ===")
    ai = FiveWhysAI()
    
    test_cases = [
        "I don't know",
        "i dont know",
        "not sure",
        "can't say",
        "idk",
        "no idea",
        "?"
    ]
    
    passed = 0
    for text in test_cases:
        result = ai._classify_answer(text)
        status = "✓" if result == AnswerType.UNKNOWN else "✗"
        print(f"  {status} '{text}' -> {result.value}")
        if result == AnswerType.UNKNOWN:
            passed += 1
    
    print(f"  Passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_classify_mechanism_answers():
    """Test MECHANISM classification for concrete technical answers."""
    print("\n=== Testing MECHANISM Classification ===")
    ai = FiveWhysAI()
    
    test_cases = [
        "The database query took too long",
        "CPU usage spiked to 100%",
        "The connection pool was exhausted",
        "WindowServer process was using high memory",
        "The API timeout was set too low"
    ]
    
    passed = 0
    for text in test_cases:
        result = ai._classify_answer(text)
        status = "✓" if result == AnswerType.MECHANISM else "✗"
        print(f"  {status} '{text[:50]}...' -> {result.value}")
        if result == AnswerType.MECHANISM:
            passed += 1
    
    print(f"  Passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_classify_vague_answers():
    """Test VAGUE classification for generic non-specific answers."""
    print("\n=== Testing VAGUE Classification ===")
    ai = FiveWhysAI()
    
    test_cases = [
        "They improved it",
        "Better UI",
        "Enhanced security",
        "Things changed"
    ]
    
    passed = 0
    for text in test_cases:
        result = ai._classify_answer(text)
        status = "✓" if result == AnswerType.VAGUE else "✗"
        print(f"  {status} '{text}' -> {result.value}")
        if result == AnswerType.VAGUE:
            passed += 1
    
    print(f"  Passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_classify_context_answers():
    """Test CONTEXT classification for informational but non-mechanism answers."""
    print("\n=== Testing CONTEXT Classification ===")
    ai = FiveWhysAI()
    
    test_cases = [
        "After the macOS update",
        "During peak hours in the morning",
        "When multiple users are active"
    ]
    
    passed = 0
    for text in test_cases:
        result = ai._classify_answer(text)
        status = "✓" if result == AnswerType.CONTEXT else "✗"
        print(f"  {status} '{text}' -> {result.value}")
        if result == AnswerType.CONTEXT:
            passed += 1
    
    print(f"  Passed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_depth_score_computation():
    """Test depth score counting only MECHANISM answers."""
    print("\n=== Testing Depth Score Computation ===")
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
    
    # Show classifications
    for i, ans in enumerate(session.answers, 1):
        ans_type = ai._classify_answer(ans.text)
        print(f"  Answer {i}: {ans_type.value:12} - '{ans.text}'")
    
    depth = ai._compute_depth_score(session)
    expected = 2  # Only answers 2 and 4 are MECHANISM
    status = "✓" if depth == expected else "✗"
    print(f"\n  {status} Depth Score: {depth} (expected {expected})")
    return depth == expected


def main():
    print("=" * 70)
    print("Manual Test Runner: Answer Classification & Depth Tracking")
    print("=" * 70)
    
    results = {
        "UNKNOWN classification": test_classify_unknown_answers(),
        "MECHANISM classification": test_classify_mechanism_answers(),
        "VAGUE classification": test_classify_vague_answers(),
        "CONTEXT classification": test_classify_context_answers(),
        "Depth score computation": test_depth_score_computation(),
    }
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results.values())
    total = len(results)
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} test groups passed")
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
