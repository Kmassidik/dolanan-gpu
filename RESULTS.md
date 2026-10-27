# Measured results

All rates are llama.cpp decode tokens per second on three RTX 3060 Ti cards with `heretic-qwen36-35b` Q3_K_M, 65,536-token context, one request, and two runs per configuration. Raw samples and server logs are local under the ignored `results/` and `plans/*.results.json` paths.

## Draft depth, `ub256`

| Configuration | Chat | Document | Chat acceptance | Document acceptance |
|---|---:|---:|---:|---:|
| No speculation | 80.7 | 81.2 | — | — |
| MTP2 | 99.3 | 111.6 | 76.0% | 88.0% |
| MTP4 | 93.4 | 109.2 | 54.4% | 67.9% |
| MTP8 | 80.6 | 146.1 | 38.2% | 85.1% |
| MTP12 | 66.7 | 131.4 | 25.7% | 61.9% |

Draft depth is workload-dependent: shallow drafting wins chat, while deeper drafting can win predictable document reproduction.

## Execution tuning

| Configuration | Chat | Document |
|---|---:|---:|
| MTP2, `ub128` | **99.8** | **117.3** |
| MTP2, `ub512` | 99.6 | 113.2 |
| MTP2, CPU sampling | 95.1 | 105.6 |
| MTP2, `p_min=0.20` | 98.1 | 111.1 |
| MTP8, `ub128` | 81.1 | 83.8 |
| MTP8, `ub512` | 81.1 | 140.6 |
| MTP8, CPU sampling | 72.7 | 132.9 |
| MTP8, `p_min=0.20` | 77.6 | 122.5 |

Backend sampling is better than CPU sampling here. `p_min=0.20` did not improve either winner. The best static general-purpose configuration so far is MTP2 with `ub128`; MTP8 remains attractive for predictable documents with `ub256` or `ub512`.
