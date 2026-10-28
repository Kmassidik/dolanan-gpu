from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/keys")
KEYS_PATH = Path(
    os.environ.get("GATEWAY_KEYS_FILE", "/root/Desktop/gpu-optimized/gateway/keys.json")
)
DEFAULTS = {
    "max_queue": 8,
    "queue_timeout_s": 60,
    "generation_timeout_s": 900,
    "long_context_tokens": 131072,
    "max_long_queued": 1,
    "keys": [],
}


def load() -> dict[str, Any]:
    try:
        data = json.loads(KEYS_PATH.read_text())
    except (OSError, ValueError):
        data = {}
    merged = dict(DEFAULTS)
    merged.update(data)
    merged["keys"] = data.get("keys", [])
    return merged


def save(data: dict[str, Any]) -> None:
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(KEYS_PATH.parent), prefix=".keys.")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, KEYS_PATH)
    os.chmod(KEYS_PATH, 0o600)


def public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": entry.get("name"),
        "prefix": entry.get("prefix") or "gk_…",
        "rpm": entry.get("rpm", 60),
        "created_at": entry.get("created_at"),
        "enabled": entry.get("enabled", True),
        "admin": bool(entry.get("admin", False)),
    }


@router.get("")
def list_keys() -> dict[str, Any]:
    data = load()
    return {"keys": [public_entry(k) for k in data["keys"]]}


@router.post("")
def issue_key(payload: dict[str, Any]) -> JSONResponse:
    name = str(payload.get("name", "")).strip()
    if not name or len(name) > 64 or not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "name must be 1-64 letters, digits, - or _")
    try:
        rpm = int(payload.get("rpm", 60))
    except (TypeError, ValueError):
        raise HTTPException(400, "rpm must be an integer") from None
    if not 1 <= rpm <= 600:
        raise HTTPException(400, "rpm must be 1..600")
    data = load()
    if any(k.get("name") == name for k in data["keys"]):
        raise HTTPException(409, "key name already exists")
    key = "gk_" + secrets.token_urlsafe(32)
    entry = {
        "name": name,
        "prefix": key[:11],
        "sha256": hashlib.sha256(key.encode()).hexdigest(),
        "max_inflight": 1,
        "max_queued": 1,
        "rpm": rpm,
        "admin": False,
        "enabled": True,
        "created_at": int(time.time()),
    }
    data["keys"].append(entry)
    save(data)
    return JSONResponse({"key": key, "entry": public_entry(entry)}, status_code=201)


@router.delete("/{name}")
def revoke_key(name: str) -> dict[str, Any]:
    data = load()
    before = len(data["keys"])
    data["keys"] = [k for k in data["keys"] if k.get("name") != name]
    if len(data["keys"]) == before:
        raise HTTPException(404, "key not found")
    save(data)
    return {"revoked": name}
