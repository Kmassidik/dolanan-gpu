from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
DB_PATH = Path(os.environ.get("FRONTEND_DB", DATA / "gliccops.db"))
TOKEN_FILE = Path(os.environ.get("FRONTEND_TOKEN_FILE", DATA / "ingest.token"))

FRONTEND_USER = os.environ.get("FRONTEND_USER", "admin")
FRONTEND_PASS = os.environ.get("FRONTEND_PASS", "")
COOKIE_SECURE = os.environ.get("FRONTEND_COOKIE_SECURE", "1") != "0"

SESSION_COOKIE = "glicc_session"
CSRF_COOKIE = "glicc_csrf"
SESSION_IDLE_SECONDS = 12 * 3600
SESSION_ABSOLUTE_SECONDS = 7 * 86400
LOGIN_WINDOW_SECONDS = 900
LOGIN_MAX_FAILURES = 5
MAX_INGEST_BYTES = 64 * 1024
