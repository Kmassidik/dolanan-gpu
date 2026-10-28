from __future__ import annotations

import sqlite3
import threading
import time
from typing import Any

from .config import DB_PATH

DB_LOCK = threading.Lock()
DB: sqlite3.Connection | None = None

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

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at INTEGER NOT NULL,
    last_login INTEGER,
    disabled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    ip TEXT,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT,
    username TEXT,
    attempted_at INTEGER NOT NULL,
    success INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip, attempted_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    user_id INTEGER,
    action TEXT NOT NULL,
    detail TEXT,
    ip TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);

PRAGMA user_version = 2;
"""


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
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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


def execute(sql: str, args: tuple = ()) -> None:
    assert DB is not None
    with DB_LOCK:
        DB.execute(sql, args)
        DB.commit()


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
            DB.execute("DELETE FROM sessions WHERE expires_at < ?", (int(time.time()),))
            DB.commit()
