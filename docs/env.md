# Environment & Secrets

## Backend (.env)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| REDIS_URL | yes | redis://localhost:6379/0 | Session storage |
| LOG_LEVEL | no | info | Adjust verbosity |
| GROQ_API_KEY | yes | (none) | AI question & analysis calls |
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
