"""Measured samples and deterministic summaries."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any, Iterable


@dataclass(frozen=True)
class Sample:
    workload: str
    run: int
    completion_tokens: int
    wall_seconds: float
    wall_tps: float
    decode_tps: float
    prefill_tps: float
    prompt_tokens: int
    cached_prompt_tokens: int
    draft_tokens: int
    accepted_draft_tokens: int

    @classmethod
    def from_response(
        cls, workload: str, run: int, response: dict[str, Any], wall_seconds: float
    ) -> "Sample":
        usage = response.get("usage") or {}
        timings = response.get("timings") or {}
        completed = int(usage.get("completion_tokens") or timings.get("predicted_n") or 0)
        if completed <= 0:
            raise RuntimeError("server returned no completion tokens")
        decode = float(timings.get("predicted_per_second") or 0.0)
        if decode <= 0:
            raise RuntimeError("server response lacks timings.predicted_per_second")
        return cls(
            workload=workload,
            run=run,
            completion_tokens=completed,
            wall_seconds=wall_seconds,
            wall_tps=completed / wall_seconds,
            decode_tps=decode,
            prefill_tps=float(timings.get("prompt_per_second") or 0.0),
            prompt_tokens=int(timings.get("prompt_n") or usage.get("prompt_tokens") or 0),
            cached_prompt_tokens=int(timings.get("cache_n") or 0),
            draft_tokens=int(timings.get("draft_n") or 0),
            accepted_draft_tokens=int(timings.get("draft_n_accepted") or 0),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Sample":
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Summary:
    workload: str
    samples: int
    decode_tps: float
    prefill_tps: float
    wall_tps: float
    acceptance: float | None


def summarize(samples: Iterable[Sample]) -> list[Summary]:
    groups: dict[str, list[Sample]] = {}
    for sample in samples:
        groups.setdefault(sample.workload, []).append(sample)
    result = []
    for workload, rows in groups.items():
        drafted = sum(row.draft_tokens for row in rows)
        accepted = sum(row.accepted_draft_tokens for row in rows)
        result.append(Summary(
            workload=workload,
            samples=len(rows),
            decode_tps=median(row.decode_tps for row in rows),
            prefill_tps=median(row.prefill_tps for row in rows),
            wall_tps=median(row.wall_tps for row in rows),
            acceptance=(accepted / drafted) if drafted else None,
        ))
    return sorted(result, key=lambda row: row.workload)


def read_samples(text: str) -> list[Sample]:
    import json
    payload = json.loads(text)
    if not isinstance(payload, dict) or not isinstance(payload.get("samples"), list):
        raise RuntimeError("result file must contain a samples list")
    return [Sample.from_dict(row) for row in payload["samples"]]
