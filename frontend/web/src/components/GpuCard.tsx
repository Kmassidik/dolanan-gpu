import type { Gpu } from "../types";

function pct(value: number | null | undefined) {
  return Math.max(0, Math.min(100, value ?? 0));
}

export function GpuCard({ gpu }: { gpu: Gpu }) {
  const used = gpu.vram_used_mib ?? 0;
  const total = gpu.vram_total_mib ?? 8192;
  const util = pct(gpu.util_pct);
  return (
    <article className="gpu-card">
      <header>
        <div className="gpu-title">
          <img className="gpu-icon" src="/icons/gpu.webp" alt="" />
          <div>
            <span className="eyebrow">GPU {gpu.gpu_index}</span>
            <h3>RTX 3060 Ti</h3>
          </div>
        </div>
        <span className={`status-dot ${util > 0 ? "hot" : ""}`} aria-label="live" />
      </header>
      <div className="gpu-metrics">
        <div>
          <span>Temp</span>
          <strong>{gpu.temp_c == null ? "—" : `${gpu.temp_c.toFixed(0)}°C`}</strong>
        </div>
        <div>
          <span>Power</span>
          <strong>{gpu.power_w == null ? "—" : `${gpu.power_w.toFixed(0)} W`}</strong>
        </div>
        <div>
          <span>Clock</span>
          <strong>{gpu.clock_mhz == null ? "—" : `${gpu.clock_mhz.toFixed(0)} MHz`}</strong>
        </div>
      </div>
      <div className="meter">
        <div className="meter-row">
          <span>Utilization</span>
          <span>{util.toFixed(0)}%</span>
        </div>
        <div className="meter-track"><span style={{ width: `${util}%` }} /></div>
      </div>
      <div className="meter">
        <div className="meter-row">
          <span>VRAM</span>
          <span>{(used / 1024).toFixed(1)} / {(total / 1024).toFixed(0)} GiB</span>
        </div>
        <div className="meter-track"><span style={{ width: `${pct((used / total) * 100)}%` }} /></div>
      </div>
    </article>
  );
}
