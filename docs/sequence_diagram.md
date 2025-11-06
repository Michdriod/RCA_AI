# 5 Whys Session Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI Backend
    participant AI as AI (Groq)
    participant R as Redis

    U->>FE: Enter problem & Start
    FE->>API: POST /session/start { problem }
    API->>R: create_session()
    API->>AI: generate_question_async(problem, step=0)
    AI-->>API: first question
    API->>R: append_question()
    API-->>FE: { session(step=0), question }
    FE->>U: Display Question #0

    loop Steps 1..4
        U->>FE: Provide answer
        FE->>API: POST /session/answer { session_id, answer }
        API->>R: append_answer()
        API-->>FE: session snapshot
        U->>FE: Click Next
        FE->>API: GET /session/next?session_id
        API->>R: get_session()
    API->>AI: generate_question_async(step<N)
        AI-->>API: next question
        API->>R: append_question()
        API-->>FE: { session, question }
        FE->>U: Display next question
    end

    U->>FE: Provide 5th answer
    FE->>API: POST /session/answer { session_id, answer }
    API->>R: append_answer()
    API-->>FE: session snapshot(step=5)
    U->>FE: Click Next OR Explicit Finalize
    FE->>API: GET /session/next OR POST /session/complete
    API->>R: get_session()
    API->>AI: analyze_root_cause_async(all 5 answers)
    AI-->>API: root cause summary + factors
    API->>R: mark_complete(root_cause)
    API-->>FE: { session(COMPLETED), root_cause }
    FE->>U: Display root cause
```

## Lifecycle States

| Step | Answers | Action `next` | Result |
|------|---------|---------------|--------|
| 0    | 0       | generate Q1   | question |
| 1-4  | 1-4     | generate next | question |
| 5    | 5       | analyze       | root_cause |
| >5   | -       | idempotent    | existing root_cause |
