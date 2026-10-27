# dolanan-gpu

`gpu-optimized`: evidence-first benchmarks and measured serving configurations for llama.cpp GPU inference. Built for a three-RTX-3060 Ti server, with benchmark support for any OpenAI-compatible llama.cpp endpoint.

The tool measures **decode throughput**, **prefill throughput**, and **draft acceptance**. It does not claim that a module is active or an optimization works merely because a flag is present.

## Requirements

- Python 3.10+
- No Python dependencies
- `ssh` on PATH when using `--ssh`

## Production launcher

On the GPU box, start the best measured configuration for the workload:

```bash
export LLAMA_API_KEY='your-key'
./scripts/serve.sh chat      # MTP3, Q4 target KV: general use
./scripts/serve.sh document  # MTP8, Q4 target KV: predictable documents
```

The launcher replaces the running `llama-server`. It reads the API key from the environment and does not store it in the repository. See `RESULTS.md` for measurements and alternatives.

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

Install the commands if desired:

```bash
python3 -m pip install -e .
gpu-optimized bench --help
gpu-optimized-sweep --help
```

## Configuration sweeps

Run this on the server itself. A sweep starts each configuration in isolation, waits for readiness, benchmarks both workloads, records failures, and stops the process before trying the next one.

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
- Raw samples are saved so comparisons do not depend on rounded console output.

Prompt processing can use server cache on later runs. Decode rate is therefore the primary comparison metric; prefill and wall-clock rate are retained in the raw samples.

## Scope

This repository contains the measurement and experiment-control layer, measured production launchers, and native llama.cpp patches kept for evaluation. Native changes require profiling and before/after measurements; a new language or flag is not itself an optimization.

## License

MIT
