export type Gpu = {
  gpu_index: number;
  temp_c: number | null;
  power_w: number | null;
  clock_mhz: number | null;
  util_pct: number | null;
  vram_used_mib: number | null;
  vram_total_mib: number | null;
  fan_rpm: number | null;
};

export type Telemetry = { ts: number; gpus: Gpu[] };

export type HistorySample = {
  ts: number;
  gpu_index: number;
  temp_c: number | null;
  util_pct: number | null;
  vram_used_mib: number | null;
};

export type Summary = {
  requests: number;
  tokens: number;
  rate_limited: number;
  avg_ttft_ms: number | null;
  latest_trace: RequestRow | null;
};

export type RequestRow = {
  request_id: string;
  model: string | null;
  status: string;
  prompt_tokens: number;
  completion_tokens: number;
  ttft_ms: number | null;
  decode_tps: number | null;
  created_at: number;
};
