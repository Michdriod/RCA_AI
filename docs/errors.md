# Error Responses

All custom errors use a unified body:

```json
{ "error": { "code": "SessionNotFound", "message": "Session not found", "classification": "not_found", "request_id": "abc123" } }
```

## Classes & HTTP Status Codes

| Code | HTTP | Classification | Meaning |
|------|------|----------------|---------|
| SessionNotFound | 404 | not_found | Unknown or deleted session |
| SessionExpired  | 410 | expired   | TTL elapsed; recreate session |
| InvalidStep     | 409 | invalid_step | Out-of-order action (e.g. finalize too early) |
| AIServiceError  | 502 | upstream_error | AI provider failure |
| InternalServerError | 500 | internal_error | Unexpected unhandled exception |

### Common Scenarios

| Scenario | Trigger | Example Message |
|----------|---------|-----------------|
| Answer after completion | POST /session/answer on completed session | "Session already completed" |
| Next before any answer | GET /session/next immediately after start | (allowed: returns next question) |
| Finalize early | POST /session/complete with <5 answers | "Cannot finalize before 5 answers" |
| Next after completion | GET /session/next after root cause | Returns existing root cause (not an error) |

### Handling in Frontend

1. Display `error.message` to user.
2. If `classification === 'expired'` suggest starting a new session.
3. For `upstream_error` allow retry of the same action.
4. Log `request_id` for correlation with backend logs.
