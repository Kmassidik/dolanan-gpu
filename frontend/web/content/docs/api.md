# API reference

## Inference API

```text
Base URL: https://llm.glicc.id/v1
```

### GET `/models`

```bash
curl https://llm.glicc.id/v1/models \
  -H "Authorization: Bearer $GLICC_API_KEY"
```

### POST `/chat/completions`

OpenAI-compatible chat completions. Supports streaming, tools, vision, and reasoning content.

```json
{
  "model": "qwen3.8-moe",
  "messages": [{ "role": "user", "content": "Hello" }],
  "max_tokens": 512,
  "stream": false
}
```

### Errors

```text
401  missing/invalid API key
404  unknown endpoint or model
429  queue or per-key rate limit
502  backend unavailable
504  queue or generation timeout
```

## Dashboard API

All dashboard API routes except login and health require a session cookie. State-changing requests require `X-CSRF-Token`, matching the readable `glicc_csrf` cookie.

```text
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/session

GET    /api/telemetry/latest
GET    /api/telemetry/history?minutes=60&gpu=0&points=60

GET    /api/summary?days=30
GET    /api/requests/recent?limit=20

GET    /api/keys
POST   /api/keys
DELETE /api/keys/{name}

GET    /api/health
```

### Login

```json
{ "username": "admin", "password": "..." }
```

Sets an `HttpOnly` session cookie and a readable CSRF cookie.

### Telemetry history

History is downsampled server-side. `points` is clamped to 1–240.

```json
{
  "minutes": 60,
  "gpu": 0,
  "bucket_seconds": 60,
  "samples": [
    { "ts": 1793164300, "gpu_index": 0, "temp_c": 38, "util_pct": 0 }
  ]
}
```

### Create key

```json
{ "name": "opencode-laptop", "rpm": 60 }
```

Returns the plaintext key once. Only its SHA-256 hash is stored.

### Error shape

```json
{ "error": "message" }
```
