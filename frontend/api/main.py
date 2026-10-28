from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import db, telemetry
from .auth import ensure_seed_user, router as auth_router, session_user
from .rest import router as rest_router
from .telemetry import router as telemetry_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    ensure_seed_user()
    stop = threading.Event()
    thread = threading.Thread(target=telemetry.collector, args=(stop,), daemon=True)
    thread.start()
    yield
    stop.set()


app = FastAPI(title="gliccOps API", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def security_and_session(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in {
        "/api/auth/login",
        "/api/health",
        "/api/requests",
    }:
        user = session_user(request)
        if not user:
            return JSONResponse({"error": "authentication required"}, status_code=401)
        request.state.user = user
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'",
    )
    return response


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "latest_ts": telemetry.LATEST_TS}


app.include_router(auth_router)
app.include_router(telemetry_router)
app.include_router(rest_router)
