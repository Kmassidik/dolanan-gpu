from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

BASE = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("GATEWAY_CONFIG", BASE / "keys.json"))
BACKEND = os.environ.get("GATEWAY_BACKEND", "http://127.0.0.1:8081").rstrip("/")
BACKEND_KEY_FILE = Path(
    os.environ.get("GATEWAY_BACKEND_KEY_FILE", "/root/Desktop/selfhostllm/glicc-api.token")
)

DEFAULTS = {
    "max_queue": 8,
    "queue_timeout_s": 60,
    "generation_timeout_s": 900,
    "long_context_tokens": 131072,
    "max_long_queued": 1,
    "keys": [],
}

_cfg_mtime: float = -1.0
_cfg: dict[str, Any] = dict(DEFAULTS)
_rpm: dict[str, deque[float]] = defaultdict(deque)


def config() -> dict[str, Any]:
    global _cfg, _cfg_mtime
    try:
        mtime = CONFIG_PATH.stat().st_mtime
    except FileNotFoundError:
        mtime = 0.0
    if mtime != _cfg_mtime:
        data = json.loads(CONFIG_PATH.read_text())
        merged = dict(DEFAULTS)
        merged.update(data)
        merged["keys"] = data.get("keys", [])
        _cfg = merged
        _cfg_mtime = mtime
    return _cfg


def backend_key() -> str:
    return BACKEND_KEY_FILE.read_text().strip()


def policy_for(request: Request) -> dict[str, Any]:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(
            401, "missing bearer token", headers={"WWW-Authenticate": "Bearer"}
        )
    token = header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, "empty bearer token", headers={"WWW-Authenticate": "Bearer"})
    digest = hashlib.sha256(token.encode()).hexdigest()
    for policy in config()["keys"]:
        if policy.get("enabled", True) and hmac.compare_digest(
            digest, str(policy.get("sha256", ""))
        ):
            return policy
    raise HTTPException(401, "invalid API key", headers={"WWW-Authenticate": "Bearer"})


def check_rpm(policy: dict[str, Any]) -> None:
    limit = int(policy.get("rpm", 60))
    if limit <= 0:
        return
    now = time.monotonic()
    q = _rpm[str(policy["name"])]
    while q and now - q[0] >= 60.0:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "per-key rate limit", headers={"Retry-After": "60"})
    q.append(now)


class QueueFull(Exception):
    pass


class QueueTimeout(Exception):
    pass


class Limiter:
    def __init__(self) -> None:
        self.sem = asyncio.Semaphore(1)
        self.lock = asyncio.Lock()
        self.pending: dict[str, int] = defaultdict(int)
        self.inflight: dict[str, int] = defaultdict(int)
        self.queue_depth = 0
        self.active = 0
        self.long_pending = 0
        self.long_active = 0
        self.accepted = 0
        self.rejected = 0
        self.timeouts = 0

    async def admit(self, policy: dict[str, Any], is_long: bool) -> tuple[str, bool]:
        cfg = config()
        key = str(policy["name"])
        async with self.lock:
            if self.queue_depth >= int(cfg["max_queue"]):
                self.rejected += 1
                raise QueueFull
            if self.pending[key] >= int(policy.get("max_queued", 1)):
                self.rejected += 1
                raise QueueFull
            if is_long and self.long_pending >= int(cfg["max_long_queued"]):
                self.rejected += 1
                raise QueueFull
            self.pending[key] += 1
            self.queue_depth += 1
            if is_long:
                self.long_pending += 1
        try:
            await asyncio.wait_for(
                self.sem.acquire(), timeout=float(cfg["queue_timeout_s"])
            )
        except asyncio.TimeoutError:
            async with self.lock:
                self.pending[key] -= 1
                self.queue_depth -= 1
                if is_long:
                    self.long_pending -= 1
            self.timeouts += 1
            raise QueueTimeout from None
        async with self.lock:
            self.pending[key] -= 1
            self.queue_depth -= 1
            if is_long:
                self.long_pending -= 1
            self.inflight[key] += 1
            self.active += 1
            if is_long:
                self.long_active += 1
        self.accepted += 1
        return key, is_long

    async def release(self, key: str, is_long: bool) -> None:
        async with self.lock:
            self.inflight[key] -= 1
            self.active -= 1
            if is_long:
                self.long_active -= 1
        self.sem.release()

    def snapshot(self) -> dict[str, Any]:
        return {
            "queue_depth": self.queue_depth,
            "active": self.active,
            "long_pending": self.long_pending,
            "long_active": self.long_active,
            "pending_by_key": dict(self.pending),
            "inflight_by_key": dict(self.inflight),
            "accepted": self.accepted,
            "rejected": self.rejected,
            "timeouts": self.timeouts,
        }


