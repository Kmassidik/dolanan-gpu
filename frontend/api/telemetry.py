from __future__ import annotations

import subprocess
import threading
import time
from typing import Any

from fastapi import APIRouter

from . import db

router = APIRouter(prefix="/api/telemetry")
LATEST: list[dict[str, Any]] = []
LATEST_TS = 0


def read_gpu() -> list[dict[str, Any]]:
    out = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=index,temperature.gpu,power.draw,clocks.sm,utilization.gpu,memory.used,memory.total,fan.speed",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        timeout=5,
    )
    ts = int(time.time())
    samples = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 8:
            continue
        idx, temp, power, clock, util, used, total, fan = parts

        def num(value: str) -> float | None:
            try:
                return float(value)
            except ValueError:
                return None

        samples.append(
            {
                "ts": ts,
                "gpu_index": int(idx),
                "temp_c": num(temp),
                "power_w": num(power),
                "clock_mhz": num(clock),
                "util_pct": num(util),
                "vram_used_mib": int(float(used)) if num(used) is not None else None,
                "vram_total_mib": int(float(total)) if num(total) is not None else None,
                "fan_pct": num(fan),
                "pcie_gbs": None,
            }
        )
    return samples


def collector(stop: threading.Event) -> None:
    global LATEST, LATEST_TS
    while not stop.is_set():
        try:
            samples = read_gpu()
            if samples:
                db.insert_samples(samples)
                LATEST = samples
                LATEST_TS = samples[0]["ts"]
        except Exception:
            pass
        stop.wait(2.0)


@router.get("/latest")
def latest() -> dict[str, Any]:
    gpus = []
    for g in LATEST:
        fan = g.get("fan_pct")
        gpus.append({**g, "fan_rpm": round(fan * 25.0, 0) if fan is not None else None})
    return {"ts": LATEST_TS, "gpus": gpus}


@router.get("/history")
def history(minutes: int = 60, gpu: int = 0, points: int = 60) -> dict[str, Any]:
    minutes = max(1, min(minutes, 1440))
    points = max(1, min(points, 240))
    since = int(time.time()) - minutes * 60
    bucket = max(1, (minutes * 60) // points)
    data = db.rows(
        """
        SELECT CAST(ts / ? AS INTEGER) * ? AS ts,
               gpu_index,
               AVG(temp_c) AS temp_c,
               AVG(power_w) AS power_w,
               AVG(clock_mhz) AS clock_mhz,
               AVG(util_pct) AS util_pct,
               AVG(vram_used_mib) AS vram_used_mib,
               AVG(fan_pct) AS fan_pct
        FROM gpu_samples
        WHERE ts>=? AND gpu_index=?
        GROUP BY CAST(ts / ? AS INTEGER)
        ORDER BY ts
        """,
        (bucket, bucket, since, gpu, bucket),
    )
    return {"minutes": minutes, "gpu": gpu, "bucket_seconds": bucket, "samples": data}
