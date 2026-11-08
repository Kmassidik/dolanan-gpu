#!/usr/bin/env bash
# llama-server launcher for the glicc endpoint.
# Engine: latest upstream llama.cpp (engines/llamacpp-latest) — the old build cannot
# load Sage-A1.5's MTP-stripped GGUF (blk.40.attn_norm.weight not found).
set -euo pipefail
cd /root/Desktop/selfhostllm
UB=${UB:-512}
PARALLEL=${PARALLEL:-1}
CTX=${CTX:-262144}
exec /root/Desktop/selfhostllm/engines/llamacpp-latest/build/bin/llama-server \
  -m models/gguf/sage-a15-heretic/Sage-A1.5-Heretic-Abliterated-Uncensored.i1-IQ3_M.gguf \
  -ngl 99 --split-mode layer -ts 1,1,0.9 -ub "$UB" -fa on \
  -ctk q4_0 -ctv q4_0 -c "$CTX" --parallel "$PARALLEL" -t 16 \
  --jinja --chat-template-kwargs '{"enable_thinking":false}' \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.05 \
  --repeat-penalty 1.0 --presence-penalty 0.0 --frequency-penalty 0.0 \
  --dry-multiplier 0.8 --dry-base 1.75 --dry-allowed-length 2 --dry-penalty-last-n 0 \
  --api-key "$(cat glicc-api.token)" -a sage-a15 --host 127.0.0.1 --port 8084
