"""Groq-only AI Agent wrapper using pydantic-ai for 5 Whys facilitation.

Simplified configuration (Groq only):
 - Set `GROQ_API_KEY` in environment.
 - Optionally set `AI_MODEL` (default: "llama-3.3-70b-versatile").
 - No provider branching, no OpenAI fallback.

Public methods (async-only for production use):
 - generate_question_async(session)
 - analyze_root_cause_async(session)
"""
from __future__ import annotations
import time
from time import perf_counter
import uuid
from typing import Sequence, Optional, Type
import os
from pydantic import BaseModel, Field, ValidationError
from httpx import HTTPError
from pydantic_ai import Agent as PydanticAIAgent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
from ..core.errors import AIServiceError
from ..core.logging import get_logger
from ..core.settings import get_settings
from ..models.question import Question
from ..models.root_cause import RootCause
from ..models.session import Session
from .prompts import (
    QAHistoryItem,
    build_initial_question_prompt,
    build_follow_up_question_prompt,
    build_final_analysis_prompt,
)

# Output schemas for pydantic-ai runs
class QuestionResponse(BaseModel):
    question: str = Field(..., min_length=1)

class RootCauseResponse(BaseModel):
    summary: str = Field(..., min_length=1)
    contributing_factors: list[str] = Field(default_factory=list)


