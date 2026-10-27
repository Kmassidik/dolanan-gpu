# Context and memory-tier experiments

Target: 256,000-token context with the same Heretic Qwen36-35B Q3_K_M model and native MTP3. The box has 3×8GB VRAM and 125GB host RAM. All variants use Q4 target and draft KV with `ub256`.

## 250K memory architecture results

Two runs per configuration.

| Configuration | Chat decode | Document decode | Result |
|---|---:|---:|---|
| GPU KV only | — | — | OOM |
| 1 MoE layer in RAM | **74.6** | **91.0** | Works |
| 2 MoE layers in RAM | 75.0 | 77.6 | Works |
| 4 MoE layers in RAM | 62.7 | 71.7 | Works |
| 8 MoE layers in RAM | 49.8 | 57.7 | Works |
| 16 MoE layers in RAM | 49.7 | 54.8 | Works |
| All KV in RAM | — | — | Failed |
| All KV + 1 MoE layer in RAM | — | — | Failed |

The useful architecture is to keep KV on the GPUs and offload only one MoE layer to host RAM. This frees enough VRAM for 250K while limiting CPU work. More offloaded MoE layers generally reduce throughput. Full KV offload did not provide a working alternative.

## CPU threads for the one-layer RAM tier

Three runs per configuration.

| CPU threads | Chat decode | Document decode |
|---:|---:|---:|
| 8 | 72.7 | 89.2 |
| 12 | 75.2 | 92.5 |
| **16** | **76.8** | **93.6** |
| 24 | 76.4 | 92.9 |
| 32 | 69.9 | 85.2 |

Sixteen threads is the best tested setting. `scripts/serve.sh long` uses 250K context, one RAM-backed MoE layer, Q4 target/draft KV, and 16 CPU threads.

The tradeoff against 64K MTP3/Q4 is approximately 28% lower chat throughput and 20% lower document throughput. The result is a real 256,000-token context, not a claim that RAM offload is free.
