"""Prompt templates for 5 Whys AI interactions.
Provides helper builders to assemble prompts for question generation and final root cause analysis.
The output style encourages concise, clear, non-repetitive questioning.
"""
from __future__ import annotations

from textwrap import dedent
from typing import Sequence
from pydantic import BaseModel

class QAHistoryItem(BaseModel):
    index: int
    question: str
    answer: str

    def to_line(self) -> str:
        return f"Step {self.index}: Q: {self.question}\nA: {self.answer}".strip()

def _format_history(history: Sequence[QAHistoryItem]) -> str:
    if not history:
        return "(No previous steps)"
    return "\n\n".join(item.to_line() for item in history)

SYSTEM_STYLE_GUIDANCE = dedent(
    """
    You are an expert facilitator applying the 5 Whys technique.
    Guidelines:
    - Questions must start with an interrogative ("Why", "What caused", "How did" if appropriate) and be specific.
    - Avoid repeating the word-for-word phrasing of prior questions.
    - Do NOT provide answers yourself. Only ask the next question.
    - Maintain a neutral, analytical tone.
    - Each question should focus on uncovering the immediate cause of the last answer, not jumping to solutions.
    - Keep questions < 160 characters.
    Tool / Function Call Avoidance:
    - Do NOT invent or call any tools, functions, or APIs (e.g. no <function=...>, no function name wrappers, no JSON tool args).
    - Output MUST be plain text for questions; no JSON, no markup, no code fences.
    - Do NOT include phrases like 'final_result', 'brute_force_search', or similar.
    - Do NOT simulate a function call or embed arguments objects; only return the question itself.
    """
).strip()


def build_initial_question_prompt(problem: str) -> str:
    return dedent(
        f"""
        Problem Statement:
        {problem}

        Task: Ask the FIRST 'Why' question to begin root cause exploration.
        Internal reasoning (DO NOT OUTPUT):
        1. Parse the problem to extract: affected system/component, failure manifestation, impact, time/context cues.
        2. Identify the most immediate observable effect that needs explanation.
        3. Formulate a single causal probing question targeting the immediate underlying cause of that effect.
        4. Ensure the question is narrowly scoped and cannot be answered with simple 'yes/no'.
        5. Avoid proposing solutions or budgets/resources unless they are explicitly part of the immediate cause.
        Output requirements:
        - Respond ONLY with the question text (plain text).
        - No numbering, no quotes, no JSON, no tool/function syntax, no prefacing.
        {SYSTEM_STYLE_GUIDANCE}
        """
    ).strip()


def build_follow_up_question_prompt(problem: str, history: Sequence[QAHistoryItem]) -> str:
    formatted = _format_history(history)
    last_answer = history[-1].answer if history else "(none)"
    step = (history[-1].index + 1) if history else 1
    return dedent(
        f"""
        Problem Statement:
        {problem}

        Prior Steps:\n{formatted}

        Last answer: {last_answer}

        Task: Ask the NEXT 'Why' question (step {step}) delving deeper based ONLY on the last answer and established causal chain.
        Internal reasoning (DO NOT OUTPUT):
        1. Infer the causal link between the last answer and prior answers.
        2. Determine the smallest proximate cause inside the last answer that has not yet been directly questioned.
        3. If the chain is becoming speculative or repeating, pivot to a clarifying causal discriminator question.
        4. Avoid broad/systemic leaps; stay local to the newly uncovered mechanism.
        5. Keep focus on cause, not solution, policy, or blame.
        Output requirements:
        - Respond ONLY with the question text (plain text).
        - No numbering, JSON, tool/function syntax, commentary, or labels.
        {SYSTEM_STYLE_GUIDANCE}
        """
    ).strip()


def build_final_analysis_prompt(problem: str, history: Sequence[QAHistoryItem]) -> str:
        formatted = _format_history(history)
        return dedent(
                f"""
                Problem Statement:
                {problem}

                Full 5 Whys History:\n{formatted}

            Task: Produce the final root cause analysis.
            Internal reasoning (DO NOT OUTPUT):
            1. Trace each Q/A pair to form a linear causal chain.
            2. Collapse redundant layers; identify the deepest actionable underlying cause (not a symptom or a solution).
            3. Distill contributing factors: only those that materially enable or amplify the underlying cause.
            4. Exclude restatements of the summary and speculative guesses.
            IMPORTANT: Return ONLY valid JSON. DO NOT prepend labels like 'Summary:' or add explanations before/after JSON.
                Output Format (STRICT JSON object):
                {{
                    "summary": "<single sentence root cause>",
                    "contributing_factors": ["<factor 1>", "<factor 2>", ...]
                }}
                Rules:
                - "summary" is a single concise sentence describing the underlying cause (no solutions).
                - "contributing_factors" are 2-6 distinct causal factors; omit the array if truly none.
                - No speculative words ("maybe", "might").
                - Do NOT repeat the summary inside contributing_factors.
                - NO additional keys beyond these two.
                - NO tool/function call syntax, code fences, markdown, or prose outside the JSON.
                """
        ).strip()

__all__ = [
    "QAHistoryItem",
    "build_initial_question_prompt",
    "build_follow_up_question_prompt",
    "build_final_analysis_prompt",
]
