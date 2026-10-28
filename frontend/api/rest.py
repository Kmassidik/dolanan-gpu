from __future__ import annotations

import hmac
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import db
from .config import MAX_INGEST_BYTES, TOKEN_FILE

router = APIRouter(prefix="/api")


def require_ingest(request: Request) -> None:
    try:
        expected = TOKEN_FILE.read_text().strip()
    except OSError:
        expected = ""
    header = request.headers.get("authorization", "")
    supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(401, "ingest token required")


@router.get("/summary")
def summary(days: int = 30) -> dict[str, Any]:
    days = max(1, min(days, 365))
    since = int(time.time()) - days * 86400
    result = db.one(
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
    trace = db.one(
        "SELECT request_id,model,status,prompt_tokens,completion_tokens,ttft_ms,decode_tps,created_at FROM requests ORDER BY created_at DESC LIMIT 1"
    )
    return {"days": days, **result, "latest_trace": trace or None}


@router.get("/requests/recent")
def requests_recent(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    return {"requests": db.rows("SELECT * FROM requests ORDER BY created_at DESC LIMIT ?", (limit,))}


@router.post("/requests")
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
    db.execute(
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
    return JSONResponse({"ok": True, "request_id": request_id}, status_code=201)
