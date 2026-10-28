from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from . import db
from .config import (
    COOKIE_SECURE,
    CSRF_COOKIE,
    FRONTEND_PASS,
    FRONTEND_USER,
    LOGIN_MAX_FAILURES,
    LOGIN_WINDOW_SECONDS,
    SESSION_ABSOLUTE_SECONDS,
    SESSION_COOKIE,
    SESSION_IDLE_SECONDS,
)

PH = PasswordHasher()
router = APIRouter(prefix="/api/auth")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def client_ip(request: Request) -> str:
    return (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )


def audit(user_id: int | None, action: str, detail: str, ip: str) -> None:
    db.execute(
        "INSERT INTO audit_log (ts,user_id,action,detail,ip) VALUES (?,?,?,?,?)",
        (int(time.time()), user_id, action, detail[:500], ip),
    )


def ensure_seed_user() -> None:
    if db.one("SELECT COUNT(*) AS n FROM users").get("n", 0):
        return
    if not FRONTEND_PASS:
        raise RuntimeError("FRONTEND_PASS is required to seed the first user")
    db.execute(
        "INSERT INTO users (username,password_hash,role,created_at) VALUES (?,?,?,?)",
        (FRONTEND_USER, PH.hash(FRONTEND_PASS), "admin", int(time.time())),
    )


def set_cookies(response: Response, token: str, csrf: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_ABSOLUTE_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=SESSION_ABSOLUTE_SECONDS,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def create_session(user_id: int, request: Request) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    now = int(time.time())
    db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
    db.execute(
        """
        INSERT INTO sessions
        (token_hash,user_id,created_at,expires_at,last_seen,ip,user_agent)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            token_hash(token),
            user_id,
            now,
            now + SESSION_ABSOLUTE_SECONDS,
            now,
            client_ip(request),
            request.headers.get("user-agent", "")[:300],
        ),
    )
    return token, csrf


def session_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    now = int(time.time())
    user = db.one(
        """
        SELECT u.id,u.username,u.role,u.disabled,s.token_hash,s.last_seen,s.expires_at
        FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token_hash=?
        """,
        (token_hash(token),),
    )
    if not user or user["disabled"] or user["expires_at"] <= now:
        return None
    if now - int(user["last_seen"]) > SESSION_IDLE_SECONDS:
        return None
    db.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (now, user["token_hash"]))
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(403, "invalid CSRF token")


@router.post("/login")
async def login(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid JSON") from None
    username = str(body.get("username", ""))[:128]
    password = str(body.get("password", ""))
    ip = client_ip(request)
    now = int(time.time())
    failures = db.one(
        "SELECT COUNT(*) AS n FROM login_attempts WHERE ip=? AND attempted_at>=? AND success=0",
        (ip, now - LOGIN_WINDOW_SECONDS),
    ).get("n", 0)
    if int(failures) >= LOGIN_MAX_FAILURES:
        return JSONResponse({"error": "Too many attempts. Try again later."}, status_code=429)
    user = db.one("SELECT * FROM users WHERE username=? AND disabled=0", (username,))
    ok = False
    if user:
        try:
            ok = PH.verify(user["password_hash"], password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            ok = False
    db.execute(
        "INSERT INTO login_attempts (ip,username,attempted_at,success) VALUES (?,?,?,?)",
        (ip, username, now, 1 if ok else 0),
    )
    if not ok:
        audit(None, "login_failed", username, ip)
        return JSONResponse({"error": "Invalid username or password."}, status_code=401)
    token, csrf = create_session(int(user["id"]), request)
    db.execute("UPDATE users SET last_login=? WHERE id=?", (now, user["id"]))
    audit(int(user["id"]), "login", username, ip)
    response = JSONResponse(
        {"user": {"username": user["username"], "role": user["role"]}, "csrf": csrf}
    )
    set_cookies(response, token, csrf)
    return response


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    require_csrf(request)
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


@router.get("/session")
def auth_session(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "authentication required")
    return {"user": user}
