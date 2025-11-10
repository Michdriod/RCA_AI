# RCA_AI – 5 Whys Root Cause Analysis

FastAPI + Redis + Groq AI backend with a React/Vite frontend for structured 5 Whys sessions.

## Features

* Start interactive session (adaptive AI questions)
* Redis persistence with TTL
* Auto or explicit finalization (root cause + factors)
* Unified error model (classification + request ID)
* React + TypeScript frontend hooks (`useSession`, `usePolling`)
* Test suites: pytest (backend) & vitest/RTL (frontend)

## Architecture

```text
backend/app/core        -> app factory, settings, logging, errors
backend/app/models      -> Pydantic models (Session, Question, Answer, RootCause)
backend/app/ai          -> prompts + Groq-based AI agent
backend/app/services    -> session repository (Redis) + FiveWhysEngine
backend/app/api         -> session lifecycle routers
frontend/src/components -> UI components
frontend/src/hooks      -> session & polling hooks
frontend/src/pages      -> Home page composition
docs/                   -> sequence diagram, errors, examples, env
```
 

## Session Lifecycle (Summary)

1. POST `/session/start` – create session + first question
2. POST `/session/answer` – store answer (no question yet)
3. GET `/session/next` – next question until 5 answers, then root cause
4. POST `/session/complete` – explicit finalization (optional)
5. GET `/session/{id}` – snapshot (counts + status)

Detailed diagram: `docs/sequence_diagram.md`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /session/start | Begin a session with a problem statement |
| POST | /session/answer | Append answer for current question |
| GET  | /session/next | Generate next question OR finalize root cause |
| POST | /session/complete | Explicitly finalize after 5 answers |
| GET  | /session/{id} | Retrieve session snapshot |

## Error Model

Unified JSON body:

```json
{ "error": { "code": "InvalidStep", "message": "Cannot finalize before 5 answers", "classification": "invalid_step", "request_id": "abc123" } }
```

Classifications: `not_found`, `expired`, `invalid_step`, `upstream_error`, `internal_error`. See `docs/errors.md`.

## Environment

Backend & frontend variable reference: `docs/env.md`.
Minimal backend `.env.example`:

```bash
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=info
GROQ_API_KEY=YOUR_GROQ_KEY_HERE
```

## Running

Backend (from repo root):

```bash
uvicorn backend.app.core.app:create_app --factory --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Visit: <http://localhost:5173> (frontend) calling <http://localhost:8000> (backend).

## Testing

Backend:

```bash
PYTHONPATH=backend pytest -q
```

Frontend:

```bash
cd frontend
npm run test
```

## Example Flow (Condensed)

Problem: "Morning API latency spike" → iterative answers → root cause: batch job schedule overlap + lack of review. Full example: `docs/examples.md`.

## Roadmap / Next Steps

* Normalize any remaining non-unified error responses
* Export/share root cause (JSON copy, markdown export)
* Authentication / multi-user session isolation
* Optional persistence beyond Redis TTL (DB)
* Observability: add metrics endpoint & dashboards

## AI Agent (Async-Only)

The internal AI layer exposes only asynchronous methods (sync versions removed to avoid event loop blocking):

```python
await five_whys_ai.generate_question_async(session)
await five_whys_ai.analyze_root_cause_async(session)
```

Question generation applies semantic deduplication using a similarity threshold (≥ 0.85) and up to 3 penalty-driven retries for deeper causal specificity.

### LLM Configuration for High-Accuracy RCA

The system uses optimized LLM parameters for focused, deterministic root cause analysis:

**Temperature:** 0.3 (range: 0.0-1.0)
- Lower values produce more consistent, contextual questions
- Reduces randomness and speculative responses
- Pre-configured default; override via `AI_TEMPERATURE` in `.env` only if needed

**Top-P (Nucleus Sampling):** 0.85 (range: 0.0-1.0)
- Balances focus with necessary flexibility
- Limits token selection to top 85% probability mass
- Pre-configured default; override via `AI_TOP_P` in `.env` only if needed

**These are hardcoded sensible defaults in `backend/app/core/settings.py`** — no `.env` configuration required unless you want to experiment with different values.

**Prompt Engineering:** Questions are generated using structured prompts with:
- Explicit 5 Whys methodology guidance
- Step-by-step internal reasoning chains
- Good vs bad question examples
- Contextual continuity rules (always reference problem + full Q/A history)
- Anti-speculation constraints (no guessing beyond provided information)

See `docs/prompt_engineering.md` for detailed prompt strategy and tuning recommendations.

### Dedup Metrics

Two counters are kept in-memory and surfaced via `GET /health`:

| Metric | Meaning |
|--------|---------|
| dedup_retries_total | Total number of retry attempts performed to avoid duplicates |
| dedup_duplicates_accepted | Times a duplicate was still accepted after max retries |

Sample health payload:

```json
{
  "status": "ok",
  "redis_backend": "redis",
  "ai_model": "llama-3.3-70b-versatile",
  "ai_key": "present",
  "dedup_retries_total": 4,
  "dedup_duplicates_accepted": 0
}
```

Future: expose Prometheus metrics & upgrade similarity to embeddings for richer semantic distance.

## License

See `LICENSE` file.

