#!/usr/bin/env bash
# llama-server launcher for the glicc endpoint. UB is the micro-batch: it sets
# prompt-processing throughput. Measured 2026-11-06: ub32 = 515 tok/s, ub256 =
# (see rnd/r33/ub_ladder.log). One process, all three cards, 256k ctx.
set -euo pipefail
cd /root/Desktop/selfhostllm
UB=${UB:-128}
PARALLEL=${PARALLEL:-2}
CTX=${CTX:-256000}
exec /root/Desktop/competitors/llama-upstream/build/bin/llama-server \
  -m models/gguf/qwen38-35b-a3b/Qwen3.8-35B-A3B-Distill.APEX-I-MiniPlus-V2.1-Abliterated.gguf \
  \
  --mmproj models/gguf/qwen38-35b-a3b/mmproj-Q8_0.gguf \
  \
  -md models/gguf/qwen38-35b-a3b/mtp-Qwen3.8-35B-A3B-Distill-Q4_0.gguf \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  -ngl 99 --split-mode layer -ts 1,1,0.9 -ub "$UB" -fa on \
  -ctk q4_0 -ctv q4_0 -ctkd q4_0 -ctvd q4_0 -c "$CTX" --parallel "$PARALLEL" -t 16 \
  --no-mmproj-offload --jinja \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.05 \
  --repeat-penalty 1.0 --presence-penalty 0.0 --frequency-penalty 0.0 \
  --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --dry-penalty-last-n 0 \
  --api-key "$(cat glicc-api.token)" -a qwen3.8-moe --host 127.0.0.1 --port 8084
