# Operations and deploy

## Architecture

```text
browser
  │
  ├─ nginx container :8082
  │    ├─ compiled React app
  │    └─ /api → FastAPI :8090
  │
  └─ FastAPI
       ├─ sessions + SQLite
       ├─ nvidia-smi collector
       └─ request ingest

llm.glicc.id → gateway :8081 → llama.cpp :8084
```

The frontend is a Docker container. The API stays on the host because the Docker installation has no NVIDIA container runtime.

## Services

```bash
systemctl status glicc-frontend-api.service
systemctl status glicc-gateway.service
docker ps --filter name=gliccops-web
```

Ports:

```text
8081  gateway
8082  nginx UI
8084  llama.cpp backend
8090  FastAPI dashboard API
```

## Build UI

```bash
cd frontend
docker compose up -d --build
```

The React build runs in a multi-stage Node container. No Node modules are installed on the host.

## Update API

```bash
cd frontend
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m py_compile api/*.py app.py
systemctl restart glicc-frontend-api.service
```

## Database

```text
frontend/data/gliccops.db
```

SQLite in WAL mode.

```text
gpu_samples     telemetry history, 7-day retention
requests        gateway request records
daily_metrics   daily rollups
settings        small config values
users           Argon2id password hashes
sessions        hashed session tokens and expiry
login_attempts  login rate limiting
audit_log       authentication events
```

Backup:

```bash
sqlite3 frontend/data/gliccops.db ".backup '/tmp/gliccops-backup.db'"
```

## Logs

```bash
docker logs gliccops-web
journalctl -u glicc-frontend-api -f
journalctl -u glicc-gateway -f
```

## Health checks

```bash
curl http://127.0.0.1:8090/api/health
curl http://127.0.0.1:8081/healthz
curl https://llminferences.glicc.id/login
curl https://llm.glicc.id/v1/models \
  -H "Authorization: Bearer $GLICC_API_KEY"
```

## Troubleshooting

| Symptom | Check |
|---|---|
| 502 on dashboard | API service, nginx container |
| 401 on inference API | key revoked or wrong key |
| dashboard cards at zero | telemetry latest endpoint |
| slow history | points/minutes parameters |
| login loop | HTTPS required for Secure cookie |
