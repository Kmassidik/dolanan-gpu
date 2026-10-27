# Measured results

Rates are llama.cpp decode tokens per second on three RTX 3060 Ti cards with `heretic-qwen36-35b` Q3_K_M, 65,536-token context, and one request. Raw samples and server logs remain local under ignored `results/` and `plans/*.results.json` paths.

## Draft depth, `ub256`

Two runs per configuration.

| Configuration | Chat | Document | Chat acceptance | Document acceptance |
|---|---:|---:|---:|---:|
| No speculation | 80.7 | 81.2 | — | — |
| MTP2 | 99.3 | 111.6 | 76.0% | 88.0% |
| MTP4 | 93.4 | 109.2 | 54.4% | 67.9% |
| MTP8 | 80.6 | 146.1 | 38.2% | 85.1% |
| MTP12 | 66.7 | 131.4 | 25.7% | 61.9% |

## Execution tuning

Two runs per configuration.

| Configuration | Chat | Document |
|---|---:|---:|
| MTP2, `ub128` | 99.8 | 117.3 |
| MTP2, `ub512` | 99.6 | 113.2 |
| MTP2, CPU sampling | 95.1 | 105.6 |
| MTP2, `p_min=0.20` | 98.1 | 111.1 |
| MTP8, `ub128` | 81.1 | 83.8 |
| MTP8, `ub512` | 81.1 | 140.6 |
| MTP8, CPU sampling | 72.7 | 132.9 |
| MTP8, `p_min=0.20` | 77.6 | 122.5 |

Backend sampling beats CPU sampling. `p_min=0.20` did not improve either winner.

## Adaptive native MTP experiment

Three runs per configuration. The final implementation starts at depth 8, falls directly to depth 2 after acceptance below 50%, and does not grow again after reaching depth 2.

| Configuration | Chat | Document |
|---|---:|---:|
| Adaptive v1, `ub256` | 75.4 | 136.9 |
| Adaptive v2, `ub256` | 78.9 | 133.1 |
| Adaptive v3, `ub128` | 93.9 | 105.8 |
| Adaptive v3, `ub256` | 94.4 | 112.6 |
| Adaptive v3, `ub512` | 94.0 | 114.3 |

The final version works but does not beat static settings. Patches are retained for evaluation history, not production.

## Kernel boundary and KV cache

Two runs per configuration with `ub256`. Q3_K MoE changes kernels between four and five drafted tokens because the verification batch crosses six tokens.

| Configuration | Chat | Document |
|---|---:|---:|
| MTP2, Q4 target KV | 99.6 | 110.3 |
| MTP4, Q4 target KV | 93.1 | 108.5 |
| MTP5, Q4 target KV | 89.1 | 125.4 |
| MTP6, Q4 target KV | 81.2 | 128.9 |
| MTP4, F16 target KV | 102.4 | 101.9 |
| MTP5, F16 target KV | 93.8 | 108.0 |
| MTP4, F16 target KV + Q4 draft KV | 99.4 | 99.7 |

## F16 KV and pipeline rebalance

Three runs per configuration.

| Configuration | Chat | Document |
|---|---:|---:|
| MTP2, F16 KV, `ub128` | 104.1 | 107.8 |
| MTP2, F16 KV, `ub256` | 104.3 | 111.6 |
| MTP2, F16 target + Q4 draft KV | 102.7 | 107.0 |
| MTP4, F16 KV, `ub128` | 104.2 | 109.6 |
| MTP8, F16 KV, `ub256` | 74.3 | 118.8 |
| MTP8, F16 KV, `ub512` | 74.5 | 144.8 |
| MTP2, Q4 KV, tensor split 15/15/12 | 100.5 | 113.4 |
| MTP4, F16 KV, tensor split 15/15/12 | 103.5 | 109.7 |

The pipeline rebalance did not help.

## Confidence gating and Q8 KV

Three runs per configuration with `ub256` unless noted.

| Configuration | Chat | Document |
|---|---:|---:|
| MTP2, F16 reference | 103.6 | 110.8 |
| MTP3, F16 | **106.3** | 107.9 |
| MTP2, Q8 | 101.9 | 109.1 |
| MTP4, F16, `p_min=0.50` | 84.7 | 111.9 |
| MTP8, Q4, `p_min=0.50` | 81.2 | 137.0 |
| MTP8, Q4, `p_min=0.75` | 84.2 | 88.6 |
| MTP8, Q4, `p_min=0.50`, `ub512` | 81.6 | 140.2 |
| MTP8, F16, `p_min=0.50`, `ub512` | 79.9 | 144.0 |

Confidence gating did not produce a better general configuration. MTP3/F16 became the new chat leader. Best document result remains MTP8/Q4 at 146.1 tok/s.
