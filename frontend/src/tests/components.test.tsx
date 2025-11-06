import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Home from '../pages/Home';

vi.mock('../services/apiClient', () => {
  let step = 0;
  return {
    startSession: vi.fn(async (problem: string) => ({
      session: { session_id: 'sess-1', step: 0, status: 'ACTIVE', problem },
      question: { text: 'Why did this happen?', index: 0 }
    })),
    submitAnswer: vi.fn(async () => ({ session: { session_id: 'sess-1', step: step, status: 'ACTIVE', question_count: step + 1, answer_count: step + 1 } })),
    nextStep: vi.fn(async () => {
      step += 1;
      if (step < 4) {
        return { type: 'question', session: { session_id: 'sess-1', problem: 'Test', step, status: 'ACTIVE', question_count: step + 1, answer_count: step }, question: { text: `Why #${step}?`, index: step } };
      }
      return { type: 'root_cause', session: { session_id: 'sess-1', problem: 'Test', step: 4, status: 'COMPLETED', question_count: 5, answer_count: 4 }, root_cause: { summary: 'Root cause found', contributing_factors: ['Factor A'] } };
    }),
    finalize: vi.fn(async () => ({ session_id: 'sess-1', step: 4, status: 'COMPLETED', root_cause: { summary: 'Root cause found', contributing_factors: ['Factor A'] } }))
  };
});

describe('Home page flow', () => {
  beforeEach(() => {
    render(<Home />);
  });

  it('starts a session from problem input', async () => {
  const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Test problem' } });
    fireEvent.click(screen.getByText(/start analysis/i));
    expect(await screen.findByText(/Why did this happen/)).toBeInTheDocument();
  });
});
