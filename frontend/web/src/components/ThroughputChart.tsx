import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistorySample } from "../types";

export function ThroughputChart({ history }: { history: HistorySample[] }) {
  const points = history
    .filter((sample) => sample.gpu_index === 0)
    .map((sample) => ({
      time: new Date(sample.ts * 1000).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      temp: sample.temp_c ?? 0,
      util: sample.util_pct ?? 0,
    }));

  if (!points.length) {
    return <p className="empty">Collecting telemetry history…</p>;
  }

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={230}>
        <AreaChart data={points} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="tempFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e6edf3" vertical={false} />
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748b" }} minTickGap={40} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748b" }} />
          <Tooltip
            contentStyle={{ borderRadius: 10, border: "1px solid #dbe3ee", fontSize: 12 }}
            labelStyle={{ color: "#334155" }}
          />
          <Area type="monotone" dataKey="temp" name="GPU 0 °C" stroke="#10b981" strokeWidth={2} fill="url(#tempFill)" />
          <Area type="monotone" dataKey="util" name="GPU 0 util %" stroke="#64748b" strokeWidth={1.5} fillOpacity={0} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
