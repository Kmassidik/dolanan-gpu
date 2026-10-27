# Context and memory-tier experiments

Target: 256,000-token context with the same Heretic Qwen36-35B Q3_K_M model and native MTP3. The box has 3×8GB VRAM and 125GB host RAM. All variants use Q4 target and draft KV with `ub256`.

## Selective KV tier (best)

The custom `0005-selective-kv-tier.patch` keeps selected full-attention layers' KV in host RAM while the rest remain in VRAM. This preserves GPU compute for weights and avoids running an entire MoE layer on the CPU.

Two runs per configuration at 256,000 context.

| KV layers in RAM | Chat decode | Document decode | Result |
|---|---:|---:|---|
| 1 layer | — | — | OOM |
| 2 layers | 99.8 | 111.9 | Works |
| **3 layers** | **100.3** | **112.5** | Works, best |
| 4 layers | 98.9 | 108.7 | Works |

This is approximately 5% below 64K chat speed while providing four times the context. It is substantially faster than moving a whole MoE layer to RAM.

## Long-context correctness

`python3 -m gpu_optimized.context_check --target-tokens 70000` inserts a hidden numeric code near the start of a large prompt, asks for it at the end, and fails unless the exact code is returned.

Verified with the three-layer KV tier:

- tokenized and processed prompt: **73,378 tokens**
- prefill: **1,433 tok/s**
- wall time: **52.7 s**
- response contained the correct secret code: **739214**

This confirms a real prompt beyond 64K, not merely a successfully allocated context.

## Whole-layer MoE RAM tier (superseded)

Two runs per configuration.

| Configuration | Chat decode | Document decode | Result |
|---|---:|---:|---|
| GPU KV only | — | — | OOM |
| 1 MoE layer in RAM | 74.6 | 91.0 | Works |
| 2 MoE layers in RAM | 75.0 | 77.6 | Works |
| 4 MoE layers in RAM | 62.7 | 71.7 | Works |
| 8 MoE layers in RAM | 49.8 | 57.7 | Works |
| 16 MoE layers in RAM | 49.7 | 54.8 | Works |
| All KV in RAM | — | — | Failed |
| All KV + 1 MoE layer in RAM | — | — | Failed |

## CPU threads for the MoE tier

Three runs per configuration. The MoE tier is retained for history but superseded by the selective KV tier.

| CPU threads | Chat decode | Document decode |
|---:|---:|---:|
| 8 | 72.7 | 89.2 |
| 12 | 75.2 | 92.5 |
| 16 | 76.8 | 93.6 |
| 24 | 76.4 | 92.9 |
| 32 | 69.9 | 85.2 |

`scripts/serve.sh long` now uses the faster selective KV tier: 250K context, MTP3, Q4 target/draft KV, and KV layers `3,7,11` in host RAM.
