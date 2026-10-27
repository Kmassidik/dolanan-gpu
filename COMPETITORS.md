# Challenger benchmark

Same model, same prompts, same hardware, one request at a time. Target model: `heretic-qwen36-35b` Q3_K_M. Box: 3× RTX 3060 Ti 8GB, 125GB host RAM, Ubuntu 24.04.

## Research conclusion

Most alternative engines cannot run this exact model:

| Project | Blocker for this box |
|---|---|
| KTransformers | Requires HF/SGLang-KT weights and an AVX2/AMX-capable CPU. This Xeon has AVX only. |
| LMDeploy / TurboMind | No GGUF loader; needs HF weights plus AWQ/GPTQ. Four-bit weights leave little room for 3-GPU layer split. |
| LightLLM | No practical GGUF route for this MoE model and quantization. |
| MNN-LLM | Mobile/edge focused; no established path for this 35B MoE GGUF on three CUDA cards. |
| PowerInfer | Requires AVX2-class CPU kernels and a different model recipe. |
| ik_llama.cpp | Loads the model in principle, but its IQK CPU backend requires AVX2/FMA. This host has neither; the build fails even after adding the missing SSE2 sigmoid fallback. Not benchmarkable here without changing the host requirements. |
| Upstream llama.cpp HEAD | **Loads the same GGUF, supports native MTP, and builds on this CPU.** Selected as the viable challenger. |

## Builds compared

| Build | Revision | Notes |
|---|---|---|
| Pinned patched llama.cpp | `aa90d0e6389bddf6d68c81761924fe2efec2a545` + `0004`, `0005` | Current project production engine before this benchmark |
| Upstream llama.cpp | `d930fe3c26d97d0c32919ca884723384d27d41dc` | Current upstream HEAD at benchmark time; `0005-selective-kv-tier.patch` applies cleanly and was applied for 250K |

## 64K results: upstream wins

Three runs per configuration. Q4 target and draft KV, `ub256`, MTP depth as listed.

| Configuration | Chat tok/s | Document tok/s |
|---|---:|---:|
| Pinned patched build, MTP3 | 105.8 | 116.4 |
| Upstream, no speculation | 94.4 | 93.6 |
| Upstream, MTP2 | 117.8 | 126.9 |
| **Upstream, MTP3** | **120.2** | **142.7** |
| Upstream, MTP4 | 111.3 | 125.4 |

Upstream is approximately **14% faster for chat** and **23% faster for document reproduction** than the pinned build at the same 64K context.

## 250K results: upstream plus our KV tier wins

Upstream without the selective KV tier OOMed at 256,000 context. Applying the project’s `0005-selective-kv-tier.patch` to upstream allowed the comparison.

| Configuration | Chat tok/s | Document tok/s |
|---|---:|---:|
| Pinned + KV tier, 3 layers | 100.3 | 111.4 |
| Upstream + KV tier, 2 layers | 111.8 | **132.1** |
| Upstream + KV tier, 3 layers | 111.8 | 130.7 |
| Upstream + KV tier, 2 layers, final 3-run check | **113.8** | **132.8** |

A real long-context retrieval test passed on the upstream build:

- Processed prompt: **73,378 tokens**
- Retrieval: correct hidden code `739214`
- Prefill: 1,584 tok/s
- Wall time: 46.9 s

## Decision

Upstream llama.cpp HEAD is the faster engine. The project’s KV tier remains valuable and portable: applying it to upstream gives the best measured 250K configuration.

`scripts/serve.sh upstream-long` now runs upstream with KV layers `3,7` in host RAM at 256,000 context. The earlier `long` mode remains available for the pinned build.

## Fairness notes

- Identical GGUF weights, prompt set, KV type, batch size, GPU count, and single-request concurrency.
- Upstream lacks the project’s phase instrumentation, so only end-to-end decode, prefill, and acceptance are compared.
- The selective KV patch is identical for both 250K runs.
- ik_llama.cpp was not benchmarked because it could not be built on this AVX-only host; the attempted compatibility patch is retained at `patches/ik-sse2-sigmoid-fallback.patch`.
