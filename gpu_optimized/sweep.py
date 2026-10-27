"""Run isolated llama-server configurations and retain every measurement."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .client import LlamaClient
from .core import Sample
from .workloads import select


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def wait_server(client: LlamaClient, process: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not ready"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited with code {process.returncode}")
        try:
            health = client._request("/health")
            if health.get("status") == "ok":
                return
            last_error = str(health)
        except RuntimeError as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"server readiness timeout: {last_error}")


def server_command(plan: dict[str, Any], variant: dict[str, Any]) -> list[str]:
    command = [plan["binary"], "-m", plan["model"]]
    if plan.get("mmproj"):
        command += ["--mmproj", plan["mmproj"]]
    command += plan.get("base_args", []) + variant.get("args", [])
    command += ["--host", "127.0.0.1", "--port", str(plan.get("port", 8081))]
    api_key = os.environ.get("LLAMA_API_KEY")
    if api_key:
        command += ["--api-key", api_key]
    return command


def run_variant(
    plan: dict[str, Any], variant: dict[str, Any], runs: int, log_dir: Path
) -> dict[str, Any]:
    name = variant["name"]
    result: dict[str, Any] = {
        "name": name,
        "args": variant.get("args", []),
        "samples": [],
        "error": None,
    }
    log_path = log_dir / f"{name}.server.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(
            server_command(plan, variant),
            cwd=plan["workdir"],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            client = LlamaClient(
                f"http://127.0.0.1:{plan.get('port', 8081)}",
                os.environ.get("LLAMA_API_KEY"),
                timeout=plan.get("request_timeout", 300),
            )
            wait_server(client, process, plan.get("startup_timeout", 180))
            for workload in select(plan.get("workload", "all")):
                for run in range(1, runs + 1):
                    response, elapsed = client.complete(
                        workload.prompt, plan.get("max_tokens") or workload.max_tokens
                    )
                    sample = Sample.from_response(workload.name, run, response, elapsed)
                    result["samples"].append(sample.to_dict())
        except (RuntimeError, OSError) as exc:
            result["error"] = f"{exc}; see {log_path}"
        finally:
            stop_process(process)
    return result


def print_result(result: dict[str, Any]) -> None:
    print(f"\n=== {result['name']} ===")
    if result["error"]:
        print(f"FAILED: {result['error']}")
        return
    samples = [Sample.from_dict(row) for row in result["samples"]]
    from .cli import print_summaries
    print_summaries(samples)


def run_plan(args: argparse.Namespace) -> None:
    plan = json.loads(args.plan.read_text())
    if args.replace_existing:
        subprocess.run(["pkill", "-9", "llama-server"], check=False)
        time.sleep(2)
    output = args.output or args.plan.with_suffix(".results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for variant in plan["variants"]:
        result = run_variant(plan, variant, args.runs or plan.get("runs", 2), output.parent)
        results.append(result)
        print_result(result)
        payload = {
            "schema": "sweep-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "plan": str(args.plan),
            "variants": results,
        }
        output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {output}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python3 -m gpu_optimized.sweep")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs", type=int)
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args(argv)
    if args.runs is not None and args.runs < 1:
        raise SystemExit("error: --runs must be at least 1")
    try:
        run_plan(args)
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
