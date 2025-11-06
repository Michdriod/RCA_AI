import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSession } from '../hooks/useSession';

vi.mock('../services/apiClient', () => {
  let step = 0;
  return {
    startSession: vi.fn(async (problem: string) => ({
      session: { session_id: 'sess-1', step: 0, status: 'ACTIVE', problem },
      question: { text: 'Initial why?', index: 0 }
    })),
    submitAnswer: vi.fn(async () => ({ session: { session_id: 'sess-1', step, status: 'ACTIVE', question_count: step + 1, answer_count: step + 1 } })),
    nextStep: vi.fn(async () => {
      step += 1;
      if (step < 4) {
        return { type: 'question', session: { session_id: 'sess-1', problem: 'Test', step, status: 'ACTIVE', question_count: step + 1, answer_count: step }, question: { text: `Why #${step}?`, index: step } };
      }
      return { type: 'root_cause', session: { session_id: 'sess-1', problem: 'Test', step: 4, status: 'COMPLETED', question_count: 5, answer_count: 4 }, root_cause: { summary: 'Found', contributing_factors: ['Factor A'] } };
    }),
    finalize: vi.fn(async () => ({ session_id: 'sess-1', step: 4, status: 'COMPLETED', root_cause: { summary: 'Found', contributing_factors: ['Factor A'] } }))
  };
});

describe('useSession hook', () => {
  it('starts and progresses to first question', async () => {
    const { result } = renderHook(() => useSession());
    await act(async () => {
      await result.current.start('Problem X');
    });
    expect(result.current.sessionId).toBe('sess-1');
    expect(result.current.currentQuestion?.text).toMatch(/Initial why/);
    expect(result.current.status).toBe('asking');
  });
});
