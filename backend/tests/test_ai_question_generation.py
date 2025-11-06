import pytest
from app.ai.prompts import (
    build_initial_question_prompt,
    build_follow_up_question_prompt,
    QAHistoryItem,
)


def test_initial_prompt_contains_problem():
    problem = "App crashes on launch"
    prompt = build_initial_question_prompt(problem)
    assert problem in prompt
    assert "FIRST" in prompt.upper()


def test_follow_up_prompt_includes_last_answer():
    history = [
        QAHistoryItem(index=1, question="Why 1?", answer="Because X"),
        QAHistoryItem(index=2, question="Why 2?", answer="Because Y"),
    ]
    prompt = build_follow_up_question_prompt("App crashes", history)
    assert "Because Y" in prompt
    assert "Step" in prompt  # formatting lines