class FiveWhysAI:
    """Groq agent manager for question generation and root cause analysis."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("AI_MODEL") or "openai/gpt-oss-20b"
        # Metrics counters (simple in-memory; reset on process restart)
        self.dedup_retries_total: int = 0
        self.dedup_duplicates_accepted: int = 0

    # -------- internal helpers ---------
    def _resolve_model(self) -> PydanticAIAgent:
        """Create Groq-bound Agent instance (model only). Output schema provided per run via output_type."""
        settings = get_settings()
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise AIServiceError("Missing GROQ_API_KEY. Define in .env or export before starting server.")
        provider = GroqProvider(api_key=api_key)
        model_obj = GroqModel(self.model_name, provider=provider)
        return PydanticAIAgent(model=model_obj)
    
    def _get_model_settings(self) -> dict:
        """Return model parameters (temperature, top_p) from settings for run() calls."""
        settings = get_settings()
        return {
            "temperature": settings.AI_TEMPERATURE,
            "top_p": settings.AI_TOP_P,
        }

    def _history_items(self, session: Session) -> Sequence[QAHistoryItem]:
        items: list[QAHistoryItem] = []
        # Pair questions with answers by index.
        answer_map = {a.index: a for a in session.answers}
        for q in session.questions:
            ans = answer_map.get(q.index)
            if ans:
                items.append(
                    QAHistoryItem(index=q.index, question=q.text, answer=ans.text)
                )
        return items

    def _extract_text(self, run_result) -> str:
        """Best-effort extraction of raw text from a pydantic-ai AgentRunResult across versions.

        Prefers explicit attributes; falls back to stringifying the output payload.
        """
        # Common attributes in earlier versions
        for attr in ("output_text", "text", "content"):
            val = getattr(run_result, attr, None)
            if isinstance(val, str) and val.strip():
                return val
        # If structured output_type wasn't used, .output may be a string
        out = getattr(run_result, "output", None)
        if isinstance(out, str) and out.strip():
            return out
        # If output is a model with a single string field, attempt heuristic
        if out is not None and hasattr(out, "__dict__"):
            # Pick first str field
            for v in out.__dict__.values():
                if isinstance(v, str) and v.strip():
                    return v
        return str(out or run_result)

    async def generate_question_async(self, session: Session) -> Question:
        """Async variant of generate_question."""
        logger = get_logger("ai")
        started = perf_counter()
        model_settings = self._get_model_settings()
        try:
            agent = self._resolve_model()
            history_items = self._history_items(session)
            if not session.questions:
                prompt = build_initial_question_prompt(session.problem)
            else:
                prompt = build_follow_up_question_prompt(session.problem, history_items)
            try:
                run_result = await agent.run(prompt, output_type=QuestionResponse, model_settings=model_settings)
                question_text = run_result.output.question.strip()
            except ModelHTTPError as mh:
                if "tool_use_failed" in str(mh):
                    raw_run = await agent.run(prompt + "\n\nReturn ONLY the next question as plain text.", model_settings=model_settings)
                    question_text = self._extract_text(raw_run).strip()
                else:
                    raise
            # Apply semantic deduplication & metrics
            question_text = await self._deduplicate_question(
                agent=agent,
                prompt=prompt,
                session=session,
                initial_question=question_text,
                logger=logger,
                model_settings=model_settings,
            )
        except (HTTPError, ValidationError, ModelHTTPError) as e:
            raise AIServiceError(f"Question generation failed (async): {e}") from e
        finally:
            duration_ms = (perf_counter() - started) * 1000
            logger.info(
                "ai.question",
                session_id=session.session_id,
                step=session.step,
                duration_ms=round(duration_ms, 2),
                model=self.model_name,
                dedup_retries_total=self.dedup_retries_total,
                dedup_duplicates_accepted=self.dedup_duplicates_accepted,
            )
        return Question(
            id=str(uuid.uuid4()),
            text=question_text,
            index=session.step + 1,
            created_at=time.time(),
        )

    async def analyze_root_cause_async(self, session: Session) -> RootCause:
        """Async variant of analyze_root_cause."""
        history_items = self._history_items(session)
        if not history_items:
            raise AIServiceError("Cannot analyze root cause without any Q/A history")
        logger = get_logger("ai")
        started = perf_counter()
        model_settings = self._get_model_settings()
        try:
            agent = self._resolve_model()
            prompt = build_final_analysis_prompt(session.problem, history_items)
            try:
                run_result = await agent.run(prompt, output_type=RootCauseResponse, model_settings=model_settings)
                rc = RootCause(
                    summary=run_result.output.summary.strip(),
                    contributing_factors=[f.strip() for f in run_result.output.contributing_factors if f.strip()],
                )
            except ModelHTTPError as mh:
                if "tool_use_failed" in str(mh):
                    # Fallback: request strict JSON without permitting fabrication.
                    raw = await agent.run(
                        prompt
                        + "\n\nReturn ONLY valid JSON with keys: summary (string), contributing_factors (list of short, concrete strings)."
                        + " Do NOT invent or speculate beyond provided Q/A history."
                        + " If a value is genuinely unavailable, set summary to an empty string and contributing_factors to an empty list.",
                        model_settings=model_settings,
                    )
                    import json as _json
                    text = self._extract_text(raw).strip()
                    # Strip accidental leading labels (e.g., 'Summary: { ... }')
                    if text.lower().startswith("summary:"):
                        # Attempt to isolate JSON after first '{'
                        brace_index = text.find('{')
                        if brace_index != -1:
                            text = text[brace_index:]
                    try:
                        data = _json.loads(text)
                        summary = str(data.get("summary") or text)
                        factors = data.get("contributing_factors") or []
                        if not isinstance(factors, list):
                            factors = [str(factors)]
                    except Exception:  # noqa: BLE001
                        summary, factors = text, []
                    rc = RootCause(summary=summary.strip(), contributing_factors=[f.strip() for f in factors if f and str(f).strip()])
                else:
                    raise
        except (HTTPError, ValidationError, ModelHTTPError) as e:
            raise AIServiceError(f"Root cause analysis failed (async): {e}") from e
        finally:
            duration_ms = (perf_counter() - started) * 1000
            logger.info(
                "ai.root_cause",
                session_id=session.session_id,
                step=session.step,
                factors=len(rc.contributing_factors) if 'rc' in locals() else None,
                duration_ms=round(duration_ms, 2),
                model=self.model_name,
            )
        return rc

    # ----------------------------
    # Metrics & Dedup Helper
    # ----------------------------
    async def _deduplicate_question(
        self,
        agent: PydanticAIAgent,
        prompt: str,
        session: Session,
        initial_question: str,
        logger,
        model_settings: dict,
    ) -> str:
        """Apply semantic deduplication with retry + metrics.

        Returns non-duplicate question (or original if retries exhausted).

        Metrics updated:
          - dedup_retries_total += number of retry attempts
          - dedup_duplicates_accepted += 1 if still duplicate after max attempts
        """
        from difflib import SequenceMatcher
        existing_texts = [q.text for q in session.questions]
        if not existing_texts:
            return initial_question

        def _similar(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        def _is_duplicate(new_q: str) -> tuple[bool, str | None, float | None]:
            best_ratio = 0.0
            best_prev = None
            for prev in existing_texts:
                r = _similar(new_q, prev)
                if r > best_ratio:
                    best_ratio, best_prev = r, prev
            return (best_ratio >= 0.85, best_prev, best_ratio)

        is_dup, prev_match, ratio = _is_duplicate(initial_question)
        if not is_dup:
            return initial_question

        attempts = 0
        max_attempts = 3
        current_question = initial_question
        while is_dup and attempts < max_attempts:
            attempts += 1
            penalty_prompt = (
                prompt
                + "\n\nPenalty: Prior attempt duplicated an earlier question (similarity="
                + f"{ratio:.2f}). Generate a deeper, non-redundant causal question targeting a more specific underlying mechanism. Do NOT rephrase: '"
                + prev_match
                + "'."
            )
            try:
                retry_result = await agent.run(penalty_prompt, output_type=QuestionResponse, model_settings=model_settings)
                candidate = retry_result.output.question.strip()
            except ModelHTTPError as mh2:
                if "tool_use_failed" in str(mh2):
                    raw_retry = await agent.run(penalty_prompt + "\nReturn ONLY the refined question as plain text.", model_settings=model_settings)
                    candidate = self._extract_text(raw_retry).strip()
                else:
                    break
            is_dup, prev_match, ratio = _is_duplicate(candidate)
            if not is_dup:
                current_question = candidate
                logger.info(
                    "ai.question.dedup_retry",
                    session_id=session.session_id,
                    step=session.step,
                    attempts=attempts,
                    similarity=f"{(ratio or 0):.2f}",
                )
                break
        # Update metrics
        self.dedup_retries_total += attempts
        if is_dup and attempts >= max_attempts:
            self.dedup_duplicates_accepted += 1
            logger.warning(
                "ai.question.duplicate_accepted",
                session_id=session.session_id,
                step=session.step,
                similarity=f"{(ratio or 0):.2f}",
                prev_question=prev_match,
            )
        return current_question

    def get_metrics(self) -> dict[str, int]:
        """Return current in-memory counters (for health endpoint / monitoring)."""
        return {
            "dedup_retries_total": self.dedup_retries_total,
            "dedup_duplicates_accepted": self.dedup_duplicates_accepted,
        }

__all__ = [
    "FiveWhysAI",
    "QuestionResponse",
    "RootCauseResponse",
]
