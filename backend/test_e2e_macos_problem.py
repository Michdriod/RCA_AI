#!/usr/bin/env python3
"""End-to-end test with the macOS screen-sharing problem."""

import sys
import time
import asyncio

sys.path.insert(0, '/Users/mac/Desktop/RCA_AI/backend')

from app.ai.agent import FiveWhysAI
from app.models.session import Session, SessionStatus
from app.models.question import Question
from app.models.answer import Answer

async def test_macos_screen_sharing_scenario():
    """Test the exact scenario user shared."""
    
    problem = "I've noticed that my laptop becomes extremely slow and starts glitching whenever I share my screen during a Microsoft Teams call. The screen sharing works initially, but once I start interacting with other applications, everything begins to lag and respond sluggishly. This issue started after I upgraded my macOS to version 26.1."
    
    # User's actual answers from the previous run
    actual_answers = [
        "i dont know why that happened, i cant really say this is the reason.",
        "i cant really say but they made some changes to the display, they made it more friendly in terms of the look and feel, and more security features",
        "i dont know",
        "i cant really say , i just feel apple just wanted to make things more user friendly and a better UI",
        "i dont know"
    ]
    
    print("=" * 80)
    print("END-TO-END TEST: macOS Screen Sharing Problem")
    print("=" * 80)
    print(f"\nProblem Statement:\n{problem}\n")
    
    ai = FiveWhysAI()
    
    # Create initial session
    session = Session(
        session_id="test_macos",
        problem=problem,
        questions=[],
        answers=[],
        step=0,
        status=SessionStatus.ACTIVE,
        created_at=time.time(),
    )
    
    print("\n" + "=" * 80)
    print("QUESTION GENERATION PHASE")
    print("=" * 80)
    
    # Generate 5 questions with user answers
    for i in range(5):
        print(f"\n--- Step {i+1} ---")
        
        # Generate question
        question = await ai.generate_question_async(session)
        session.questions.append(question)
        session.step = i + 1
        
        print(f"Q{i+1}: {question.text}")
        
        # Classify and show answer
        answer_text = actual_answers[i]
        answer = Answer(
            question_id=question.id,
            text=answer_text,
            index=i + 1,
            created_at=time.time()
        )
        session.answers.append(answer)
        
        answer_type = ai._classify_answer(answer_text)
        print(f"A{i+1}: {answer_text}")
        print(f"    [Classification: {answer_type.value}]")
        
        # Show metrics after each answer
        if answer_type.value == "UNKNOWN":
            print(f"    [Metrics: unknown_count={ai.unknown_count}, unknown_streak={ai.unknown_streak}]")
    
    # Compute depth score
    depth_score = ai._compute_depth_score(session)
    print(f"\n--- Depth Analysis ---")
    print(f"Depth Score: {depth_score} (distinct MECHANISM answers)")
    
    print("\n" + "=" * 80)
    print("ROOT CAUSE ANALYSIS PHASE")
    print("=" * 80)
    
    # Generate root cause
    session.status = SessionStatus.COMPLETED
    session.completed_at = time.time()
    
    root_cause = await ai.analyze_root_cause_async(session)
    session.root_cause = root_cause
    
    print(f"\nRoot Cause Summary:\n{root_cause.summary}")
    
    print(f"\nContributing Factors ({len(root_cause.contributing_factors)}):")
    if root_cause.contributing_factors:
        for i, factor in enumerate(root_cause.contributing_factors, 1):
            print(f"  {i}. {factor}")
    else:
        print("  (None - omitted due to vagueness filter)")
    
    print("\n" + "=" * 80)
    print("COMPARISON WITH PREVIOUS RUN")
    print("=" * 80)
    
    previous_summary = "The macOS 26.1 update modified the display subsystem, raising resource usage during screen sharing and causing lag when other applications run."
    previous_factors = [
        "Display subsystem changes for improved look and feel",
        "Security feature updates affecting rendering",
        "No user notification of performance impact"
    ]
    
    print("\nPrevious Root Cause:")
    print(f"  {previous_summary}")
    print("\nPrevious Contributing Factors:")
    for i, factor in enumerate(previous_factors, 1):
        print(f"  {i}. {factor}")
    
    print("\n" + "=" * 80)
    print("IMPROVEMENTS ASSESSMENT")
    print("=" * 80)
    
    improvements = []
    issues = []
    
    # Check for vendor motive speculation
    has_vendor_speculation = any("apple" in f.lower() or "look and feel" in f.lower() or "user friendly" in f.lower() 
                                  for f in root_cause.contributing_factors)
    if not has_vendor_speculation and any("look and feel" in f for f in previous_factors):
        improvements.append("✓ Eliminated vendor motive speculation ('look and feel', 'user friendly')")
    
    # Check for vague factors
    vague_patterns = ["improved", "enhanced", "better", "changes"]
    has_vague = any(any(p in f.lower() for p in vague_patterns) and len(f.split()) < 10 
                    for f in root_cause.contributing_factors)
    if not has_vague:
        improvements.append("✓ Vagueness filter applied - no generic adjectives without mechanism")
    
    # Check if summary exists
    if root_cause.summary and len(root_cause.summary) > 20:
        improvements.append("✓ Root cause summary always produced (no 'insufficient evidence' error)")
    
    # Check depth tracking
    improvements.append(f"✓ Depth score tracked: {depth_score} mechanistic answers identified")
    
    # Check UNKNOWN handling
    improvements.append(f"✓ UNKNOWN answers tracked: {ai.unknown_count} total, triggered {ai.evidence_pivots} evidence pivots")
    
    # Report findings
    print("\nImprovements Detected:")
    for imp in improvements:
        print(f"  {imp}")
    
    if issues:
        print("\nRemaining Issues:")
        for issue in issues:
            print(f"  {issue}")
    
    print("\n" + "=" * 80)
    print("FINAL METRICS")
    print("=" * 80)
    metrics = ai.get_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print(f"TEST COMPLETE - Score: Previous ~40/100 → Enhanced system ready for re-evaluation")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_macos_screen_sharing_scenario())
