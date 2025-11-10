# Environment & Secrets

## Backend (.env)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| REDIS_URL | yes | redis://localhost:6379/0 | Session storage |
| LOG_LEVEL | no | info | Adjust verbosity |
| GROQ_API_KEY | yes | (none) | AI question & analysis calls |
| AI_MODEL | no | openai/gpt-oss-20b | Groq model name (e.g., llama-3.3-70b-versatile) |
| CORS_ALLOW_ORIGINS | no | * | Comma list of allowed origins for browser access; `*` means all |

## Frontend (.env)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| VITE_API_BASE | no | <http://localhost:8000> | Backend API base URL |

### Notes

1. Never commit real keys; use `.env.example` for placeholders.
2. Rotate `GROQ_API_KEY` if upstream errors persist unexpectedly.
3. For production, set `LOG_LEVEL=info` (avoid debug verbosity).
4. Ensure Redis is running before starting the API if you want persistence. Without Redis the app will fall back to an in-memory volatile store (data lost on restart).

### Redis Setup (Local)

Pick one method:

```bash
# Homebrew (macOS)
brew install redis
brew services start redis

# OR Docker
docker run --name redis -p 6379:6379 -d redis:7-alpine
```

Quick connectivity check:

```bash
redis-cli ping  # Expect PONG
```

If Redis is unreachable at startup, you'll see a warning `redis_fallback_memory` and sessions won't persist across restarts.

### Minimal `.env.example`

```bash
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=info
GROQ_API_KEY=YOUR_GROQ_KEY_HERE
CORS_ALLOW_ORIGINS=*
```

### Advanced Configuration (Optional)

For tuning AI behavior, these can be set in `.env` to override sensible defaults already configured in the code:

```bash
# AI Model Configuration (optional overrides)
AI_MODEL=llama-3.3-70b-versatile    # Default: openai/gpt-oss-20b
AI_TEMPERATURE=0.3                  # Default: 0.3 (range: 0.0-1.0, recommended: 0.2-0.4 for RCA)
AI_TOP_P=0.85                       # Default: 0.85 (range: 0.0-1.0, recommended: 0.8-0.9 for RCA)
```

**Note:** The system is pre-configured with optimal `AI_TEMPERATURE=0.3` and `AI_TOP_P=0.85` for accurate root cause analysis. Only override these if you need to tune for specific use cases (see `docs/prompt_engineering.md`).
