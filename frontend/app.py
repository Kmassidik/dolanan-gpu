from __future__ import annotations

import base64
import hmac
import json
import os
import sqlite3
import subprocess
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
PUBLIC = BASE / "public"
DATA = BASE / "data"
DB_PATH = Path(os.environ.get("FRONTEND_DB", DATA / "gliccops.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TOKEN_FILE = Path(
    os.environ.get("FRONTEND_TOKEN_FILE", DATA / "ingest.token")
)
MAX_INGEST_BYTES = 64 * 1024
FRONTEND_USER = os.environ.get("FRONTEND_USER", "admin")
FRONTEND_PASS = os.environ.get("FRONTEND_PASS", "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS gpu_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    gpu_index INTEGER NOT NULL,
    temp_c REAL,
    power_w REAL,
    clock_mhz REAL,
    util_pct REAL,
    vram_used_mib INTEGER,
    vram_total_mib INTEGER,
    fan_pct REAL,
    pcie_gbs REAL
);
CREATE INDEX IF NOT EXISTS idx_gpu_samples_ts ON gpu_samples(ts);
CREATE INDEX IF NOT EXISTS idx_gpu_samples_gpu_ts ON gpu_samples(gpu_index, ts);

CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    ttft_ms REAL,
    decode_tps REAL,
    api_key_name TEXT,
    created_at INTEGER NOT NULL,
    finished_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_requests_created ON requests(created_at);

CREATE TABLE IF NOT EXISTS daily_metrics (
    day TEXT PRIMARY KEY,
    requests INTEGER NOT NULL DEFAULT 0,
    tokens INTEGER NOT NULL DEFAULT 0,
    rate_limited INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
PRAGMA user_version = 1;
"""

DB_LOCK = threading.Lock()
DB: sqlite3.Connection | None = None
LATEST: list[dict[str, Any]] = []
LATEST_TS = 0


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    global DB
    DB = connect()
    with DB_LOCK:
        DB.executescript(SCHEMA)
        DB.commit()


def rows(sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    assert DB is not None
    with DB_LOCK:
        return [dict(r) for r in DB.execute(sql, args).fetchall()]


def one(sql: str, args: tuple = ()) -> dict[str, Any]:
    assert DB is not None
    with DB_LOCK:
        row = DB.execute(sql, args).fetchone()
        return dict(row) if row else {}


def insert_samples(samples: list[dict[str, Any]]) -> None:
    assert DB is not None
    with DB_LOCK:
        DB.executemany(
            """
            INSERT INTO gpu_samples
            (ts,gpu_index,temp_c,power_w,clock_mhz,util_pct,vram_used_mib,vram_total_mib,fan_pct,pcie_gbs)
            VALUES (:ts,:gpu_index,:temp_c,:power_w,:clock_mhz,:util_pct,:vram_used_mib,:vram_total_mib,:fan_pct,:pcie_gbs)
            """,
            samples,
        )
        DB.commit()
        if int(time.time()) % 300 < 2:
            DB.execute("DELETE FROM gpu_samples WHERE ts < ?", (int(time.time()) - 7 * 86400,))
            DB.commit()


def read_gpu() -> list[dict[str, Any]]:
    out = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=index,temperature.gpu,power.draw,clocks.sm,utilization.gpu,memory.used,memory.total,fan.speed",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        timeout=5,
    )
    ts = int(time.time())
    samples = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 8:
            continue
        idx, temp, power, clock, util, used, total, fan = parts

        def num(value: str) -> float | None:
            try:
                return float(value)
            except ValueError:
                return None

        fan_pct = num(fan)
        samples.append(
            {
                "ts": ts,
                "gpu_index": int(idx),
                "temp_c": num(temp),
                "power_w": num(power),
                "clock_mhz": num(clock),
                "util_pct": num(util),
                "vram_used_mib": int(float(used)) if num(used) is not None else None,
                "vram_total_mib": int(float(total)) if num(total) is not None else None,
                "fan_pct": fan_pct,
                "pcie_gbs": None,
            }
        )
    return samples


def collector(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            samples = read_gpu()
            if samples:
                insert_samples(samples)
                global LATEST, LATEST_TS
                LATEST = samples
                LATEST_TS = samples[0]["ts"]
        except Exception:
            pass
        stop.wait(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    stop = threading.Event()
    thread = threading.Thread(target=collector, args=(stop,), daemon=True)
    thread.start()
    yield
    stop.set()


app = FastAPI(title="gliccOps frontend API", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    # Gateway ingest paths authenticate with the dedicated ingest token.
    if request.url.path in {"/api/requests", "/api/requests/recent"}:
        return await call_next(request)
    if not FRONTEND_PASS:
        return JSONResponse({"error": "frontend auth not configured"}, status_code=503)
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("basic "):
        return Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="gliccOps"'},
        )
    try:
        decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
        user, password = decoded.split(":", 1)
    except Exception:
        return Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="gliccOps"'},
        )
    if hmac.compare_digest(user, FRONTEND_USER) and hmac.compare_digest(
        password, FRONTEND_PASS
    ):
        return await call_next(request)
    return Response(
        "Unauthorized",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="gliccOps"'},
    )


def require_ingest(request: Request) -> None:
    try:
        expected = TOKEN_FILE.read_text().strip()
    except OSError:
        expected = ""
    header = request.headers.get("authorization", "")
    supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(401, "ingest token required")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "latest_ts": LATEST_TS}


@app.get("/api/telemetry/latest")
def telemetry_latest() -> dict[str, Any]:
    gpus = []
    for g in LATEST:
        fan = g.get("fan_pct")
        gpus.append(
            {
                **g,
                "fan_rpm": round(fan * 25.0, 0) if fan is not None else None,
            }
        )
    return {"ts": LATEST_TS, "gpus": gpus}


@app.get("/api/telemetry/history")
def telemetry_history(minutes: int = 60) -> dict[str, Any]:
    minutes = max(1, min(minutes, 1440))
    since = int(time.time()) - minutes * 60
    data = rows(
        "SELECT ts,gpu_index,temp_c,power_w,clock_mhz,util_pct,vram_used_mib,vram_total_mib,fan_pct FROM gpu_samples WHERE ts>=? ORDER BY ts",
        (since,),
    )
    return {"minutes": minutes, "samples": data}


@app.get("/api/summary")
def summary(days: int = 30) -> dict[str, Any]:
    days = max(1, min(days, 365))
    since = int(time.time()) - days * 86400
    r = one(
        """
        SELECT COUNT(*) AS requests,
               COALESCE(SUM(completion_tokens),0) AS tokens,
               COALESCE(SUM(CASE WHEN status='rate_limited' THEN 1 ELSE 0 END),0) AS rate_limited,
               AVG(ttft_ms) AS avg_ttft_ms,
               AVG(decode_tps) AS avg_decode_tps
        FROM requests WHERE created_at>=?
        """,
        (since,),
    )
    trace = one(
        "SELECT request_id,model,status,prompt_tokens,completion_tokens,ttft_ms,decode_tps,created_at FROM requests ORDER BY created_at DESC LIMIT 1"
    )
    return {"days": days, **r, "latest_trace": trace or None}


@app.get("/api/requests/recent")
def requests_recent(request: Request, limit: int = 20) -> dict[str, Any]:
    require_ingest(request)
    limit = max(1, min(limit, 100))
    return {"requests": rows("SELECT * FROM requests ORDER BY created_at DESC LIMIT ?", (limit,))}


@app.post("/api/requests")
async def record_request(request: Request) -> JSONResponse:
    require_ingest(request)
    try:
        length = int(request.headers.get("content-length") or 0)
    except ValueError:
        raise HTTPException(400, "invalid content-length") from None
    if length > MAX_INGEST_BYTES:
        raise HTTPException(413, "request record too large")
    raw = await request.body()
    if len(raw) > MAX_INGEST_BYTES:
        raise HTTPException(413, "request record too large")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid JSON") from None
    if not isinstance(body, dict):
        raise HTTPException(400, "object required")
    now = int(time.time())
    request_id = str(body.get("request_id") or f"req-{now}-{time.time_ns()}")[:128]
    try:
        prompt_tokens = max(0, int(body.get("prompt_tokens", 0)))
        completion_tokens = max(0, int(body.get("completion_tokens", 0)))
        created_at = int(body.get("created_at", now))
        finished_at = body.get("finished_at")
        finished_at = int(finished_at) if finished_at is not None else None
        ttft_ms = body.get("ttft_ms")
        ttft_ms = float(ttft_ms) if ttft_ms is not None else None
        decode_tps = body.get("decode_tps")
        decode_tps = float(decode_tps) if decode_tps is not None else None
    except (TypeError, ValueError):
        raise HTTPException(400, "invalid numeric field") from None
    if not (0 <= created_at <= now + 300):
        raise HTTPException(400, "invalid created_at")
    assert DB is not None
    with DB_LOCK:
        DB.execute(
            """
            INSERT OR REPLACE INTO requests
            (request_id,model,status,prompt_tokens,completion_tokens,ttft_ms,decode_tps,api_key_name,created_at,finished_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                request_id,
                str(body.get("model") or "")[:128],
                str(body.get("status") or "completed")[:32],
                prompt_tokens,
                completion_tokens,
                ttft_ms,
                decode_tps,
                str(body.get("api_key_name") or "")[:64],
                created_at,
                finished_at,
            ),
        )
        DB.commit()
    return JSONResponse({"ok": True, "request_id": request_id}, status_code=201)


app.mount("/", StaticFiles(directory=str(PUBLIC), html=True), name="static")
