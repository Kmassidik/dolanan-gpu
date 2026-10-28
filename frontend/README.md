# gliccOps

Self-hosted inference command center for the three-GPU Qwen3.8 deployment.

```text
https://llminferences.glicc.id
```

## Architecture

```text
Browser
  │
  ├─ Docker nginx :8082
  │    ├─ /            compiled React app
  │    ├─ /icons/*     icon assets
  │    └─ /api/*       proxy to FastAPI
  │
  └─ FastAPI :8090 (host)
       ├─ session auth + CSRF
       ├─ SQLite
       ├─ nvidia-smi collector
       └─ request ingest
```

The UI runs in Docker. The API stays on the host because this Docker install has no NVIDIA container runtime; the collector needs `nvidia-smi` and the GPUs.

## Layout

```text
frontend/
  api/
    config.py       env + constants
    db.py           SQLite schema and helpers
    auth.py         login, sessions, CSRF, rate limit
    telemetry.py    nvidia-smi collector + history
    rest.py         summary, requests, ingest
    main.py         app assembly + security headers
  web/
    src/            React + TypeScript
    public/icons/   transparent icon set
    dist/           local build output, gitignored
  Dockerfile        node build → nginx runtime
  docker-compose.yml
  nginx.conf
  glicc-frontend-api.service
  requirements.txt
  data/             SQLite + ingest token, gitignored
```

## Services

```bash
systemctl status glicc-frontend-api.service
docker ps --filter name=gliccops-web
```

Ports:

```text
127.0.0.1:8082  nginx container
127.0.0.1:8090  FastAPI
```

## Build and deploy

UI:

```bash
cd /root/Desktop/gpu-optimized/frontend
docker compose up -d --build
```

API:

```bash
cd /root/Desktop/gpu-optimized/frontend
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m py_compile api/*.py app.py
systemctl restart glicc-frontend-api.service
```

Do not install Node modules on the host. Docker builds the React app.

## Authentication

- Argon2id password hashes
- server-side sessions in SQLite
- `HttpOnly`, `Secure`, `SameSite=Lax` session cookie
- CSRF double-submit token for state-changing requests
- 5 failed logins per IP / 15 minutes

Routes:

```text
POST /api/auth/login
POST /api/auth/logout   requires X-CSRF-Token
GET  /api/auth/session
```

Credentials are configured in `/etc/glicc-frontend.env`:

```text
FRONTEND_USER
FRONTEND_PASS
FRONTEND_DB
FRONTEND_TOKEN_FILE
```

The file is mode `600`. Change the password there and restart the API; the existing Argon2 hash remains until the seeded user is recreated. User management is intentionally not exposed over HTTP.

## Database

```text
data/gliccops.db
```

SQLite, WAL mode.

```text
gpu_samples     telemetry history, 7-day retention
requests        gateway request records
daily_metrics   daily rollups
settings        small config values
users           Argon2id password hashes
sessions        hashed session tokens + expiry
login_attempts  login rate limiting
audit_log       login/logout events
```

Backup:

```bash
sqlite3 data/gliccops.db ".backup '/root/gliccops-backup.db'"
```

## API

See [docs/API.md](docs/API.md).

## Security

- No API docs exposed publicly.
- CSP, frame denial, nosniff, referrer policy.
- Ingest endpoint uses a separate random token, not a session.
- Request bodies are size-limited.
- SQL is parameterized.
- No CDN scripts in the UI build.

## Icons

Transparent PNG and WebP assets live in:

```text
web/public/icons/
```

Favicon:

```text
web/public/icons/gpu.png
```

Icon size is controlled in `web/src/styles.css`:

```css
.stat-icon { width: 28px; height: 28px; }
.gpu-icon  { width: 34px; height: 34px; }
.brand-icon{ width: 36px; height: 36px; }
```

## Troubleshooting

| Symptom | Check |
|---|---|
| 502 from hostname | `curl http://127.0.0.1:8090/api/health`, `docker ps` |
| 401 everywhere | session cookie / login |
| telemetry stale | `systemctl status glicc-frontend-api`, `nvidia-smi` |
| Docker build fails | `docker compose build`, check node build log |
| login loop | cookie Secure requires HTTPS; use the public hostname |
