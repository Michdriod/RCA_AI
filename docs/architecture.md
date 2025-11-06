# Architecture Overview
Frontend (React) <-> FastAPI API <-> Pydantic AI agent
Redis stores session: problem_statement, questions[], answers[], status.
Flow: submit problem -> loop Q/A (5) -> root cause summary -> optional external callback.