LIMITER = Limiter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,
            read=float(config()["generation_timeout_s"]),
            write=30.0,
            pool=5.0,
        ),
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
    )
    yield
    await app.state.client.aclose()


app = FastAPI(
    title="Glicc queue gateway",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


def estimate_tokens(body: dict[str, Any]) -> int:
    total = 0
    for message in body.get("messages") or []:
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            total += max(1, len(content) // 4)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    total += max(1, len(part["text"]) // 4)
    if isinstance(body.get("prompt"), str):
        total += max(1, len(body["prompt"]) // 4)
    total += int(body.get("max_tokens") or body.get("max_completion_tokens") or 0)
    return total


def outgoing_headers(request: Request) -> dict[str, str]:
    headers = {
        "authorization": "Bearer " + backend_key(),
        "content-type": request.headers.get("content-type", "application/json"),
        "accept": request.headers.get("accept", "application/json"),
    }
    return headers


def response_headers(resp: httpx.Response) -> dict[str, str]:
    skip = {"content-length", "transfer-encoding", "connection", "content-type"}
    return {k: v for k, v in resp.headers.items() if k.lower() not in skip}


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    snap = LIMITER.snapshot()
    return {"status": "ok", **snap}


@app.get("/metrics")
async def metrics(request: Request) -> dict[str, Any]:
    policy = policy_for(request)
    if not policy.get("admin", False):
        raise HTTPException(403, "admin key required")
    return {
        "status": "ok",
        **LIMITER.snapshot(),
        "keys": len(config()["keys"]),
        "max_queue": config()["max_queue"],
    }


@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def v1(path: str, request: Request):
    if path not in {"models", "chat/completions", "completions"}:
        raise HTTPException(404, "unknown endpoint")

    policy = policy_for(request)
    check_rpm(policy)

    raw = await request.body()
    body: dict[str, Any] = {}
    if raw:
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(400, "invalid JSON body") from None

    is_long = estimate_tokens(body) >= int(config()["long_context_tokens"])
    queued = path != "models"
    key = str(policy["name"])
    admitted = False
    if queued:
        try:
            key, is_long = await LIMITER.admit(policy, is_long)
            admitted = True
        except QueueFull:
            return JSONResponse(
                {"error": "queue full", "detail": "retry shortly"},
                status_code=429,
                headers={"Retry-After": "5"},
            )
        except QueueTimeout:
            return JSONResponse(
                {"error": "queue wait timed out"}, status_code=504
            )

    url = BACKEND + "/v1/" + path
    stream = bool(body.get("stream")) and request.method == "POST"
    client: httpx.AsyncClient = request.app.state.client
    release_needed = admitted
    try:
        if stream:
            req = client.build_request(
                "POST", url, content=raw, headers=outgoing_headers(request)
            )
            resp = await client.send(req, stream=True)
            if resp.status_code >= 400:
                payload = await resp.aread()
                await resp.aclose()
                return Response(
                    payload,
                    status_code=resp.status_code,
                    headers=response_headers(resp),
                    media_type=resp.headers.get("content-type"),
                )
            release_needed = False

            async def chunks():
                try:
                    async for chunk in resp.aiter_raw():
                        yield chunk
                finally:
                    await resp.aclose()
                    if admitted:
                        await LIMITER.release(key, is_long)

            return StreamingResponse(
                chunks(),
                status_code=resp.status_code,
                headers=response_headers(resp),
                media_type=resp.headers.get("content-type"),
            )

        resp = await client.request(
            request.method,
            url,
            content=raw if request.method == "POST" else None,
            headers=outgoing_headers(request),
            params=request.query_params,
        )
        return Response(
            resp.content,
            status_code=resp.status_code,
            headers=response_headers(resp),
            media_type=resp.headers.get("content-type"),
        )
    except httpx.TimeoutException:
        return JSONResponse({"error": "upstream timeout"}, status_code=504)
    except httpx.HTTPError:
        return JSONResponse({"error": "upstream unavailable"}, status_code=502)
    finally:
        if release_needed and admitted:
            await LIMITER.release(key, is_long)
