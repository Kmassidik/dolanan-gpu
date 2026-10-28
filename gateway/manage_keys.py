#!/usr/bin/env python3
"""Issue and revoke gateway API keys.

The plaintext key is printed once. Only its SHA-256 hash is stored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("GATEWAY_CONFIG", BASE / "keys.json"))


def load() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "max_queue": 8,
        "queue_timeout_s": 60,
        "generation_timeout_s": 900,
        "long_context_tokens": 131072,
        "max_long_queued": 1,
        "keys": [],
    }


def save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(CONFIG_PATH.parent), prefix=".keys.")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, CONFIG_PATH)
    os.chmod(CONFIG_PATH, 0o600)


def issue(name: str, rpm: int, admin: bool) -> None:
    data = load()
    if any(k.get("name") == name for k in data["keys"]):
        raise SystemExit(f"key '{name}' already exists")
    key = "gk_" + secrets.token_urlsafe(32)
    data["keys"].append(
        {
            "name": name,
            "sha256": hashlib.sha256(key.encode()).hexdigest(),
            "max_inflight": 1,
            "max_queued": 1,
            "rpm": rpm,
            "admin": admin,
            "enabled": True,
        }
    )
    save(data)
    print(f"name={name}")
    print(f"key={key}")
    print("store this key now; it cannot be recovered")


def revoke(name: str) -> None:
    data = load()
    before = len(data["keys"])
    data["keys"] = [k for k in data["keys"] if k.get("name") != name]
    if len(data["keys"]) == before:
        raise SystemExit(f"key '{name}' not found")
    save(data)
    print(f"revoked={name}")


def listing() -> None:
    data = load()
    for k in data["keys"]:
        print(
            f"{k.get('name')}\trpm={k.get('rpm', 60)}\t"
            f"admin={bool(k.get('admin'))}\tenabled={k.get('enabled', True)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("issue")
    p.add_argument("name")
    p.add_argument("--rpm", type=int, default=60)
    p.add_argument("--admin", action="store_true")
    p = sub.add_parser("revoke")
    p.add_argument("name")
    sub.add_parser("list")
    args = parser.parse_args()
    if args.cmd == "issue":
        issue(args.name, args.rpm, args.admin)
    elif args.cmd == "revoke":
        revoke(args.name)
    else:
        listing()


if __name__ == "__main__":
    main()
