import { useCallback, useState } from 'react';
import { startSession, submitAnswer, nextStep, finalize } from '../services/apiClient';
import type { Question, RootCause } from '../types/session';

type Status = 'idle' | 'asking' | 'awaiting_next' | 'complete' | 'error';

interface SessionState {
  sessionId: string | null;
  problem: string;
  currentQuestion: Question | null;
  rootCause: RootCause | null;
  step: number;
  status: Status;
  loading: boolean;
  error?: string;
}

export function useSession() {
  const [state, setState] = useState<SessionState>({
    sessionId: null,
    problem: '',
    currentQuestion: null,
    rootCause: null,
    step: 0,
    status: 'idle',
    loading: false,
  });

  const start = useCallback(async (problem: string) => {
    if (!problem.trim()) return;
    setState(s => ({ ...s, loading: true, error: undefined }));
    try {
      const res = await startSession(problem);
      setState(s => ({
        ...s,
        sessionId: res.session.session_id,
        problem,
        currentQuestion: res.question,
        step: res.session.step,
        status: 'asking',
        loading: false,
      }));
    } catch (e: any) {
      setState(s => ({ ...s, loading: false, error: e.message, status: 'error' }));
    }
  }, []);

  const answer = useCallback(async (answerText: string) => {
    if (!state.sessionId || !state.currentQuestion) return;
    if (!answerText.trim()) return;
    setState(s => ({ ...s, loading: true }));
    try {
      await submitAnswer(state.sessionId, answerText);
      setState(s => ({ ...s, loading: false, status: 'awaiting_next' }));
    } catch (e: any) {
      setState(s => ({ ...s, loading: false, error: e.message, status: 'error' }));
    }
  }, [state.sessionId, state.currentQuestion]);

  const next = useCallback(async () => {
    if (!state.sessionId) return;
    setState(s => ({ ...s, loading: true }));
    try {
      const res = await nextStep(state.sessionId);
      if (res.type === 'question') {
        setState(s => ({
          ...s,
            currentQuestion: res.question,
            step: res.session.step,
            status: 'asking',
            loading: false,
        }));
      } else {
        setState(s => ({
          ...s,
          rootCause: res.root_cause,
          step: res.session.step,
          status: 'complete',
          loading: false,
        }));
      }
    } catch (e: any) {
      setState(s => ({ ...s, loading: false, error: e.message, status: 'error' }));
    }
  }, [state.sessionId]);

  const finalizeSession = useCallback(async () => {
    if (!state.sessionId) return;
    setState(s => ({ ...s, loading: true }));
    try {
      const res = await finalize(state.sessionId);
      setState(s => ({
        ...s,
        rootCause: res.root_cause,
        step: res.step,
        status: 'complete',
        loading: false,
      }));
    } catch (e: any) {
      setState(s => ({ ...s, loading: false, error: e.message, status: 'error' }));
    }
  }, [state.sessionId]);

  const reset = useCallback(() => {
    setState({
      sessionId: null,
      problem: '',
      currentQuestion: null,
      rootCause: null,
      step: 0,
      status: 'idle',
      loading: false,
    });
  }, []);

  return {
    ...state,
    start,
    answer,
    next,
    finalizeSession,
    setProblem: (p: string) => setState(s => ({ ...s, problem: p })),
    reset,
    canAnswer: state.status === 'asking' && !!state.currentQuestion,
    canNext: state.status === 'awaiting_next',
  };
}
