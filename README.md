# dolanan-gpu

`gpu-optimized`: evidence-first benchmarks and measured serving configurations for llama.cpp GPU inference. Built for a three-RTX-3060 Ti server, with benchmark support for any OpenAI-compatible llama.cpp endpoint.

The tool measures **decode throughput**, **prefill throughput**, **draft acceptance**, and native inference phases. It does not claim that a module is active or an optimization works merely because a flag is present.

## Requirements

- Python 3.10+
- No Python dependencies
- `ssh` on PATH when using `--ssh`

## Production launcher

On the GPU box, start the best measured configuration for the workload:

```bash
export LLAMA_API_KEY='your-key'
./scripts/serve.sh chat      # 64K, MTP3/Q4: general use
./scripts/serve.sh document  # 64K, MTP8/Q4: predictable documents
./scripts/serve.sh long      # 250K, MTP3/Q4 + selective KV tier
```

The long mode keeps KV layers `3,7,11` in host RAM and the rest in VRAM. It measured about 100 chat / 112 document tok/s and passed a 73K-token retrieval test.

The launcher replaces the running `llama-server`. It reads the API key from the environment and does not store it in the repository. See `RESULTS.md`, `CONTEXT.md`, and `PHASES.md` for measurements.

## Benchmark

Direct server:

```bash
python3 -m gpu_optimized bench --url http://127.0.0.1:8081 --runs 3
```

Remote server bound to localhost on the GPU box:

```bash
python3 -m gpu_optimized bench \
  --ssh root@100.122.45.32 \
  --runs 3 \
  --output results/native-mtp.json
```

Compare two configurations measured with identical workloads:

```bash
python3 -m gpu_optimized compare results/stock.json results/candidate.json
```

Long-context retrieval validation:

```bash
python3 -m gpu_optimized.context_check --target-tokens 70000
```

Install the commands if desired:

```bash
python3 -m pip install -e .
gpu-optimized bench --help
gpu-optimized-sweep --help
gpu-context-check --help
```

## Configuration sweeps

Run this on the server itself. A sweep starts each configuration in isolation, waits for readiness, benchmarks both workloads, records failures, and stops the process before trying the next one. A variant may set extra environment variables with its `env` object.

```bash
python3 -m gpu_optimized.sweep \
  --plan plans/mtp-depth.json \
  --replace-existing
```

`--replace-existing` deliberately kills any running `llama-server` first. Omit it when an existing service must remain untouched. Results and per-configuration server logs are written beside the plan's result file. API keys come from `LLAMA_API_KEY` and are never saved in result JSON.

## Method

- `chat`: 128-token open-ended explanation.
- `document`: 256-token reproduction of a repetitive document.
- Reported decode rate: llama.cpp `timings.predicted_per_second`.
- Reported summary: median across runs.
- Acceptance: total accepted draft tokens divided by total proposed draft tokens.
- Native phase fields: `draft_ms`, `target_ms`, `catchup_ms`, and `accept_ms` when the instrumented server provides them.
- Long-context check: hidden-code retrieval with a prompt greater than 65,536 tokens.
- Raw samples are saved so comparisons do not depend on rounded console output.

Prompt processing can use server cache on later runs. Decode rate is therefore the primary comparison metric; prefill and wall-clock rate are retained in the raw samples.

## Scope

This repository contains the measurement and experiment-control layer, measured production launchers, and native llama.cpp patches kept for evaluation. Native changes require profiling and before/after measurements; a new language or flag is not itself an optimization.

## License

MIT
