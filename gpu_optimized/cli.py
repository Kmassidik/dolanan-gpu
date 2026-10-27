"""Command-line interface for reproducible llama.cpp measurements."""
from __future__ import annotations

import argparse
import json
import os
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .client import LlamaClient, ssh_tunnel
from .core import Sample, read_samples, summarize
from .workloads import select


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="gpu-optimized")
    commands = root.add_subparsers(dest="command", required=True)
    bench = commands.add_parser("bench", help="measure a running llama.cpp server")
    bench.add_argument("--url", default="http://127.0.0.1:8081")
    bench.add_argument("--api-key", default=os.environ.get("LLAMA_API_KEY"))
    bench.add_argument("--ssh", help="SSH host; tunnel to its localhost server")
    bench.add_argument("--remote-port", type=int, default=8081)
    bench.add_argument("--local-port", type=int, default=18081)
    bench.add_argument("--workload", choices=["all", "chat", "document"], default="all")
    bench.add_argument("--runs", type=int, default=3)
    bench.add_argument("--max-tokens", type=int, help="override each workload's token limit")
    bench.add_argument("--timeout", type=float, default=300)
    bench.add_argument("--output", type=Path, help="write raw samples as JSON")
    compare = commands.add_parser("compare", help="compare two bench JSON files")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    return root


def print_summaries(samples: Sequence[Sample]) -> None:
    print(f"{'WORKLOAD':<12} {'RUNS':>4} {'DECODE':>10} {'PREFILL':>10} {'ACCEPT':>9}")
    for row in summarize(samples):
        acceptance = f"{row.acceptance:.1%}" if row.acceptance is not None else "—"
        print(f"{row.workload:<12} {row.samples:>4} {row.decode_tps:>7.1f} t/s "
              f"{row.prefill_tps:>7.1f} t/s {acceptance:>9}")


def run_bench(args: argparse.Namespace) -> None:
    if args.runs < 1:
        raise RuntimeError("--runs must be at least 1")
    if args.max_tokens is not None and args.max_tokens < 1:
        raise RuntimeError("--max-tokens must be at least 1")
    transport = ssh_tunnel(args.ssh, args.remote_port, args.local_port) if args.ssh else nullcontext(args.url)
    with transport as url:
        client = LlamaClient(url, args.api_key, args.timeout)
        client.wait_ready()
        samples = []
        for workload in select(args.workload):
            for run in range(1, args.runs + 1):
                response, elapsed = client.complete(
                    workload.prompt, args.max_tokens or workload.max_tokens
                )
                samples.append(Sample.from_response(workload.name, run, response, elapsed))
        print_summaries(samples)
        if args.output:
            payload = {
                "schema": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "target": "ssh" if args.ssh else "direct",
                "workload_tokens": args.max_tokens,
                "samples": [sample.to_dict() for sample in samples],
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2) + "\n")
            print(f"wrote {args.output}")


def run_compare(args: argparse.Namespace) -> None:
    baseline = {row.workload: row for row in summarize(read_samples(args.baseline.read_text()))}
    candidate = {row.workload: row for row in summarize(read_samples(args.candidate.read_text()))}
    common = sorted(set(baseline) & set(candidate))
    if not common:
        raise RuntimeError("result files have no workloads in common")
    print(f"{'WORKLOAD':<12} {'BASELINE':>12} {'CANDIDATE':>12} {'CHANGE':>10}")
    for name in common:
        before, after = baseline[name].decode_tps, candidate[name].decode_tps
        change = ((after / before) - 1) * 100
        print(f"{name:<12} {before:>9.1f} t/s {after:>9.1f} t/s {change:>+9.1f}%")


def main(argv: Sequence[str] | None = None) -> None:
    args = parser().parse_args(argv)
    try:
        if args.command == "bench":
            run_bench(args)
        else:
            run_compare(args)
    except (RuntimeError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
