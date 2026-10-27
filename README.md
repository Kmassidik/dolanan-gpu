# dolanan-gpu

`gpu-optimized`: evidence-first benchmarks for llama.cpp GPU inference. Built for a remote three-RTX-3060 Ti server, usable with any OpenAI-compatible llama.cpp endpoint.

The tool measures **decode throughput**, **prefill throughput**, and **draft acceptance**. It does not claim that a module is active or an optimization works merely because a flag is present.

## Requirements

- Python 3.10+
- No Python dependencies
- `ssh` on PATH when using `--ssh`

## Run

Direct server:

```bash
export LLAMA_API_KEY='your-key'
python3 -m gpu_optimized bench --url http://127.0.0.1:8081 --runs 3
```

Remote server bound to localhost on the GPU box:

```bash
python3 -m gpu_optimized bench \
  --ssh root@100.122.45.32 \
  --runs 3 \
  --output results/native-mtp.json
```

Chat only:

```bash
python3 -m gpu_optimized bench --workload chat --runs 5
```

Compare two configurations measured with identical workloads:

```bash
python3 -m gpu_optimized compare results/stock.json results/candidate.json
```

Install the `gpu-optimized` command if desired:

```bash
python3 -m pip install -e .
gpu-optimized bench --help
```

## Method

- `chat`: 128-token open-ended explanation.
- `document`: 256-token reproduction of a repetitive document.
- Reported decode rate: llama.cpp `timings.predicted_per_second`.
- Reported summary: median across runs.
- Acceptance: total accepted draft tokens divided by total proposed draft tokens.
- Raw samples are saved so comparisons do not depend on rounded console output.

Prompt processing can use server cache on later runs. Decode rate is therefore the primary comparison metric; prefill and wall-clock rate are retained in the raw samples.

## Scope

This is the measurement layer for optimization work. It benchmarks an existing server; it does not restart it, change kernels, or pretend a new language automatically improves inference. Use it to decide which changes deserve deeper engine work.

## License

MIT
