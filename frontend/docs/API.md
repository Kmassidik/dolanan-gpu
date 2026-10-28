# gliccOps API

Base URL:

```text
https://llminferences.glicc.id/api
```

All endpoints except login and health require a valid session cookie.

## Authentication

### POST `/api/auth/login`

```json
{
  "username": "admin",
  "password": "..."
}
```

Success `200`:

```json
{
  "user": { "username": "admin", "role": "admin" },
  "csrf": "..."
}
```

Sets two cookies:

```text
glicc_session  HttpOnly, Secure, SameSite=Lax
glicc_csrf     readable by the app
```

Errors:

| Status | Meaning |
|---|---|
| `400` | invalid JSON |
| `401` | invalid credentials |
| `429` | too many failed attempts |

### GET `/api/auth/session`

Returns `200` with the current user or `401`.

### POST `/api/auth/logout`

Requires header:

```text
X-CSRF-Token: <glicc_csrf cookie value>
```

Returns `200`, clears cookies.

## Telemetry

### GET `/api/telemetry/latest`

```json
{
  "ts": 1793164300,
  "gpus": [
    {
      "gpu_index": 0,
      "temp_c": 38,
      "power_w": 24.2,
      "clock_mhz": 210,
      "util_pct": 0,
      "vram_used_mib": 6399,
      "vram_total_mib": 8192,
      "fan_pct": 0,
      "pcie_gbs": null,
      "fan_rpm": 0
    }
  ]
}
```

### GET `/api/telemetry/history?minutes=60&gpu=0&points=60`

```text
minutes: 1..1440
gpu:     0..n
points:  1..240
```

History is downsampled server-side; it does not return every 2-second sample.

```json
{
  "minutes": 60,
  "gpu": 0,
  "bucket_seconds": 60,
  "samples": [
    {
      "ts": 1793164300,
      "gpu_index": 0,
      "temp_c": 38,
      "power_w": 24.2,
      "clock_mhz": 210,
      "util_pct": 0,
      "vram_used_mib": 6399,
      "vram_total_mib": 8192,
      "fan_pct": 0
    }
  ]
}
```

## Summary

### GET `/api/summary?days=30`

```json
{
  "days": 30,
  "requests": 3,
  "tokens": 16,
  "rate_limited": 0,
  "avg_ttft_ms": 175,
  "avg_decode_tps": 84.3,
  "latest_trace": {
    "request_id": "...",
    "model": "qwen3.8-moe",
    "status": "completed",
    "prompt_tokens": 12,
    "completion_tokens": 16,
    "ttft_ms": 175,
    "decode_tps": 84.3,
    "created_at": 1793164300
  }
}
```

## Requests

### GET `/api/requests/recent?limit=20`

```json
{
  "requests": [
    {
      "request_id": "...",
      "model": "qwen3.8-moe",
      "status": "completed",
      "prompt_tokens": 12,
      "completion_tokens": 16,
      "ttft_ms": 175,
      "decode_tps": 84.3,
      "created_at": 1793164300
    }
  ]
}
```

### POST `/api/requests`

Internal gateway ingest. Uses a separate token, not a user session:

```text
Authorization: Bearer <data/ingest.token>
Content-Type: application/json
```

```json
{
  "request_id": "gateway-generated-id",
  "model": "qwen3.8-moe",
  "status": "completed",
  "prompt_tokens": 12,
  "completion_tokens": 16,
  "ttft_ms": 175,
  "decode_tps": 84.3,
  "api_key_name": "alice",
  "created_at": 1793164300,
  "finished_at": 1793164303
}
```

Limits: 64 KiB body, validated numeric fields.

## Health

### GET `/api/health`

Public:

```json
{ "status": "ok", "latest_ts": 1793164300 }
```

## Error format

```json
{ "error": "message" }
```

Common statuses:

```text
401  missing or expired session
403  missing/invalid CSRF
413  body too large
429  login rate limit
```
