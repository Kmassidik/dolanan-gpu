import { useEffect, useState } from "react";
import { GpuCard } from "../components/GpuCard";
import { RequestsTable } from "../components/RequestsTable";
import { StatCard } from "../components/StatCard";
import { ThroughputChart } from "../components/ThroughputChart";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import type { Gpu, HistorySample, RequestRow, Summary, Telemetry } from "../types";

const zeroSummary: Summary = {
  requests: 0,
  tokens: 0,
  rate_limited: 0,
  avg_ttft_ms: null,
  latest_trace: null,
};

function signedOut(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    window.location.assign("/login");
    return true;
  }
  return false;
}

function compact(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return value.toString();
}

export function Dashboard() {
  const { user, logout } = useAuth();
  const [gpus, setGpus] = useState<Gpu[]>([]);
  const [history, setHistory] = useState<HistorySample[]>([]);
  const [summary, setSummary] = useState<Summary>(zeroSummary);
  const [requests, setRequests] = useState<RequestRow[]>([]);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const [latest, hist, sum, recent] = await Promise.all([
          api<Telemetry>("/api/telemetry/latest"),
          api<{ samples: HistorySample[] }>("/api/telemetry/history?minutes=60"),
          api<Summary>("/api/summary"),
          api<{ requests: RequestRow[] }>("/api/requests/recent?limit=8"),
        ]);
        if (!alive) return;
        setGpus(latest.gpus);
        setHistory(hist.samples);
        setSummary(sum);
        setRequests(recent.requests);
        setUpdated(latest.ts * 1000);
        setError("");
      } catch (err) {
        if (!signedOut(err) && alive) setError("Live telemetry unavailable.");
      }
    }
    load();
    const fast = window.setInterval(load, 3000);
    const slow = window.setInterval(load, 15000);
    return () => {
      alive = false;
      window.clearInterval(fast);
      window.clearInterval(slow);
    };
  }, []);

  const used = gpus.reduce((sum, gpu) => sum + (gpu.vram_used_mib ?? 0), 0);
  const capacity = gpus.reduce((sum, gpu) => sum + (gpu.vram_total_mib ?? 0), 0);
  const util = gpus.length
    ? gpus.reduce((sum, gpu) => sum + (gpu.util_pct ?? 0), 0) / gpus.length
    : 0;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>gliccOps</span>
        </div>
        <div className="topbar-actions">
          <span className="live"><i /> {updated ? "live" : "connecting"}</span>
          <span className="user">{user?.username}</span>
          <button className="ghost" onClick={() => void logout()}>Sign out</button>
        </div>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">Self-hosted inference</p>
            <h1>Command Center</h1>
            <p className="muted">
              RTX 3060 Ti × 3 · Qwen3.8 MoE · {updated ? `updated ${new Date(updated).toLocaleTimeString()}` : "waiting for telemetry"}
            </p>
          </div>
          <span className={`fleet-state ${error ? "bad" : ""}`}>{error || "healthy"}</span>
        </section>

        <section className="stats">
          <StatCard label="Requests" value={compact(summary.requests)} note="last 30 days" />
          <StatCard label="Tokens" value={compact(summary.tokens)} note="completion tokens" />
          <StatCard label="Rate limited" value={compact(summary.rate_limited)} note="gateway rejections" />
          <StatCard
            label="Avg TTFT"
            value={summary.avg_ttft_ms == null ? "—" : `${summary.avg_ttft_ms.toFixed(0)} ms`}
            note="prompt latency"
          />
        </section>

        <section className="split">
          <div className="panel">
            <div className="panel-head">
              <h2>Compute fleet</h2>
              <span className="muted">{gpus.length} nodes</span>
            </div>
            <div className="fleet-summary">
              <div><strong>{(used / 1024).toFixed(1)}</strong><span>GiB VRAM</span></div>
              <div><strong>{util.toFixed(0)}%</strong><span>utilization</span></div>
              <div><strong>{(capacity / 1024).toFixed(0)}</strong><span>GiB total</span></div>
            </div>
            <div className="gpu-grid">
              {gpus.map((gpu) => <GpuCard key={gpu.gpu_index} gpu={gpu} />)}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h2>GPU 0 — last hour</h2>
              <span className="muted">temperature / utilization</span>
            </div>
            <ThroughputChart history={history} />
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Latest requests</h2>
            <span className="muted">gateway → SQLite</span>
          </div>
          <RequestsTable requests={requests} />
        </section>
      </main>
    </div>
  );
}
