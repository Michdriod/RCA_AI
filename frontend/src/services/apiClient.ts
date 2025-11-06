import axios from 'axios';
import type {
  StartSessionResponse,
  SubmitAnswerResponse,
  NextResponse,
  FinalizeResponse,
  ErrorResponse
} from '../types/session';

const API_BASE = import.meta?.env?.VITE_API_BASE || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

function unwrapError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const data = e.response?.data as ErrorResponse | undefined;
    if (!data) return e.message;
    if (data.error?.message) return data.error.message;
    if (data.detail) return data.detail;
    return e.message;
  }
  return 'Unexpected error';
}

export async function startSession(problem: string): Promise<StartSessionResponse> {
  try {
    const res = await api.post<StartSessionResponse>('/session/start', { problem });
    return res.data;
  } catch (e) {
    throw new Error(unwrapError(e));
  }
}

export async function submitAnswer(sessionId: string, answer: string): Promise<SubmitAnswerResponse> {
  try {
    const res = await api.post<SubmitAnswerResponse>('/session/answer', { session_id: sessionId, answer });
    return res.data;
  } catch (e) {
    throw new Error(unwrapError(e));
  }
}

export async function nextStep(sessionId: string): Promise<NextResponse> {
  try {
    const res = await api.get<NextResponse>('/session/next', { params: { session_id: sessionId } });
    return res.data;
  } catch (e) {
    throw new Error(unwrapError(e));
  }
}

export async function finalize(sessionId: string): Promise<FinalizeResponse> {
  try {
    const res = await api.post<FinalizeResponse>('/session/complete', { session_id: sessionId });
    return res.data;
  } catch (e) {
    throw new Error(unwrapError(e));
  }
}

export async function getState(sessionId: string) {
  try {
    const res = await api.get<{ session: { session_id: string; problem: string; step: number; status: string; question_count: number; answer_count: number; } }>(`/session/${sessionId}`);
    return res.data.session;
  } catch (e) {
    throw new Error(unwrapError(e));
  }
}
