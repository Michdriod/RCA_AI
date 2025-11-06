"""Five Whys orchestration service.

Coordinates session lifecycle with AI question generation and final root cause analysis.
Designed for async usage inside FastAPI endpoints.

Public contract now separates concerns to better map to planned endpoints:
  - start_session(problem) -> (Session, Question)
  - submit_answer(session_id, answer_text) -> Session   (answer stored; no question generation)
  - next_step(session_id) -> (Session, Question | RootCause)
      * Generates next question if <5 answers
      * Finalizes and returns RootCause if after 5 answers
  - finalize(session_id) -> (Session, RootCause)
      * Explicit root cause analysis (only valid when 5 answers present)
"""
from __future__ import annotations

import time
from typing import Tuple, Union

from app.core.errors import InvalidStep, SessionNotFound, AIServiceError
from app.models.session import Session, SessionStatus
from app.models.root_cause import RootCause
from app.models.question import Question
from app.models.answer import Answer
from app.ai.agent import FiveWhysAI
from app.core.logging import get_logger
from . import session_repository as repo


class FiveWhysEngine:
    def __init__(self, ai: FiveWhysAI):
        self.ai = ai
        self.logger = get_logger("engine")

    # -------------------------------------------------
    # Session lifecycle operations
    # -------------------------------------------------
    async def start_session(self, problem: str) -> Tuple[Session, Question]:
        """Create a new session and generate the first question.

        Returns the persisted session (step=0) and the first Question.
        """
        session = await repo.create_session(problem)
        q = await self.ai.generate_question_async(session)
        await repo.append_question(session.session_id, q.text)
        session = await repo.get_session(session.session_id)
        self.logger.info(
            "session.start",
            session_id=session.session_id,
            step=session.step,
            question_id=q.id,
            question_index=q.index,
        )
        return session, q

    async def submit_answer(self, session_id: str, answer_text: str) -> Session:
        """Persist the answer only. Question generation deferred to next_step.

        Returns the updated session after answer (step incremented).
        """
        session = await repo.get_session(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise InvalidStep("Session already completed")
        if session.step >= 5:
            raise InvalidStep("Maximum steps already reached")
        await repo.append_answer(session_id, answer_text)
        updated = await repo.get_session(session_id)
        self.logger.debug(
            "session.answer",
            session_id=session_id,
            step=updated.step,
            answer_index=updated.step - 1,
            question_count=len(updated.questions),
            answer_count=len(updated.answers),
        )
        return updated

    async def next_step(self, session_id: str) -> Tuple[Session, Union[Question, RootCause]]:
        """Advance to next question OR finalize root cause if 5 answers reached.

        Endpoint semantics:
          - If session has fewer than 5 answers -> generate & append next question.
          - If session has exactly 5 answers and not completed -> analyze root cause and complete.
          - If already completed -> return existing root cause.
        """
        session = await repo.get_session(session_id)
        if session.status == SessionStatus.COMPLETED:
            if session.root_cause is None:
                raise InvalidStep("Completed session missing root cause")
            return session, session.root_cause

        if session.step < 5:
            next_q = await self.ai.generate_question_async(session)
            await repo.append_question(session.session_id, next_q.text)
            session = await repo.get_session(session.session_id)
            self.logger.info(
                "session.next.question",
                session_id=session.session_id,
                step=session.step,
                question_id=next_q.id,
                question_index=next_q.index,
            )
            return session, next_q

        # Finalization path (exactly 5 answers, not yet completed)
        root_cause = await self._analyze(session)
        await repo.mark_complete(session.session_id, root_cause)
        session = await repo.get_session(session.session_id)
        self.logger.info(
            "session.next.root_cause",
            session_id=session.session_id,
            step=session.step,
            factors=len(root_cause.contributing_factors),
        )
        return session, root_cause

    async def finalize(self, session_id: str) -> Tuple[Session, RootCause]:
        """Explicitly finalize a session once 5 answers exist.
        Raises InvalidStep if fewer than 5 answers.
        Idempotent: returns existing root cause if already completed.
        """
        session = await repo.get_session(session_id)
        if session.status == SessionStatus.COMPLETED:
            if session.root_cause is None:
                raise InvalidStep("Completed session missing root cause")
            return session, session.root_cause
        if session.step < 5:
            raise InvalidStep("Cannot finalize before 5 answers")
        root_cause = await self._analyze(session)
        await repo.mark_complete(session.session_id, root_cause)
        session = await repo.get_session(session.session_id)
        self.logger.info(
            "session.complete",
            session_id=session.session_id,
            step=session.step,
            factors=len(root_cause.contributing_factors),
        )
        return session, root_cause

    # -------------------------------------------------
    # Internals
    # -------------------------------------------------
    async def _analyze(self, session: Session) -> RootCause:
        try:
            return await self.ai.analyze_root_cause_async(session)
        except AIServiceError:
            raise

    async def get_session(self, session_id: str) -> Session:
        return await repo.get_session(session_id)

__all__ = ["FiveWhysEngine"]
