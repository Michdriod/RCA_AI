import { useState, useCallback } from 'react';
import type { Question, RootCause, NextResponse } from '../types/session';
import { startSession, submitAnswer, nextStep, finalize } from './apiClient';

interface FlowState {
  sessionId: string | null;
  problem: string;
  currentQuestion: Question | null;
  step: number;
  status: string;
  rootCause: RootCause | null;
  loading: boolean;
  error: string | null;
}

export function useSessionFlow() {
  const [state, setState] = useState<FlowState>({
    sessionId: null,
    problem: '',
    currentQuestion: null,
    step: 0,
    status: 'IDLE',
    rootCause: null,
    loading: false,
    error: null,
  });

  const setProblem = useCallback((p: string) => setState(s => ({ ...s, problem: p })), []);

  const start = useCallback(async () => {
    if (!state.problem.trim()) return;
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const data = await startSession(state.problem.trim());
      setState(s => ({
        ...s,
        sessionId: data.session.session_id,
        currentQuestion: data.question,
        step: data.session.step,
        status: data.session.status,
        loading: false,
      }));
    } catch (e) {
      setState(s => ({ ...s, error: (e as Error).message, loading: false }));
    }
  }, [state.problem]);

  const answer = useCallback(async (text: string) => {
    if (!state.sessionId) return;
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const data = await submitAnswer(state.sessionId, text);
      setState(s => ({
        ...s,
        step: data.session.step,
        status: data.session.status,
        loading: false,
      }));
    } catch (e) {
      setState(s => ({ ...s, error: (e as Error).message, loading: false }));
    }
  }, [state.sessionId]);

  const next = useCallback(async () => {
    if (!state.sessionId) return;
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const data: NextResponse = await nextStep(state.sessionId);
      if (data.type === 'question') {
        setState(s => ({
          ...s,
            currentQuestion: data.question,
            step: data.session.step,
            status: data.session.status,
            loading: false,
        }));
      } else {
        setState(s => ({
          ...s,
          currentQuestion: null,
          rootCause: data.root_cause,
          step: data.session.step,
          status: data.session.status,
          loading: false,
        }));
      }
    } catch (e) {
      setState(s => ({ ...s, error: (e as Error).message, loading: false }));
    }
  }, [state.sessionId]);

  const forceFinalize = useCallback(async () => {
    if (!state.sessionId) return;
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const data = await finalize(state.sessionId);
      setState(s => ({
        ...s,
        status: data.status,
        rootCause: data.root_cause,
        step: data.step,
        currentQuestion: null,
        loading: false,
      }));
    } catch (e) {
      setState(s => ({ ...s, error: (e as Error).message, loading: false }));
    }
  }, [state.sessionId]);

  return {
    sessionId: state.sessionId,
    problem: state.problem,
    setProblem,
    currentQuestion: state.currentQuestion,
    step: state.step,
    status: state.status,
    rootCause: state.rootCause,
    startSession: start,
    submitAnswer: answer,
    nextStep: next,
    finalize: forceFinalize,
    loading: state.loading,
    error: state.error,
  };
}
