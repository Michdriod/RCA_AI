export interface SessionMeta {
  session_id: string;
  step: number;
  status: string; // ACTIVE | COMPLETED
  problem: string;
}

export interface Question {
  id?: string; // not always present in snapshots
  text: string;
  index: number;
}

export interface RootCause {
  summary: string;
  contributing_factors: string[];
}

export interface SessionSnapshot {
  session_id: string;
  problem: string;
  step: number;
  status: string;
  question_count: number;
  answer_count: number;
}

export interface StartSessionResponse {
  session: SessionMeta;
  question: Question;
}

export interface SubmitAnswerResponse {
  session: {
    session_id: string;
    step: number;
    status: string;
    question_count: number;
    answer_count: number;
  };
}

export interface NextQuestionResponse {
  type: 'question';
  session: SessionSnapshot;
  question: Question;
}

export interface NextRootCauseResponse {
  type: 'root_cause';
  session: SessionSnapshot;
  root_cause: RootCause;
}

export type NextResponse = NextQuestionResponse | NextRootCauseResponse;

export interface FinalizeResponse {
  session_id: string;
  step: number;
  status: string;
  root_cause: RootCause;
}

export interface ErrorResponse {
  error?: {
    code?: string;
    message?: string;
    classification?: string;
    request_id?: string;
  };
  detail?: string; // FastAPI default HTTPException body
}
