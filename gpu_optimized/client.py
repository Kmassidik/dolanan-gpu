"""Minimal OpenAI-compatible client and optional SSH transport."""
from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Any, Iterator


class LlamaClient:
    def __init__(self, base_url: str, api_key: str | None, timeout: float = 300):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"server returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"cannot reach {self.base_url}: {exc.reason}") from exc

    def wait_ready(self, attempts: int = 30) -> None:
        for attempt in range(attempts):
            try:
                health = self._request("/health")
                if health.get("status") == "ok":
                    return
            except RuntimeError:
                if attempt == attempts - 1:
                    raise
            time.sleep(1)
        raise RuntimeError("server did not become ready")

    def complete(self, prompt: str, max_tokens: int) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        response = self._request("/v1/completions", {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.0,
        })
        return response, time.perf_counter() - started


@contextmanager
def ssh_tunnel(host: str, remote_port: int, local_port: int) -> Iterator[str]:
    command = [
        "ssh", "-N", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-o", "ExitOnForwardFailure=yes",
        "-L", f"{local_port}:127.0.0.1:{remote_port}", host,
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while True:
            if process.poll() is not None:
                detail = process.stderr.read().decode(errors="replace") if process.stderr else ""
                raise RuntimeError(f"SSH tunnel failed: {detail.strip()}")
            try:
                with socket.create_connection(("127.0.0.1", local_port), timeout=1):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("SSH tunnel did not open within 15 seconds")
                time.sleep(0.2)
        yield f"http://127.0.0.1:{local_port}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
